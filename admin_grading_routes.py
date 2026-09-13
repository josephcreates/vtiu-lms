"""
ADMIN GRADING ROUTES
====================
Location: In routes/admin_routes.py or separate grading_routes.py

All administrative endpoints for grade management.
Includes: finalization, release, recall, locking, and reporting.
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import (
    Course, StudentCourseGrade, SemesterResultRelease, 
    StudentProfile, User, db
)
from services.grading_calculation_engine import GradingCalculationEngine
from services.semester_grading_service import SemesterGradingService
from services.result_builder import ResultBuilder
from datetime import datetime
from functools import wraps
import logging
from flask import request, abort
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Optional: Create separate blueprint for grading
grading_bp = Blueprint('grading', __name__)  # REMOVE url_prefix here

def admin_only(f):
    """Decorator to ensure admin/superadmin access grading functions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'superadmin', 'academic_admin']:
            flash("Unauthorized access", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ===== MAIN GRADING DASHBOARD =====

@grading_bp.route('/manage')
@login_required
@admin_only
def manage_grading():
    """
    Main grading management dashboard.
    Shows semester statuses and allows bulk operations.
    """
    
    academic_year = request.args.get('academic_year')
    semester = request.args.get('semester')
    status_filter = request.args.get('status')

    # Get all semesters with grades
    semesters_query = db.session.query(
        StudentCourseGrade.academic_year,
        StudentCourseGrade.semester
    ).distinct()

    if academic_year:
        semesters_query = semesters_query.filter_by(academic_year=academic_year)
    if semester:
        semesters_query = semesters_query.filter_by(semester=semester)

    semesters = semesters_query.order_by(
        StudentCourseGrade.academic_year.desc(),
        StudentCourseGrade.semester.desc()
    ).all()

    # Build semester status list
    semester_statuses = []
    
    for sem_year, sem_name in semesters:
        summary = SemesterGradingService.get_semester_summary(sem_year, sem_name)
        
        # Apply status filter
        if status_filter and summary['status'] != status_filter:
            continue
        
        semester_statuses.append({
            'academic_year': sem_year,
            'semester': sem_name,
            'status': summary['status'],
            'total_grades': summary['total_grades'],
            'finalized_count': summary['finalized_count'],
            'released_count': summary['released_count'],
            'total_students': summary['total_students'],
            'average_gpa': summary['average_gpa']
        })

    # Get unique values for filters
    all_years = db.session.query(
        StudentCourseGrade.academic_year
    ).distinct().order_by(StudentCourseGrade.academic_year.desc()).all()
    
    all_semesters = db.session.query(
        StudentCourseGrade.semester
    ).distinct().order_by(StudentCourseGrade.semester).all()

    return render_template(
        'admin/manage_grading.html',
        semester_statuses=semester_statuses,
        available_years=[y[0] for y in all_years],
        available_semesters=[s[0] for s in all_semesters],
        academic_year_filter=academic_year,
        semester_filter=semester,
        status_filter=status_filter
    )


# ===== FINALIZATION OPERATIONS =====

@grading_bp.route('/semester/<path:academic_year>/<semester>/finalize', methods=['GET', 'POST'])
@login_required
@admin_only
def finalize_semester(academic_year, semester):
    """
    Finalize all grades for a semester.
    
    GET: Show confirmation page with details
    POST: Perform finalization
    """
    
    # If no semester selected, redirect to manage_grading to filter
    if not academic_year or not semester:
        return redirect(url_for('grading.manage_grading'))
    
    # Get all courses for this semester
    courses = Course.query.filter_by(
        academic_year=academic_year,
        semester=semester
    ).all()

    # Get unfinalized grades. If `is_finalized` isn't present, use NULL `final_score`.
    if hasattr(StudentCourseGrade, 'is_finalized'):
        unfinalized = StudentCourseGrade.query.filter_by(
            academic_year=academic_year,
            semester=semester,
            is_finalized=False
        ).count()
    else:
        unfinalized = StudentCourseGrade.query.filter(
            StudentCourseGrade.academic_year == academic_year,
            StudentCourseGrade.semester == semester,
            StudentCourseGrade.final_score == None
        ).count()

    if request.method == 'POST':
        # Perform finalization
        result = SemesterGradingService.finalize_all_course_grades(
            academic_year, semester
        )

        if result['total_errors'] > 0:
            flash(
                f"⚠ Finalized {result['total_success']} grades with "
                f"{result['total_errors']} errors",
                "warning"
            )
        else:
            flash(
                f"✓ Successfully finalized {result['total_success']} grades",
                "success"
            )

        return redirect(url_for('grading.semester_details', 
                              academic_year=academic_year, 
                              semester=semester))

    return render_template(
        'admin/finalize_semester.html',
        academic_year=academic_year,
        semester=semester,
        courses=courses,
        unfinalized_count=unfinalized
    )


@grading_bp.route('/course/<int:course_id>/finalize', methods=['POST'])
@login_required
@admin_only
def finalize_course(course_id):
    """Finalize grades for a single course"""
    
    course = Course.query.get_or_404(course_id)
    
    result = SemesterGradingService.finalize_semester_grades(
        course_id,
        course.academic_year,
        course.semester
    )

    flash(
        f"✓ {result['success_count']} grades finalized for {course.name}",
        "success"
    )

    return redirect(url_for('grading.semester_details',
                          academic_year=course.academic_year,
                          semester=course.semester))


# ===== RESULT RELEASE OPERATIONS =====

@grading_bp.route('/semester/<path:academic_year>/<semester>/release', methods=['POST'])
@login_required
@admin_only
def release_semester_results(academic_year, semester):
    """
    Release results for a semester to students.
    Students can now view their grades.
    """
    
    result = SemesterGradingService.release_semester_results(academic_year, semester)

    if result.get('success'):
        flash(result['message'], "success")
    else:
        flash(result['message'], "danger")

    return redirect(url_for('grading.semester_details',
                          academic_year=academic_year,
                          semester=semester))


@grading_bp.route('/semester/<path:academic_year>/<semester>/recall', methods=['POST'])
@login_required
@admin_only
def recall_semester_results(academic_year, semester):
    """
    Recall (un-release) results for a semester.
    Makes grades private again.
    """
    
    result = SemesterGradingService.recall_semester_results(academic_year, semester)

    if result.get('success'):
        flash(result['message'], "success")
    else:
        flash(result['error'], "danger")

    return redirect(url_for('grading.semester_details',
                          academic_year=academic_year,
                          semester=semester))


# ===== SEMESTER LOCKING =====

@grading_bp.route('/semester/<path:academic_year>/<semester>/lock', methods=['POST'])
@login_required
@admin_only
def lock_semester(academic_year, semester):
    """Lock a semester to prevent further modifications"""
    
    result = SemesterGradingService.lock_semester(academic_year, semester)
    flash(result['message'], "success")

    return redirect(url_for('grading.semester_details',
                          academic_year=academic_year,
                          semester=semester))


@grading_bp.route('/semester/<path:academic_year>/<semester>/unlock', methods=['POST'])
@login_required
@admin_only
def unlock_semester(academic_year, semester):
    """Unlock a semester to allow modifications"""
    
    result = SemesterGradingService.unlock_semester(academic_year, semester)

    if result.get('success'):
        flash(result['message'], "success")
    else:
        flash(result['error'], "danger")

    return redirect(url_for('grading.semester_details',
                          academic_year=academic_year,
                          semester=semester))


# ===== SEMESTER DETAILS & REPORTING =====

@grading_bp.route('/semester/<path:academic_year>/<semester>/details')
@login_required
@admin_only
def semester_details(academic_year, semester):
    """
    Get detailed report for a semester.
    Shows statistics and allows operations.
    """
    
    # If no semester selected, redirect to manage_grading to filter
    if not academic_year or not semester:
        return redirect(url_for('grading.manage_grading'))
    
    # Get semester summary
    summary = SemesterGradingService.get_semester_summary(academic_year, semester)
    
    # Get semester status
    status = SemesterGradingService.get_semester_status(academic_year, semester)
    
    # Get all courses
    courses = Course.query.filter_by(
        academic_year=academic_year,
        semester=semester
    ).all()

    # Get course-level statistics
    course_stats = []
    for course in courses:
        grades = StudentCourseGrade.query.filter_by(
            course_id=course.id,
            academic_year=academic_year,
            semester=semester
        ).all()

        finalized = sum(1 for g in grades if getattr(g, 'is_finalized', g.final_score is not None))
        released = sum(1 for g in grades if getattr(g, 'is_released', False))
        # Compute average only over grades that have a numeric final_score
        final_scores = [g.final_score for g in grades if g.final_score is not None]
        avg_score = (sum(final_scores) / len(final_scores)) if final_scores else 0

        course_stats.append({
            'course': course,
            'total_students': len(grades),
            'finalized_count': finalized,
            'released_count': released,
            'average_score': round(avg_score, 2)
        })

    return render_template(
        'admin/semester_details.html',
        academic_year=academic_year,
        semester=semester,
        summary=summary,
        status=status,
        course_stats=course_stats
    )


# ===== CLASS RESULTS REPORT =====

@grading_bp.route('/class/<programme_name>/<programme_level>/results')
@login_required
@admin_only
def class_results(programme_name, programme_level):
    """
    Get results for a specific class/level.
    Shows all students' grades and statistics.
    """
    
    academic_year = request.args.get('academic_year')
    semester = request.args.get('semester')

    if not academic_year or not semester:
        flash("Academic year and semester required", "danger")
        return redirect(url_for('grading.manage_grading'))

    # Get class results
    results = ResultBuilder.class_results(
        academic_year, semester,
        programme_name, int(programme_level)
    )

    return render_template(
        'admin/class_results.html',
        results=results,
        programme_name=programme_name,
        programme_level=programme_level,
        academic_year=academic_year,
        semester=semester
    )


# ===== STUDENT GRADE DETAILS =====

@grading_bp.route('/student/<student_id>/semester/<path:academic_year>/<semester>')
@login_required
@admin_only
def student_semester_grades(student_id, academic_year, semester):
    """
    View all grades for a student in a specific semester.
    Shows detailed breakdown by assessment type.
    """
    
    user = User.query.filter_by(user_id=student_id).first_or_404()
    profile = StudentProfile.query.filter_by(user_id=student_id).first()

    # Get all grades for the semester
    grades = StudentCourseGrade.query.filter_by(
        student_id=user.id,
        academic_year=academic_year,
        semester=semester
    ).all()

    # Build detailed view
    detailed_grades = []
    total_points = 0
    total_credits = 0

    for grade in grades:
        course = grade.course
        credits = course.credit_hours or 3
        
        detailed_grades.append({
            'course_code': course.code,
            'course_name': course.name,
            'credits': credits,
            'quiz_score': f"{grade.quiz_raw_score}/{grade.quiz_max_score}",
            'quiz_pct': f"{grade.quiz_percentage}%",
            'assignment_score': f"{grade.assignment_raw_score}/{grade.assignment_max_score}",
            'assignment_pct': f"{grade.assignment_percentage}%",
            'exam_score': f"{grade.exam_raw_score}/{grade.exam_max_score}",
            'exam_pct': f"{grade.exam_percentage}%",
            'final_score': grade.final_score,
            'grade': grade.grade_letter,
            'grade_point': grade.grade_point,
            'points': grade.grade_point * credits,
            'is_finalized': getattr(grade, 'is_finalized', grade.final_score is not None),
            'is_released': getattr(grade, 'is_released', False)
        })
        
        total_points += grade.grade_point * credits
        total_credits += credits

    semester_gpa = (total_points / total_credits) if total_credits > 0 else 0.0

    return render_template(
        'admin/student_semester_grades.html',
        student=user,
        profile=profile,
        academic_year=academic_year,
        semester=semester,
        grades=detailed_grades,
        semester_gpa=round(semester_gpa, 2),
        total_credits=total_credits
    )


# ===== RECALCULATION =====

@grading_bp.route('/student/<student_id>/recalculate', methods=['POST'])
@login_required
@admin_only
def recalculate_student_grades(student_id):
    """
    Manually recalculate grades for a student.
    Useful if assessment weights or scores changed.
    """
    
    user = User.query.filter_by(user_id=student_id).first_or_404()
    
    academic_year = request.form.get('academic_year')
    semester = request.form.get('semester')

    result = GradingCalculationEngine.recalculate_student_all_courses(
        user.id, academic_year, semester
    )

    if result['error_count'] > 0:
        flash(
            f"Recalculated {result['success_count']} with "
            f"{result['error_count']} errors",
            "warning"
        )
    else:
        flash(
            f"✓ Recalculated {result['success_count']} grades",
            "success"
        )

    return redirect(url_for('grading.student_semester_grades',
                          student_id=student_id,
                          academic_year=academic_year,
                          semester=semester))


# ===== API ENDPOINTS =====

@grading_bp.route('/semester/<path:academic_year>/<semester>/summary')
@login_required
@admin_only
def api_semester_summary(academic_year, semester):
    """API endpoint for semester summary (JSON)"""
    
    summary = SemesterGradingService.get_semester_summary(academic_year, semester)
    status = SemesterGradingService.get_semester_status(academic_year, semester)
    
    return jsonify({**summary, **status})


@grading_bp.route('/course/<int:course_id>/status')
@login_required
@admin_only
def api_course_status(course_id):
    """API endpoint for course grading status"""
    
    course = Course.query.get_or_404(course_id)
    
    grades = StudentCourseGrade.query.filter_by(course_id=course_id).all()
    
    finalized = sum(1 for g in grades if getattr(g, 'is_finalized', g.final_score is not None))
    released = sum(1 for g in grades if getattr(g, 'is_released', False))
    
    return jsonify({
        'course_id': course_id,
        'course_code': course.code,
        'course_name': course.name,
        'total_students': len(grades),
        'finalized': finalized,
        'released': released,
        'finalized_percent': int((finalized / len(grades) * 100)) if grades else 0,
        'released_percent': int((released / len(grades) * 100)) if grades else 0
    })


# Register blueprint in main app
def register_grading_routes(app):
    """Register grading routes with Flask app"""
    app.register_blueprint(grading_bp)


# ===== PAST RELEASES (ADMIN) =====

@grading_bp.route('/releases')
@login_required
@admin_only
def past_releases():
    """List past released semesters for admin review."""
    releases = SemesterResultRelease.query.filter_by(is_released=True).order_by(
        SemesterResultRelease.released_at.desc()
    ).all()

    return render_template('admin/past_releases.html', releases=releases)


# Helper: accept academic_year/semester via query string and redirect safely
@grading_bp.route('/semester/details')
@login_required
@admin_only
def semester_details_query():
    """Redirect to the path-based semester details route using safe quoting.

    This helps when `academic_year` or `semester` contain slashes or special chars.
    """
    academic_year = request.args.get('academic_year')
    semester = request.args.get('semester')
    if not academic_year or not semester:
        abort(400)

    # Quote values to percent-encode reserved chars (including '/')
    ay_q = quote(academic_year, safe='')
    sem_q = quote(semester, safe='')

    return redirect(f"/semester/{ay_q}/{sem_q}/details")