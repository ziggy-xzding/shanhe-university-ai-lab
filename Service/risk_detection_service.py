"""校园助手的最小必要心理风险识别与预警记录。"""

from sqlalchemy import select

from Model.risk_alert_tables import CounselorAssignment, RiskAlert, UnassignedRiskAlert


HIGH_RISK_PHRASES = ("自杀", "自残", "伤害自己", "伤害他人", "不想活")


def has_high_risk_signal(message: str) -> bool:
    return any(phrase in message for phrase in HIGH_RISK_PHRASES)


def create_minimal_risk_alert(db, student_no: str) -> bool:
    """只写入处置必需的学生、辅导员和摘要，绝不保存聊天原文。"""
    assignment = db.execute(
        select(CounselorAssignment).where(CounselorAssignment.student_no == student_no)
    ).scalar_one_or_none()
    if not assignment:
        existing_unassigned = db.execute(
            select(UnassignedRiskAlert).where(
                UnassignedRiskAlert.student_no == student_no,
                UnassignedRiskAlert.status == "open",
            )
        ).scalar_one_or_none()
        if existing_unassigned:
            return False
        db.add(
            UnassignedRiskAlert(
                student_no=student_no,
                risk_level="high",
                status="open",
                trigger_summary="检测到需立即人工关注的心理风险信号，尚未配置辅导员，请由学生事务人员尽快分配并按学校流程联系学生。",
            )
        )
        return True
    existing = db.execute(
        select(RiskAlert).where(
            RiskAlert.student_no == student_no,
            RiskAlert.counselor_staff_no == assignment.counselor_staff_no,
            RiskAlert.status.in_(("open", "reviewed")),
        )
    ).scalar_one_or_none()
    if existing:
        return False
    db.add(
        RiskAlert(
            student_no=student_no,
            counselor_staff_no=assignment.counselor_staff_no,
            risk_level="high",
            status="open",
            trigger_summary="检测到需立即人工关注的心理风险信号，请按学校处置流程联系学生。",
        )
    )
    return True
