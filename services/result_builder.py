"""
RESULT BUILDER SERVICE
======================
Location: services/result_builder.py

Builds student results by aggregating grades by semester and calculating GPA.
Used by student and admin dashboards.
"""

from models import (
    StudentCourseGrade, StudentCourseRegistration, Course, 
    StudentProfile, User, SemesterResultRelease, db
)
from sqlalchemy import func
from datetime import datetime


class ResultBuilder:
    """
    Builds student result data for display.
    Handles semester results, transcripts, and GPA calculations.
    """

    @staticmethod
    def semester(student_id, academic_year=None, semester=None):
        """
        Get semester results for a student.
        
        Args:
            student_id: Student's database ID (not user_id)
            academic_year: Academic year (optional - uses current if not provided)
            semester: Semester (optional - uses current if not provided)
            
        Returns:
            dict with:
                - results: List of course grades with details
                - academic_year: The academic year
                - semester: The semester
                - released: Whether results are released to student
                - semester_gpa: GPA for this semester
                - credit_hours: Total credit hours taken
        """
        
        # Resolve academic period dynamically
        if not academic_year or not semester:
            release = SemesterResultRelease.query.filter_by(
                is_released=True
            ).order_by(SemesterResultRelease.released_at.desc()).first()
            
            if not release:
                return {
                    "results": [],
                    "academic_year": None,
                    "semester": None,
                    "released": False,
                    "semester_gpa": 0.0,
                    "credit_hours": 0
                }
            
            academic_year = release.academic_year
            semester = release.semester

        # Get all grades for this semester. Use `is_finalized` if present; otherwise
        # treat non-NULL `final_score` as finalized.
        if hasattr(StudentCourseGrade, 'is_finalized'):
            grades = StudentCourseGrade.query.filter_by(
                student_id=student_id,
                academic_year=academic_year,
                semester=semester,
                is_finalized=True
            ).all()
        else:
            grades = StudentCourseGrade.query.filter(
                StudentCourseGrade.student_id == student_id,
                StudentCourseGrade.academic_year == academic_year,
                StudentCourseGrade.semester == semester,
                StudentCourseGrade.final_score != None
            ).all()

        # Check if released
        is_released = (
            SemesterResultRelease.query.filter_by(
                academic_year=academic_year,
                semester=semester,
                is_released=True
            ).first() is not None
        )

        # Build results list
        from models import CourseAssessmentScheme
        results = []
        total_points = 0.0
        total_credits = 0
        
        for grade in grades:
            course = grade.course
            # Fetch assessment scheme for this course (to show weights)
            scheme = CourseAssessmentScheme.query.filter_by(course_id=course.id).first()
            
            result_entry = {
                "course_code": course.code,
                "course_name": course.name,
                "credit_hours": course.credit_hours or 3,
                "score": grade.final_score,
                "grade": grade.grade_letter,
                "grade_point": grade.grade_point,
                "pass_fail": grade.pass_fail,
                "points": (grade.grade_point or 0) * (course.credit_hours or 3),
                "quiz_score": grade.quiz_total_score,
                "quiz_max": grade.quiz_max_possible,
                "assignment_score": grade.assignment_total_score,
                "assignment_max": grade.assignment_max_possible,
                "exam_score": grade.exam_total_score,
                "exam_max": grade.exam_max_possible,
                "quiz_weight": scheme.quiz_weight if scheme else 10.0,
                "assignment_weight": scheme.assignment_weight if scheme else 30.0,
                "exam_weight": scheme.exam_weight if scheme else 60.0
            }
            results.append(result_entry)
            
            total_points += (grade.grade_point or 0) * (course.credit_hours or 3)
            total_credits += course.credit_hours or 3

        # Calculate semester GPA
        semester_gpa = (total_points / total_credits) if total_credits > 0 else 0.0

        return {
            "results": results,
            "academic_year": academic_year,
            "semester": semester,
            "released": is_released,
            "semester_gpa": round(semester_gpa, 2),
            "credit_hours": total_credits,
            "total_points": round(total_points, 2),
            "total_grades": len(grades)
        }

    @staticmethod
    def transcript(student_id):
        """
        Get complete transcript for a student (all semesters).
        
        Args:
            student_id: Student's database ID
            
        Returns:
            dict with:
                - records: Grouped by (academic_year, semester)
                - overall_gpa: GPA across all semesters
                - total_credits: Total credit hours completed
                - grade_distribution: Count of each grade letter
        """
        
        # Get all finalized grades. Use `is_finalized` if present; otherwise select
        # grades with non-NULL `final_score`.
        if hasattr(StudentCourseGrade, 'is_finalized'):
            all_grades = StudentCourseGrade.query.filter_by(
                student_id=student_id,
                is_finalized=True
            ).all()
        else:
            all_grades = StudentCourseGrade.query.filter(
                StudentCourseGrade.student_id == student_id,
                StudentCourseGrade.final_score != None
            ).all()

        # Group by semester
        grouped = {}
        for grade in all_grades:
            key = (grade.academic_year, grade.semester)
            if key not in grouped:
                grouped[key] = []
            
            course = grade.course
            grouped[key].append({
                "course_code": course.code,
                "course_name": course.name,
                "credit_hours": course.credit_hours or 3,
                "score": grade.final_score,
                "grade": grade.grade_letter,
                "grade_point": grade.grade_point,
                "academic_year": grade.academic_year,
                "semester": grade.semester
            })

        # Calculate overall GPA
        gpa_mapping = {
            'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'F': 0.0
        }
        
        total_points = 0.0
        total_credits = 0
        grade_distribution = {}
        
        for grade in all_grades:
            gp = gpa_mapping.get(grade.grade_letter, 0)
            credits = grade.course.credit_hours or 3
            total_points += gp * credits
            total_credits += credits
            
            # Count grades
            grade_distribution[grade.grade_letter] = (
                grade_distribution.get(grade.grade_letter, 0) + 1
            )

        overall_gpa = (total_points / total_credits) if total_credits > 0 else 0.0

        # Sort by year/semester (newest first)
        sorted_records = {}
        for key in sorted(grouped.keys(), reverse=True):
            sorted_records[key] = grouped[key]

        return {
            "records": sorted_records,
            "overall_gpa": round(overall_gpa, 2),
            "total_credits": total_credits,
            "total_grades": len(all_grades),
            "grade_distribution": grade_distribution
        }

    @staticmethod
    def student_summary(student_id):
        """
        Get quick summary of student's academic standing.
        
        Args:
            student_id: Student's database ID
            
        Returns:
            dict with key metrics
        """
        
        # Get student info
        student = User.query.get(student_id)
        profile = StudentProfile.query.filter_by(user_id=student.user_id).first()
        
        # Get latest semester results. Use `is_finalized` when available,
        # otherwise select grades with non-NULL `final_score`.
        if hasattr(StudentCourseGrade, 'is_finalized'):
            latest_grades = (
                StudentCourseGrade.query
                .filter_by(student_id=student_id, is_finalized=True)
                .order_by(StudentCourseGrade.calculated_at.desc())
                .limit(5)
                .all()
            )
        else:
            latest_grades = (
                StudentCourseGrade.query
                .filter(StudentCourseGrade.student_id == student_id,
                        StudentCourseGrade.final_score != None)
                .order_by(StudentCourseGrade.calculated_at.desc())
                .limit(5)
                .all()
            )
        
        # Calculate current semester GPA (if available)
        if latest_grades:
            latest_year = latest_grades[0].academic_year
            latest_sem = latest_grades[0].semester
            latest_result = ResultBuilder.semester(student_id, latest_year, latest_sem)
        else:
            latest_result = None

        # Get all-time transcript
        transcript = ResultBuilder.transcript(student_id)

        return {
            "student_name": f"{student.first_name} {student.last_name}",
            "student_id": student.user_id,
            "programme": profile.current_programme if profile else None,
            "level": profile.programme_level if profile else None,
            "index_number": profile.index_number if profile else None,
            "admission_date": profile.admission_date if profile else None,
            "latest_semester": latest_result,
            "overall_gpa": transcript["overall_gpa"],
            "total_credits": transcript["total_credits"],
            "total_grades": transcript["total_grades"],
            "academic_status": profile.academic_status if profile else "Unknown"
        }

    @staticmethod
    def class_results(academic_year, semester, programme_name, programme_level):
        """
        Get all results for a class (used by admin/teachers).
        
        Args:
            academic_year: Academic year
            semester: Semester
            programme_name: Programme name
            programme_level: Programme level (e.g., "100")
            
        Returns:
            dict with class-level statistics and individual results
        """
        
        # Get all students in this class
        students = StudentProfile.query.filter_by(
            current_programme=programme_name,
            programme_level=programme_level
        ).all()
        
        student_results = []
        class_stats = {
            'total_students': len(students),
            'grades_submitted': 0,
            'grades_finalized': 0,
            'grades_released': 0,
            'average_gpa': 0.0,
            'highest_gpa': 0.0,
            'lowest_gpa': 4.0,
            'pass_rate': 0.0
        }
        
        total_gpa = 0.0
        passes = 0
        
        for student in students:
            user = User.query.filter_by(user_id=student.user_id).first()
            if not user:
                continue
            
            # Get all grades for this semester
            grades = StudentCourseGrade.query.filter_by(
                student_id=user.id,
                academic_year=academic_year,
                semester=semester
            ).all()
            
            if not grades:
                continue
            
            # Calculate student GPA for this semester
            gpa_mapping = {
                'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'F': 0.0
            }
            
            total_points = sum(
                gpa_mapping.get(g.grade_letter, 0) for g in grades
            )
            gpa = total_points / len(grades) if grades else 0.0
            
            pass_count = sum(
                1 for g in grades if g.pass_fail == 'PASS'
            )
            
            student_results.append({
                'student_id': student.user_id,
                'name': f"{user.first_name} {user.last_name}",
                'index_number': student.index_number,
                'gpa': round(gpa, 2),
                'grades_count': len(grades),
                'passed': pass_count,
                'failed': len(grades) - pass_count,
                'is_finalized': all(getattr(g, 'is_finalized', g.final_score is not None) for g in grades),
                'is_released': all(getattr(g, 'is_released', False) for g in grades)
            })
            
            total_gpa += gpa
            class_stats['grades_submitted'] += len(grades)
            if all(getattr(g, 'is_finalized', g.final_score is not None) for g in grades):
                class_stats['grades_finalized'] += 1
            if all(getattr(g, 'is_released', False) for g in grades):
                class_stats['grades_released'] += 1
            
            if pass_count == len(grades):
                passes += 1
            
            class_stats['highest_gpa'] = max(class_stats['highest_gpa'], gpa)
            class_stats['lowest_gpa'] = min(class_stats['lowest_gpa'], gpa)

        if student_results:
            class_stats['average_gpa'] = round(
                total_gpa / len(student_results), 2
            )
            class_stats['pass_rate'] = round(
                (passes / len(student_results)) * 100, 2
            )

        return {
            'academic_year': academic_year,
            'semester': semester,
            'programme': programme_name,
            'level': programme_level,
            'statistics': class_stats,
            'student_results': sorted(
                student_results,
                key=lambda x: x['gpa'],
                reverse=True
            )
        }
    