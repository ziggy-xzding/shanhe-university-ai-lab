from typing import List

from sqlalchemy.orm import Session
from Model.teacher_table import teacher_table
from Schema.teacher_schema import TeacherUpdate, TeacherCreate


# 查询所有老师（排除已逻辑删除）
def dao_get_teacher(db):
    return db.query(teacher_table).filter(teacher_table.t_is_delete == False).all()


# 按id查询老师信息
def dao_get_teacher_byid(db,tid):
    return db.query(teacher_table).filter(teacher_table.tid == tid,teacher_table.t_is_delete == 0).first()


# 新增老师
def dao_add_teacher(db,data):
    data.pop('tid', None)
    teacher = teacher_table(**data)
    db.add(teacher)
    try:
        db.commit()
        db.refresh(teacher)
    except Exception as e:
        db.rollback()
        print(f"!!! 真实数据库错误: {type(e).__name__}: {e}")
        raise ValueError(f"数据库写入失败: {e}") from e
    return teacher

# 批量新增
def dao_update_teacher_batch(db:Session, teacher: List[TeacherCreate]):

    new_teachers = [teacher_table(**t.model_dump(exclude={'tid'})) for t in teacher]
    db.add_all(new_teachers)
    db.commit()
    return new_teachers

# 更新老师信息
def dao_update_teacher(db: Session, teacher_id: int, update_data: TeacherUpdate):
    try:
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return 0
        rows = (
            db.query(teacher_table)
            .filter(teacher_table.tid == teacher_id,teacher_table.t_is_delete == 0)  # 👈 修正：用路径参数值过滤
            .update(update_dict)  # 👈 修正：直接传入 dict
        )
        db.commit()
        return rows
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"更新老师(tid={teacher_id})失败: {e}") from e


# 删除老师
def dao_delete_teacher(db: Session, teacher: teacher_table):
    try:
        rows = (
            db.query(teacher_table)
            .filter(teacher_table.tid == teacher.tid)
            .update({"t_is_delete": 1})
        )
        db.commit()
        return rows
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"逻辑删除老师(tid={teacher.tid})失败: {e}") from e
