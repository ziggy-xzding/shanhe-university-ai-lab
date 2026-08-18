"""教师工作台与班级范围查询。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from Model.Student_score_table import Score
from Model.class_table import Class
from Model.student_table import Student


def teacher_class_ids(db: Session, teacher_id: int | None) -> set[int]:
    if teacher_id is None:
        return set()
    rows = db.execute(
        select(Class.id).where(
            Class.is_deleted == 0,
            (Class.head_teacher_id == teacher_id) | (Class.instructor_id == teacher_id),
        )
    ).all()
    return {int(row.id) for row in rows}


def list_teacher_classes(db: Session, teacher_id: int | None) -> list[dict]:
    class_ids = teacher_class_ids(db, teacher_id)
    if not class_ids:
        return []
    rows = db.execute(
        select(
            Class.id,
            Class.class_no,
            Class.name,
            func.count(Student.id).label("student_count"),
            func.avg(Score.score).label("average_score"),
        )
        .outerjoin(Student, (Student.class_id == Class.id) & (Student.is_deleted.is_(False)))
        .outerjoin(Score, (Score.student_no == Student.student_no) & (Score.is_deleted.is_(False)))
        .where(Class.id.in_(class_ids), Class.is_deleted == 0)
        .group_by(Class.id, Class.class_no, Class.name)
        .order_by(Class.class_no)
    ).all()
    return [
        {
            "id": row.id,
            "class_no": row.class_no,
            "name": row.name,
            "student_count": int(row.student_count or 0),
            "average_score": round(float(row.average_score), 1)
            if row.average_score is not None
            else None,
        }
        for row in rows
    ]


def list_class_students(db: Session, class_id: int) -> list[dict]:
    rows = db.execute(
        select(
            Student.student_no,
            Student.name,
            Student.gender,
            Student.age,
            func.avg(Score.score).label("average_score"),
        )
        .outerjoin(Score, (Score.student_no == Student.student_no) & (Score.is_deleted.is_(False)))
        .where(Student.class_id == class_id, Student.is_deleted.is_(False))
        .group_by(Student.student_no, Student.name, Student.gender, Student.age)
        .order_by(Student.student_no)
    ).all()
    return [
        {
            "student_no": row.student_no,
            "name": row.name,
            "gender": row.gender,
            "age": row.age,
            "average_score": round(float(row.average_score), 1)
            if row.average_score is not None
            else None,
        }
        for row in rows
    ]


def class_score_analysis(db: Session, class_id: int) -> dict:
    rows = db.execute(
        select(Score.exam_seq, func.avg(Score.score).label("average_score"))
        .join(Student, Student.student_no == Score.student_no)
        .where(
            Student.class_id == class_id,
            Student.is_deleted.is_(False),
            Score.is_deleted.is_(False),
        )
        .group_by(Score.exam_seq)
        .order_by(Score.exam_seq)
    ).all()
    students = list_class_students(db, class_id)
    attention_count = sum(
        1 for item in students if item["average_score"] is not None and item["average_score"] < 60
    )
    return {
        "class_id": class_id,
        "trend": [
            {"exam_seq": row.exam_seq, "average_score": round(float(row.average_score), 1)}
            for row in rows
        ],
        "student_count": len(students),
        "attention_count": attention_count,
    }
