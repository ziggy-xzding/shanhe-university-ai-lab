# Api/student_score.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from DAO.db import get_db
from DAO.student_dao_score import ScoreDAO
from Model.student_table import Student
from Schema.Score import ScoreCreate, ScoreUpdate, ScoreResponse, MessageResponse
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles
from Api.teacher_workbench_api import ensure_teacher_can_access_class

router = APIRouter(
    prefix="/score",
    tags=["成绩管理模块"],
    responses={
        400: {"description": "请求参数错误"},
        404: {"description": "资源不存在"},
        409: {"description": "数据冲突"},
        422: {"description": "参数验证失败"}
    }
)


@router.post(
    "/",
    response_model=ScoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="录入成绩"
)
async def create_score(
        score: ScoreCreate,
        db: Session = Depends(get_db),
        principal: AuthPrincipal = Depends(require_roles("teacher", "admin")),
):
    """录入成绩"""
    dao = ScoreDAO(db)
    _ensure_score_scope(db, principal, score.student_no)

    # 检查成绩是否已存在
    if dao.check_score_exists(score.student_no, score.exam_seq):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"学生 {score.student_no} 的第 {score.exam_seq} 次成绩已存在"
        )

    try:
        db_score = dao.create_score(score)
        return ScoreResponse.model_validate(db_score)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"录入成绩失败：{str(e)}"
        )


@router.get(
    "/{student_no}",
    response_model=List[ScoreResponse],
    summary="查询学生成绩"
)
async def get_student_scores(
        student_no: str,
        exam_seq: Optional[int] = Query(
            None,
            description="考试序次，可选。指定则返回该次成绩"
        ),
        db: Session = Depends(get_db)
):
    """查询学生成绩"""
    dao = ScoreDAO(db)
    scores = dao.get_scores_by_student_no(student_no, exam_seq)
    return [ScoreResponse.model_validate(s) for s in scores]


@router.put(
    "/",
    response_model=ScoreResponse,
    summary="修改成绩"
)
async def update_score(
        update_data: ScoreUpdate,
        db: Session = Depends(get_db),
        principal: AuthPrincipal = Depends(require_roles("teacher", "admin")),
):
    """修改成绩"""
    dao = ScoreDAO(db)
    _ensure_score_scope(db, principal, update_data.student_no)

    # 检查成绩是否存在
    if not dao.check_score_exists(update_data.student_no, update_data.exam_seq):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"学生 {update_data.student_no} 的第 {update_data.exam_seq} 次成绩不存在"
        )

    try:
        score_record = dao.update_score(
            update_data.student_no,
            update_data.exam_seq,
            update_data.new_score
        )
        return ScoreResponse.model_validate(score_record)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改成绩失败：{str(e)}"
        )


@router.delete(
    "/{student_no}/{exam_seq}",
    response_model=MessageResponse,
    summary="删除成绩"
)
async def delete_score(
        student_no: str,
        exam_seq: int,
        db: Session = Depends(get_db),
        principal: AuthPrincipal = Depends(require_roles("teacher", "admin")),
):
    """删除成绩"""
    dao = ScoreDAO(db)
    _ensure_score_scope(db, principal, student_no)

    # 检查成绩是否存在
    if not dao.check_score_exists(student_no, exam_seq):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"学生 {student_no} 的第 {exam_seq} 次成绩不存在或已删除"
        )

    # 执行删除
    success = dao.delete_score(student_no, exam_seq)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除成绩失败，请稍后重试"
        )

    return MessageResponse(
        message=f"学生 {student_no} 的第 {exam_seq} 次成绩已删除"
    )


def _ensure_score_scope(
    db: Session,
    principal: AuthPrincipal,
    student_no: str,
) -> None:
    student = db.query(Student).filter(
        Student.student_no == student_no,
        Student.is_deleted.is_(False),
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    ensure_teacher_can_access_class(db, principal, student.class_id)


# ============================================================
# 统计接口
# ============================================================

@router.get(
    "/statistics/above-80",
    summary="查询每次考试都在80分以上的学生"
)
async def get_students_above_80(db: Session = Depends(get_db)):
    """查询每次考试成绩都在80分以上的学生"""
    dao = ScoreDAO(db)
    result = dao.get_students_above_80_all_exams()
    return {
        "total": len(result),
        "data": result
    }


@router.get(
    "/statistics/multiple-failures",
    summary="查询有两次以上不及格的学生"
)
async def get_students_with_multiple_failures(db: Session = Depends(get_db)):
    """查询有两次以上不及格的学生"""
    dao = ScoreDAO(db)
    result = dao.get_students_with_multiple_failures()
    return {
        "total": len(result),
        "data": result
    }


@router.get(
    "/statistics/class-exam-avg",
    summary="统计每次考试每个班级的平均分"
)
async def get_average_score_by_exam_and_class(db: Session = Depends(get_db)):
    """统计每次考试每个班级的平均分"""
    dao = ScoreDAO(db)
    result = dao.get_average_score_by_exam_and_class()
    return {
        "total": len(result),
        "data": result
    }
