import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker,DeclarativeBase


load_dotenv()
_echo = os.getenv("DB_ECHO", "false").lower() == "true"
db_url = os.getenv("DATABASE_URL")
if db_url:
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, connect_args=connect_args, echo=_echo)
else:
    _db_host = os.getenv("DB_HOST", "127.0.0.1")
    _db_port = os.getenv("DB_PORT", "3306")
    _db_user = os.getenv("DB_USER", "root")
    _db_pass = os.getenv("DB_PASSWORD", "123456")
    _db_name = os.getenv("DB_NAME", "ai0522")
    db_url = (
        f"mysql+pymysql://{quote_plus(_db_user)}:{quote_plus(_db_pass)}"
        f"@{_db_host}:{_db_port}/{_db_name}?charset=utf8mb4"
    )
    engine = create_engine(
        db_url,
        pool_size=max(1, int(os.getenv("DB_POOL_SIZE", "10"))),
        max_overflow=max(0, int(os.getenv("DB_MAX_OVERFLOW", "20"))),
        pool_timeout=max(1, int(os.getenv("DB_POOL_TIMEOUT", "30"))),
        pool_recycle=max(60, int(os.getenv("DB_POOL_RECYCLE", "1800"))),
        pool_pre_ping=True,
        isolation_level=os.getenv("DB_ISOLATION_LEVEL", "READ COMMITTED"),
        echo=_echo,
    )
session = sessionmaker(bind=engine)
class Base(DeclarativeBase):
    pass
def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_compatibility() -> None:
    """Add small additive columns for databases created before the current model."""
    if "students" not in inspect(engine).get_table_names():
        return
    inspector = inspect(engine)
    with engine.begin() as connection:
        student_columns = {column["name"] for column in inspector.get_columns("students")}
        if "password_hash" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN password_hash VARCHAR(255)"))
        if "courses" in inspector.get_table_names():
            course_columns = {column["name"] for column in inspector.get_columns("courses")}
            if "course_type" not in course_columns:
                connection.execute(text("ALTER TABLE courses ADD COLUMN course_type VARCHAR(20) NOT NULL DEFAULT '必修课'"))
            if engine.dialect.name == "mysql":
                connection.execute(text("ALTER TABLE courses MODIFY credits DECIMAL(4,1) NOT NULL"))
        if "course_grades" in inspector.get_table_names():
            grade_columns = {column["name"] for column in inspector.get_columns("course_grades")}
            if "grade_label" not in grade_columns:
                connection.execute(text("ALTER TABLE course_grades ADD COLUMN grade_label VARCHAR(20) NULL"))
            if engine.dialect.name == "mysql":
                connection.execute(text("ALTER TABLE course_grades MODIFY score DECIMAL(5,2) NULL"))
