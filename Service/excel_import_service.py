"""高校 Excel 导入预校验服务。"""

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO

import pandas as pd
from sqlalchemy import select

from Model.class_table import Class
from Model.student_table import Student
from Model.teacher_table import teacher_table
from Model.university_tables import (
    AcademicTerm,
    College,
    Course,
    ImportBatch,
    ImportRowError,
    Major,
    StudentAcademicProfile,
    TeachingSection,
)


STUDENT_COLUMNS = [
    "student_no",
    "name",
    "college_code",
    "major_code",
    "class_no",
    "grade",
    "phone",
]
CLASS_COLUMNS = ["class_no", "name", "start_date", "head_teacher_id", "instructor_id"]
COURSE_COLUMNS = ["code", "name", "credits", "hours"]
TEACHING_SECTION_COLUMNS = [
    "course_code", "term_code", "teacher_id", "capacity",
    "selection_open_at", "selection_close_at", "timetable_json",
]


def _errors_for_batch(db, batch_id: int) -> list[dict[str, object]]:
    rows = db.execute(
        select(ImportRowError)
        .where(ImportRowError.batch_id == batch_id)
        .order_by(ImportRowError.row_number, ImportRowError.id)
    ).scalars()
    return [
        {"row_number": item.row_number, "field": item.field, "message": item.message}
        for item in rows
    ]


def preview_student_import(
    db, file_bytes: bytes, actor: str, allowed_college_id: int | None = None
) -> dict[str, object]:
    checksum = sha256(file_bytes).hexdigest()
    existing_batch = db.execute(
        select(ImportBatch).where(
            ImportBatch.kind == "students", ImportBatch.checksum == checksum
        )
    ).scalar_one_or_none()
    if existing_batch:
        return {
            "batch_id": existing_batch.id,
            "status": existing_batch.status,
            "errors": _errors_for_batch(db, existing_batch.id),
        }

    frame = pd.read_excel(BytesIO(file_bytes), sheet_name="students", dtype=str).fillna("")
    missing = [column for column in STUDENT_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"缺少必要列: {', '.join(missing)}")

    if allowed_college_id is not None:
        referenced_codes = {
            str(value).strip()
            for value in frame["college_code"].tolist()
            if str(value).strip()
        }
        referenced_colleges = {
            item.code: item.id
            for item in db.execute(
                select(College).where(College.code.in_(referenced_codes))
            ).scalars()
        }
        if any(
            college_id != allowed_college_id
            for college_id in referenced_colleges.values()
        ):
            raise PermissionError("学院管理员只能导入本学院学生数据")

    rows = [
        {column: str(value).strip() for column, value in row.items()}
        for row in frame[STUDENT_COLUMNS].to_dict("records")
    ]
    batch = ImportBatch(
        kind="students",
        checksum=checksum,
        created_by=actor,
        result_json={"rows": rows},
    )
    db.add(batch)
    db.flush()
    college_by_code = {
        item.code: item
        for item in db.execute(select(College)).scalars()
    }
    major_by_college_code = {
        (item.college_id, item.code): item
        for item in db.execute(select(Major)).scalars()
    }
    class_numbers = set(db.execute(select(Class.class_no)).scalars())
    existing_student_numbers = set(db.execute(select(Student.student_no)).scalars())

    for row_number, row in enumerate(rows, start=2):
        student_no = row["student_no"]
        college = college_by_code.get(row["college_code"])
        major = (
            major_by_college_code.get((college.id, row["major_code"]))
            if college
            else None
        )
        if student_no in existing_student_numbers:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="student_no", message="学号已存在"))
        elif not student_no:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="student_no", message="学号不能为空"))
        if not college:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="college_code", message="学院不存在"))
        elif not major:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="major_code", message="专业不存在"))
        if row["class_no"] not in class_numbers:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="class_no", message="班级不存在"))
    db.commit()
    return {"batch_id": batch.id, "status": batch.status, "errors": _errors_for_batch(db, batch.id)}


def confirm_student_import(db, batch_id: int, actor: str) -> dict[str, int]:
    batch = db.execute(
        select(ImportBatch).where(ImportBatch.id == batch_id).with_for_update()
    ).scalar_one_or_none()
    if not batch or batch.kind != "students":
        raise ValueError("导入批次不存在")
    if batch.status == "confirmed":
        return {"created": 0, "skipped": 0}
    if _errors_for_batch(db, batch.id):
        raise ValueError("导入批次存在校验错误，不能确认入库")

    colleges = {item.code: item for item in db.execute(select(College)).scalars()}
    majors = {
        (item.college_id, item.code): item
        for item in db.execute(select(Major)).scalars()
    }
    classes = {item.class_no: item for item in db.execute(select(Class)).scalars()}
    created = 0
    for row in (batch.result_json or {}).get("rows", []):
        student = db.execute(
            select(Student).where(Student.student_no == row["student_no"])
        ).scalar_one_or_none()
        if student:
            continue
        college = colleges[row["college_code"]]
        major = majors[(college.id, row["major_code"])]
        student = Student(
            student_no=row["student_no"],
            name=row["name"],
            class_id=classes[row["class_no"]].id,
        )
        db.add(student)
        db.flush()
        db.add(
            StudentAcademicProfile(
                student_no=student.student_no,
                college_id=college.id,
                major_id=major.id,
                class_id=student.class_id,
                grade=row["grade"],
                phone=row["phone"] or None,
            )
        )
        created += 1
    batch.status = "confirmed"
    batch.confirmed_at = datetime.now()
    batch.result_json = {**(batch.result_json or {}), "created": created, "confirmed_by": actor}
    db.commit()
    return {"created": created, "skipped": 0}


def preview_class_import(db, file_bytes: bytes, actor: str) -> dict[str, object]:
    checksum = sha256(file_bytes).hexdigest()
    existing_batch = db.execute(
        select(ImportBatch).where(ImportBatch.kind == "classes", ImportBatch.checksum == checksum)
    ).scalar_one_or_none()
    if existing_batch:
        return {"batch_id": existing_batch.id, "status": existing_batch.status, "errors": _errors_for_batch(db, existing_batch.id)}
    frame = pd.read_excel(BytesIO(file_bytes), sheet_name="classes", dtype=str).fillna("")
    missing = [column for column in CLASS_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"缺少必要列: {', '.join(missing)}")
    rows = [{column: str(value).strip() for column, value in row.items()} for row in frame[CLASS_COLUMNS].to_dict("records")]
    batch = ImportBatch(kind="classes", checksum=checksum, created_by=actor, result_json={"rows": rows})
    db.add(batch)
    db.flush()
    existing_numbers = set(db.execute(select(Class.class_no)).scalars())
    teacher_ids = set(db.execute(select(teacher_table.tid)).scalars())
    for row_number, row in enumerate(rows, start=2):
        if not row["class_no"]:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="class_no", message="班级编号不能为空"))
        elif row["class_no"] in existing_numbers:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="class_no", message="班级编号已存在"))
        if not row["name"]:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="name", message="班级名称不能为空"))
        try:
            datetime.fromisoformat(row["start_date"])
        except ValueError:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="start_date", message="开班日期格式无效"))
        for field in ("head_teacher_id", "instructor_id"):
            try:
                teacher_id = int(row[field])
            except ValueError:
                teacher_id = None
            if teacher_id not in teacher_ids:
                db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field=field, message="教师不存在"))
    db.commit()
    return {"batch_id": batch.id, "status": batch.status, "errors": _errors_for_batch(db, batch.id)}


def confirm_class_import(db, batch_id: int, actor: str) -> dict[str, int]:
    batch = db.execute(select(ImportBatch).where(ImportBatch.id == batch_id).with_for_update()).scalar_one_or_none()
    if not batch or batch.kind != "classes":
        raise ValueError("班级导入批次不存在")
    if batch.status == "confirmed":
        return {"created": 0, "skipped": 0}
    if _errors_for_batch(db, batch.id):
        raise ValueError("班级导入批次存在校验错误，不能确认入库")
    created = 0
    for row in (batch.result_json or {}).get("rows", []):
        if db.execute(select(Class).where(Class.class_no == row["class_no"])).scalar_one_or_none():
            continue
        db.add(Class(
            class_no=row["class_no"],
            name=row["name"],
            start_date=datetime.fromisoformat(row["start_date"]),
            head_teacher_id=int(row["head_teacher_id"]),
            instructor_id=int(row["instructor_id"]),
            is_deleted=0,
        ))
        created += 1
    batch.status = "confirmed"
    batch.confirmed_at = datetime.now()
    batch.result_json = {**(batch.result_json or {}), "created": created, "confirmed_by": actor}
    db.commit()
    return {"created": created, "skipped": 0}


def preview_course_import(db, file_bytes: bytes, actor: str) -> dict[str, object]:
    checksum = sha256(file_bytes).hexdigest()
    existing_batch = db.execute(
        select(ImportBatch).where(ImportBatch.kind == "courses", ImportBatch.checksum == checksum)
    ).scalar_one_or_none()
    if existing_batch:
        return {"batch_id": existing_batch.id, "status": existing_batch.status, "errors": _errors_for_batch(db, existing_batch.id)}
    frame = pd.read_excel(BytesIO(file_bytes), sheet_name="courses", dtype=str).fillna("")
    missing = [column for column in COURSE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"缺少必要列: {', '.join(missing)}")
    rows = [{column: str(value).strip() for column, value in row.items()} for row in frame[COURSE_COLUMNS].to_dict("records")]
    batch = ImportBatch(kind="courses", checksum=checksum, created_by=actor, result_json={"rows": rows})
    db.add(batch)
    db.flush()
    existing_codes = set(db.execute(select(Course.code)).scalars())
    codes_in_file: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        code = row["code"].upper()
        if not code:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="code", message="课程代码不能为空"))
        elif code in existing_codes:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="code", message="课程代码已存在"))
        elif code in codes_in_file:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="code", message="导入文件内课程代码重复"))
        codes_in_file.add(code)
        if not row["name"]:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="name", message="课程名称不能为空"))
        for field, maximum in (("credits", 30), ("hours", 500)):
            try:
                numeric_value = Decimal(row[field]) if field == "credits" else int(row[field])
            except (ValueError, InvalidOperation):
                numeric_value = -1
            if numeric_value < 0 or numeric_value > maximum:
                db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field=field, message=f"{field} 必须是 0 到 {maximum} 的整数"))
    db.commit()
    return {"batch_id": batch.id, "status": batch.status, "errors": _errors_for_batch(db, batch.id)}


def confirm_course_import(db, batch_id: int, actor: str) -> dict[str, int]:
    batch = db.execute(select(ImportBatch).where(ImportBatch.id == batch_id).with_for_update()).scalar_one_or_none()
    if not batch or batch.kind != "courses":
        raise ValueError("课程导入批次不存在")
    if batch.status == "confirmed":
        return {"created": 0, "skipped": 0}
    if _errors_for_batch(db, batch.id):
        raise ValueError("课程导入批次存在校验错误，不能确认入库")
    created = 0
    skipped = 0
    for row in (batch.result_json or {}).get("rows", []):
        code = row["code"].upper()
        if db.execute(select(Course).where(Course.code == code)).scalar_one_or_none():
            skipped += 1
            continue
        db.add(Course(code=code, name=row["name"], credits=Decimal(row["credits"]), hours=int(row["hours"]), status="active"))
        created += 1
    batch.status = "confirmed"
    batch.confirmed_at = datetime.now()
    batch.result_json = {**(batch.result_json or {}), "created": created, "confirmed_by": actor}
    db.commit()
    return {"created": created, "skipped": skipped}


def preview_teaching_section_import(db, file_bytes: bytes, actor: str) -> dict[str, object]:
    checksum = sha256(file_bytes).hexdigest()
    existing_batch = db.execute(
        select(ImportBatch).where(ImportBatch.kind == "teaching_sections", ImportBatch.checksum == checksum)
    ).scalar_one_or_none()
    if existing_batch:
        return {"batch_id": existing_batch.id, "status": existing_batch.status, "errors": _errors_for_batch(db, existing_batch.id)}
    frame = pd.read_excel(BytesIO(file_bytes), sheet_name="teaching_sections", dtype=str).fillna("")
    missing = [column for column in TEACHING_SECTION_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"缺少必要列: {', '.join(missing)}")
    rows = [{column: str(value).strip() for column, value in row.items()} for row in frame[TEACHING_SECTION_COLUMNS].to_dict("records")]
    batch = ImportBatch(kind="teaching_sections", checksum=checksum, created_by=actor, result_json={"rows": rows})
    db.add(batch)
    db.flush()
    courses = {item.code: item for item in db.execute(select(Course)).scalars()}
    terms = {item.code: item for item in db.execute(select(AcademicTerm)).scalars()}
    teacher_ids = set(db.execute(select(teacher_table.tid)).scalars())
    for row_number, row in enumerate(rows, start=2):
        if row["course_code"].upper() not in courses:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="course_code", message="课程不存在"))
        if row["term_code"] not in terms:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="term_code", message="学期不存在"))
        try:
            teacher_id = int(row["teacher_id"]) if row["teacher_id"] else None
        except ValueError:
            teacher_id = -1
        if teacher_id is not None and teacher_id not in teacher_ids:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="teacher_id", message="教师不存在"))
        try:
            capacity = int(row["capacity"])
        except ValueError:
            capacity = 0
        if capacity < 1 or capacity > 500:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="capacity", message="容量必须是 1 到 500 的整数"))
        try:
            opens_at = datetime.fromisoformat(row["selection_open_at"])
            closes_at = datetime.fromisoformat(row["selection_close_at"])
            if closes_at <= opens_at:
                raise ValueError
        except ValueError:
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="selection_open_at", message="选课时间格式无效或截止时间不晚于开始时间"))
        try:
            timetable = json.loads(row["timetable_json"] or "[]")
            if not isinstance(timetable, list):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            db.add(ImportRowError(batch_id=batch.id, row_number=row_number, field="timetable_json", message="课表必须是 JSON 数组"))
    db.commit()
    return {"batch_id": batch.id, "status": batch.status, "errors": _errors_for_batch(db, batch.id)}


def confirm_teaching_section_import(db, batch_id: int, actor: str) -> dict[str, int]:
    batch = db.execute(select(ImportBatch).where(ImportBatch.id == batch_id).with_for_update()).scalar_one_or_none()
    if not batch or batch.kind != "teaching_sections":
        raise ValueError("教学班导入批次不存在")
    if batch.status == "confirmed":
        return {"created": 0, "skipped": 0}
    if _errors_for_batch(db, batch.id):
        raise ValueError("教学班导入批次存在校验错误，不能确认入库")
    courses = {item.code: item for item in db.execute(select(Course)).scalars()}
    terms = {item.code: item for item in db.execute(select(AcademicTerm)).scalars()}
    created = 0
    for row in (batch.result_json or {}).get("rows", []):
        db.add(TeachingSection(
            course_id=courses[row["course_code"].upper()].id,
            academic_term_id=terms[row["term_code"]].id,
            teacher_id=int(row["teacher_id"]) if row["teacher_id"] else None,
            capacity=int(row["capacity"]),
            enrolled_count=0,
            selection_open_at=datetime.fromisoformat(row["selection_open_at"]),
            selection_close_at=datetime.fromisoformat(row["selection_close_at"]),
            timetable_json=json.loads(row["timetable_json"] or "[]"),
            status="open",
        ))
        created += 1
    batch.status = "confirmed"
    batch.confirmed_at = datetime.now()
    batch.result_json = {**(batch.result_json or {}), "created": created, "confirmed_by": actor}
    db.commit()
    return {"created": created, "skipped": 0}
