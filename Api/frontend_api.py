"""
前端页面路由 — Jinja2 模板渲染
================================
提供完整的系统前端界面。
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from sqlalchemy import text
from DAO.db import get_db
from DAO import employment_dao
from Service.auth_service import AuthPrincipal
from Service.authorization import get_current_principal
from Service.module_registry import agent_module_for_role, modules_for_role, nav_sections_for_role

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))

approuter_frontend = APIRouter(prefix="/pages")


def _render(template_name: str, context: dict) -> HTMLResponse:
    template = _env.get_template(template_name)
    render_context = dict(context)
    principal = render_context.get("principal")
    if principal is not None:
        render_context.setdefault("modules", modules_for_role(principal.role))
        render_context.setdefault("nav_sections", nav_sections_for_role(principal.role))
        render_context.setdefault("agent_module", agent_module_for_role(principal.role))
    return HTMLResponse(template.render(**render_context))


def _require_page_role(
    request: Request,
    db: Session,
    allowed_roles: set[str],
) -> AuthPrincipal | RedirectResponse:
    try:
        principal = get_current_principal(request, db)
    except HTTPException:
        return RedirectResponse("/pages/login", status_code=307)
    if principal.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="当前身份无权访问该页面")
    return principal


def _admin_context(request: Request, db: Session, active: str) -> dict | RedirectResponse:
    principal = _require_page_role(request, db, {"admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return {"request": request, "active": active, "principal": principal}


@approuter_frontend.get("/login")
def page_login(request: Request):
    return _render("login.html", {"request": request})


@approuter_frontend.get("/student-agent")
def page_student_agent(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"student"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "student_agent.html",
        {"request": request, "principal": principal, "active": "student-agent"},
    )


@approuter_frontend.get("/admin-modules")
def page_admin_modules(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "admin_modules.html",
        {"request": request, "principal": principal, "active": "admin-modules", "modules": modules_for_role("admin")},
    )


@approuter_frontend.get("/campus-assistant")
def page_campus_assistant(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(
        request,
        db,
        {"admin", "college_admin", "academic_admin", "student_affairs", "counselor", "teacher", "archive_admin", "staff", "student"},
    )
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "campus_assistant.html",
        {"request": request, "principal": principal, "active": "campus-agent"},
    )


def _page_service_module(request: Request, db: Session, roles: set[str], title: str, description: str, kind: str):
    principal = _require_page_role(request, db, roles)
    if isinstance(principal, RedirectResponse):
        return principal
    return _render("service_module.html", {"request": request, "principal": principal, "active": kind, "module_title": title, "module_description": description, "module_kind": kind})


@approuter_frontend.get("/campus-life")
def page_campus_life(request: Request, db: Session = Depends(get_db)):
    return _page_service_module(request, db, {"staff", "student_affairs"}, "生活服务", "宿舍、校园活动、报修和校园日常服务统一入口。", "campus-life")


@approuter_frontend.get("/library")
def page_library(request: Request, db: Session = Depends(get_db)):
    return _page_service_module(request, db, {"student"}, "图书借阅", "查看当前借阅、归还日期和逾期提醒；后续可接入学校图书馆系统。", "library")


@approuter_frontend.get("/career")
def page_career(request: Request, db: Session = Depends(get_db)):
    return _page_service_module(request, db, {"student", "teacher", "staff"}, "就业指导", "岗位信息、实习实践、简历与职业规划服务。", "career")


@approuter_frontend.get("/mental-health")
def page_mental_health(request: Request, db: Session = Depends(get_db)):
    return _page_service_module(request, db, {"student", "counselor", "student_affairs"}, "心理健康", "情绪打卡、心理科普和专业咨询转介入口。", "mental-health")


@approuter_frontend.get("/teacher-dashboard")
def page_teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"teacher", "admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "teacher_dashboard.html",
        {"request": request, "principal": principal, "active": "teacher-dashboard"},
    )


@approuter_frontend.get("/grade-entry")
def page_grade_entry(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"teacher"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "grade_entry.html",
        {"request": request, "principal": principal, "active": "grade-entry"},
    )


@approuter_frontend.get("/grade-approval")
def page_grade_approval(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin", "academic_admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "grade_approval.html",
        {"request": request, "principal": principal, "active": "grade-approval"},
    )


@approuter_frontend.get("/university-dashboard")
def page_university_dashboard(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(
        request,
        db,
        {
            "admin", "college_admin", "academic_admin", "student_affairs",
            "counselor", "teacher", "archive_admin", "staff", "student",
        },
    )
    if isinstance(principal, RedirectResponse):
        return principal
    if principal.role == "admin":
        return RedirectResponse("/pages/admin-modules", status_code=307)
    return _render(
        "university_dashboard.html",
        {
            "request": request,
            "principal": principal,
            "active": "university-dashboard",
            "modules": modules_for_role(principal.role),
        },
    )


@approuter_frontend.get("/academic-management")
def page_academic_management(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin", "academic_admin", "teacher"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "academic_management.html",
        {"request": request, "principal": principal, "active": "academic-management"},
    )


@approuter_frontend.get("/organization-curriculum")
def page_organization_curriculum(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin", "academic_admin", "college_admin", "teacher"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "organization_curriculum.html",
        {"request": request, "principal": principal, "active": "organization-curriculum"},
    )


@approuter_frontend.get("/data-import")
def page_data_import(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin", "college_admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "data_import.html",
        {"request": request, "principal": principal, "active": "data-import"},
    )


@approuter_frontend.get("/university-statistics")
def page_university_statistics(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin", "college_admin", "academic_admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "university_statistics.html",
        {"request": request, "principal": principal, "active": "university-statistics"},
    )


@approuter_frontend.get("/staff-management")
def page_staff_management(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "staff_management.html",
        {"request": request, "principal": principal, "active": "staff-management"},
    )


@approuter_frontend.get("/student-affairs")
def page_student_affairs(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(
        request,
        db,
        {"admin", "student_affairs", "counselor", "student"},
    )
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "student_affairs.html",
        {"request": request, "principal": principal, "active": "student-affairs"},
    )


@approuter_frontend.get("/complaints")
def page_complaints(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin", "student_affairs", "student"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "complaints.html",
        {"request": request, "principal": principal, "active": "complaints"},
    )


@approuter_frontend.get("/risk-alerts")
def page_risk_alerts(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"counselor"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "risk_alerts.html",
        {"request": request, "principal": principal, "active": "risk-alerts"},
    )


@approuter_frontend.get("/archive-management")
def page_archive_management(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"admin", "archive_admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "archive_management.html",
        {"request": request, "principal": principal, "active": "archive-management"},
    )


@approuter_frontend.get("/course-selection")
def page_course_selection(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"student"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "course_selection.html",
        {"request": request, "principal": principal, "active": "course-selection"},
    )


@approuter_frontend.get("/dorm-selection")
def page_dorm_selection(request: Request, db: Session = Depends(get_db)):
    """Keep old bookmarks working after dorm selection moved into Student Affairs."""
    return RedirectResponse(url="/pages/student-affairs", status_code=307)


@approuter_frontend.get("/transcript")
def page_transcript(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(request, db, {"student"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "transcript.html",
        {"request": request, "principal": principal, "active": "transcript"},
    )


# ============================================================
# 首页仪表盘
# ============================================================
@approuter_frontend.get("/dashboard")
def page_dashboard(request: Request, db: Session = Depends(get_db)):
    context = _admin_context(request, db, "dashboard")
    if isinstance(context, RedirectResponse):
        return context
    return RedirectResponse("/pages/university-dashboard", status_code=307)
    # 统计数据
    total_students = db.execute(text("SELECT COUNT(*) FROM students WHERE is_deleted=0")).scalar()
    total_employed = db.execute(text("SELECT COUNT(*) FROM employment WHERE is_deleted=0")).scalar()
    total_teachers = db.execute(text("SELECT COUNT(*) FROM teacher_table WHERE t_is_delete=0")).scalar()
    total_classes = db.execute(text("SELECT COUNT(*) FROM classes WHERE is_deleted=0")).scalar()
    unemployed = total_students - total_employed
    rate = round(total_employed / total_students * 100, 1) if total_students > 0 else 0

    context.update({
        "stats": {
            "students": total_students, "employed": total_employed,
            "teachers": total_teachers, "classes": total_classes,
            "unemployed": unemployed, "employment_rate": rate,
        },
        "top5": employment_dao.dao_top5_salary(db),
        "class_avg": employment_dao.dao_class_avg_employment_duration(db),
    })
    return _render("dashboard.html", context)


# ============================================================
# 学生列表
# ============================================================
@approuter_frontend.get("/students")
def page_students(
    request: Request,
    name: Optional[str] = Query(None),
    class_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    principal = _require_page_role(request, db, {"admin", "college_admin"})
    if isinstance(principal, RedirectResponse):
        return principal
    return _render(
        "student_management.html",
        {"request": request, "principal": principal, "active": "students"},
    )
    context = _admin_context(request, db, "students")
    if isinstance(context, RedirectResponse):
        return context
    sql = """
        SELECT s.student_no, s.name, c.name AS class_name, s.age, s.gender,
               s.education, s.major, s.graduate_school,
               CASE WHEN e.student_no IS NOT NULL THEN 1 ELSE 0 END AS employed
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id AND c.is_deleted = 0
        LEFT JOIN employment e ON s.student_no = e.student_no AND e.is_deleted = 0
        WHERE s.is_deleted = 0
    """
    params = {}
    if name:
        sql += " AND s.name LIKE :name"
        params["name"] = f"%{name}%"
    if class_id:
        sql += " AND s.class_id = :cid"
        params["cid"] = int(class_id)
    sql += " ORDER BY s.student_no"

    rows = db.execute(text(sql), params).mappings().all()
    classes = db.execute(text("SELECT id, name FROM classes WHERE is_deleted=0")).mappings().all()

    context.update({
        "rows": rows, "classes": classes,
        "name": name or "", "class_id": class_id or "",
    })
    return _render("student_list.html", context)


# ============================================================
# 成绩列表
# ============================================================
@approuter_frontend.get("/scores")
def page_scores(
    request: Request,
    student_no: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    context = _admin_context(request, db, "scores")
    if isinstance(context, RedirectResponse):
        return context
    return RedirectResponse("/pages/grade-approval", status_code=307)
    sql = """
        SELECT sc.student_no, s.name AS student_name, sc.exam_seq, sc.score
        FROM scores sc
        JOIN students s ON sc.student_no = s.student_no AND s.is_deleted = 0
        WHERE sc.is_deleted = 0
    """
    params = {}
    if student_no:
        sql += " AND sc.student_no = :no"
        params["no"] = student_no
    sql += " ORDER BY sc.student_no, sc.exam_seq"

    rows = db.execute(text(sql), params).mappings().all()
    context.update({
        "rows": rows, "student_no": student_no or "",
    })
    return _render("score_list.html", context)


# ============================================================
# 就业列表
# ============================================================
@approuter_frontend.get("/employment")
def page_employment(
    request: Request,
    student_name: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    min_salary: Optional[str] = Query(None),
    max_salary: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
):
    raise HTTPException(
        status_code=410,
        detail="旧就业管理页面已由学生事务中的毕业去向模块替代。",
    )


# ============================================================
# 统计看板
# ============================================================
@approuter_frontend.get("/statistics")
def page_statistics(request: Request, db: Session = Depends(get_db)):
    context = _admin_context(request, db, "statistics")
    if isinstance(context, RedirectResponse):
        return context
    return RedirectResponse("/pages/university-statistics", status_code=307)
    # 8大统计查询
    overage = db.execute(text(
        "SELECT s.student_no, s.name, s.age, s.gender, c.name AS class_name "
        "FROM students s LEFT JOIN classes c ON s.class_id=c.id AND c.is_deleted=0 "
        "WHERE s.age>30 AND s.is_deleted=0 ORDER BY s.age DESC"
    )).mappings().all()
    gender_stats = db.execute(text(
        "SELECT c.name AS class_name, COUNT(s.id) AS total, "
        "SUM(CASE WHEN s.gender='男' THEN 1 ELSE 0 END) AS male, "
        "SUM(CASE WHEN s.gender='女' THEN 1 ELSE 0 END) AS female "
        "FROM classes c LEFT JOIN students s ON s.class_id=c.id AND s.is_deleted=0 "
        "WHERE c.is_deleted=0 GROUP BY c.id, c.name ORDER BY total DESC"
    )).mappings().all()
    above80 = db.execute(text(
        "SELECT s.student_no, s.name AS student_name, c.name AS class_name, "
        "GROUP_CONCAT(sc.score ORDER BY sc.exam_seq) AS scores, "
        "ROUND(AVG(sc.score),1) AS avg_score, COUNT(sc.id) AS exam_count "
        "FROM students s JOIN scores sc ON sc.student_no=s.student_no AND sc.is_deleted=0 "
        "LEFT JOIN classes c ON s.class_id=c.id AND c.is_deleted=0 "
        "WHERE s.is_deleted=0 GROUP BY s.student_no, s.name, c.name HAVING MIN(sc.score)>=80 ORDER BY s.student_no"
    )).mappings().all()
    failed = db.execute(text(
        "SELECT s.name AS student_name, c.name AS class_name, COUNT(sc.id) AS fail_count, "
        "GROUP_CONCAT(sc.score ORDER BY sc.exam_seq) AS fail_scores "
        "FROM students s JOIN scores sc ON sc.student_no=s.student_no AND sc.is_deleted=0 AND sc.score<60 "
        "LEFT JOIN classes c ON s.class_id=c.id AND c.is_deleted=0 "
        "WHERE s.is_deleted=0 GROUP BY s.student_no, s.name, c.name HAVING COUNT(sc.id)>=2 ORDER BY s.name"
    )).mappings().all()
    class_avg_score = db.execute(text(
        "SELECT sc.exam_seq, c.name AS class_name, ROUND(AVG(sc.score),1) AS avg_score "
        "FROM scores sc JOIN students s ON sc.student_no=s.student_no AND s.is_deleted=0 "
        "JOIN classes c ON s.class_id=c.id AND c.is_deleted=0 "
        "WHERE sc.is_deleted=0 GROUP BY sc.exam_seq, c.name ORDER BY sc.exam_seq, avg_score DESC"
    )).mappings().all()

    context.update({
        "top5": employment_dao.dao_top5_salary(db),
        "durations": employment_dao.dao_employment_duration(db),
        "class_avg": employment_dao.dao_class_avg_employment_duration(db),
        "overage": overage, "gender_stats": gender_stats,
        "above80": above80, "failed": failed,
        "class_avg_score": class_avg_score,
    })
    return _render("statistics.html", context)


# ============================================================
# 教师列表
# ============================================================
@approuter_frontend.get("/teachers")
def page_teachers(request: Request, db: Session = Depends(get_db)):
    context = _admin_context(request, db, "teachers")
    if isinstance(context, RedirectResponse):
        return context
    return RedirectResponse("/pages/staff-management", status_code=307)
    rows = db.execute(text(
        "SELECT tid, tname, tphone, tsubject, t_code FROM teacher_table WHERE t_is_delete=0 ORDER BY tid"
    )).mappings().all()
    context["rows"] = rows
    return _render("teacher_list.html", context)


# ============================================================
# 班级列表
# ============================================================
@approuter_frontend.get("/classes")
def page_classes(request: Request, db: Session = Depends(get_db)):
    context = _admin_context(request, db, "classes")
    if isinstance(context, RedirectResponse):
        return context
    return RedirectResponse("/pages/data-import", status_code=307)
    rows = db.execute(text("""
        SELECT c.class_no, c.name, c.start_date, c.head_teacher_id, c.instructor_id,
               th.tname AS head_teacher_name, ti.tname AS instructor_name,
               (SELECT COUNT(*) FROM students s WHERE s.class_id = c.id AND s.is_deleted = 0) AS student_count
        FROM classes c
        LEFT JOIN teacher_table th ON c.head_teacher_id = th.tid AND th.t_is_delete = 0
        LEFT JOIN teacher_table ti ON c.instructor_id = ti.tid AND ti.t_is_delete = 0
        WHERE c.is_deleted = 0 ORDER BY c.class_no
    """)).mappings().all()
    context["rows"] = rows
    return _render("class_list.html", context)


# ============================================================
# 部门列表
# ============================================================
@approuter_frontend.get("/departments")
def page_departments(request: Request, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=410,
        detail="旧部门管理页面已退役；请在教职工管理中维护人员部门归属。",
    )


# ============================================================
# 顾问列表
# ============================================================
@approuter_frontend.get("/consultants")
def page_consultants(request: Request, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=410,
        detail="顾问管理属于旧教培业务，已由高校角色与学生事务模块替代。",
    )


# ============================================================
# 三国知识问答
# ============================================================
@approuter_frontend.get("/sanguo")
def page_sanguo(request: Request, db: Session = Depends(get_db)):
    principal = _require_page_role(
        request,
        db,
        {"admin", "college_admin", "academic_admin", "student_affairs", "counselor", "teacher", "archive_admin", "staff", "student"},
    )
    if isinstance(principal, RedirectResponse):
        return principal
    return _render("sanguo_chat.html", {"request": request, "active": "sanguo", "principal": principal})


# ============================================================
# 风电知识库问答
# ============================================================
@approuter_frontend.get("/windfarm")
def page_windfarm(request: Request, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=410,
        detail="风电知识问答不属于高校学生管理系统，已下线。",
    )
