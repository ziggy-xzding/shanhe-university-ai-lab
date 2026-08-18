from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Boolean, UniqueConstraint
from datetime import datetime
from DAO.db import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True, comment='成绩记录ID')
    student_no = Column(
        String(20),
        nullable=False,
        comment='学号'
        # 注意：移除外键
    )
    exam_seq = Column(Integer, nullable=False, comment='第几次考核')
    score = Column(DECIMAL(5, 2), nullable=False, comment='考核分数')  # ← 改为 DECIMAL
    is_deleted = Column(Boolean, nullable=False, default=False, comment='软删除标记')
    created_at = Column(
        DateTime,
        nullable=False,  # 改为 NOT NULL，与数据库一致
        default=datetime.now,
        comment='创建时间'
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment='更新时间'
    )

    __table_args__ = (
        UniqueConstraint('student_no', 'exam_seq', name='uq_student_exam'),
        # CheckConstraint 在 ORM 中定义，但数据库中也应该有
        # CheckConstraint('score >= 0 AND score <= 100', name='ck_score_range'),
    )