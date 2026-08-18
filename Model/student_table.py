"""
学生表 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey,DateTime
from sqlalchemy.orm import relationship
from DAO.db import Base
from sqlalchemy.orm import relationship
from Model.class_table import Class
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="学生ID")
    student_no = Column(String(20), unique=True, nullable=False, comment="学生编号")
    name = Column(String(20), nullable=False, comment="姓名")
    password_hash = Column(String(255), nullable=True, comment="学生登录密码哈希")
    class_id = Column(Integer, comment="班级ID")
    hometown = Column(String(50), comment="籍贯")
    graduate_school = Column(String(50), comment="毕业院校")
    major = Column(String(50), comment="专业")
    enrollment_time = Column(DateTime, comment="入学时间")
    graduation_time = Column(DateTime, comment="毕业时间")
    education = Column(String(10), comment="学历")
    advisor_id = Column(Integer, comment="顾问编号")
    age = Column(Integer, comment="年龄")
    gender = Column(String(3), comment="性别")
    is_deleted = Column(Boolean, default=False, comment='逻辑删除字段:False=未删除, True=已删除')
    employment = relationship("Employment", back_populates="student", uselist=False, foreign_keys="Employment.student_no")
