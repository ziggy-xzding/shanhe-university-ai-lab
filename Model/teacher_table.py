from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import relationship
from DAO.db import Base
from sqlalchemy.dialects.mysql import DATETIME

class teacher_table(Base):
    __tablename__ = 'teacher_table'
    tid = Column(Integer, primary_key=True,autoincrement=True,nullable=False,comment='老师id')
    tname = Column(String(20), nullable=False,index=True, comment="姓名")
    tphone = Column(String(11), nullable=False, comment="电话")
    tsubject = Column(String(20), nullable=False, comment="所授科目")
    t_code = Column(Enum('在职','离职','停用',nullable=False), nullable=False,comment='状态')
    t_is_delete = Column(Boolean, default=False, comment="逻辑删除标记")
    create_date = Column(DATETIME(fsp=6), default=datetime.now, nullable=False)
    update_date = Column(DATETIME(fsp=6), default=datetime.now, nullable=False, onupdate=datetime.now)

    # head_classes_id = relationship("Class", foreign_keys="[Class.head_teacher_id]", back_populates="head_teacher_rel")
    # instruct_classes_id = relationship("Class", foreign_keys="[Class.instructor_id]", back_populates="instructor_rel")