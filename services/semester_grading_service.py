"""
SEMESTER GRADING SERVICE
========================
Location: services/semester_grading_service.py

Handles semester-level operations:
- Bulk grade calculations
- Result release/recall
- Semester locking/unlocking
- Grading reports
"""

from datetime import datetime
from models import (
    StudentCourseRegistration, Course, SemesterResultRelease, 
    StudentCourseGrade, StudentProfile, User, db
)
from services.grading_calculation_engine import GradingCalculationEngine
import logging

logger = logging.getLogger(__name__)


class SemesterGradingService:
    """
    Service for semester-level grading operations.
    Handles batch calculations, result releases, and semester management.
    """

    @staticmethod
    def finalize_semester_grades(course_id, academic_year, semester):
        """
        Finalize all grades for a course in a specific semester.
        Calculates final grades for all enrolled students.
        
        Args:
            course_id: Course.id
            academic_year: Academic year (e.g., "2024")
            semester: Semester (e.g., "First" or "1")
            
        Returns:
            dict with:
                - success_count: Number of grades calculated
                - error_count: Number of errors
                - errors: List of error details
                - course: Course object
                - academic_year: Year
                - semester: Semester
        """
        course = Course.query.get(course_id)
        if not course:
            return {
                'success_count': 0,
                'error_count': 0,
                'errors': ['Course not found']
            }

        # Get all registrations for this course/semester
        registrations = StudentCourseRegistration.query.filter_by(
            course_id=course_id,
            academic_year=academic_year,
            semester=semester
        ).all()

        success_count = 0
        error_count = 0
        errors = []

        for registration in registrations:
            try:
                student = User.query.get(registration.student_id)
                if not student:
                    error_count += 1
                    errors.append({
                        'student_id': registration.student_id,
                        'error': 'Student not found'
                    })
                    continue

                GradingCalculationEngine.calculate_course_grade(
                    student.user_id,
                    course_id,
                    academic_year,
                    semester
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    'student_id': registration.student_id,
                    'error': str(e)
                })
                logger.exception(f"Error calculating grade for student {registration.student_id}")

        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors,
            'course': course,
            'academic_year': academic_year,
            'semester': semester,
            'total_students': len(registrations)
        }

    @staticmethod
    def finalize_all_course_grades(academic_year, semester):
        """
        Finalize grades for ALL courses in a semester.
        
        Args:
            academic_year: Academic year (e.g., "2024")
            semester: Semester (e.g., "First" or "1")
            
        Returns:
            dict with results for each course
        """
        # Get all unique courses for this semester
        courses = (
            Course.query
            .filter_by(academic_year=academic_year, semester=semester)
            .all()
        )

        results = {
            'academic_year': academic_year,
            'semester': semester,
            'courses': [],
            'total_success': 0,
            'total_errors': 0,
            'timestamp': datetime.utcnow().isoformat()
        }

        for course in courses:
            course_result = SemesterGradingService.finalize_semester_grades(
                course.id, academic_year, semester
            )
            results['courses'].append(course_result)
            results['total_success'] += course_result['success_count']
            results['total_errors'] += course_result['error_count']

        logger.info(
            f"Finalized {results['total_success']} grades for "
            f"{academic_year} {semester}"
        )

        return results

    @staticmethod
    def release_semester_results(academic_year, semester):
        """
        Release results for a semester to students.
        Marks semester as released so students can view their grades.
        
        Args:
            academic_year: Academic year (e.g., "2024")
            semester: Semester (e.g., "First" or "1")
            
        Returns:
            dict with release information
        """
        # Check if release record exists
        release = SemesterResultRelease.query.filter_by(
            academic_year=academic_year,
            semester=semester
        ).first()

        if not release:
            release = SemesterResultRelease(
                academic_year=academic_year,
                semester=semester
            )
            db.session.add(release)

        # Check if all grades are finalized. Fall back to checking `final_score` when
        # model doesn't have `is_finalized` attribute.
        if hasattr(StudentCourseGrade, 'is_finalized'):
            unfinalized = StudentCourseGrade.query.filter_by(
                academic_year=academic_year,
                semester=semester,
                is_finalized=False
            ).count()
        else:
            # treat a grade as finalized when `final_score` is not NULL
            unfinalized = StudentCourseGrade.query.filter(
                StudentCourseGrade.academic_year == academic_year,
                StudentCourseGrade.semester == semester,
                StudentCourseGrade.final_score == None
            ).count()

        if unfinalized > 0:
            return {
                'success': False,
                'message': f"Cannot release: {unfinalized} grades not yet finalized"
            }

        release.is_released = True
        release.released_at = datetime.utcnow()
        db.session.commit()

        # Mark all grades as released if the model supports those flags.
        if hasattr(StudentCourseGrade, 'is_finalized') and hasattr(StudentCourseGrade, 'is_released'):
            StudentCourseGrade.query.filter_by(
                academic_year=academic_year,
                semester=semester,
                is_finalized=True
            ).update({'is_released': True, 'released_at': datetime.utcnow()})
            db.session.commit()

        logger.info(f"Released results for {academic_year} {semester}")

        return {
            'success': True,
            'academic_year': academic_year,
            'semester': semester,
            'is_released': True,
            'released_at': release.released_at,
            'message': f"Results released for {academic_year} Semester {semester}"
        }

    @staticmethod
    def recall_semester_results(academic_year, semester):
        """
        Recall (un-release) results for a semester.
        Makes grades private again if needed.
        
        Args:
            academic_year: Academic year
            semester: Semester
            
        Returns:
            dict with updated release information
        """
        release = SemesterResultRelease.query.filter_by(
            academic_year=academic_year,
            semester=semester
        ).first()

        if not release:
            return {
                'success': False,
                'error': 'No release record found for this semester'
            }

        release.is_released = False
        db.session.commit()

        # Mark all grades as not released if supported by model
        if hasattr(StudentCourseGrade, 'is_released'):
            StudentCourseGrade.query.filter_by(
                academic_year=academic_year,
                semester=semester,
                is_released=True
            ).update({'is_released': False, 'released_at': None})
            db.session.commit()

        logger.info(f"Recalled results for {academic_year} {semester}")

        return {
            'success': True,
            'academic_year': academic_year,
            'semester': semester,
            'is_released': False,
            'message': f"Results recalled for {academic_year} Semester {semester}"
        }

    @staticmethod
    def lock_semester(academic_year, semester, submitted_by=None, submitted_by_name=None, submitted_note=None, submitted_courses=None):
        """
        Lock a semester to prevent further grade modifications.
        
        Args:
            academic_year: Academic year
            semester: Semester
            
        Returns:
            dict with lock information
        """
        release = SemesterResultRelease.query.filter_by(
            academic_year=academic_year,
            semester=semester
        ).first()

        if not release:
            release = SemesterResultRelease(
                academic_year=academic_year,
                semester=semester
            )
            db.session.add(release)

        release.is_locked = True
        release.locked_at = datetime.utcnow()

        # Record submitter info if provided
        if submitted_by:
            release.submitted_by = submitted_by
        if submitted_by_name:
            release.submitted_by_name = submitted_by_name
        if submitted_note:
            release.submitted_note = submitted_note
        if submitted_courses:
            # expect submitted_courses as JSON string
            release.submitted_courses = submitted_courses

        # mark submitted_at when locking
        if not release.submitted_at:
            release.submitted_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"Locked semester {academic_year} {semester} by {submitted_by_name or submitted_by}")

        return {
            'success': True,
            'academic_year': academic_year,
            'semester': semester,
            'is_locked': True,
            'message': f"Semester {academic_year} {semester} is now locked",
            'locked_at': release.locked_at,
            'submitted_by': release.submitted_by,
            'submitted_by_name': release.submitted_by_name,
        }

    @staticmethod
    def unlock_semester(academic_year, semester):
        """
        Unlock a semester to allow grade modifications.
        
        Args:
            academic_year: Academic year
            semester: Semester
            
        Returns:
            dict with unlock information
        """
        release = SemesterResultRelease.query.filter_by(
            academic_year=academic_year,
            semester=semester
        ).first()

        if not release:
            return {
                'success': False,
                'error': 'No release record found for this semester'
            }

        release.is_locked = False
        db.session.commit()

        logger.info(f"Unlocked semester {academic_year} {semester}")

        return {
            'success': True,
            'academic_year': academic_year,
            'semester': semester,
            'is_locked': False,
            'message': f"Semester {academic_year} {semester} is now unlocked"
        }

    @staticmethod
    def get_semester_status(academic_year, semester):
        """
        Get current status of a semester (released/locked).
        
        Args:
            academic_year: Academic year
            semester: Semester
            
        Returns:
            dict: Semester status
        """
        release = SemesterResultRelease.query.filter_by(
            academic_year=academic_year,
            semester=semester
        ).first()

        if not release:
            return {
                'academic_year': academic_year,
                'semester': semester,
                'is_released': False,
                'is_locked': False,
                'released_at': None,
                'locked_at': None
            }

        return {
            'academic_year': academic_year,
            'semester': semester,
            'is_released': release.is_released,
            'is_locked': release.is_locked,
            'released_at': release.released_at,
            'locked_at': getattr(release, 'locked_at', None)
        }

    @staticmethod
    def get_semester_summary(academic_year, semester):
        """
        Get summary statistics for a semester across all courses.
        
        Args:
            academic_year: Academic year (e.g., "2024")
            semester: Semester (e.g., "First" or "1")
            
        Returns:
            dict with course and grading statistics
        """
        # Get all courses for this semester
        courses = (
            Course.query
            .filter_by(academic_year=academic_year, semester=semester)
            .all()
        )

        # Get all grades for this semester
        all_grades = (
            StudentCourseGrade.query
            .filter_by(academic_year=academic_year, semester=semester)
            .all()
        )

        if not all_grades:
            return {
                'academic_year': academic_year,
                'semester': semester,
                'total_courses': len(courses),
                'total_students': 0,
                'total_grades': 0,
                'average_gpa': 0.0,
                'grade_distribution': {},
                'status': 'No grades'
            }

        # Calculate statistics
        grade_counts = {}
        gpa_scale = {
            'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'F': 0.0
        }
        total_gpa_points = 0
        count_for_gpa = 0

        for grade in all_grades:
            letter = grade.grade_letter or 'N/A'
            grade_counts[letter] = grade_counts.get(letter, 0) + 1

            if letter in gpa_scale:
                total_gpa_points += gpa_scale[letter]
                count_for_gpa += 1

        average_gpa = (
            total_gpa_points / count_for_gpa if count_for_gpa > 0 else 0.0
        )

        # Get unique students count
        unique_students = len(set(g.student_id for g in all_grades))

        # Determine status using available model fields. If `is_finalized` isn't
        # present, consider a grade finalized when `final_score` is not None.
        finalized = sum(1 for g in all_grades if getattr(g, 'is_finalized', g.final_score is not None))
        released = sum(1 for g in all_grades if getattr(g, 'is_released', False))

        if released == len(all_grades):
            status = 'Released'
        elif finalized == len(all_grades):
            status = 'Finalized'
        else:
            status = 'In Progress'

        return {
            'academic_year': academic_year,
            'semester': semester,
            'total_courses': len(courses),
            'total_students': unique_students,
            'total_grades': len(all_grades),
            'finalized_count': finalized,
            'released_count': released,
            'average_gpa': round(average_gpa, 2),
            'grade_distribution': grade_counts,
            'status': status
        }

    @staticmethod
    def get_current_semester():
        """
        Get the current academic semester from school settings.
        
        Returns:
            tuple: (academic_year, semester) or (None, None) if not set
        """
        from models import SchoolSettings
        
        settings = SchoolSettings.query.first()
        if settings:
            return (settings.current_academic_year, settings.current_semester)
        return (None, None)
    