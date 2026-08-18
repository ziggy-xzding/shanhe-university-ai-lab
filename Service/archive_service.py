"""电子档案版本服务。"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select

from Model.archive_tables import ArchiveAudit, ArchiveDocument, ArchiveVersion


def create_archive_version(
    db,
    storage,
    document: ArchiveDocument,
    actor_staff_no: str,
    file_name: str,
    mime_type: str,
    content: bytes,
    correction_reason: str | None = None,
) -> ArchiveVersion:
    latest_version = db.execute(
        select(func.max(ArchiveVersion.version_no)).where(
            ArchiveVersion.document_id == document.id
        )
    ).scalar_one()
    version_no = (latest_version or 0) + 1
    if version_no > 1 and not (correction_reason or "").strip():
        raise ValueError("归档材料更正必须填写原因")
    suffix = Path(file_name).suffix.lower() or ".bin"
    object_key = f"{document.student_no}/{document.id}/v{version_no}-{uuid4().hex}{suffix}"
    digest = sha256(content).hexdigest()
    storage.save(content, object_key)
    version = ArchiveVersion(
        document_id=document.id,
        version_no=version_no,
        object_key=object_key,
        sha256=digest,
        file_name=file_name,
        mime_type=mime_type,
        correction_reason=correction_reason.strip() if correction_reason else None,
        archived_by=actor_staff_no,
        archived_at=datetime.now(),
    )
    db.add(version)
    db.flush()
    db.add(
        ArchiveAudit(
            document_id=document.id,
            version_id=version.id,
            actor_staff_no=actor_staff_no,
            action="create_version",
            detail_json={"version_no": version_no, "sha256": digest},
        )
    )
    db.flush()
    return version
