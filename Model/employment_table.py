"""
就业表 ORM 模型 — P5 负责
===========================
数据库表: employment (就业信息表)
设计要点:
  - student_id 是唯一外键，一个学生只有一条就业记录
  - student_name / class_name 是冗余字段，避免高频查询的 JOIN 开销
  - is_deleted 逻辑删除，保证数据可追溯
"""
from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from DAO.db import Base


class Employment(Base):
    __tablename__ = "employment"

    # ======================== 主键 ========================
    id = Column(Integer, primary_key=True, autoincrement=True, comment="就业记录ID（自增）")

    # ======================== 关联字段 ========================
    student_no = Column(
        String(20),
        ForeignKey("students.student_no"),
        unique=True,   # 一对一：一个学生一条就业记录
        comment="学号（外键 → students.student_no）"
    )

    # ======================== 关联字段（班级） ========================
    class_no = Column(
        String(20),
        ForeignKey("classes.class_no"),
        comment="班级编号（外键 → classes.class_no）"
    )

    # ======================== 冗余字段 ========================
    student_name = Column(String(20), comment="学生姓名（冗余字段）")
    class_no = Column(String(20), comment="班级编号（冗余字段）")
    class_name = Column(String(50), comment="班级名称（冗余字段）")

    # ======================== 业务字段 ========================
    open_time = Column(DateTime, comment="就业开放时间（学生进入就业阶段的时间）")
    offer_time = Column(DateTime, comment="Offer下发时间（拿到Offer的时间）")
    company = Column(String(100), comment="就业公司名称")
    salary = Column(DECIMAL(10, 2), comment="就业薪资（元/月）")

    # ======================== 逻辑删除 ========================
    is_deleted = Column(Boolean, default=False, comment="逻辑删除标记（True=已删除）")

    # ======================== ORM 关联 ========================
    student = relationship("Student", back_populates="employment", foreign_keys=[student_no])
