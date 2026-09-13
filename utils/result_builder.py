from datetime import datetime
from models import User, StudentProfile, SchoolSettings, ExamSubmission

class ResultBuilder:
    """Build result data for tertiary students"""

    @staticmethod
    def build(student_id):
        """
        Build all variables required by result templates.
        student_id is the integer primary key of User (current_user.id)
        """

        user = User.query.get(student_id)

        if not user:
            student = {
                "name": "Unknown Student",
                "index_number": "-",
                "programme": "-",
                "level": "-",
            }
            attendance = {"present": 0, "total": 0}
        else:
            profile = getattr(user, "student_profile", None)

            student = {
                "name": user.full_name if user else "Unknown Student",
                "index_number": getattr(profile, "index_number", "-") if profile else "-",
                "programme": getattr(profile, "current_programme", "-") if profile else "-",
                "level": getattr(profile, "programme_level", "-") if profile else "-",
            }

            attendance = {
                "present": getattr(profile, "attendance_present", 0) if profile else 0,
                "total": getattr(profile, "attendance_total", 0) if profile else 0,
            }

        # === SCHOOL INFO ===
        settings = SchoolSettings.query.first()
        school_info = {
            "school_name": getattr(settings, "school_name", "My Institution"),
            "school_address": getattr(settings, "school_address", ""),
            "school_logo": getattr(settings, "school_logo", ""),
        }
        academic_year = getattr(settings, "current_academic_year", "2025")
        semester = getattr(settings, "current_semester", "1")

        # === EXAM RESULTS ===
        exam_submissions = ExamSubmission.query.filter_by(
            student_id=user.user_id if user else None
        ).all()
        
        results = []
        for sub in exam_submissions:
            exam = getattr(sub, "exam", None)
            total = getattr(sub, "score", 0) or 0
            grade = ResultBuilder.grade(total)
            results.append({
                "course": getattr(exam, "title", "Unknown Course"),
                "exam_score": getattr(sub, "score", 0) or 0,
                "total": total,
                "grade": grade,
                "remark": ResultBuilder.remark(grade),
            })

        # === FINAL PAYLOAD ===
        return {
            "student": student,
            "results": results,
            "attendance": attendance,
            "academic_year": academic_year,
            "semester": semester,
            **school_info,
            "now": datetime.utcnow().date(),
        }

    @staticmethod
    def grade(score):
        """Convert score to grade (tertiary grading scale)"""
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        if score >= 50:
            return "D"
        return "F"

    @staticmethod
    def remark(grade):
        """Convert grade to remark"""
        mapping = {
            "A": "Excellent",
            "B": "Very Good",
            "C": "Good",
            "D": "Pass",
            "F": "Fail"
        }
        return mapping.get(grade, "")
    