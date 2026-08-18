"""学生发展 Agent 的受控编排与本地降级回复。"""

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.student_agent_dao import (
    create_message,
    create_report,
    get_latest_active_session,
    list_messages,
)
from Service.auth_service import AuthPrincipal
from Service.score_analysis_service import build_student_overview
from Model.risk_alert_tables import CounselorAssignment, RiskAlert


URGENT_WORDS = ("自杀", "自残", "伤害自己", "伤害他人", "不想活")
COMFORT_WORDS = ("焦虑", "难过", "压力", "委屈", "害怕", "失眠")


def detect_intent(message: str) -> str:
    if any(word in message for word in URGENT_WORDS):
        return "comfort"
    if any(word in message for word in COMFORT_WORDS):
        return "comfort"
    if any(word in message for word in ("评语", "报告", "总结")):
        return "report"
    if any(word in message for word in ("成绩", "分数", "排名", "均分")):
        return "grade_query"
    if any(word in message for word in ("趋势", "进步", "退步", "分析")):
        return "analysis"
    return "general"


def is_urgent(message: str) -> bool:
    return any(word in message for word in URGENT_WORDS)


def create_risk_alert_for_student(db: Session, student_no: str) -> RiskAlert | None:
    assignment = db.execute(
        select(CounselorAssignment).where(CounselorAssignment.student_no == student_no)
    ).scalar_one_or_none()
    if not assignment:
        return None
    alert = RiskAlert(
        student_no=student_no,
        counselor_staff_no=assignment.counselor_staff_no,
        risk_level="high",
        status="open",
        trigger_summary="检测到紧急心理风险信号，请立即联系学生并按照学校工作流程处理。",
    )
    db.add(alert)
    return alert


def build_fallback_reply(intent: str, overview: dict, *, urgent: bool = False) -> str:
    if urgent:
        return (
            "我很在意你现在的安全。请先不要独自承受，立即联系身边可信的家人、老师或学校心理老师；"
            "如果你正处于紧急危险中，请马上联系当地紧急服务。"
        )
    average = overview["average_score"]
    latest_change = overview["latest_change"]
    if average is None:
        return "目前还没有可分析的成绩记录。先完成下一次阶段考核，再陪你一起复盘。"
    trend = (
        f"最近一次比前一次提高了 {latest_change:.1f} 分"
        if latest_change is not None and latest_change > 0
        else f"当前综合均分是 {average:.1f} 分"
    )
    if intent == "comfort":
        return (
            f"能进步却还感到焦虑，说明你对自己有期待。{trend}，这不是偶然。"
            "先把目标和步骤想清楚；你也先只做一件小事："
            "把最近一次错题整理成 3 个知识点，明天逐个补上。"
        )
    if intent in {"grade_query", "analysis"}:
        return (
            f"你的综合均分为 {average:.1f} 分，班级排名第 {overview['class_rank'] or '-'} 名，{trend}。"
            "先保留有效的复习方法，再把波动较大的考点拆成每天 20 分钟的小任务。"
        )
    return (
        f"学习助手看到你目前的综合均分是 {average:.1f} 分。"
        "学习不必一口气抵达终点；先定下本周一个可完成的小目标。"
    )


def compose_growth_reply(intent: str, message: str, overview: dict) -> str:
    """调用已有百炼客户端生成个性化表达；调用方负责异常降级。"""
    from rag_core.clients.llm_client import LLMClient

    system_prompt = (
        "你是山河大学的学习助手，提供沉稳、具体的学习复盘建议。"
        "先共情，再解释成绩，再给一个不超过三步的行动建议；不得冒充真实人物，"
        "不得诊断心理疾病，不得捏造成绩。"
    )
    user_prompt = (
        f"学生消息：{message}\n意图：{intent}\n"
        f"成绩摘要：均分={overview['average_score']}，班均={overview['class_average']}，"
        f"排名={overview['class_rank']}，近次变化={overview['latest_change']}。"
    )
    return LLMClient().generate_growth_reply(system_prompt, user_prompt)


def chat_with_student(db: Session, principal: AuthPrincipal, message: str) -> dict:
    overview = build_student_overview(db, principal.subject_id)
    session = get_latest_active_session(db, principal.subject_id)
    if not session:
        raise ValueError("学生会话不存在或已过期")
    intent = detect_intent(message)
    urgent = is_urgent(message)
    create_message(
        db,
        session_id=session.id,
        role="user",
        content=message,
        intent=intent,
        risk_level="urgent" if urgent else "normal",
    )
    if urgent:
        create_risk_alert_for_student(db, principal.subject_id)
    fallback_used = True
    use_remote_model = os.getenv("GROWTH_AGENT_USE_LLM", "false").lower() == "true"
    if urgent:
        answer = build_fallback_reply(intent, overview, urgent=True)
    elif use_remote_model:
        try:
            answer = compose_growth_reply(intent, message, overview)
            fallback_used = False
        except Exception:
            answer = build_fallback_reply(intent, overview)
    else:
        answer = build_fallback_reply(intent, overview)
    assistant_message = create_message(
        db,
        session_id=session.id,
        role="assistant",
        content=answer,
        intent=intent,
        source_refs=[],
        risk_level="urgent" if urgent else "normal",
    )
    db.commit()
    return {
        "message_id": assistant_message.id,
        "intent": intent,
        "answer": answer,
        "sources": [],
        "risk_level": "urgent" if urgent else "normal",
        "fallback_used": fallback_used,
    }


def generate_report(db: Session, principal: AuthPrincipal, report_type: str) -> dict:
    overview = build_student_overview(db, principal.subject_id)
    comment = build_fallback_reply("analysis", overview)
    report = create_report(
        db,
        student_no=principal.subject_id,
        report_type=report_type,
        metrics_snapshot=overview,
        attention_level=overview["attention_level"],
        strengths="保持已有的有效学习节奏。",
        improvements="复盘最近一次考核中的错题。",
        action_plan="本周完成三组错题归纳并复测。",
        comment=comment,
        generated_by="fallback",
    )
    db.commit()
    return {
        "id": report.id,
        "comment": report.comment,
        "attention_level": report.attention_level,
        "generated_by": report.generated_by,
    }


def get_student_messages(db: Session, principal: AuthPrincipal, limit: int) -> list[dict]:
    session = get_latest_active_session(db, principal.subject_id)
    if not session:
        return []
    return [
        {
            "id": item.id,
            "role": item.role,
            "intent": item.intent,
            "content": item.content,
            "risk_level": item.risk_level,
            "created_at": item.created_at,
        }
        for item in list_messages(db, session.id, limit)
    ]
