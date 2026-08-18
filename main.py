from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import uvicorn
from DAO.db import engine, Base, ensure_schema_compatibility
from Model.department_table import Department
from Model.staff_account_table import StaffAccount
from Model.auth_login_log_table import AuthLoginLog
from Model.agent_session_table import AgentSession
from Model.agent_message_table import AgentMessage
from Model.agent_report_table import AgentReport
from Model import university_tables  # noqa: F401
from Model import archive_tables  # noqa: F401
from Model import complaint_tables  # noqa: F401
from Model import risk_alert_tables  # noqa: F401
from Model import student_affairs_tables  # noqa: F401
from Model import platform_tables  # noqa: F401
from Api.frontend_api import approuter_frontend
from Api.sanguo_api import sanguo_router
from Api.rag_api import rag_router
from Api.auth_api import auth_router
from Api.teacher_workbench_api import teacher_workbench_router
from Api.admin_staff_api import admin_staff_router
from Api.university_academic_api import university_academic_router
from Api.university_import_api import university_import_router
from Api.university_student_api import university_student_router
from Api.university_statistics_api import university_statistics_router
from Api.archive_api import archive_router
from Api.complaint_api import complaint_router
from Api.risk_alert_api import risk_alert_router
from Api.campus_assistant_api import campus_assistant_router
from Api.multi_agent_api import router as multi_agent_router
from Api.platform_api import router as platform_router
from Api.student_agent_api import student_agent_router
from Api.student_affairs_api import student_affairs_router
from Api.university_department_api import department_router

import asyncio
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)
    await asyncio.to_thread(ensure_schema_compatibility)
    yield

app = FastAPI(title="山河大学学生管理系统", version="1.0.0", lifespan=lifespan)

CORS_ALLOW_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://127.0.0.1:8801,http://localhost:8801",
    ).split(",")
    if origin.strip()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(approuter_frontend)
app.include_router(sanguo_router)
app.include_router(rag_router)
app.include_router(auth_router)
app.include_router(teacher_workbench_router)
app.include_router(admin_staff_router)
app.include_router(university_academic_router)
app.include_router(university_import_router)
app.include_router(university_student_router)
app.include_router(university_statistics_router)
app.include_router(archive_router)
app.include_router(complaint_router)
app.include_router(risk_alert_router)
app.include_router(campus_assistant_router)
app.include_router(multi_agent_router)
app.include_router(platform_router)
app.include_router(student_agent_router)
app.include_router(student_affairs_router)
app.include_router(department_router)

app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=BASE_DIR / "js"), name="js")
app.mount("/img", StaticFiles(directory=BASE_DIR / "img"), name="img")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/pages/login")


if __name__ == '__main__':
    import os as _os
    _host = _os.getenv("APP_HOST", "0.0.0.0")
    _port = int(_os.getenv("APP_PORT", "8801"))
    uvicorn.run(app, host=_host, port=_port)
