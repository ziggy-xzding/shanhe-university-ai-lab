from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Index
from DAO.db import Base
from datetime import datetime

class Consultant(Base):
    __tablename__ = 'consultant'
    __table_args__ = (
        Index('ix_consultant_dept_deleted', 'dept_no', 'is_deleted'),
    )
    consultant_id = Column(
        Integer,
        primary_key = True,
        autoincrement = True,
        comment = '顾问ID'
    )
    consultant_no = Column(
        String(10),
        nullable = False,
        unique = True,
        comment = '顾问编号'
    )
    name = Column(
        String(20),
        nullable = False,
        comment = '顾问名字'
    )
    gender = Column(
        String(10),
        nullable = False,
        comment = '顾问性别'
    )
    phone = Column(
        String(11),
        nullable = False,
        comment = '顾问手机号'
    )
    email = Column(
        String(50),
        nullable = True,
        comment = '顾问邮箱'
    )
    dept_no = Column(
        String(20),
        nullable = False,
        index = True,
        comment = '顾问部门编号'
    )
    title = Column(
        String(20),
        nullable = False,
        comment = '顾问职称'
    )
    region = Column(
        String(20),
        nullable = True,
        comment = '顾问区域'
    )
    is_deleted = Column(
        Boolean,
        nullable = False,
        default = False,
        comment = '是否删除'
    )
    create_time = Column(
        DateTime,
        nullable = False,
        default = datetime.now,
        server_default = func.now(),
        comment = '创建时间'
    )
    update_time = Column(
        DateTime,
        nullable = False,
        default = datetime.now,
        onupdate = datetime.now,
        server_default = func.now(),
        comment = '更新时间'
    )