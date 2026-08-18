"""
班级数据访问层
===============
封装班级表的所有数据库操作，增删改查
"""
from Model.class_table import Class


def dao_get_class(id:int,db):
    q=db.query(Class).filter(Class.is_deleted == 0)
    if id:
        q=q.filter(Class.id == id)
    classinfo =q.all()
    if classinfo:
        return [{"class_id": i.id, "class_no": i.class_no, "name": i.name, "head_teacher_id": i.head_teacher_id,
                 "instructor_id": i.instructor_id} for i in classinfo]


def dao_create_class(db, data: dict) -> Class:
    """新增班级，返回 ORM 对象"""
    cls = Class(**data)   #字典解包 → 创建 Class ORM 对象
    db.add(cls)
    db.commit()
    db.refresh(cls)   #刷新对象（从库中查回最新数据，获取自增 ID）
    return cls     #返回含完整数据的 ORM 对象


def dao_update_class(id,c,db):  #更新班级信息
    try:
        rows=db.query(Class).filter(Class.id==id).update(c.model_dump(exclude_unset=True))#只更新前端传了的字段，不会把未提交字段置空覆盖原有数据库数据
        db.commit()
        return rows
    except :
        db.rollback()


def dao_delete_class(id,db):
    try:
        rows=db.query(Class).filter(Class.id == id).update({'is_deleted':1})
        db.commit()
        return rows
    except :
        db.rollback()
