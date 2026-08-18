"""
部门表 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Boolean,DateTime
from DAO.db import Base
from datetime import datetime

# 部门编号、名称、部门主管、办公位置、联系电话、状态
class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer,
                primary_key=True,
                autoincrement=True,
                comment="部门ID"
                )
    dept_no = Column(String(20),
                     nullable=False,
                     comment="部门编号"
                     )
    dept_name = Column(String(50),
                  nullable=False,
                  comment="部门名称"
                  )
    dept_manager = Column(String(20),
                     comment="部门负责人"
                     )
    dept_location = Column(String(50),
                     comment="办公位置"
                     )
    dept_phone = Column(String(20),
                      comment="联系电话"
                      )
    is_deleted = Column(Boolean,
                        default=False,
                        comment="删除标记"
                        )
    create_date = Column(DateTime
                         , default=datetime.now  # 默认值是创建的当时间
                         , nullable=False
                         )
    update_date = Column(DateTime
                         , default=datetime.now  # 默认值是创建的当时间
                         , nullable=False
                         , onupdate=datetime.now  # 后续更新这条数据时，自动赋值当时的时间记录
                         )
