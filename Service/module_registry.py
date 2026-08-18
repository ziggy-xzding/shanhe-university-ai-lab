"""Role-aware navigation registry for the university workspace."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleDefinition:
    key: str
    label: str
    icon: str
    href: str
    roles: frozenset[str]


@dataclass(frozen=True)
class NavSection:
    label: str
    modules: tuple[ModuleDefinition, ...]


MODULES = (
    ModuleDefinition("growth-center", "学生发展", "bi-bar-chart-line", "/pages/student-agent", frozenset({"student"})),
    ModuleDefinition("enrollment", "选课中心", "bi-calendar2-check", "/pages/course-selection", frozenset({"student"})),
    ModuleDefinition("grades", "我的成绩单", "bi-mortarboard", "/pages/transcript", frozenset({"student"})),
    ModuleDefinition("student-affairs", "学生事务", "bi-heart-pulse", "/pages/student-affairs", frozenset({"admin", "student_affairs", "counselor", "student"})),
    ModuleDefinition("complaints", "问题与建议", "bi-chat-left-text", "/pages/complaints", frozenset({"admin", "student_affairs", "student"})),
    ModuleDefinition("library", "图书借阅", "bi-book", "/pages/library", frozenset({"student"})),
    ModuleDefinition("campus-life", "生活服务", "bi-house-heart", "/pages/campus-life", frozenset({"staff", "student_affairs"})),
    ModuleDefinition("career", "就业指导", "bi-briefcase", "/pages/career", frozenset({"student", "teacher", "staff"})),
    ModuleDefinition("mental-health", "心理健康", "bi-heart-pulse", "/pages/mental-health", frozenset({"counselor", "student_affairs"})),
    ModuleDefinition("teaching", "课程与教学班", "bi-journal-bookmark", "/pages/academic-management", frozenset({"admin", "academic_admin", "teacher"})),
    ModuleDefinition("organization", "课程设计与专业", "bi-buildings", "/pages/organization-curriculum", frozenset({"admin", "academic_admin", "college_admin", "teacher"})),
    ModuleDefinition("grade-entry", "成绩录入", "bi-clipboard-check", "/pages/grade-entry", frozenset({"teacher"})),
    ModuleDefinition("student-profile", "学生档案管理", "bi-person-vcard", "/pages/students", frozenset({"admin", "college_admin"})),
    ModuleDefinition("grade-approval", "成绩审核", "bi-check2-square", "/pages/grade-approval", frozenset({"admin", "academic_admin"})),
    ModuleDefinition("university-statistics", "高校统计概览", "bi-graph-up", "/pages/university-statistics", frozenset({"admin", "college_admin", "academic_admin"})),
    ModuleDefinition("staff", "教师基础管理", "bi-people", "/pages/staff-management", frozenset({"admin"})),
    ModuleDefinition("risk-alerts", "心理风险预警", "bi-shield-exclamation", "/pages/risk-alerts", frozenset({"counselor"})),
    ModuleDefinition("archives", "电子档案", "bi-folder2-open", "/pages/archive-management", frozenset({"admin", "archive_admin"})),
    ModuleDefinition("campus-agent", "山河智能中枢", "bi-robot", "/pages/campus-assistant", frozenset({"admin", "college_admin", "academic_admin", "student_affairs", "counselor", "teacher", "archive_admin", "staff", "student"})),
)


def _by_key(key: str) -> ModuleDefinition:
    return next(module for module in MODULES if module.key == key)


def modules_for_role(role: str) -> tuple[ModuleDefinition, ...]:
    """Return regular navigation items; the intelligent center is rendered separately."""
    return tuple(module for module in MODULES if module.key != "campus-agent" and role in module.roles)


def agent_module_for_role(role: str) -> ModuleDefinition | None:
    module = _by_key("campus-agent")
    return module if role in module.roles else None


def nav_sections_for_role(role: str) -> tuple[NavSection, ...]:
    if role == "student":
        keys = ("growth-center", "enrollment", "grades", "student-affairs", "complaints", "library", "career")
        return (NavSection("学生模块", tuple(_by_key(key) for key in keys)),)
    if role == "teacher":
        keys = ("teaching", "organization", "grade-entry", "career")
        return (NavSection("教师模块", tuple(_by_key(key) for key in keys)),)
    if role == "admin":
        student_keys = ("student-profile", "student-affairs", "complaints")
        teacher_keys = ("staff", "teaching", "organization", "grade-approval", "university-statistics")
        return (
            NavSection("学生模块", tuple(_by_key(key) for key in student_keys)),
            NavSection("教师模块", tuple(_by_key(key) for key in teacher_keys)),
        )
    return (NavSection("校园服务", modules_for_role(role)),)
