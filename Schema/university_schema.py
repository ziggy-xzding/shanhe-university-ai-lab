from datetime import datetime

from pydantic import BaseModel


class EnrollmentResponse(BaseModel):
    id: int
    student_no: str
    teaching_section_id: int
    status: str
    enrolled_at: datetime
