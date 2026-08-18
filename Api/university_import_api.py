"""高校批量导入接口。"""

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles
from Model.university_tables import ImportBatch
from Service.excel_import_service import (
    confirm_class_import,
    confirm_course_import,
    confirm_student_import,
    confirm_teaching_section_import,
    preview_class_import,
    preview_course_import,
    preview_student_import,
    preview_teaching_section_import,
)


university_import_router = APIRouter(prefix="/api/university/imports", tags=["高校数据导入"])
require_importer = require_roles("admin", "college_admin")
require_schoolwide_importer = require_roles("admin")
EXCEL_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _import_template(sheet_name: str, columns: list[str], filename: str) -> Response:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(columns)
    worksheet.freeze_panes = "A2"
    for column in worksheet.columns:
        worksheet.column_dimensions[column[0].column_letter].width = 20
    stream = BytesIO()
    workbook.save(stream)
    return Response(
        content=stream.getvalue(),
        media_type=EXCEL_MIME_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _assert_student_batch_confirmation_scope(
    db: Session, batch_id: int, principal: AuthPrincipal
) -> None:
    """学院管理员只能确认本人预校验过的学生批次。"""
    if principal.role != "college_admin":
        return
    batch = db.execute(
        select(ImportBatch).where(ImportBatch.id == batch_id)
    ).scalar_one_or_none()
    if batch is None or batch.kind != "students" or batch.created_by != principal.subject_id:
        raise HTTPException(status_code=403, detail="无权确认该学生导入批次")


@university_import_router.get("/templates/students")
def download_student_import_template(
    principal: AuthPrincipal = Depends(require_importer),
):
    return _import_template(
        "students",
        ["student_no", "name", "college_code", "major_code", "class_no", "grade", "phone"],
        "students-import-template.xlsx",
    )


@university_import_router.get("/templates/classes")
def download_class_import_template(
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
):
    return _import_template(
        "classes",
        ["class_no", "name", "start_date", "head_teacher_id", "instructor_id"],
        "classes-import-template.xlsx",
    )


@university_import_router.get("/templates/courses")
def download_course_import_template(
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
):
    return _import_template(
        "courses",
        ["code", "name", "credits", "hours"],
        "courses-import-template.xlsx",
    )


@university_import_router.get("/templates/teaching-sections")
def download_teaching_section_import_template(
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
):
    return _import_template(
        "teaching_sections",
        ["course_code", "term_code", "teacher_id", "capacity", "selection_open_at", "selection_close_at", "timetable_json"],
        "teaching-sections-import-template.xlsx",
    )


@university_import_router.post("/students/preview")
async def preview_students(
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(require_importer),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="请上传 .xlsx 文件")
    if principal.role == "college_admin" and principal.college_id is None:
        raise HTTPException(status_code=403, detail="学院管理员未配置学院数据范围")
    try:
        return preview_student_import(
            db,
            await file.read(),
            principal.subject_id,
            principal.college_id if principal.role == "college_admin" else None,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@university_import_router.post("/{batch_id}/confirm")
def confirm_students(
    batch_id: int,
    principal: AuthPrincipal = Depends(require_importer),
    db: Session = Depends(get_db),
):
    _assert_student_batch_confirmation_scope(db, batch_id, principal)
    try:
        return confirm_student_import(db, batch_id, principal.subject_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@university_import_router.post("/classes/preview")
async def preview_classes(
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="请上传 .xlsx 文件")
    try:
        return preview_class_import(db, await file.read(), principal.subject_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@university_import_router.post("/classes/{batch_id}/confirm")
def confirm_classes(
    batch_id: int,
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
    db: Session = Depends(get_db),
):
    try:
        return confirm_class_import(db, batch_id, principal.subject_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@university_import_router.post("/courses/preview")
async def preview_courses(
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="请上传 .xlsx 文件")
    try:
        return preview_course_import(db, await file.read(), principal.subject_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@university_import_router.post("/courses/{batch_id}/confirm")
def confirm_courses(
    batch_id: int,
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
    db: Session = Depends(get_db),
):
    try:
        return confirm_course_import(db, batch_id, principal.subject_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@university_import_router.post("/teaching-sections/preview")
async def preview_teaching_sections(
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="请上传 .xlsx 文件")
    try:
        return preview_teaching_section_import(db, await file.read(), principal.subject_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@university_import_router.post("/teaching-sections/{batch_id}/confirm")
def confirm_teaching_sections(
    batch_id: int,
    principal: AuthPrincipal = Depends(require_schoolwide_importer),
    db: Session = Depends(get_db),
):
    try:
        return confirm_teaching_section_import(db, batch_id, principal.subject_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
