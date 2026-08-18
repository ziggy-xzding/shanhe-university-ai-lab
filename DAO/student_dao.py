"""
学生数据访问层
===============
封装学生表的所有数据库操作。
支持多条件筛选、模糊搜索、逻辑删除。
"""
from typing import Optional
from Model.student_table import Student
from sqlalchemy import func,case


def dao_get_all_students(db, student_no: Optional[str] = None,
                         name: Optional[str] = None,
                         class_id: Optional[int] = None):
    """查询学生列表，支持按编号、姓名、班级筛选"""
    query = db.query(Student).filter(Student.is_deleted == 0)
    if student_no:
        query = query.filter(Student.student_no == student_no)
    if name:
        query = query.filter(Student.name.like(f"%{name}%"))
    if class_id:
        query = query.filter(Student.class_id == class_id)
    return query.all()


def dao_get_student_by_id(db, student_id: int):
    """按ID查询单个学生"""
    return db.query(Student).filter(
        Student.id == student_id,
        Student.is_deleted == 0,
    ).first()


def dao_get_student_by_no(db, student_no: str):
    """按学生编号查询（唯一性检查）"""
    return db.query(Student).filter(
        Student.student_no == student_no,
        Student.is_deleted == 0,
    ).first()


def dao_create_student(db, data: dict) -> Student:
    """新增学生"""
    student = Student(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def dao_update_student(db, student: Student, data: dict) :
    """更新学生（部分字段）"""
    for key, value in data.items():
        setattr(student, key, value)
    db.commit()
    return student


def dao_delete_student(db, student: Student):
    """逻辑删除学生"""
    student.is_deleted = True
    db.commit()
    return {"msg": "删除成功"}


#查询年龄大于x岁的人
def get_students_overage(age, db):
    q = db.query(Student).filter(Student.age > age, Student.is_deleted == False).all()
    lst = [{"student_id": stu.id,
                    "class_id": stu.class_id,
                    "student_name": stu.name,
                    "age": stu.age,
                    "gender": stu.gender} for stu in q]
    # for stu in q:
    #     lst.append({"student_id": stu.id,
    #                 "class_id": stu.class_id,
    #                 "student_name": stu.name,
    #                 "age": stu.age,
    #                 "gender": stu.gender})
    return lst


#统计班级人数以及男女生人数
def get_sex_num(db):
    statistics_result = db.query(
        Student.class_id,
        func.count(Student.id),
        func.sum(case((Student.gender == '男', 1), else_=0)),
        func.sum(case((Student.gender == '女', 1), else_=0))
    ).filter(Student.is_deleted == False).group_by(Student.class_id).all()

    stat_list = []
    for class_id, total, male, female in statistics_result:
        stat_list.append({"班级编号": class_id,
                          "班级总人数": total,
                          "男生人数": male,
                          "女生人数": female})
    return stat_list