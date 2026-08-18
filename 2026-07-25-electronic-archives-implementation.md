# 电子档案模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为高校学生官方档案提供版本不可直接改写、按授权只读和全程审计的电子化管理。

**Architecture:** 文件二进制由可替换存储适配器保存，数据库仅保存 SHA-256、版本链、归档状态和权限关系。归档档案永不覆盖；更正创建新版本，历史版本与审计记录保留。

**Tech Stack:** FastAPI、SQLAlchemy 2、Pydantic 2、pytest；开发环境使用本地存储适配器，生产环境替换为对象存储。

## Global Constraints

- 学生账户永远不得读取、下载、修改官方档案。
- 归档版本不提供更新或删除接口；仅档案管理员可创建新版本并必须写明更正原因。
- 查阅授权只读，可按学生和档案材料授权；所有查阅、下载、授权、归档和新版本创建写入审计。
- 档案管理员只能操作所属学院学生；校级管理员可跨学院审计。
- 文件数据不写入 MySQL；本期仅允许 PDF、图片和 Word 格式，最大 20MB。

---

### Task 1: 档案元数据、版本和审计 ORM

**Files:**
- Create: `Model/archive_tables.py`
- Modify: `main.py`
- Test: `tests/test_archive_models.py`

- [ ] Write a failing test that creates an `ArchiveDocument` version 1 and verifies `UniqueConstraint(document_id, version_no)`.
- [ ] Run `python -m pytest tests/test_archive_models.py -q`; expect a missing module failure.
- [ ] Create `ArchiveDocument(student_no, category, title, college_id, status)`, `ArchiveVersion(document_id, version_no, object_key, sha256, file_name, mime_type, correction_reason, archived_by, archived_at)`, `ArchiveGrant(document_id, grantee_staff_no, granted_by, expires_at)` and `ArchiveAudit(document_id, version_id, actor_staff_no, action, detail_json, created_at)`; register the module in `main.py`.
- [ ] Run the model test; expect PASS.
- [ ] Commit the model and test files.

### Task 2: 版本创建与不可改写服务

**Files:**
- Create: `Service/archive_storage.py`
- Create: `Service/archive_service.py`
- Test: `tests/test_archive_service.py`

- [ ] Write a failing test that archives an initial file then requests a correction and asserts versions are `[1, 2]` with distinct SHA-256 values and one `create_version` audit event.
- [ ] Run the focused test; expect `ImportError`.
- [ ] Implement `LocalArchiveStorage.save(content, object_key)` and `create_archive_version(db, actor, student_no, category, file_name, mime_type, content, correction_reason=None)`; reject a new version unless the caller is archive/admin and a correction reason is supplied after version 1.
- [ ] Run the focused test; expect PASS.
- [ ] Commit service and tests.

### Task 3: 授权只读与档案 API

**Files:**
- Create: `Api/archive_api.py`
- Modify: `main.py`
- Test: `tests/test_archive_api.py`

- [ ] Write a failing test that proves a student gets 403 while an explicitly granted staff account receives document metadata, and the read creates an `view` audit event.
- [ ] Run the test; expect 404.
- [ ] Add `POST /api/archives/documents`, `POST /api/archives/documents/{id}/versions`, `POST /api/archives/documents/{id}/grants`, `GET /api/archives/documents/{id}` and `GET /api/archives/documents/{id}/versions/{version}/download`; every GET checks authorization before reading storage.
- [ ] Run archive API tests; expect PASS.
- [ ] Commit API and tests.

### Task 4: 文档、演示数据与回归

**Files:**
- Modify: `scripts/seed_demo_data.py`
- Modify: `README.md`
- Test: `tests/test_seed_demo_data.py`

- [ ] Add a failing seed test for one document and one archive-admin account.
- [ ] Implement idempotent archive demo metadata (no real personal file content), update README with storage path and roles.
- [ ] Run `python -m pytest -q -p no:cacheprovider --basetemp .pytest-tmp`; expect PASS.
- [ ] Commit documentation and seed updates.

## Self-review

The plan covers immutable versions, read-only grants, students denied access, audit evidence, and replaceable file storage. Anonymous complaints and psychological risk records are intentionally excluded because they have separate privacy policies.

