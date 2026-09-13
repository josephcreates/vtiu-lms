"""
UNIVERSITY GRADING SYSTEM - COMPLETE IMPLEMENTATION
====================================================

This module provides a complete, unified grading system for a tertiary education LMS.
All grade calculations follow the standard weighted average formula:

  Final Score = (Quiz% × Quiz_Weight) + (Assignment% × Assignment_Weight) + (Exam% × Exam_Weight)

ARCHITECTURE:
  - GradingCalculationEngine: Main engine for calculating course grades
  - GradeService: Lookup service for converting scores to letter grades
  - Supports both simple and credit-weighted GPA calculations
  - Configurable assessment weights per course

USAGE:
  # Calculate a single course grade
  grade = GradingCalculationEngine.calculate_course_grade(
      student_id=user.id,
      course_id=course.id,
      academic_year="2024",
      semester="1"
  )
  
  # Recalculate all courses for a student in a semester
  result = GradingCalculationEngine.recalculate_student_all_courses(
      student_id=user.id,
      academic_year="2024",
      semester="1"
  )
  
  # Get transcript data
  grades = GradingCalculationEngine.get_student_grades_for_semester(
      student_id=user.id,
      academic_year="2024",
      semester="1"
  )
  gpa = GradingCalculationEngine.calculate_gpa(grades)
"""

from models import (
    Quiz, StudentQuizSubmission,
    Assignment, AssignmentSubmission,
    Exam, ExamSubmission, CourseAssessmentScheme,
    GradingScale, Course, StudentCourseGrade, db
)
from datetime import datetime
from sqlalchemy import func


class GradingCalculationEngine:
    """
    Main grading engine - calculates final grades using weighted average.
    """

    @staticmethod
    def calculate_course_grade(student_id, course_id, academic_year, semester):
        """
        Calculate final course grade for a student.
        
        Args:
            student_id: Student's user_id (string like "STD001")
            course_id: Course.id (integer)
            academic_year: Academic year string (e.g., "2024")
            semester: Semester string (e.g., "First" or "1")
            
        Returns:
            StudentCourseGrade object with calculated grade, or None if no scheme
            
        Raises:
            Exception: If database operations fail
        """
        try:
            # 1. Get or create grade record
            grade_record = StudentCourseGrade.query.filter_by(
                student_id=student_id,
                course_id=course_id,
                academic_year=academic_year,
                semester=semester
            ).first()

            if not grade_record:
                grade_record = StudentCourseGrade(
                    student_id=student_id,
                    course_id=course_id,
                    academic_year=academic_year,
                    semester=semester
                )
                db.session.add(grade_record)

            # 2. Get assessment scheme
            scheme = CourseAssessmentScheme.query.filter_by(course_id=course_id).first()
            if not scheme:
                return None

            # 3. Calculate category totals
            quiz_score, quiz_max = GradingCalculationEngine._get_quiz_totals(
                student_id, course_id
            )
            ass_score, ass_max = GradingCalculationEngine._get_assignment_totals(
                student_id, course_id
            )
            exam_score, exam_max = GradingCalculationEngine._get_exam_totals(
                student_id, course_id
            )

            # 4. Convert to percentages
            quiz_pct = (quiz_score / quiz_max * 100) if quiz_max > 0 else 0.0
            ass_pct = (ass_score / ass_max * 100) if ass_max > 0 else 0.0
            exam_pct = (exam_score / exam_max * 100) if exam_max > 0 else 0.0

            # 5. Apply weights (STANDARD FORMULA)
            # weighted = (percentage / 100) × weight_percent
            quiz_weighted = (quiz_pct / 100) * (scheme.quiz_weight or 0)
            ass_weighted = (ass_pct / 100) * (scheme.assignment_weight or 0)
            exam_weighted = (exam_pct / 100) * (scheme.exam_weight or 0)

            final_score = round(quiz_weighted + ass_weighted + exam_weighted, 2)

            # 6. Get letter grade
            grade_obj = GradeService.get_grade(final_score)

            # 7. Update grade record
            grade_record.quiz_raw_score = quiz_score
            grade_record.quiz_max_score = quiz_max
            grade_record.quiz_percentage = round(quiz_pct, 2)
            grade_record.quiz_weighted_score = round(quiz_weighted, 2)

            grade_record.assignment_raw_score = ass_score
            grade_record.assignment_max_score = ass_max
            grade_record.assignment_percentage = round(ass_pct, 2)
            grade_record.assignment_weighted_score = round(ass_weighted, 2)

            grade_record.exam_raw_score = exam_score
            grade_record.exam_max_score = exam_max
            grade_record.exam_percentage = round(exam_pct, 2)
            grade_record.exam_weighted_score = round(exam_weighted, 2)

            grade_record.final_score = final_score
            grade_record.grade_letter = grade_obj.grade_letter if grade_obj else 'F'
            grade_record.grade_point = grade_obj.grade_point if grade_obj else 0.0
            grade_record.pass_fail = grade_obj.pass_fail if grade_obj else 'FAIL'
            grade_record.is_finalized = False
            grade_record.calculated_at = datetime.utcnow()

            db.session.commit()
            return grade_record

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error calculating grade for {student_id}: {str(e)}")

    @staticmethod
    def _get_quiz_totals(student_id, course_id):
        """
        Get total quiz score and max for a student in a course.
        
        Sums all quiz submissions for the course.
        
        Example:
            Quiz 1: 4/5
            Quiz 2: 15/20
            Result: (19, 25)  <- Total 19 points out of 25
        """
        subs = (
            StudentQuizSubmission.query
            .join(Quiz)
            .filter(
                StudentQuizSubmission.student_id == student_id,
                Quiz.course_id == course_id
            ).all()
        )
        
        total_score = sum(s.score for s in subs if s.score is not None)
        total_max = sum(s.quiz.max_score for s in subs if s.quiz.max_score)
        
        return total_score, total_max

    @staticmethod
    def _get_assignment_totals(student_id, course_id):
        """
        Get total assignment score and max for a student in a course.
        
        Sums all assignment submissions for the course.
        """
        subs = (
            AssignmentSubmission.query
            .join(Assignment)
            .filter(
                AssignmentSubmission.student_id == student_id,
                Assignment.course_id == course_id
            ).all()
        )
        
        total_score = sum(s.score for s in subs if s.score is not None)
        total_max = sum(s.assignment.max_score for s in subs if s.assignment.max_score)
        
        return total_score, total_max

    @staticmethod
    def _get_exam_totals(student_id, course_id):
        """
        Get total exam score and max for a student in a course.
        
        Sums all exam submissions for the course.
        """
        subs = (
            ExamSubmission.query
            .join(Exam)
            .filter(
                ExamSubmission.student_id == student_id,
                Exam.course_id == course_id
            ).all()
        )
        
        total_score = sum(s.score for s in subs if s.score is not None)
        total_max = sum(s.exam.max_score for s in subs if s.exam.max_score)
        
        return total_score, total_max

    @staticmethod
    def recalculate_student_all_courses(student_id, academic_year, semester):
        """
        Recalculate grades for a student across all courses in a semester.
        
        Args:
            student_id: Student's user_id
            academic_year: Academic year
            semester: Semester
            
        Returns:
            dict with 'success_count' and 'error_count'
        """
        courses = Course.query.filter_by(
            academic_year=academic_year,
            semester=semester
        ).all()
        
        success_count = 0
        error_count = 0
        errors = []
        
        for course in courses:
            try:
                GradingCalculationEngine.calculate_course_grade(
                    student_id, course.id, academic_year, semester
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    'course_id': course.id,
                    'course_name': course.name,
                    'error': str(e)
                })
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }

    @staticmethod
    def recalculate_all_students_all_courses(academic_year, semester):
        """
        Recalculate all grades for all students in all courses for a semester.
        Called after grading period ends to finalize grades.
        
        Args:
            academic_year: Academic year
            semester: Semester
            
        Returns:
            dict with statistics
        """
        courses = Course.query.filter_by(
            academic_year=academic_year,
            semester=semester
        ).all()
        
        total_success = 0
        total_errors = 0
        
        for course in courses:
            # Get all students in this course
            registrations = StudentCourseGrade.query.filter_by(
                course_id=course.id,
                academic_year=academic_year,
                semester=semester
            ).all()
            
            for reg in registrations:
                try:
                    GradingCalculationEngine.calculate_course_grade(
                        reg.student_id, course.id, academic_year, semester
                    )
                    total_success += 1
                except Exception as e:
                    total_errors += 1
        
        return {
            'total_calculated': total_success,
            'total_errors': total_errors,
            'academic_year': academic_year,
            'semester': semester
        }






    @staticmethod
    def get_student_grades_for_semester(student_id, academic_year, semester):
        """
        Fetch finalized student course grades for a specific semester.
        Returns a list of StudentCourseGrade objects.
        """
        query = StudentCourseGrade.query.filter_by(
            student_id=student_id,
            academic_year=academic_year,
            semester=semester
        )
        # If the model has an is_finalized flag, only return finalized grades
        if hasattr(StudentCourseGrade, 'is_finalized'):
            query = query.filter_by(is_finalized=True)
        return query.all()

    @staticmethod
    def get_student_all_grades(student_id):
        """
        Fetch all finalized student course grades across all semesters.
        Returns a list of StudentCourseGrade objects ordered by year/semester.
        """
        query = StudentCourseGrade.query.filter_by(student_id=student_id)
        if hasattr(StudentCourseGrade, 'is_finalized'):
            query = query.filter_by(is_finalized=True)
        # Order by academic year and semester where available
        try:
            return query.order_by(StudentCourseGrade.academic_year, StudentCourseGrade.semester).all()
        except Exception:
            return query.all()

    @staticmethod
    def calculate_gpa(grades):
        """
        Calculate a simple (unweighted) GPA from a list of StudentCourseGrade objects.
        If `grade_point` is available on the grade object it is used; otherwise
        a mapping from `grade_letter` is used as fallback.
        Returns a float rounded to 2 decimals.
        """
        if not grades:
            return 0.0

        gp_map = {
            'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'F': 0.0
        }

        total = 0.0
        count = 0
        for g in grades:
            gp = getattr(g, 'grade_point', None)
            if gp is None:
                gp = gp_map.get(getattr(g, 'grade_letter', None), 0.0)
            total += (gp or 0.0)
            count += 1

        return round((total / count) if count > 0 else 0.0, 2)

    @staticmethod
    def calculate_weighted_gpa(grades):
        """
        Calculate credit-weighted GPA from a list of StudentCourseGrade objects.
        Uses `grade_point` if present, otherwise falls back to `grade_letter` mapping.
        Returns a float rounded to 2 decimals.
        """
        if not grades:
            return 0.0

        gp_map = {
            'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'F': 0.0
        }

        total_points = 0.0
        total_credits = 0.0

        for g in grades:
            gp = getattr(g, 'grade_point', None)
            if gp is None:
                gp = gp_map.get(getattr(g, 'grade_letter', None), 0.0)
            # Attempt to read credit hours from related course
            credits = 0
            try:
                credits = (g.course.credit_hours or 0)
            except Exception:
                credits = 0

            total_points += (gp or 0.0) * (credits or 0)
            total_credits += (credits or 0)

        weighted = (total_points / total_credits) if total_credits > 0 else 0.0
        return round(weighted, 2)


class GradeService:
    """
    Grade lookup service - converts scores to letter grades.
    Uses GradingScale model for configurable grading boundaries.
    """

    @staticmethod
    def get_grade(percent):
        """
        Get letter grade object for a percentage score.
        
        Args:
            percent: Score as percentage (0-100)
            
        Returns:
            GradingScale object with grade details, or None if no match
            
        Example:
            85.4 → GradingScale(grade_letter='B+', grade_point=3.3, ...)
        """
        if percent is None:
            return None

        return (
            GradingScale.query
            .filter(GradingScale.min_score <= percent)
            .filter(GradingScale.max_score >= percent)
            .first()
        )

    @staticmethod
    def get_all_grades():
        """Get all grading scale entries (for reference)"""
        return GradingScale.query.order_by(GradingScale.min_score.desc()).all()


# ============ GRADING SYSTEM DOCUMENTATION ============
"""
COMPLETE GRADING SYSTEM IMPLEMENTATION GUIDE
==============================================

1. CORE FORMULA (Used Consistently)
   ─────────────────────────────────
   Final Score = (Quiz% × Quiz_Weight) + (Assignment% × Assignment_Weight) + (Exam% × Exam_Weight)
   
   Where:
   - Quiz% = (Quiz_Score / Quiz_Max) × 100
   - Assignment% = (Assignment_Score / Assignment_Max) × 100
   - Exam% = (Exam_Score / Exam_Max) × 100
   - Weights sum to 100% (e.g., 10% + 30% + 60%)

2. KEY CLASSES
   ────────────
   
   GradingCalculationEngine
   • Main calculation engine
   • Handles score aggregation and weighted grade calculation
   • Single source of truth for all calculations
   
   GradeService
   • Simple lookup service (moved from models.py)
   • Converts numeric scores to letter grades
   • Uses configurable GradingScale model
   
   StudentCourseGrade (Model)
   • Stores calculated results per course per semester
   • Includes raw scores, percentages, weighted scores, and final grade

3. USAGE EXAMPLES
   ───────────────
   
   Example 1: Calculate grade for a single student/course
   ───────────────────────────────────────────────────────
   from services.grading_calculation_engine import GradingCalculationEngine
   
   grade = GradingCalculationEngine.calculate_course_grade(
       student_id=student.id,
       course_id=course.id,
       academic_year="2024",
       semester="1"
   )
   
   print(f"Score: {grade.final_score}")
   print(f"Grade: {grade.grade_letter}")
   print(f"Pass/Fail: {grade.pass_fail}")
   
   Example 2: Recalculate all courses for a student in a semester
   ──────────────────────────────────────────────────────────────
   result = GradingCalculationEngine.recalculate_student_all_courses(
       student_id=student.id,
       academic_year="2024",
       semester="1"
   )
   
   print(f"Success: {result['success_count']}")
   print(f"Errors: {result['error_count']}")
   
   Example 3: Get transcript for a semester
   ─────────────────────────────────────────
   grades = GradingCalculationEngine.get_student_grades_for_semester(
       student_id=student.id,
       academic_year="2024",
       semester="1"
   )
   
   gpa = GradingCalculationEngine.calculate_gpa(grades)
   weighted_gpa = GradingCalculationEngine.calculate_weighted_gpa(grades)
   
   Example 4: Full academic transcript
   ────────────────────────────────────
   all_grades = GradingCalculationEngine.get_student_all_grades(student_id=student.id)
   cumulative_gpa = GradingCalculationEngine.calculate_gpa(all_grades)
   
   Example 5: Real calculation with numbers
   ──────────────────────────────────────
   Student: STD001, Course: CSC101
   Academic Year: 2024, Semester: 1
   
   Assessments:
   • Quiz: 19/25 = 76%
   • Assignment: 37/40 = 92.5%
   • Exam: 42/50 = 84%
   
   Assessment Scheme:
   • Quiz Weight: 10%
   • Assignment Weight: 30%
   • Exam Weight: 60%
   
   Calculation:
   1. Convert to percentages:
      - Quiz: 76%
      - Assignment: 92.5%
      - Exam: 84%
   
   2. Apply weights:
      - Quiz_weighted = (76 / 100) × 10 = 7.6
      - Assignment_weighted = (92.5 / 100) × 30 = 27.75
      - Exam_weighted = (84 / 100) × 60 = 50.4
   
   3. Sum weighted scores:
      - Final_Score = 7.6 + 27.75 + 50.4 = 85.75
   
   4. Get letter grade:
      - 85.75 → Grade: B+ (or A- depending on scale)
      - Grade Point: 3.3 (or 3.7)
      - Pass/Fail: PASS

4. METHOD REFERENCE
   ─────────────────
   
   calculate_course_grade(student_id, course_id, academic_year, semester)
   • Main calculation method
   • Returns StudentCourseGrade object with all calculations
   • Stores to database
   
   recalculate_student_all_courses(student_id, academic_year, semester)
   • Recalculate grades for all courses in a semester
   • Returns dict with success/error counts
   
   recalculate_all_students_all_courses(academic_year, semester)
   • Batch recalculation for semester finalization
   • Called after grading period ends
   
   get_student_grades_for_semester(student_id, academic_year, semester)
   • Fetch grades for a specific semester
   • Returns list of StudentCourseGrade objects
   
   get_student_all_grades(student_id)
   • Fetch all historical grades
   • Returns list ordered by year/semester
   
   calculate_gpa(grades)
   • Simple (unweighted) GPA from grade list
   • Uses grade_point field or letter → point mapping
   
   calculate_weighted_gpa(grades)
   • Credit-weighted GPA calculation
   • Multiplies grade_point by course credit hours

5. GRADING SCALE CONFIGURATION
   ────────────────────────────
   The system uses GradingScale model for configurable grades.
   Example entries:
   
   Grade Letter | Min Score | Max Score | Grade Point | Pass/Fail
   ──────────────────────────────────────────────────────────────
   A            | 90        | 100       | 4.0         | PASS
   B+           | 85        | 89        | 3.3         | PASS
   B            | 80        | 84        | 3.0         | PASS
   C            | 70        | 79        | 2.0         | PASS
   F            | 0         | 69        | 0.0         | FAIL
   
   Each institution can customize these boundaries.

6. DATABASE SCHEMA
   ────────────────
   StudentCourseGrade stores:
   - Raw scores (quiz_raw_score, assignment_raw_score, exam_raw_score)
   - Max possible scores
   - Percentages for each category
   - Weighted scores for each category
   - Final combined score
   - Letter grade
   - Grade point
   - Pass/Fail status
   - Finalization and release flags
   - Timestamps

7. MIGRATION FROM OLD SYSTEM
   ──────────────────────────
   Old (from models.py):
     from models import GradingService
     GradingService.calculate_final_grade(...)
   
   New (consolidated):
     from services.grading_calculation_engine import GradingCalculationEngine
     GradingCalculationEngine.calculate_course_grade(...)
   
   The old UniversityResultEngine in result_engine.py now delegates
   to GradingCalculationEngine for backward compatibility.
"""
