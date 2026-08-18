# 高校管理系统基础能力实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** 在不破坏当前学生、教师与认证数据的前提下，交付可扩展的高校组织、教学、选课、Excel 导入和角色化入口。

**Architecture:** 新高校业务以独立模型、服务与 API 模块接入。旧 \`students\`、\`classes\` 和 \`teacher_table\` 保持可用；高校字段由新的一对一档案表承载，教学班和选课使用新表，后续档案、投诉和 Agent 可复用相同权限和模块注册边界。

**Tech Stack:** Python 3.10、FastAPI、SQLAlchemy 2、Pydantic 2、MySQL、pandas、pytest。

## Global Constraints

- 保持现有学生验证、教师登录和页面路径可用；新 API 统一使用 \`/api/university\`。
- 角色只能取 \`admin\`、\`college_admin\`、\`academic_admin\`、\`student_affairs\`、\`counselor\`、\`teacher\`、\`archive_admin\`、\`staff\`、\`student\`。
- 新列表接口必须分页，默认 \`page=1,page_size=20\`，上限 100。
- 权限必须在服务端按角色、学院、部门、班级和个人范围校验；隐藏菜单不构成授权。
- 不删除现有业务数据；迁移只能创建新增表和索引，必须可重复执行。
- Excel 导入必须预校验、逐行报错、确认入库、生成批次审计且重复确认不重复写入。
- 每个任务必须严格执行先失败测试、后最小实现、再通过测试的 TDD 周期。

---

## 文件结构

| 文件 | 职责 |
| --- | --- |
| \`Model/university_tables.py\` | 新高校领域 ORM。 |
| \`Schema/university_schema.py\` | 新 API 请求、响应和分页模型。 |
| \`Service/data_scope.py\` | 服务端数据范围校验。 |
| \`Service/academic_service.py\` | 教学班、选课、退选和成绩事务。 |
| \`Service/excel_import_service.py\` | Excel 预览、校验、确认与批次审计。 |
| \`Service/module_registry.py\` | 根据角色显示可增减的系统模块。 |
| \`Api/university_academic_api.py\` | 高校教学 API。 |
| \`Api/university_import_api.py\` | 批量导入 API。 |
| \`scripts/migrate_university_schema.py\` | 仅创建新增表的迁移入口。 |

## Task 1: 建立高校领域模型和安全迁移

**Files:**
- Create: \`Model/university_tables.py\`
- Create: \`scripts/migrate_university_schema.py\`
- Modify: \`main.py\`
- Test: \`tests/test_university_models.py\`

**Interfaces:**
- Produces: \`College\`、\`Major\`、\`AcademicTerm\`、\`Course\`、\`TeachingSection\`、\`CourseEnrollment\`、\`StudentAcademicProfile\`、\`StaffProfile\`、\`ImportBatch\`、\`ImportRowError\`。
- Consumes: \`Student.student_no\`、\`Class.id\`、\`teacher_table.tid\`。

- [ ] **Step 1: Write the failing test**

~~~python
def test_enrollment_is_unique_per_student_and_section(test_session):
    from sqlalchemy.exc import IntegrityError
    from Model.university_tables import CourseEnrollment, TeachingSection

    section = TeachingSection(
        course_code="CS101", term_code="2026-2027-1", capacity=40,
        selection_open_at=datetime(2026, 8, 1), selection_close_at=datetime(2026, 9, 1),
        timetable_json=[],
    )
    test_session.add(section)
    test_session.flush()
    test_session.add_all([
        CourseEnrollment(student_no="ST2401001", teaching_section_id=section.id, status="enrolled"),
        CourseEnrollment(student_no="ST2401001", teaching_section_id=section.id, status="enrolled"),
    ])
    with pytest.raises(IntegrityError):
        test_session.commit()
~~~

- [ ] **Step 2: Verify RED**

Run: \`python -m pytest tests/test_university_models.py::test_enrollment_is_unique_per_student_and_section -q\`

Expected: FAIL with \`ModuleNotFoundError\`.

- [ ] **Step 3: Write the minimal implementation**

Create all ten ORM models. The required unique/index definitions are:

~~~python
class Major(Base):
    __tablename__ = "majors"
    __table_args__ = (UniqueConstraint("college_id", "code", name="uq_major_college_code"),)
    id = Column(Integer, primary_key=True)
    college_id = Column(ForeignKey("colleges.id"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active")

class TeachingSection(Base):
    __tablename__ = "teaching_sections"
    __table_args__ = (Index("ix_section_term_course", "term_code", "course_code"),)
    id = Column(Integer, primary_key=True)
    course_code = Column(String(30), nullable=False, index=True)
    term_code = Column(String(20), nullable=False, index=True)
    teacher_id = Column(ForeignKey("teacher_table.tid"))
    capacity = Column(Integer, nullable=False)
    enrolled_count = Column(Integer, nullable=False, default=0)
    selection_open_at = Column(DateTime, nullable=False)
    selection_close_at = Column(DateTime, nullable=False)
    timetable_json = Column(JSON, nullable=False, default=list)

class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("student_no", "teaching_section_id", name="uq_enrollment_student_section"),)
    id = Column(Integer, primary_key=True)
    student_no = Column(ForeignKey("students.student_no"), nullable=False, index=True)
    teaching_section_id = Column(ForeignKey("teaching_sections.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="enrolled")
    enrolled_at = Column(DateTime, nullable=False, default=datetime.now)
~~~

\`College\` uses \`code,name,status\`; \`Course\` uses \`code,name,credits,hours,status\`; \`AcademicTerm\` uses \`code,name,starts_at,ends_at\`; \`StudentAcademicProfile\` uses \`student_no,college_id,major_id,grade,class_id,status,phone\`; \`StaffProfile\` uses \`staff_no,college_id,department_id,position\`; \`ImportBatch\` uses \`kind,checksum,status,created_by,confirmed_at\`; \`ImportRowError\` uses \`batch_id,row_number,field,message\`. Add indexes for each foreign key and status filter. Import the module in \`main.py\`. The migration script must run only \`Base.metadata.create_all(bind=engine)\`; it must never call drop/delete.

- [ ] **Step 4: Verify GREEN**

Run: \`python -m pytest tests/test_university_models.py -q\`

Expected: PASS; duplicate enrollment violates the database unique constraint.

- [ ] **Step 5: Commit**

~~~powershell
git add Model/university_tables.py scripts/migrate_university_schema.py main.py tests/test_university_models.py
git commit -m "feat: add extensible university domain models"
~~~

## Task 2: 扩展身份角色和数据范围服务

**Files:**
- Modify: \`Service/auth_service.py\`
- Modify: \`Service/authorization.py\`
- Create: \`Service/data_scope.py\`
- Test: \`tests/test_university_authorization.py\`

**Interfaces:**
- Produces: \`assert_college_scope(db, principal, college_id)\`、\`assert_student_scope(db, principal, student_no)\`、\`assert_section_scope(db, principal, section)\`。
- Error: 无权访问必须抛 \`HTTPException(status_code=403)\`。

- [ ] **Step 1: Write the failing test**

~~~python
def test_college_admin_cannot_read_foreign_student(seeded_university_db):
    db, college_admin, foreign_student_no = seeded_university_db
    with pytest.raises(HTTPException) as exc:
        assert_student_scope(db, college_admin, foreign_student_no)
    assert exc.value.status_code == 403
~~~

- [ ] **Step 2: Verify RED**

Run: \`python -m pytest tests/test_university_authorization.py::test_college_admin_cannot_read_foreign_student -q\`

Expected: FAIL because \`assert_student_scope\` is absent.

- [ ] **Step 3: Write the minimal implementation**

Add optional \`staff_id,college_id,department_id\` to \`AuthPrincipal\` and its JWT payload. Expand token validation to the nine global roles. Implement these exact rules: \`admin\` and \`academic_admin\` have all teaching scope; \`college_admin\` and \`archive_admin\` require matching \`college_id\`; \`teacher\` requires \`section.teacher_id == principal.teacher_id\`; \`student\` requires \`student_no == principal.subject_id\`; all other cases raise 403. Preserve the existing \`require_roles(*roles)\` callable API.

- [ ] **Step 4: Verify GREEN**

Run: \`python -m pytest tests/test_auth_service.py tests/test_teacher_authorization.py tests/test_university_authorization.py -q\`

Expected: PASS, including the pre-existing teacher/admin tests.

- [ ] **Step 5: Commit**

~~~powershell
git add Service/auth_service.py Service/authorization.py Service/data_scope.py tests/test_university_authorization.py
git commit -m "feat: enforce university data scopes"
~~~

## Task 3: 实现课程、教学班、选课和成绩工作流

**Files:**
- Create: \`Schema/university_schema.py\`
- Create: \`Service/academic_service.py\`
- Create: \`Api/university_academic_api.py\`
- Modify: \`main.py\`
- Test: \`tests/test_academic_api.py\`

**Interfaces:**
- Produces: \`POST /api/university/sections/{section_id}/enrollments\`、\`DELETE /api/university/sections/{section_id}/enrollments/me\`、\`POST /api/university/sections/{section_id}/grades\`、\`GET /api/university/me/schedule\`。
- Produces: \`enroll_student(db, student_no, section_id, now)\` and \`submit_grade(db, teacher_id, student_no, section_id, score)\`.

- [ ] **Step 1: Write the failing test**

~~~python
def test_student_cannot_enroll_when_section_is_full(student_client, full_section):
    response = student_client.post(f"/api/university/sections/{full_section.id}/enrollments")
    assert response.status_code == 409
    assert response.json()["detail"] == "教学班人数已满"

def test_student_cannot_enroll_in_overlapping_section(student_client, overlapping_section):
    response = student_client.post(f"/api/university/sections/{overlapping_section.id}/enrollments")
    assert response.status_code == 409
    assert response.json()["detail"] == "课程时间冲突"
~~~

- [ ] **Step 2: Verify RED**

Run: \`python -m pytest tests/test_academic_api.py -q\`

Expected: FAIL with 404 because the router is not registered.

- [ ] **Step 3: Write the minimal implementation**

\`enroll_student\` must lock the section with \`with_for_update()\`, require active student status, require \`selection_open_at <= now <= selection_close_at\`, reject capacity/full, existing active enrollment, and overlapping \`timetable_json\`; on success insert \`status="enrolled"\` and increment \`enrolled_count\` in the same transaction. Drop changes status to \`dropped\` and decrements only within the same window. Grades use a unique \`(student_no, teaching_section_id)\` table, score 0–100, and initial \`submitted\` status; only the section teacher can submit and only \`academic_admin\` can approve.

- [ ] **Step 4: Verify GREEN**

Run: \`python -m pytest tests/test_academic_api.py tests/test_university_authorization.py -q\`

Expected: PASS; capacity, overlap, selection window and teacher scope return 4xx.

- [ ] **Step 5: Commit**

~~~powershell
git add Schema/university_schema.py Service/academic_service.py Api/university_academic_api.py main.py tests/test_academic_api.py
git commit -m "feat: add teaching sections and enrollment workflow"
~~~

## Task 4: 实现 Excel 预校验和可审计确认导入

**Files:**
- Create: \`Service/excel_import_service.py\`
- Create: \`Api/university_import_api.py\`
- Modify: \`main.py\`
- Test: \`tests/test_excel_import.py\`

**Interfaces:**
- Produces: \`POST /api/university/imports/students/preview\`、\`POST /api/university/imports/{batch_id}/confirm\`、\`GET /api/university/imports/{batch_id}\`。
- Produces: \`preview_student_import(db, file_bytes, actor)\` and \`confirm_student_import(db, batch_id, actor)\`.

- [ ] **Step 1: Write the failing test**

~~~python
def test_preview_reports_each_invalid_row(admin_client, invalid_student_workbook):
    response = admin_client.post("/api/university/imports/students/preview", files={"file": invalid_student_workbook})
    assert response.status_code == 200
    assert response.json()["errors"] == [
        {"row_number": 3, "field": "student_no", "message": "学号已存在"},
        {"row_number": 4, "field": "major_code", "message": "专业不存在"},
    ]

def test_confirming_same_batch_twice_is_idempotent(admin_client, valid_preview_batch):
    first = admin_client.post(f"/api/university/imports/{valid_preview_batch}/confirm")
    second = admin_client.post(f"/api/university/imports/{valid_preview_batch}/confirm")
    assert first.json()["created"] == 2
    assert second.json()["created"] == 0
~~~

- [ ] **Step 2: Verify RED**

Run: \`python -m pytest tests/test_excel_import.py -q\`

Expected: FAIL with 404.

- [ ] **Step 3: Write the minimal implementation**

Read only worksheet \`students\` using \`pandas.read_excel\`; require columns \`student_no,name,college_code,major_code,class_no,grade,phone\`. Preview computes SHA-256, writes \`ImportBatch(status="previewed")\` and one \`ImportRowError\` per invalid field without writing \`Student\`. Validate duplicate student number and referenced college/major/class. Confirm rejects batches with errors using 422; otherwise creates missing student plus \`StudentAcademicProfile\` in one transaction, marks the batch \`confirmed\`, and returns its historical result when already confirmed. Only \`admin\` and scope-matching \`college_admin\` may call these endpoints.

- [ ] **Step 4: Verify GREEN**

Run: \`python -m pytest tests/test_excel_import.py -q\`

Expected: PASS; invalid preview produces zero students, success confirmation is idempotent.

- [ ] **Step 5: Commit**

~~~powershell
git add Service/excel_import_service.py Api/university_import_api.py main.py tests/test_excel_import.py
git commit -m "feat: add audited student excel imports"
~~~

## Task 5: 实现按角色增减的模块化工作台

**Files:**
- Create: \`Service/module_registry.py\`
- Modify: \`Api/frontend_api.py\`
- Modify: \`templates/base.html\`
- Create: \`templates/university_dashboard.html\`
- Test: \`tests/test_role_dashboard.py\`

**Interfaces:**
- Produces: \`modules_for_role(role) -> tuple[ModuleDefinition, ...]\` and \`GET /pages/university-dashboard\`.

- [ ] **Step 1: Write the failing test**

~~~python
def test_student_dashboard_excludes_admin_modules(student_client):
    response = student_client.get("/pages/university-dashboard")
    assert response.status_code == 200
    assert "选课中心" in response.text
    assert "课程与教学班管理" not in response.text

def test_academic_admin_dashboard_includes_teaching_module(academic_admin_client):
    response = academic_admin_client.get("/pages/university-dashboard")
    assert "课程与教学班管理" in response.text
~~~

- [ ] **Step 2: Verify RED**

Run: \`python -m pytest tests/test_role_dashboard.py -q\`

Expected: FAIL with 404.

- [ ] **Step 3: Write the minimal implementation**

Define frozen \`ModuleDefinition(key, label, icon, href, roles)\`. Register separate entries for “学生档案、课程与教学班管理、选课中心、成绩管理、学院专业、教职工、学生事务、投诉建议、电子档案、关羽问答、校园智能助手”. \`modules_for_role\` filters only by the current role. The base template must loop over \`modules\`, not hard-code role branches. The new page supplies the current role’s modules and a minimal pending-work summary.

- [ ] **Step 4: Verify GREEN**

Run: \`python -m pytest tests/test_role_dashboard.py tests/test_student_pages.py tests/test_teacher_authorization.py -q\`

Expected: PASS; new modules are role-filtered and old pages remain reachable.

- [ ] **Step 5: Commit**

~~~powershell
git add Service/module_registry.py Api/frontend_api.py templates/base.html templates/university_dashboard.html tests/test_role_dashboard.py
git commit -m "feat: add role-aware modular university dashboard"
~~~

## Task 6: 演示数据、运行说明和全量验证

**Files:**
- Modify: \`scripts/seed_demo_data.py\`
- Modify: \`README.md\`
- Test: \`tests/test_seed_demo_data.py\`

**Interfaces:**
- Produces: \`seed_university_data(db) -> dict[str, int]\`, with 2 colleges, 4 majors, 4 classes, 48 students, 6 courses, 2 terms and teaching sections.

- [ ] **Step 1: Write the failing test**

~~~python
def test_seed_university_data_is_idempotent(db_session):
    first = seed_university_data(db_session)
    second = seed_university_data(db_session)
    assert first["students"] == second["students"] == 48
    assert first["courses"] == second["courses"] == 6
~~~

- [ ] **Step 2: Verify RED**

Run: \`python -m pytest tests/test_seed_demo_data.py::test_seed_university_data_is_idempotent -q\`

Expected: FAIL because the function is absent.

- [ ] **Step 3: Write the minimal implementation**

Implement get-or-create by business keys; never delete old rows. Update README with \`python scripts/migrate_university_schema.py\`, seed command, new roles, Excel columns and \`python -m pytest -q\`.

- [ ] **Step 4: Verify GREEN**

Run: \`python -m pytest -q\`

Expected: PASS without failures or errors.

- [ ] **Step 5: Commit**

~~~powershell
git add scripts/seed_demo_data.py README.md tests/test_seed_demo_data.py
git commit -m "docs: document university foundation workflow"
~~~

## Follow-up plans

After this independently usable foundation is accepted, write separate plans for electronic archives/object storage, student affairs and anonymous complaints, dual-Agent private conversation with risk escalation, and production queue/caching/load testing. Keeping them separate prevents sensitive archive and mental-health rules from destabilizing the core teaching release.

## Self-review

- The accepted design’s organization, personnel, courses, enrollment, import, role isolation and extensibility requirements are implemented by Tasks 1–6.
- Electronic archives, complaints and mental-health data are intentionally separated into dedicated follow-up plans due to their stricter privacy and storage requirements.
- Public interfaces remain consistent across tasks: \`TeachingSection\`, \`CourseEnrollment\`, \`StudentAcademicProfile\`, \`assert_student_scope\` and \`modules_for_role\`.

