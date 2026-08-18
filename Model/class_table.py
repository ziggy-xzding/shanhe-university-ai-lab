"""
班级表 ORM 模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from DAO.db import Base


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="班级ID")
    class_no = Column(String(20), unique=True, nullable=False, comment="班级编号")
    name = Column(String(50), nullable=False, comment="班级名称")
    start_date = Column(DateTime, comment="开课时间")
    head_teacher_id = Column(Integer, comment="班主任")
    instructor_id = Column(Integer, comment="授课老师")
    is_deleted = Column(Integer, default=0, comment="逻辑删除标记")