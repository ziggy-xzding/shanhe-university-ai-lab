"""可复用的学生成绩趋势与关注等级计算。"""

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from Model.Student_score_table import Score
from Model.student_table import Student


@dataclass(frozen=True)
class ScoreSummary:
    average_score: float | None
    pass_rate: float | None
    latest_change: float | None
    attention_level: str


def classify_attention(scores: Sequence[float]) -> str:
    """依据成绩水平、连续不及格和近期变化给出非惩罚性关注等级。"""
    if not scores:
        return "attention"
    if len(scores) >= 2 and scores[-1] < 60 and scores[-2] < 60:
        return "urgent"
    average = sum(scores) / len(scores)
    if average >= 90 and min(scores) >= 80:
        return "excellent"
    if average < 60 or (len(scores) >= 2 and scores[-1] - scores[-2] <= -15):
        return "attention"
    return "stable"


def summarize_scores(scores: Sequence[float]) -> ScoreSummary:
    """汇总阶段成绩；空成绩返回可直接用于空状态的指标。"""
    if not scores:
        return ScoreSummary(
            average_score=None,
            pass_rate=None,
            latest_change=None,
            attention_level="attention",
        )
    values = [float(score) for score in scores]
    return ScoreSummary(
        average_score=round(sum(values) / len(values), 1),
        pass_rate=round(sum(score >= 60 for score in values) / len(values), 3),
        latest_change=round(values[-1] - values[-2], 1)
        if len(values) >= 2
        else None,
        attention_level=classify_attention(values),
    )


def build_student_overview(db: Session, student_no: str) -> dict:
    """查询某一学生的成绩序列及仅含汇总值的班级对比。"""
    student = db.execute(
        select(Student).where(
            Student.student_no == student_no,
            Student.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if not student:
        raise ValueError("学生不存在")

    score_rows = db.execute(
        select(Score.exam_seq, Score.score)
        .where(Score.student_no == student_no, Score.is_deleted.is_(False))
        .order_by(Score.exam_seq)
    ).all()
    values = [float(row.score) for row in score_rows]
    summary = summarize_scores(values)

    class_size = db.execute(
        select(func.count(Student.id)).where(
            Student.class_id == student.class_id,
            Student.is_deleted.is_(False),
        )
    ).scalar_one()
    class_average = db.execute(
        select(func.avg(Score.score))
        .join(Student, Student.student_no == Score.student_no)
        .where(
            Student.class_id == student.class_id,
            Student.is_deleted.is_(False),
            Score.is_deleted.is_(False),
        )
    ).scalar_one()

    rank_rows = db.execute(
        select(Student.student_no, func.avg(Score.score).label("average_score"))
        .join(Score, Score.student_no == Student.student_no)
        .where(
            Student.class_id == student.class_id,
            Student.is_deleted.is_(False),
            Score.is_deleted.is_(False),
        )
        .group_by(Student.student_no)
        .order_by(func.avg(Score.score).desc(), Student.student_no)
    ).all()
    class_rank = next(
        (index for index, row in enumerate(rank_rows, start=1) if row.student_no == student_no),
        None,
    )

    return {
        "student_no": student.student_no,
        "student_name": student.name,
        "class_id": student.class_id,
        "average_score": summary.average_score,
        "pass_rate": summary.pass_rate,
        "latest_change": summary.latest_change,
        "attention_level": summary.attention_level,
        "class_average": round(float(class_average), 1)
        if class_average is not None
        else None,
        "class_rank": class_rank,
        "class_size": int(class_size),
        "scores": [
            {"exam_seq": row.exam_seq, "score": float(row.score)}
            for row in score_rows
        ],
    }
