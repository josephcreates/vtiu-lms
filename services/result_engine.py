"""
University Result Engine - DEPRECATED
=====================================

This module is deprecated. Use GradingCalculationEngine from grading_calculation_engine.py instead.

The UniversityResultEngine previously handled grade calculations but this functionality
has been consolidated into GradingCalculationEngine for better maintainability.

MIGRATION GUIDE:
  OLD: result = UniversityResultEngine.compute_course(student_id, course)
  NEW: result = GradingCalculationEngine.calculate_course_grade(
      student_id=student_id,
      course_id=course.id,
      academic_year=course.academic_year,
      semester=course.semester
  )
"""

from models import (
    Quiz, StudentQuizSubmission,
    Assignment, AssignmentSubmission,
    Exam, ExamSubmission, CourseAssessmentScheme
)
from services.grading_calculation_engine import GradingCalculationEngine
from services.grade_service import GradeService


class UniversityResultEngine:
    """
    DEPRECATED: Use GradingCalculationEngine instead.
    
    Maintained for backward compatibility only.
    All compute_course calls should be migrated to GradingCalculationEngine.calculate_course_grade
    """

    @staticmethod
    def compute_course(student_id, course):
        """
        DEPRECATED: Use GradingCalculationEngine.calculate_course_grade() instead.
        
        This method now delegates to the consolidated grading engine.
        """
        try:
            # Use the consolidated grading engine
            grade_record = GradingCalculationEngine.calculate_course_grade(
                student_id=student_id,
                course_id=course.id,
                academic_year=course.academic_year,
                semester=course.semester
            )
            
            if not grade_record:
                return None
            
            return {
                "course": course,
                "score": grade_record.final_score,
                "grade": grade_record.grade_letter,
                "grade_point": grade_record.grade_point,
                "pass_fail": grade_record.pass_fail,
                "credit_hours": course.credit_hours,
                "points": (grade_record.grade_point or 0.0) * course.credit_hours
            }
        except Exception as e:
            print(f"Error computing course grade: {str(e)}")
            return None

    # ============ LEGACY METHODS - DO NOT USE ============
    # These methods are kept only for reference and backward compatibility
    # They are no longer used internally; use GradingCalculationEngine instead

    @staticmethod
    def _quiz_totals(student_id, course):
        """
        DEPRECATED: Use GradingCalculationEngine._get_quiz_totals() instead.
        """
        return GradingCalculationEngine._get_quiz_totals(student_id, course.id)

    @staticmethod
    def _assignment_totals(student_id, course):
        """
        DEPRECATED: Use GradingCalculationEngine._get_assignment_totals() instead.
        """
        return GradingCalculationEngine._get_assignment_totals(student_id, course.id)

    @staticmethod
    def _exam_totals(student_id, course):
        """
        DEPRECATED: Use GradingCalculationEngine._get_exam_totals() instead.
        """
        return GradingCalculationEngine._get_exam_totals(student_id, course.id)


# ============ EXAMPLE CALCULATION ============
"""
SCENARIO:
  Quiz: 4/5 = 80% → weight 10% → 8.0
  Assignment: 18/20 = 90% → weight 30% → 27.0
  Exam: 42/50 = 84% → weight 60% → 50.4
  ────────────────────────────────────
  Final Score: 8.0 + 27.0 + 50.4 = 85.4

FORMULA:
  final = (quiz_pct / 100 × quiz_weight) + (ass_pct / 100 × ass_weight) + (exam_pct / 100 × exam_weight)
  final = (80 / 100 × 10) + (90 / 100 × 30) + (84 / 100 × 60)
  final = (0.8 × 10) + (0.9 × 30) + (0.84 × 60)
  final = 8.0 + 27.0 + 50.4
  final = 85.4 ✓
"""