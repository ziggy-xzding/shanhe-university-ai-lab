from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case
from typing import Optional, List, Dict, Any
from Model.Student_score_table import Score
from Model.student_table import Student
from Model.class_table import Class
from Schema.Score import ScoreCreate, ScoreUpdate


class ScoreDAO:
    """成绩数据访问对象"""

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # 基础查询方法
    # ============================================================

    def _get_base_query(self):
        """获取基础查询（排除已删除）"""
        return self.db.query(Score).filter(Score.is_deleted == False)

    def check_score_exists(self, student_no: str, exam_seq: int) -> bool:
        """检查指定学生的某次成绩是否存在（只查未删除的）"""
        return self.db.query(Score).filter(
            Score.student_no == student_no,
            Score.exam_seq == exam_seq,
            Score.is_deleted == False
        ).first() is not None

    def get_score_by_student_and_seq(
            self,
            student_no: str,
            exam_seq: int
    ) -> Optional[Score]:
        """根据学号和序次获取成绩（只查未删除的）"""
        return self.db.query(Score).filter(
            Score.student_no == student_no,
            Score.exam_seq == exam_seq,
            Score.is_deleted == False
        ).first()

    def get_scores_by_student_no(
            self,
            student_no: str,
            exam_seq: Optional[int] = None
    ) -> List[Score]:
        """根据学号获取成绩列表"""
        query = self._get_base_query().filter(Score.student_no == student_no)

        if exam_seq is not None:
            query = query.filter(Score.exam_seq == exam_seq)

        return query.order_by(Score.exam_seq).all()

    def get_all_scores(self) -> List[Score]:
        """获取所有成绩（只查未删除的）"""
        return self._get_base_query().order_by(
            Score.student_no,
            Score.exam_seq
        ).all()

    # ============================================================
    # 增删改方法
    # ============================================================

    def create_score(self, score_data: ScoreCreate) -> Score:
        """创建成绩记录"""
        try:
            # 验证学生是否存在（不使用外键）
            student = self.db.query(Student).filter(
                Student.student_no == score_data.student_no,
                Student.is_deleted == False
            ).first()

            if not student:
                raise ValueError(f"学生 {score_data.student_no} 不存在")

            db_score = Score(
                student_no=score_data.student_no,
                exam_seq=score_data.exam_seq,
                score=score_data.score
            )
            self.db.add(db_score)
            self.db.commit()
            self.db.refresh(db_score)
            return db_score
        except Exception as e:
            self.db.rollback()
            raise e

    def update_score(
            self,
            student_no: str,
            exam_seq: int,
            new_score: float
    ) -> Optional[Score]:
        """更新成绩"""
        try:
            score_record = self.get_score_by_student_and_seq(student_no, exam_seq)
            if not score_record:
                return None

            score_record.score = new_score
            self.db.commit()
            self.db.refresh(score_record)
            return score_record
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_score(self, student_no: str, exam_seq: int) -> bool:
        """软删除成绩"""
        try:
            score_record = self.db.query(Score).filter(
                Score.student_no == student_no,
                Score.exam_seq == exam_seq,
                Score.is_deleted == False
            ).first()

            if not score_record:
                return False

            score_record.is_deleted = True
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"删除成绩失败: {e}")
            return False

    # ============================================================
    # 高级统计方法（使用多表连接查询）
    # ============================================================

    def get_students_above_80_all_exams(self) -> List[Dict[str, Any]]:
        """
        查询每次考试成绩都在80分以上的学生
        使用多表连接查询，不依赖外键
        """
        # 构建子查询：找出所有有低于80分成绩的学生学号
        failed_subquery = self.db.query(Score.student_no).filter(
            Score.score < 80,
            Score.is_deleted == False
        ).distinct().subquery()

        # 主查询：使用多表连接（去掉select_from，直接在query中指定表）
        results = self.db.query(
            Student.student_no,
            Student.name.label('student_name'),
            Class.name.label('class_name'),
            func.group_concat(
                func.concat('第', Score.exam_seq, '次:', Score.score),
                '; '
            ).label('scores'),
            func.round(func.avg(Score.score), 2).label('avg_score'),
            func.count(Score.exam_seq).label('exam_count')
        ).join(
            Score,
            and_(
                Student.student_no == Score.student_no,
                Score.is_deleted == False
            )
        ).outerjoin(
            Class,
            Student.class_id == Class.id
        ).filter(
            Student.is_deleted == False,
            Student.student_no.notin_(failed_subquery)
        ).group_by(
            Student.student_no,
            Student.name,
            Class.name
        ).order_by(
            func.avg(Score.score).desc()
        ).all()

        return [{
            'student_no': r[0],
            'student_name': r[1],
            'class_name': r[2] or '未分配班级',
            'scores': r[3],
            'avg_score': r[4],
            'exam_count': r[5]
        } for r in results]

    def get_students_with_multiple_failures(
            self,
            fail_threshold: float = 60
    ) -> List[Dict[str, Any]]:
        """
        查询有两次以上不及格的学生
        使用多表连接查询
        """
        results = self.db.query(
            Student.name.label('student_name'),
            Class.name.label('class_name'),
            func.count(Score.exam_seq).label('fail_count'),
            func.group_concat(
                func.concat('第', Score.exam_seq, '次:', Score.score),
                '; '
            ).label('fail_scores')
        ).join(
            Score,
            and_(
                Student.student_no == Score.student_no,
                Score.is_deleted == False,
                Score.score < fail_threshold
            )
        ).outerjoin(
            Class,
            Student.class_id == Class.id
        ).filter(
            Student.is_deleted == False
        ).group_by(
            Student.name,
            Class.name
        ).having(
            func.count(Score.exam_seq) >= 2
        ).order_by(
            func.count(Score.exam_seq).desc()
        ).all()

        return [{
            'student_name': r[0],
            'class_name': r[1] or '未分配班级',
            'fail_count': r[2],
            'fail_scores': r[3]
        } for r in results]

    def get_average_score_by_exam_and_class(self) -> List[Dict[str, Any]]:
        """
        统计每次考试每个班级的平均分
        使用多表连接查询
        """
        fail_case = case(
            (Score.score < 60, 1),
            else_=0
        )

        results = self.db.query(
            Score.exam_seq,
            Class.name.label('class_name'),
            func.count(Score.student_no).label('student_count'),
            func.round(func.avg(Score.score), 2).label('avg_score'),
            func.round(func.max(Score.score), 2).label('max_score'),
            func.round(func.min(Score.score), 2).label('min_score'),
            func.round(
                func.sum(fail_case) / func.count(Score.student_no) * 100,
                2
            ).label('fail_rate')
        ).join(
            Student,
            and_(
                Student.student_no == Score.student_no,
                Student.is_deleted == False
            )
        ).outerjoin(
            Class,
            Student.class_id == Class.id
        ).filter(
            Score.is_deleted == False
        ).group_by(
            Score.exam_seq,
            Class.name
        ).order_by(
            Score.exam_seq,
            func.avg(Score.score).desc()
        ).all()

        return [{
            'exam_seq': r[0],
            'class_name': r[1] or '未分配班级',
            'student_count': r[2],
            'avg_score': r[3],
            'max_score': r[4],
            'min_score': r[5],
            'fail_rate': r[6]
        } for r in results]

    # ============================================================
    # 额外的学生验证方法
    # ============================================================

    def get_student_by_no(self, student_no: str) -> Optional[Student]:
        """根据学号获取学生信息"""
        return self.db.query(Student).filter(
            Student.student_no == student_no,
            Student.is_deleted == False
        ).first()