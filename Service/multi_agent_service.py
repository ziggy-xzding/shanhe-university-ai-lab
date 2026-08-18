"""山河智能中枢：主智能体与可插拔子智能体编排。"""

from __future__ import annotations

import json
import os
import pickle
import re
from functools import lru_cache
from pathlib import Path

from Service.auth_service import AuthPrincipal
from Service.agent_tools import execute_agent_tool
from Service.knowledge_base_service import (
    list_uploaded_books,
    search_uploaded_books,
    uploaded_documents,
    vector_search_uploaded_books,
)
from Service.risk_detection_service import create_minimal_risk_alert

ROOT = Path(__file__).resolve().parent.parent
SANGUO_INDEX = ROOT / "data" / "faiss" / "sanguo_chunks.pkl"

SUB_AGENTS = (
    {"key": "academic_assistant", "name": "教务助手", "icon": "bi-journal-bookmark", "hint": "课程、课表、成绩、选课、学分"},
    {"key": "counselor_assistant", "name": "辅导员助手", "icon": "bi-person-heart", "hint": "请假、销假、奖助学金、预警、谈心"},
    {"key": "campus_life", "name": "生活管家", "icon": "bi-buildings", "hint": "宿舍、报修、食堂、活动、一卡通"},
    {"key": "career_advisor", "name": "就业导师", "icon": "bi-briefcase", "hint": "岗位、简历、招聘、实习、面试"},
    {"key": "mental_companion", "name": "心理伙伴", "icon": "bi-heart-pulse", "hint": "情绪、压力、焦虑、失眠、倾诉"},
    {"key": "learning_coach", "name": "学习教练", "icon": "bi-lightbulb", "hint": "学习、复习、作业、考试、教材、图书"},
    {"key": "safety_guardian", "name": "安全卫士", "icon": "bi-shield-check", "hint": "诈骗、转账、验证码、陌生链接、报警"},
)

AGENT_CAPABILITIES = {
    "primary_agent": "负责理解校园问题、协调各子智能体，并回答暂时无法明确分流的综合问题。",
    "academic_assistant": "负责课程、课表、选课、成绩和学业规划。",
    "counselor_assistant": "负责请销假、困难帮扶、学生预警和辅导员事务引导。",
    "campus_life": "负责宿舍、活动、报修、一卡通和校园生活服务。",
    "career_advisor": "负责岗位、简历、实习、面试和职业规划。",
    "mental_companion": "负责情绪陪伴、压力疏导和心理中心等专业支持的转介。",
    "learning_coach": "负责学习计划、复习方法和基于知识库的学习与图书检索。",
    "safety_guardian": "负责反诈识别、风险提醒和校园安全求助指引。",
    "system_feedback": "负责收集系统故障、页面报错和使用问题，并转交系统维护人员。",
}

AGENT_INTENTS = {
    "primary_agent": "general",
    "academic_assistant": "academic",
    "counselor_assistant": "counselor",
    "campus_life": "life",
    "career_advisor": "career",
    "mental_companion": "mental",
    "learning_coach": "learning",
    "safety_guardian": "safety",
    "system_feedback": "feedback",
}

AGENT_DISPLAY_NAMES = {
    "academic_assistant": "教务助手",
    "counselor_assistant": "辅导员助手",
    "campus_life": "生活管家",
    "career_advisor": "就业导师",
    "mental_companion": "心理伙伴",
    "learning_coach": "学习教练",
    "safety_guardian": "安全卫士",
    "system_feedback": "问题反馈子智能体",
    "primary_agent": "山河主智能体",
}

CRISIS_TERMS = ("自杀", "自伤", "不想活", "伤害自己", "想死", "立即结束生命")


def _deepseek_request(agent_type: str, question: str, context: dict | None = None) -> tuple[str, str]:
    capability = AGENT_CAPABILITIES.get(agent_type, AGENT_CAPABILITIES["primary_agent"])
    context_text = json.dumps(context or {}, ensure_ascii=False, default=str)[:12000]
    system = (
        "你是山河大学多智能体系统中的一个专业子智能体。\n"
        f"你的名称和职责：{capability}\n"
        "请直接、温和、具体地回答用户，不要声称已经完成无法完成的操作。"
        "回答开头要自然地让用户知道你是谁以及能提供什么帮助。"
        "涉及心理问题时不要诊断，不要责备；涉及危机时必须建议联系可信任的人、学校心理中心或当地紧急服务。"
        "涉及校园数据时只使用提供的数据，不要编造。"
    )
    prompt = f"用户问题：{question}\n\n可用校园数据或知识库参考：{context_text}"
    return prompt, system


def _deepseek_answer(agent_type: str, question: str, context: dict | None = None) -> dict | None:
    """Generate a natural answer while keeping a deterministic fallback above it."""
    try:
        from Engine.llm_client import get_llm

        prompt, system = _deepseek_request(agent_type, question, context)
        return {"answer": get_llm().generate(prompt, system=system, temperature=0.55, max_tokens=700), "llm_processed": True}
    except Exception:
        return None


def _deepseek_stream(agent_type: str, question: str, context: dict | None = None):
    from Engine.llm_client import get_llm

    prompt, system = _deepseek_request(agent_type, question, context)
    yield from get_llm().stream(prompt, system=system, temperature=0.55, max_tokens=700)


def _with_conversation_history(context: dict | None, conversation_history: list[dict] | None) -> dict:
    """Add a small, sanitized conversation window to an agent context."""
    payload = context or {}
    if not conversation_history:
        return payload
    history = [
        {
            "role": item.get("role", "user"),
            "agent_type": item.get("agent_type"),
            "content": str(item.get("content", ""))[:800],
        }
        for item in conversation_history[-8:]
    ]
    return {"current_data": payload, "conversation_history": history}


def _conversation_turn_count(conversation_history: list[dict] | None) -> int:
    """Count completed user turns, not the user/assistant message rows behind them."""
    return sum(1 for item in (conversation_history or []) if item.get("role") == "user")


@lru_cache(maxsize=1)
def _sanguo_documents() -> tuple[dict, ...]:
    if not SANGUO_INDEX.exists():
        return ()
    try:
        with SANGUO_INDEX.open("rb") as handle:
            payload = pickle.load(handle)
        documents = payload.get("documents", [])
        metadata = payload.get("metadatas", [])
        return tuple({"content": text, **(metadata[index] if index < len(metadata) else {})} for index, text in enumerate(documents))
    except Exception:
        return ()


def _book_name_from_file(path: Path) -> str:
    return path.stem.replace("_", " ")


def _uploaded_books() -> list[dict]:
    return list_uploaded_books()


def _read_uploaded_text(path: Path) -> str:
    try:
        if path.suffix.lower() == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        if path.suffix.lower() == ".docx":
            from docx import Document
            return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    except Exception:
        return ""
    return ""


def _uploaded_documents() -> list[dict]:
    return uploaded_documents()


def list_knowledge_books() -> list[dict]:
    books = [{"book_name": "三国演义", "status": "ready", "source": "内置演示知识库", "chunks": len(_sanguo_documents())}]
    books.extend(_uploaded_books())
    return books


def _local_sanguo_search(question: str, limit: int = 3) -> list[dict]:
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", question.lower()))
    query_terms = {chinese[index:index + 2] for index in range(max(0, len(chinese) - 1))}
    query_terms.update(term for term in re.findall(r"[A-Za-z0-9]+", question.lower()))
    scored = []
    for index, item in enumerate(_sanguo_documents()):
        content = item.get("content", "")
        score = sum(content.lower().count(term) for term in query_terms)
        score += sum(5 for term in ("桃园", "结义", "刘备", "关羽", "张飞", "曹操", "赤壁") if term in question and term in content)
        if score:
            first_line = content.splitlines()[0].strip() if content else ""
            chapter = first_line if re.match(r"第[一二三四五六七八九十百]+回", first_line) else f"第 {index + 1} 节"
            scored.append((score, {"book_name": "三国演义", "chapter": chapter, "content": content[:420], "score": round(min(.99, score / 10), 3)}))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def _uploaded_book_search(question: str, limit: int = 3) -> list[dict]:
    return search_uploaded_books(question, limit)


def _vector_sanguo_search(question: str, limit: int = 3) -> list[dict]:
    """Search the FAISS index with the configured Ollama embedding model."""
    try:
        from Engine.embedding_client import get_embedding
        from Engine.milvus_client import COLLECTIONS, get_milvus

        store = get_milvus()
        collection = COLLECTIONS["sanguo"]
        if not store.has_collection(collection):
            return []
        hits = store.search(collection, get_embedding().encode(question), top_k=limit)
        return [
            {
                "book_name": item.get("book_name") or "三国演义",
                "chapter": item.get("chapter") or f"第 {item.get('chunk_index', index) + 1} 节",
                "content": item.get("text", "")[:420],
                "score": item.get("score", 0),
            }
            for index, item in enumerate(hits)
        ]
    except Exception:
        return []


def _knowledge_answer(question: str, conversation_history: list[dict] | None = None) -> dict:
    sources = _vector_sanguo_search(question) + _local_sanguo_search(question) + vector_search_uploaded_books(question) + _uploaded_book_search(question)
    sources = sorted(sources, key=lambda item: item.get("score", 0), reverse=True)[:3]
    if sources:
        generated = _deepseek_answer("learning_coach", question, _with_conversation_history({"retrieved_sources": sources}, conversation_history))
        if generated:
            return {**generated, "sources": sources}
        source_text = "、".join(dict.fromkeys(item["book_name"] for item in sources))
        excerpts = "\n".join(f"{item['chapter']}：{item['content'][:180]}" for item in sources)
        return {"answer": f"学习教练暂时无法调用 DeepSeek。当前检索到《{source_text}》相关内容：\n{excerpts}", "sources": sources, "llm_processed": False}
    return {"answer": "暂未在《三国演义》知识库中检索到足够依据，请换一个更具体的问法。", "sources": [], "llm_processed": False}


def _heuristic_intent(message: str) -> str:
    if any(word in message for word in ("自杀", "自伤", "不想活", "伤害自己", "危机", "崩溃", "想死", "提不起劲", "没精神", "心情不好", "情绪低落", "心里很乱", "想聊聊", "难受", "焦虑", "压力大", "压力很大", "烦躁", "孤独", "失眠", "睡不着")):
        return "mental"
    if any(word in message for word in ("诈骗", "转账", "被骗", "验证码", "陌生链接", "刷单", "冒充", "紧急", "报警", "威胁", "危险")):
        return "safety"
    if any(word in message for word in ("简历", "招聘", "岗位", "就业", "找工作", "实习", "面试", "职业", "职业规划", "换个方向", "发展方向", "职业方向", "未来规划", "未来发展", "想做什么", "转行")):
        return "career"
    if any(word in message for word in ("请假", "销假", "谈心", "辅导员", "预警", "困难生", "困难补助", "奖学金", "助学金")):
        return "counselor"
    if any(word in message for word in ("宿舍", "寝室", "活动", "报修", "一卡通", "食堂", "场馆", "校园生活")):
        return "life"
    if any(word in message for word in ("系统", "打不开", "报错", "故障", "bug", "反馈", "登录不了")):
        return "feedback"
    if any(word in message for word in ("学习", "复习", "作业", "知识点", "计划", "怎么学", "考试", "三国", "桃园", "刘备", "关羽", "张飞", "曹操", "赤壁", "书中", "原著", "课本", "教材", "图书", "图书馆书籍")):
        return "learning"
    if any(word in message for word in ("课程", "课表", "成绩", "分数", "选课", "教学班", "学分", "课程安排")):
        return "academic"
    return "unknown"


_ROUTER_INTENTS = ("mental", "safety", "career", "counselor", "life", "feedback", "learning", "academic", "general")


def _llm_intent(message: str, conversation_history: list[dict] | None = None) -> dict | None:
    """Use DeepSeek for semantic routing and return a normalized route decision."""
    mode = os.getenv("AGENT_ROUTER_ENABLED", "auto").strip().lower()
    if mode in {"0", "false", "off", "no"}:
        return None
    # The project uses DeepSeek for both answers and semantic routing. Keep
    # compatibility with the older Aliyun names for deployments that still use them.
    llm_configured = any(
        os.getenv(name)
        for name in ("DEEPSEEK_API_KEY", "LLM_API_KEY", "DASHSCOPE_API_KEY", "ALIYUN_API_KEY")
    )
    if mode == "auto" and not llm_configured:
        return None
    try:
        from Engine.llm_client import get_llm

        history_text = ""
        if conversation_history:
            history_text = "\nRecent conversation context:\n" + "\n".join(
                f"{item.get('role', 'user')}: {str(item.get('content', ''))[:400]}"
                for item in conversation_history[-6:]
            )
        raw = get_llm().generate(
            "Classify this campus request and return JSON only. "
            "mental means emotional distress, low mood, anxiety, pressure, loneliness, or wanting to talk; "
            "safety means fraud, danger, emergency, or reporting; "
            "career means jobs, future direction, career planning, resumes, internships, or interviews; "
            "academic means courses, schedules, enrollment, credits, or grades; "
            "learning means studying, reviewing, homework, exams, textbooks, or books; "
            "feedback means a software/system fault; "
            "general means a greeting, a broad campus question, or a request that does not clearly belong to one sub-agent; "
            f"Labels: {', '.join(_ROUTER_INTENTS)}. "
            'Use this shape: {"intents":[{"intent":"academic","confidence":0.0}],"primary_intent":"academic"}. '
            "Return up to three intents when the request contains independent tasks for different specialists. "
            "Request: " + message + history_text,
            system="You are the routing layer of a university multi-agent assistant.",
            temperature=0,
            max_tokens=120,
        ).strip()
        parsed = {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            try:
                parsed = json.loads(match.group(0)) if match else {}
            except (TypeError, ValueError):
                parsed = {}
        raw_items = parsed.get("intents") if isinstance(parsed.get("intents"), list) else []
        if not raw_items and parsed.get("intent"):
            raw_items = [{"intent": parsed.get("intent"), "confidence": parsed.get("confidence", 0.78)}]
        intents = []
        for item in raw_items:
            if isinstance(item, str):
                item = {"intent": item, "confidence": 0.78}
            intent = str(item.get("intent", "")).strip().lower()
            if intent not in _ROUTER_INTENTS or any(existing["intent"] == intent for existing in intents):
                continue
            try:
                confidence = float(item.get("confidence", 0.78))
            except (TypeError, ValueError):
                confidence = 0.78
            intents.append({"intent": intent, "confidence": max(0.0, min(1.0, confidence))})
        if not intents:
            match = re.search(r"\b(" + "|".join(_ROUTER_INTENTS) + r")\b", raw.lower())
            if match:
                intents = [{"intent": match.group(1), "confidence": 0.78}]
        if not intents:
            return None
        primary = str(parsed.get("primary_intent", "")).strip().lower()
        if primary not in {item["intent"] for item in intents}:
            primary = intents[0]["intent"]
        primary_item = next(item for item in intents if item["intent"] == primary)
        return {"intent": primary, "confidence": primary_item["confidence"], "source": "llm", "intents": intents[:3]}
    except Exception:
        return None


def _route_message(message: str, forced_agent_type: str | None = None, conversation_history: list[dict] | None = None) -> dict:
    """Route with safety guardrails, explicit selection, semantic routing, then keywords."""
    heuristic = _heuristic_intent(message)
    # Crisis and safety signals always bypass model routing.
    if heuristic == "safety" or any(term in message for term in CRISIS_TERMS):
        return {"intent": heuristic if heuristic != "unknown" else "mental", "confidence": 1.0, "source": "safety_guardrail"}
    if forced_agent_type:
        intent = AGENT_INTENTS.get(forced_agent_type)
        if intent:
            return {"intent": intent, "confidence": 1.0, "source": "manual", "agent_type": forced_agent_type}
    llm_intent = _llm_intent(message, conversation_history)
    if llm_intent:
        return llm_intent
    if heuristic != "unknown":
        return {"intent": heuristic, "confidence": 0.68, "source": "keyword_fallback"}
    if conversation_history and len(message.strip()) <= 24:
        for item in reversed(conversation_history):
            agent_type = item.get("agent_type")
            intent = AGENT_INTENTS.get(agent_type)
            if item.get("role") == "assistant" and intent:
                return {"intent": intent, "confidence": 0.55, "source": "history_fallback", "agent_type": agent_type}
    return {"intent": "general", "confidence": 0.35, "source": "default"}


def _intent(message: str) -> str:
    return _route_message(message)["intent"]


def _multi_intent_specs(route: dict) -> list[dict]:
    """Convert the router protocol into bounded, callable specialist tasks."""
    agent_by_intent = {intent: agent for agent, intent in AGENT_INTENTS.items() if agent != "primary_agent"}
    items = route.get("intents") or [{"intent": route.get("intent"), "confidence": route.get("confidence", 0)}]
    specs = []
    for item in items:
        intent = item.get("intent")
        agent_type = agent_by_intent.get(intent)
        if not agent_type or any(spec["intent"] == intent for spec in specs):
            continue
        specs.append({"intent": intent, "agent_type": agent_type, "confidence": item.get("confidence", 0)})
    return specs[:3]


def _dispatch_multi_intent(db, principal: AuthPrincipal, message: str, route: dict, conversation_history: list[dict] | None) -> dict:
    specs = _multi_intent_specs(route)
    subtasks = []
    for index, spec in enumerate(specs, start=1):
        result = dispatch_message(db, principal, message, spec["agent_type"], conversation_history)
        subtasks.append({
            "task_id": f"task-{index}",
            "intent": spec["intent"],
            "agent_type": spec["agent_type"],
            "confidence": spec["confidence"],
            "status": "completed",
            "answer": result["answer"],
            "data": result.get("data", {}),
            "sources": result.get("sources", []),
            "tool_calls": result.get("tool_calls", []),
            "risk_level": result.get("risk_level", "normal"),
            "risk_alert_created": result.get("risk_alert_created", False),
        })
    synthesis_context = {
        "task_results": [
            {"task_id": item["task_id"], "agent_type": item["agent_type"], "answer": item["answer"][:1600], "data": item["data"]}
            for item in subtasks
        ],
        "conversation_history": conversation_history or [],
    }
    synthesized = _deepseek_answer("primary_agent", message, synthesis_context)
    if synthesized:
        answer = synthesized["answer"]
        llm_processed = True
    else:
        answer = "\n\n".join(f"【{item['agent_type']}】\n{item['answer']}" for item in subtasks)
        llm_processed = False
    sources = [source for item in subtasks for source in item["sources"]]
    tool_calls = [{"tool_name": "primary.decompose_request", "name": "拆解多事项", "status": "completed", "summary": f"已拆解 {len(subtasks)} 个子任务"}]
    tool_calls.extend(tool for item in subtasks for tool in item["tool_calls"])
    agent_trace = [{"agent_type": "primary_agent", "name": AGENT_DISPLAY_NAMES["primary_agent"], "status": "routed", "action": "识别多个独立事项并拆解任务"}]
    agent_trace.extend({"agent_type": item["agent_type"], "name": AGENT_DISPLAY_NAMES[item["agent_type"]], "status": "completed", "action": "完成子任务"} for item in subtasks)
    return {
        "answer": answer,
        "primary_agent": AGENT_DISPLAY_NAMES["primary_agent"],
        "agent_type": "primary_agent",
        "sub_agents": [{"name": AGENT_DISPLAY_NAMES[item["agent_type"]], "agent_type": item["agent_type"], "status": item["status"], "sources": item["sources"]} for item in subtasks],
        "sub_tasks": subtasks,
        "agent_trace": agent_trace,
        "routing": {**route, "strategy": "multi_intent_decomposition"},
        "tool_calls": tool_calls,
        "memory_turns": _conversation_turn_count(conversation_history),
        "sources": sources[:6],
        "data": {"sub_tasks": subtasks},
        "intent": "multi_intent",
        "risk_level": "high" if any(item.get("risk_level") == "high" for item in subtasks) else "normal",
        "risk_alert_created": any(item.get("risk_alert_created", False) for item in subtasks),
        "llm_processed": llm_processed or route.get("source") == "llm",
        "knowledge_books": list_knowledge_books(),
    }


def dispatch_message(db, principal: AuthPrincipal, message: str, forced_agent_type: str | None = None, conversation_history: list[dict] | None = None) -> dict:
    route = _route_message(message, forced_agent_type, conversation_history)
    if not forced_agent_type and len(_multi_intent_specs(route)) > 1:
        return _dispatch_multi_intent(db, principal, message, route, conversation_history)
    key = route["intent"]
    routed_by_llm = route["source"] == "llm"
    risk_level = "normal"
    tool_calls: list[dict] = []
    llm_context = lambda data: _with_conversation_history(data, conversation_history)
    if key == "learning" and any(word in message for word in ("三国", "桃园", "刘备", "关羽", "张飞", "曹操", "赤壁", "书中", "原著", "教材", "图书")):
        result = _knowledge_answer(message, conversation_history)
        tool_calls.append({"tool_name": "learning.knowledge_search", "name": "检索知识库", "status": "completed", "summary": f"已检索到 {len(result.get('sources', []))} 条相关资料"})
        agent_name, agent_type = "学习教练", "learning_coach"
    elif key == "academic":
        tool_result = execute_agent_tool("academic.query_student_data", db, principal, message)
        tool_calls.append(tool_result)
        campus_result = tool_result.get("data", {})
        result = _deepseek_answer("academic_assistant", message, llm_context(campus_result.get("data", {})))
        if not result:
            result = {"answer": "我是教务助手，主要负责课程、课表、选课、成绩和学业规划。" + campus_result.get("answer", "请告诉我具体课程或学业问题。"), "llm_processed": False}
        result["data"] = campus_result.get("data", {})
        result["sources"] = []
        agent_name, agent_type = "教务助手", "academic_assistant"
    elif key == "learning":
        result = _deepseek_answer("learning_coach", message, llm_context({}))
        if not result:
            result = {"answer": "我是学习教练，主要帮助你制定学习计划、复习课程和整理知识点。请告诉我课程名称、考试内容或考试日期。", "sources": [], "llm_processed": False}
        agent_name, agent_type = "学习教练", "learning_coach"
    elif key == "mental":
        crisis = any(term in message for term in CRISIS_TERMS)
        if crisis:
            risk_level = "high"
            result_alert = create_minimal_risk_alert(db, principal.subject_id) if principal.role == "student" else False
            result = {"answer": "我是心理伙伴，主要提供情绪陪伴和心理支持转介。你刚才提到的内容可能涉及紧急风险，请先联系身边可信任的人、山河大学心理中心或当地紧急服务，不要独自承受。", "sources": [], "llm_processed": False}
            result["risk_alert_created"] = result_alert
        else:
            result = _deepseek_answer("mental_companion", message, llm_context({}))
            if not result:
                result = {"answer": "我是心理伙伴，主要提供情绪陪伴和压力疏导。你可以慢慢说说最近发生了什么，我会先听你说，也可以一起整理下一步能做的小事。", "sources": [], "llm_processed": False}
        agent_name, agent_type = "心理伙伴", "mental_companion"
    elif key == "safety":
        result = _deepseek_answer("safety_guardian", message, llm_context({}))
        if not result:
            result = {"answer": "我是安全卫士，主要帮助识别诈骗和处理紧急安全问题。请先暂停转账、不要点击陌生链接，保留聊天与支付凭证，并联系学校保卫处或当地反诈服务。", "sources": [], "llm_processed": False}
        agent_name, agent_type = "安全卫士", "safety_guardian"
    elif key == "career":
        tool_result = execute_agent_tool("career.list_opportunities", db, principal, message)
        tool_calls.append(tool_result)
        data = tool_result.get("data", {})
        result = _deepseek_answer("career_advisor", message, llm_context(data)) or {"answer": "我是就业导师，主要帮助你筛选岗位、优化简历、准备面试和规划职业方向。", "llm_processed": False}
        result["data"] = data
        result["sources"] = []
        agent_name, agent_type = "就业导师", "career_advisor"
    elif key == "counselor":
        tool_result = execute_agent_tool("counselor.count_open_alerts", db, principal, message)
        tool_calls.append(tool_result)
        data = tool_result.get("data", {})
        result = _deepseek_answer("counselor_assistant", message, llm_context(data)) or {"answer": "我是辅导员助手，主要协助请销假、困难帮扶、学生预警和事务办理。请告诉我具体事项，我会为你整理下一步。", "llm_processed": False}
        result["data"] = data
        result["sources"] = []
        agent_name, agent_type = "辅导员助手", "counselor_assistant"
    elif key == "life":
        tool_result = execute_agent_tool("campus_life.list_activities", db, principal, message)
        tool_calls.append(tool_result)
        data = tool_result.get("data", {})
        result = _deepseek_answer("campus_life", message, llm_context(data)) or {"answer": "我是生活管家，主要负责宿舍、活动、报修、一卡通和校园生活服务。请告诉我你想办理或查询的事项。", "llm_processed": False}
        result["data"] = data
        result["sources"] = []
        agent_name, agent_type = "生活管家", "campus_life"
    elif key == "feedback":
        result = _deepseek_answer("system_feedback", message, llm_context({})) or {"answer": "我是问题反馈子智能体，主要负责收集系统故障、页面报错和使用问题。请补充发生页面、操作步骤和报错信息，我会整理后转交系统维护人员。", "sources": [], "llm_processed": False}
        agent_name, agent_type = "问题反馈子智能体", "system_feedback"
    else:
        result = _deepseek_answer("primary_agent", message, llm_context({}))
        if not result:
            result = {"answer": "我是山河主智能体，主要负责理解校园问题、协调教务、辅导员、生活、就业、心理、学习和安全子智能体。你可以直接描述想解决的事情，我会自动判断是否需要转交。", "sources": [], "llm_processed": False}
        agent_name, agent_type = "山河主智能体", "primary_agent"
    agent_trace = [{
        "agent_type": "primary_agent",
        "name": AGENT_DISPLAY_NAMES["primary_agent"],
        "status": "routed" if agent_type != "primary_agent" else "completed",
        "action": "理解问题并匹配专业智能体" if agent_type != "primary_agent" else "直接回答综合问题",
    }]
    if agent_type != "primary_agent":
        agent_trace.append({
            "agent_type": agent_type,
            "name": agent_name,
            "status": "completed",
            "action": "生成专业回答",
        })
    return {
        "answer": result["answer"],
        "primary_agent": "山河主智能体",
        "agent_type": agent_type,
        "sub_agents": [{"name": agent_name, "agent_type": agent_type, "status": "completed", "sources": result.get("sources", [])}],
        "agent_trace": agent_trace,
        "routing": route,
        "tool_calls": tool_calls,
        "memory_turns": _conversation_turn_count(conversation_history),
        "sources": result.get("sources", []),
        "data": result.get("data", {}),
        "intent": key,
        "risk_level": risk_level,
        "risk_alert_created": bool(result.get("risk_alert_created", False)),
        "llm_processed": bool(result.get("llm_processed", False) or routed_by_llm),
        "knowledge_books": list_knowledge_books(),
    }


def _stream_text(text: str, chunk_size: int = 24):
    for index in range(0, len(text), chunk_size):
        yield text[index:index + chunk_size]


def _stream_multi_intent(db, principal: AuthPrincipal, message: str, route: dict, conversation_history: list[dict] | None):
    specs = _multi_intent_specs(route)
    subtasks = []
    for index, spec in enumerate(specs, start=1):
        result = dispatch_message(db, principal, message, spec["agent_type"], conversation_history)
        subtasks.append({
            "task_id": f"task-{index}",
            "intent": spec["intent"],
            "agent_type": spec["agent_type"],
            "confidence": spec["confidence"],
            "status": "completed",
            "answer": result["answer"],
            "data": result.get("data", {}),
            "sources": result.get("sources", []),
            "tool_calls": result.get("tool_calls", []),
            "risk_level": result.get("risk_level", "normal"),
            "risk_alert_created": result.get("risk_alert_created", False),
        })
    synthesis_context = {
        "task_results": [
            {"task_id": item["task_id"], "agent_type": item["agent_type"], "answer": item["answer"][:1600], "data": item["data"]}
            for item in subtasks
        ],
        "conversation_history": conversation_history or [],
    }
    sources = [source for item in subtasks for source in item["sources"]]
    tool_calls = [{"tool_name": "primary.decompose_request", "name": "拆解多事项", "status": "completed", "summary": f"已拆解 {len(subtasks)} 个子任务"}]
    tool_calls.extend(tool for item in subtasks for tool in item["tool_calls"])
    trace = [{"agent_type": "primary_agent", "name": AGENT_DISPLAY_NAMES["primary_agent"], "status": "routed", "action": "识别多个独立事项并拆解任务"}]
    trace.extend({"agent_type": item["agent_type"], "name": AGENT_DISPLAY_NAMES[item["agent_type"]], "status": "completed", "action": "完成子任务"} for item in subtasks)
    meta = {
        "agent_name": AGENT_DISPLAY_NAMES["primary_agent"],
        "agent_type": "primary_agent",
        "intent": "multi_intent",
        "risk_level": "high" if any(item["risk_level"] == "high" for item in subtasks) else "normal",
        "sources": sources[:6],
        "data": {"sub_tasks": subtasks},
        "routed_by_llm": route.get("source") == "llm",
        "routing": {**route, "strategy": "multi_intent_decomposition"},
        "agent_trace": trace,
        "tool_calls": tool_calls,
        "sub_tasks": subtasks,
        "memory_turns": _conversation_turn_count(conversation_history),
    }
    yield {"event": "meta", "data": meta}
    answer_parts = []
    try:
        for token in _deepseek_stream("primary_agent", message, synthesis_context):
            answer_parts.append(token)
            yield {"event": "token", "data": {"text": token}}
    except Exception:
        pass
    if not answer_parts:
        fallback = "\n\n".join(f"【{item['agent_type']}】\n{item['answer']}" for item in subtasks)
        for token in _stream_text(fallback):
            answer_parts.append(token)
            yield {"event": "token", "data": {"text": token}}
    yield {"event": "done", "data": {
        **meta,
        "answer": "".join(answer_parts),
        "primary_agent": AGENT_DISPLAY_NAMES["primary_agent"],
        "sub_agents": [{"name": AGENT_DISPLAY_NAMES[item["agent_type"]], "agent_type": item["agent_type"], "status": "completed", "sources": item["sources"]} for item in subtasks],
        "agent_trace": trace,
        "risk_alert_created": any(item["risk_alert_created"] for item in subtasks),
        "llm_processed": bool(answer_parts) or route.get("source") == "llm",
        "knowledge_books": list_knowledge_books(),
    }}


def stream_dispatch_message(db, principal: AuthPrincipal, message: str, forced_agent_type: str | None = None, conversation_history: list[dict] | None = None):
    """Yield orchestration status, metadata, answer tokens, and a final result."""
    yield {"event": "status", "data": {"message": "正在识别问题并匹配专业智能体…"}}
    route = _route_message(message, forced_agent_type, conversation_history)
    if not forced_agent_type and len(_multi_intent_specs(route)) > 1:
        yield from _stream_multi_intent(db, principal, message, route, conversation_history)
        return
    key = route["intent"]
    routed_by_llm = route["source"] == "llm"
    risk_level = "normal"
    sources: list[dict] = []
    data: dict = {}
    tool_calls: list[dict] = []
    fallback = ""
    stream_agent: str | None = None
    allow_llm = True
    llm_context = lambda current_data: _with_conversation_history(current_data, conversation_history)

    if key == "learning" and any(word in message for word in ("三国", "桃园", "刘备", "关羽", "张飞", "曹操", "赤壁", "书中", "原著", "教材", "图书")):
        sources = _vector_sanguo_search(message) + _local_sanguo_search(message) + vector_search_uploaded_books(message) + _uploaded_book_search(message)
        sources = sorted(sources, key=lambda item: item.get("score", 0), reverse=True)[:3]
        tool_calls.append({"tool_name": "learning.knowledge_search", "name": "检索知识库", "status": "completed", "summary": f"已检索到 {len(sources)} 条相关资料"})
        stream_agent = "learning_coach"
        if sources:
            fallback = "学习教练暂时无法调用 DeepSeek，当前检索到相关书籍内容：\n" + "\n".join(
                f"{item['chapter']}：{item['content'][:180]}" for item in sources
            )
            data = {"retrieved_sources": sources}
        else:
            fallback = "暂未在知识库中检索到足够依据，请换一个更具体的问法。"
            allow_llm = False
    elif key == "academic":
        tool_result = execute_agent_tool("academic.query_student_data", db, principal, message)
        tool_calls.append(tool_result)
        campus_result = tool_result.get("data", {})
        data = campus_result.get("data", {})
        fallback = "我是教务助手，主要负责课程、课表、选课、成绩和学业规划。" + campus_result.get("answer", "请告诉我具体课程或学业问题。")
        stream_agent = "academic_assistant"
    elif key == "learning":
        fallback = "我是学习教练，主要帮助你制定学习计划、复习课程和整理知识点。请告诉我课程名称、考试内容或考试日期。"
        stream_agent = "learning_coach"
    elif key == "mental":
        stream_agent = "mental_companion"
        if any(term in message for term in CRISIS_TERMS):
            risk_level = "high"
            risk_alert_created = create_minimal_risk_alert(db, principal.subject_id) if principal.role == "student" else False
            fallback = "我是心理伙伴，主要提供情绪陪伴和心理支持转介。你刚才提到的内容可能涉及紧急风险，请先联系身边可信任的人、山河大学心理中心或当地紧急服务，不要独自承受。"
            data = {"risk_alert_created": risk_alert_created}
            allow_llm = False
        else:
            fallback = "我是心理伙伴，主要提供情绪陪伴和压力疏导。你可以慢慢说说最近发生了什么，我会先听你说，也可以一起整理下一步能做的小事。"
    elif key == "safety":
        fallback = "我是安全卫士，主要帮助识别诈骗和处理紧急安全问题。请先暂停转账、不要点击陌生链接，保留聊天与支付凭证，并联系学校保卫处或当地反诈服务。"
        stream_agent = "safety_guardian"
    elif key == "career":
        tool_result = execute_agent_tool("career.list_opportunities", db, principal, message)
        tool_calls.append(tool_result)
        data = tool_result.get("data", {})
        fallback = "我是就业导师，主要帮助你筛选岗位、优化简历、准备面试和规划职业方向。"
        stream_agent = "career_advisor"
    elif key == "counselor":
        tool_result = execute_agent_tool("counselor.count_open_alerts", db, principal, message)
        tool_calls.append(tool_result)
        data = tool_result.get("data", {})
        fallback = "我是辅导员助手，主要协助请销假、困难帮扶、学生预警和事务办理。请告诉我具体事项，我会为你整理下一步。"
        stream_agent = "counselor_assistant"
    elif key == "life":
        tool_result = execute_agent_tool("campus_life.list_activities", db, principal, message)
        tool_calls.append(tool_result)
        data = tool_result.get("data", {})
        fallback = "我是生活管家，主要负责宿舍、活动、报修、一卡通和校园生活服务。请告诉我你想办理或查询的事项。"
        stream_agent = "campus_life"
    elif key == "feedback":
        fallback = "我是问题反馈子智能体，主要负责收集系统故障、页面报错和使用问题。请补充发生页面、操作步骤和报错信息，我会整理后转交系统维护人员。"
        stream_agent = "system_feedback"
    else:
        fallback = "我是山河主智能体，主要负责理解校园问题、协调教务、辅导员、生活、就业、心理、学习和安全子智能体。你可以直接描述想解决的事情，我会自动判断是否需要转交。"
        stream_agent = "primary_agent"

    agent_name = AGENT_DISPLAY_NAMES[stream_agent]
    agent_trace = [{
        "agent_type": "primary_agent",
        "name": AGENT_DISPLAY_NAMES["primary_agent"],
        "status": "routed" if stream_agent != "primary_agent" else "completed",
        "action": "理解问题并匹配专业智能体" if stream_agent != "primary_agent" else "直接回答综合问题",
    }]
    if stream_agent != "primary_agent":
        agent_trace.append({"agent_type": stream_agent, "name": agent_name, "status": "working", "action": "生成专业回答"})
    meta = {
        "agent_name": agent_name,
        "agent_type": stream_agent,
        "intent": key,
        "risk_level": risk_level,
        "sources": sources,
        "data": data,
        "routed_by_llm": routed_by_llm,
        "routing": route,
        "agent_trace": agent_trace,
        "tool_calls": tool_calls,
        "memory_turns": _conversation_turn_count(conversation_history),
    }
    yield {"event": "meta", "data": meta}

    answer_parts: list[str] = []
    used_llm = False
    if allow_llm:
        try:
            for token in _deepseek_stream(stream_agent, message, llm_context(data)):
                answer_parts.append(token)
                yield {"event": "token", "data": {"text": token}}
            used_llm = bool(answer_parts)
        except Exception:
            pass
    if not answer_parts:
        for token in _stream_text(fallback):
            answer_parts.append(token)
            yield {"event": "token", "data": {"text": token}}

    answer = "".join(answer_parts)
    result = {
        **meta,
        "answer": answer,
        "primary_agent": "山河主智能体",
        "sub_agents": [{"name": agent_name, "agent_type": stream_agent, "status": "completed", "sources": sources}],
        "agent_trace": [
            *agent_trace[:-1],
            {**agent_trace[-1], "status": "completed"},
        ],
        "routing": route,
        "tool_calls": tool_calls,
        "memory_turns": _conversation_turn_count(conversation_history),
        "risk_alert_created": bool(data.get("risk_alert_created", False)),
        "llm_processed": bool(used_llm or routed_by_llm),
        "knowledge_books": list_knowledge_books(),
    }
    yield {"event": "done", "data": result}
