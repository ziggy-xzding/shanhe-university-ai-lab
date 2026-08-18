"""电子档案授权只读接口。"""

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.archive_tables import ArchiveAudit, ArchiveDocument, ArchiveGrant, ArchiveVersion
from Model.staff_account_table import StaffAccount
from Model.university_tables import StudentAcademicProfile
from Service.auth_service import AuthPrincipal
from Service.authorization import get_current_principal
from Service.archive_service import create_archive_version
from Service.archive_storage import LocalArchiveStorage
from Service.data_scope import assert_college_scope, assert_student_scope


archive_router = APIRouter(prefix="/api/archives", tags=["电子档案"])
ALLOWED_ARCHIVE_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}
DEFAULT_MAX_ARCHIVE_FILE_BYTES = 20 * 1024 * 1024


class ArchiveGrantRequest(BaseModel):
    grantee_staff_no: str
    expires_at: datetime | None = None


def _max_archive_file_bytes() -> int:
    try:
        configured_megabytes = float(os.getenv("MAX_ARCHIVE_FILE_MB", "20"))
        if configured_megabytes <= 0:
            raise ValueError
        return int(configured_megabytes * 1024 * 1024)
    except ValueError:
        return DEFAULT_MAX_ARCHIVE_FILE_BYTES


def _can_view_document(db: Session, principal: AuthPrincipal, document_id: int) -> bool:
    if principal.role == "admin":
        return True
    if principal.role == "archive_admin":
        document = db.execute(
            select(ArchiveDocument).where(ArchiveDocument.id == document_id)
        ).scalar_one_or_none()
        return document is not None and principal.college_id == document.college_id
    if principal.role == "student":
        return False
    grant = db.execute(
        select(ArchiveGrant).where(
            ArchiveGrant.document_id == document_id,
            ArchiveGrant.grantee_staff_no == principal.subject_id,
            or_(ArchiveGrant.expires_at.is_(None), ArchiveGrant.expires_at > datetime.now()),
        )
    ).scalar_one_or_none()
    return grant is not None


def _assert_archive_manager_scope(
    db: Session, principal: AuthPrincipal, college_id: int
) -> None:
    if principal.role not in {"admin", "archive_admin"}:
        raise HTTPException(status_code=403, detail="无权管理档案材料")
    assert_college_scope(db, principal, college_id)


@archive_router.get("/documents")
def list_archive_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    if principal.role not in {"admin", "archive_admin"}:
        raise HTTPException(status_code=403, detail="无权查看档案清单")
    statement = select(ArchiveDocument).order_by(ArchiveDocument.created_at.desc(), ArchiveDocument.id.desc())
    if principal.role == "archive_admin":
        if principal.college_id is None:
            raise HTTPException(status_code=403, detail="未配置档案管理员学院范围")
        statement = statement.where(ArchiveDocument.college_id == principal.college_id)
    documents = list(
        db.execute(statement.offset((page - 1) * page_size).limit(page_size)).scalars()
    )
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": document.id,
                "student_no": document.student_no,
                "college_id": document.college_id,
                "category": document.category,
                "title": document.title,
                "status": document.status,
                "created_at": document.created_at,
            }
            for document in documents
        ],
    }


@archive_router.post("/documents", status_code=201)
async def create_document(
    student_no: str = Form(...),
    college_id: int = Form(...),
    category: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    _assert_archive_manager_scope(db, principal, college_id)
    profile = db.execute(
        select(StudentAcademicProfile).where(
            StudentAcademicProfile.student_no == student_no
        )
    ).scalar_one_or_none()
    if profile is not None:
        assert_student_scope(db, principal, student_no)
        if profile.college_id != college_id:
            raise HTTPException(status_code=422, detail="档案学院必须与学生学籍所属学院一致")
    if file.content_type not in ALLOWED_ARCHIVE_MIME_TYPES:
        raise HTTPException(status_code=422, detail="不支持的档案文件格式")
    content = await file.read()
    if not content or len(content) > _max_archive_file_bytes():
        raise HTTPException(status_code=422, detail="档案文件为空或超过20MB")
    document = ArchiveDocument(
        student_no=student_no,
        college_id=college_id,
        category=category,
        title=title,
        status="archived",
    )
    db.add(document)
    db.flush()
    storage = LocalArchiveStorage(Path(os.getenv("ARCHIVE_STORAGE_DIR", "data/archive_files")))
    version = create_archive_version(
        db,
        storage,
        document,
        principal.subject_id,
        file.filename or "archive.bin",
        file.content_type,
        content,
    )
    db.commit()
    return {"document_id": document.id, "version_no": version.version_no}


@archive_router.post("/documents/{document_id}/grants", status_code=201)
def grant_document_access(
    document_id: int,
    payload: ArchiveGrantRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    document = db.execute(select(ArchiveDocument).where(ArchiveDocument.id == document_id)).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="档案材料不存在")
    _assert_archive_manager_scope(db, principal, document.college_id)
    grantee = db.execute(
        select(StaffAccount).where(
            StaffAccount.staff_no == payload.grantee_staff_no.strip(),
            StaffAccount.status == "active",
        )
    ).scalar_one_or_none()
    if not grantee:
        raise HTTPException(status_code=422, detail="被授权教职工不存在或已停用")
    grant = db.execute(
        select(ArchiveGrant).where(
            ArchiveGrant.document_id == document_id,
            ArchiveGrant.grantee_staff_no == payload.grantee_staff_no,
        )
    ).scalar_one_or_none()
    if not grant:
        grant = ArchiveGrant(
            document_id=document_id,
            grantee_staff_no=payload.grantee_staff_no,
            granted_by=principal.subject_id,
            expires_at=payload.expires_at,
        )
        db.add(grant)
    else:
        grant.expires_at = payload.expires_at
    db.add(ArchiveAudit(document_id=document_id, actor_staff_no=principal.subject_id, action="grant", detail_json={"grantee": payload.grantee_staff_no, "expires_at": payload.expires_at.isoformat() if payload.expires_at else None}))
    db.commit()
    return {"document_id": document_id, "grantee_staff_no": payload.grantee_staff_no, "expires_at": grant.expires_at}


@archive_router.delete("/documents/{document_id}/grants/{grantee_staff_no}")
def revoke_document_access(
    document_id: int,
    grantee_staff_no: str,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    document = db.execute(
        select(ArchiveDocument).where(ArchiveDocument.id == document_id)
    ).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="档案材料不存在")
    _assert_archive_manager_scope(db, principal, document.college_id)
    grant = db.execute(
        select(ArchiveGrant).where(
            ArchiveGrant.document_id == document_id,
            ArchiveGrant.grantee_staff_no == grantee_staff_no,
        )
    ).scalar_one_or_none()
    if not grant:
        raise HTTPException(status_code=404, detail="档案查阅授权不存在")
    db.delete(grant)
    db.add(
        ArchiveAudit(
            document_id=document_id,
            actor_staff_no=principal.subject_id,
            action="revoke",
            detail_json={"grantee": grantee_staff_no},
        )
    )
    db.commit()
    return {"document_id": document_id, "grantee_staff_no": grantee_staff_no, "revoked": True}


@archive_router.post("/documents/{document_id}/versions", status_code=201)
async def create_correction_version(
    document_id: int,
    correction_reason: str = Form(""),
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    document = db.execute(select(ArchiveDocument).where(ArchiveDocument.id == document_id)).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="档案材料不存在")
    _assert_archive_manager_scope(db, principal, document.college_id)
    if not correction_reason.strip():
        raise HTTPException(status_code=422, detail="归档材料更正必须填写原因")
    if file.content_type not in ALLOWED_ARCHIVE_MIME_TYPES:
        raise HTTPException(status_code=422, detail="不支持的档案文件格式")
    content = await file.read()
    if not content or len(content) > _max_archive_file_bytes():
        raise HTTPException(status_code=422, detail="档案文件为空或超过20MB")
    storage = LocalArchiveStorage(Path(os.getenv("ARCHIVE_STORAGE_DIR", "data/archive_files")))
    version = create_archive_version(
        db, storage, document, principal.subject_id, file.filename or "archive.bin", file.content_type, content, correction_reason
    )
    db.commit()
    return {"document_id": document.id, "version_no": version.version_no}


@archive_router.get("/documents/{document_id}")
def get_document(
    document_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    document = db.execute(
        select(ArchiveDocument).where(ArchiveDocument.id == document_id)
    ).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="档案材料不存在")
    if not _can_view_document(db, principal, document_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查阅该档案")
    versions = list(
        db.execute(
            select(ArchiveVersion)
            .where(ArchiveVersion.document_id == document_id)
            .order_by(ArchiveVersion.version_no.desc())
        ).scalars()
    )
    db.add(
        ArchiveAudit(
            document_id=document_id,
            actor_staff_no=None if principal.role == "student" else principal.subject_id,
            action="view",
            detail_json={"role": principal.role},
        )
    )
    db.commit()
    return {
        "id": document.id,
        "student_no": document.student_no,
        "category": document.category,
        "title": document.title,
        "status": document.status,
        "versions": [
            {"version_no": item.version_no, "file_name": item.file_name, "archived_at": item.archived_at}
            for item in versions
        ],
    }


@archive_router.get("/documents/{document_id}/versions/{version_no}/download")
def download_archive_version(
    document_id: int,
    version_no: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    document = db.execute(
        select(ArchiveDocument).where(ArchiveDocument.id == document_id)
    ).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="档案材料不存在")
    if not _can_view_document(db, principal, document_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权下载该档案")
    version = db.execute(
        select(ArchiveVersion).where(
            ArchiveVersion.document_id == document_id,
            ArchiveVersion.version_no == version_no,
        )
    ).scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="档案版本不存在")
    try:
        content = LocalArchiveStorage(
            Path(os.getenv("ARCHIVE_STORAGE_DIR", "data/archive_files"))
        ).read(version.object_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="档案文件不存在") from exc
    db.add(
        ArchiveAudit(
            document_id=document_id,
            version_id=version.id,
            actor_staff_no=None if principal.role == "student" else principal.subject_id,
            action="download",
            detail_json={"role": principal.role, "version_no": version_no},
        )
    )
    db.commit()
    return Response(
        content=content,
        media_type=version.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{version.file_name}"'},
    )
