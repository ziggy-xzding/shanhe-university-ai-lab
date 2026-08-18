"""Business tools exposed to campus sub-agents.

The model chooses a specialist, while this module owns the actual database
queries and returns auditable tool results. Mutating tools can be added here
later with an explicit confirmation requirement.
"""

from __future__ import annotations

from sqlalchemy import func, select

from Model.platform_tables import CampusActivity, CareerOpportunity
from Model.risk_alert_tables import RiskAlert
from Service.auth_service import AuthPrincipal
from Service.campus_assistant_service import answer_campus_query


TOOL_DEFINITIONS = {
    "academic.query_student_data": {
        "agent_type": "academic_assistant",
        "name": "查询教务数据",
        "description": "查询当前用户有权限访问的课程、课表、成绩、选课和学分信息。",
        "read_only": True,
    },
    "career.list_opportunities": {
        "agent_type": "career_advisor",
        "name": "查询就业岗位",
        "description": "查询当前已发布的岗位、实习和招聘信息。",
        "read_only": True,
    },
    "counselor.count_open_alerts": {
        "agent_type": "counselor_assistant",
        "name": "查询预警概况",
        "description": "查询当前系统中的开放学生预警数量。",
        "read_only": True,
    },
    "campus_life.list_activities": {
        "agent_type": "campus_life",
        "name": "查询校园活动",
        "description": "查询近期已发布的校园活动。",
        "read_only": True,
    },
}


def list_tools_for_agents() -> dict[str, list[dict]]:
    """Return display-safe tool descriptions grouped by specialist."""
    grouped: dict[str, list[dict]] = {}
    for tool_name, definition in TOOL_DEFINITIONS.items():
        grouped.setdefault(definition["agent_type"], []).append(
            {"key": tool_name, "name": definition["name"], "description": definition["description"], "read_only": definition["read_only"]}
        )
    return grouped


def _tool_trace(tool_name: str, status: str, summary: str, data: dict | None = None) -> dict:
    definition = TOOL_DEFINITIONS[tool_name]
    result = {
        "tool_name": tool_name,
        "name": definition["name"],
        "status": status,
        "summary": summary,
    }
    if data is not None:
        result["data"] = data
    return result


def execute_agent_tool(tool_name: str, db, principal: AuthPrincipal, message: str) -> dict:
    """Execute one read-only tool and return data plus an audit trace."""
    definition = TOOL_DEFINITIONS.get(tool_name)
    if definition is None:
        raise ValueError(f"Unknown agent tool: {tool_name}")
    try:
        if tool_name == "academic.query_student_data":
            data = answer_campus_query(db, principal, message)
            return _tool_trace(tool_name, "completed", "已查询当前用户可访问的教务数据", data)
        if tool_name == "career.list_opportunities":
            jobs = db.execute(
                select(CareerOpportunity)
                .where(CareerOpportunity.status == "published")
                .order_by(CareerOpportunity.deadline)
                .limit(3)
            ).scalars().all()
            data = {"opportunities": [{"title": job.title, "organization": job.organization, "city": job.city, "job_type": job.job_type} for job in jobs]}
            return _tool_trace(tool_name, "completed", f"已找到 {len(jobs)} 条已发布岗位信息", data)
        if tool_name == "counselor.count_open_alerts":
            count = db.execute(select(func.count(RiskAlert.id)).where(RiskAlert.status == "open")).scalar_one()
            return _tool_trace(tool_name, "completed", f"当前有 {count} 条开放预警", {"open_alerts": count})
        if tool_name == "campus_life.list_activities":
            activities = db.execute(
                select(CampusActivity)
                .where(CampusActivity.status == "published")
                .order_by(CampusActivity.starts_at)
                .limit(3)
            ).scalars().all()
            data = {"activities": [{"title": item.title, "category": item.category, "location": item.location} for item in activities]}
            return _tool_trace(tool_name, "completed", f"已找到 {len(activities)} 条近期校园活动", data)
    except Exception as exc:
        return _tool_trace(tool_name, "failed", f"工具调用失败：{type(exc).__name__}")
    raise ValueError(f"Tool is not implemented: {tool_name}")
