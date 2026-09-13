"""
STUDENT RESULTS ROUTES
======================
Location: In routes/student_routes.py or separate results_routes.py

Endpoints for students to view their grades and transcripts.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user
from models import (
    StudentProfile, SemesterResultRelease, StudentCourseGrade, User, db
)
from services.result_builder import ResultBuilder
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib import colors

results_bp = Blueprint('results', __name__, url_prefix='/student/results')


# ===== SEMESTER RESULTS =====

@results_bp.route('/semester')
@login_required
def my_results():
    """
    View current semester results.
    Only shows if semester is released.
    """
    
    if current_user.role != 'student':
        abort(403)

    # Get student database ID from user
    student_id = current_user.id
    
    # Get semester results
    data = ResultBuilder.semester(student_id)

    # Check if released
    if not data["released"]:
        return render_template(
            'student/results_not_released.html',
            academic_year=data['academic_year'],
            semester=data['semester']
        )

    return render_template(
        'student/results.html',
        results=data['results'],
        academic_year=data['academic_year'],
        semester=data['semester'],
        semester_gpa=data['semester_gpa'],
        credit_hours=data['credit_hours'],
        total_points=data['total_points']
    )


@results_bp.route('/semester/<path:academic_year>/<semester>')
@login_required
def semester_results(academic_year, semester):
    """
    View results for a specific semester.
    """
    
    if current_user.role != 'student':
        abort(403)

    student_id = current_user.id
    
    # Get results
    data = ResultBuilder.semester(student_id, academic_year, semester)

    # Check if released
    if not data["released"]:
        flash(
            f"Results for {academic_year} {semester} have not been released yet.",
            "info"
        )
        return render_template(
            'student/results_not_released.html',
            academic_year=academic_year,
            semester=semester
        )

    return render_template(
        'student/results.html',
        results=data['results'],
        academic_year=data['academic_year'],
        semester=data['semester'],
        semester_gpa=data['semester_gpa'],
        credit_hours=data['credit_hours'],
        total_points=data['total_points']
    )


@results_bp.route('/semester/<path:academic_year>/<semester>/download-pdf')
@login_required
def download_semester_results_pdf(academic_year, semester):
    """
    Download semester results as PDF.
    """
    
    if current_user.role != 'student':
        abort(403)

    student_id = current_user.id
    
    # Get results
    data = ResultBuilder.semester(student_id, academic_year, semester)

    if not data["released"]:
        flash("Cannot download: Results not released yet", "danger")
        return redirect(url_for('results.semester_results',
                              academic_year=academic_year,
                              semester=semester))

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor("#1f77b4"),
        alignment=1,
        spaceAfter=12
    )
    
    student = User.query.get(current_user.id)
    profile = StudentProfile.query.filter_by(user_id=student.user_id).first()

    elements.append(Paragraph(
        f"SEMESTER RESULTS - {academic_year} {semester}",
        title_style
    ))
    elements.append(Spacer(1, 12))

    # Student info
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    elements.append(Paragraph(f"<b>Student Name:</b> {student.full_name}", info_style))
    elements.append(Paragraph(f"<b>Student ID:</b> {student.user_id}", info_style))
    if profile:
        elements.append(Paragraph(
            f"<b>Programme:</b> {profile.current_programme}",
            info_style
        ))
        elements.append(Paragraph(
            f"<b>Level:</b> {profile.programme_level}",
            info_style
        ))
        if profile.index_number:
            elements.append(Paragraph(
                f"<b>Index Number:</b> {profile.index_number}",
                info_style
            ))

    elements.append(Spacer(1, 12))

    # Results table
    table_data = [
        [
            "Course Code", "Course Name", "Credits",
            "Quiz", "Assignment", "Exam",
            "Score", "Grade"
        ]
    ]

    for result in data['results']:
        table_data.append([
            result['course_code'],
            result['course_name'],
            str(result['credit_hours']),
            f"{result['quiz_score']}/{result['quiz_max']}",
            f"{result['assignment_score']}/{result['assignment_max']}",
            f"{result['exam_score']}/{result['exam_max']}",
            str(result['score']),
            result['grade']
        ])

    # Summary row
    table_data.append([
        "", "", "",
        "", "", "",
        f"GPA: {data['semester_gpa']}", f"Credits: {data['credit_hours']}"
    ])

    table = Table(table_data, colWidths=[0.8*inch, 1.5*inch, 0.6*inch, 0.7*inch, 
                                         0.8*inch, 0.7*inch, 0.7*inch, 0.6*inch])
    
    from reportlab.lib.units import inch
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f0f0f0")]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e6e6e6")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Footer
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y %H:%M')}",
        styles['Normal']
    ))

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Results_{student.user_id}_{academic_year}_{semester}.pdf",
        mimetype='application/pdf'
    )


# ===== TRANSCRIPT =====

@results_bp.route('/transcript')
@login_required
def transcript():
    """
    View complete transcript (all semesters).
    """
    
    if current_user.role != 'student':
        abort(403)

    student_id = current_user.id
    
    # Get transcript
    data = ResultBuilder.transcript(student_id)
    
    student = User.query.get(student_id)
    profile = StudentProfile.query.filter_by(user_id=student.user_id).first()

    return render_template(
        'student/transcript.html',
        student=student,
        profile=profile,
        transcript=data['records'],
        overall_gpa=data['overall_gpa'],
        total_credits=data['total_credits'],
        total_grades=data['total_grades'],
        grade_distribution=data['grade_distribution']
    )


@results_bp.route('/transcript/download-pdf')
@login_required
def download_transcript_pdf():
    """
    Download complete transcript as PDF.
    """
    
    if current_user.role != 'student':
        abort(403)

    student_id = current_user.id
    
    # Get transcript
    data = ResultBuilder.transcript(student_id)
    
    student = User.query.get(student_id)
    profile = StudentProfile.query.filter_by(user_id=student.user_id).first()

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor("#1f77b4"),
        alignment=1,
        spaceAfter=12
    )

    elements.append(Paragraph("ACADEMIC TRANSCRIPT", title_style))
    elements.append(Spacer(1, 12))

    # Student info
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    elements.append(Paragraph(f"<b>Student Name:</b> {student.full_name}", info_style))
    elements.append(Paragraph(f"<b>Student ID:</b> {student.user_id}", info_style))
    if profile:
        elements.append(Paragraph(
            f"<b>Programme:</b> {profile.current_programme}",
            info_style
        ))
        if profile.index_number:
            elements.append(Paragraph(
                f"<b>Index Number:</b> {profile.index_number}",
                info_style
            ))

    elements.append(Spacer(1, 12))

    # Semester sections
    for (year, semester), courses in sorted(data['records'].items(), reverse=True):
        elements.append(Paragraph(
            f"<b>{year} - {semester}</b>",
            styles['Heading3']
        ))

        # Build table for semester
        table_data = [
            ["Course Code", "Course Name", "Credits", "Score", "Grade", "Points"]
        ]

        semester_points = 0
        semester_credits = 0

        for course in courses:
            table_data.append([
                course['course_code'],
                course['course_name'],
                str(course['credit_hours']),
                str(course['score']),
                course['grade'],
                str(course['points'])
            ])
            semester_points += course['points']
            semester_credits += course['credit_hours']

        # Semester summary
        sem_gpa = (semester_points / semester_credits) if semester_credits > 0 else 0
        table_data.append([
            "", "", "",
            f"Semester GPA: {sem_gpa:.2f}", "",
            str(semester_credits)
        ])

        from reportlab.lib.units import inch
        table = Table(table_data, colWidths=[0.9*inch, 2*inch, 0.7*inch, 
                                            0.7*inch, 0.6*inch, 0.7*inch])

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f0f0f0")]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e6e6e6")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))

    # Overall summary
    elements.append(Paragraph("<b>Overall Academic Summary</b>", styles['Heading3']))
    
    summary_data = [
        [f"<b>Overall GPA:</b>", f"{data['overall_gpa']}"],
        [f"<b>Total Credits:</b>", f"{data['total_credits']}"],
        [f"<b>Total Courses:</b>", f"{data['total_grades']}"],
    ]

    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f0f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # Footer
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y %H:%M')}",
        styles['Normal']
    ))

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Transcript_{student.user_id}.pdf",
        mimetype='application/pdf'
    )


# ===== SUMMARY =====

@results_bp.route('/summary')
@login_required
def academic_summary():
    """
    View academic standing summary.
    Quick overview of performance.
    """
    
    if current_user.role != 'student':
        abort(403)

    student_id = current_user.id
    
    summary = ResultBuilder.student_summary(student_id)

    return render_template(
        'student/academic_summary.html',
        summary=summary
    )


# Register blueprint
def register_results_routes(app):
    """Register results routes with Flask app"""
    app.register_blueprint(results_bp)
    