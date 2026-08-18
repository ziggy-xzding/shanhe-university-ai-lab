"""高校官方电子档案的元数据、版本、授权和审计模型。"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from DAO.db import Base


class ArchiveDocument(Base):
    __tablename__ = "archive_documents"
    __table_args__ = (
        Index("ix_archive_document_student_status", "student_no", "status"),
        Index("ix_archive_document_college_category", "college_id", "category"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    category = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="archived")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ArchiveVersion(Base):
    __tablename__ = "archive_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_archive_document_version"),
        UniqueConstraint("object_key", name="uq_archive_object_key"),
        Index("ix_archive_version_document_time", "document_id", "archived_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("archive_documents.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    object_key = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    correction_reason = Column(Text, nullable=True)
    archived_by = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False)
    archived_at = Column(DateTime, nullable=False, default=datetime.now)


class ArchiveGrant(Base):
    __tablename__ = "archive_grants"
    __table_args__ = (
        UniqueConstraint("document_id", "grantee_staff_no", name="uq_archive_document_grantee"),
        Index("ix_archive_grant_grantee_expiry", "grantee_staff_no", "expires_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("archive_documents.id"), nullable=False)
    grantee_staff_no = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False)
    granted_by = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ArchiveAudit(Base):
    __tablename__ = "archive_audits"
    __table_args__ = (Index("ix_archive_audit_document_time", "document_id", "created_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("archive_documents.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("archive_versions.id"), nullable=True)
    actor_staff_no = Column(String(20), nullable=True)
    action = Column(String(40), nullable=False)
    detail_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
