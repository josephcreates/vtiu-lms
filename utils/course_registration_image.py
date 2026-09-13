"""
Course Registration Image Generator
Generates PNG image instead of PDF for course registration
"""

from io import BytesIO
from datetime import datetime
from flask import render_template_string


def generate_course_registration_image(student, registered_courses, semester, academic_year, logo_path=None):
    """
    Generate an image for course registration
    
    Args:
        student: Current user object (from Flask-Login)
        registered_courses: List of StudentCourseRegistration objects
        semester: Semester name (e.g., 'First')
        academic_year: Year (e.g., '2025')
        logo_path: Full path to logo file (optional)
    
    Returns:
        BytesIO object with PNG image data
    """
    
    import os
    from utils.image_generator import generate_image_from_html
    
    # Get course list
    courses = [r.course for r in registered_courses]
    
    # Logo HTML - only add if logo exists
    logo_html = ""
    if logo_path and os.path.exists(logo_path):
        logo_html = f'<img src="file:///{logo_path}" alt="Logo" style="height: 60px; margin-bottom: 10px;">'
    
    # Count mandatory vs optional
    mandatory_count = sum(1 for c in courses if c.is_mandatory)
    optional_count = len(courses) - mandatory_count
    
    # HTML for the image (no @page CSS for image output)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Course Registration</title>
        <base href="file:///">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20pt;
                color: #333;
                background: white;
                width: 800px;
            }}
            
            .header {{
                text-align: center;
                border-bottom: 3pt solid #1e40af;
                padding-bottom: 15pt;
                margin-bottom: 25pt;
            }}
            
            .header h1 {{
                color: #1e40af;
                margin: 0 0 5pt 0;
                font-size: 24pt;
            }}
            
            .header p {{
                margin: 3pt 0;
                color: #666;
                font-size: 11pt;
            }}
            
            .student-info {{
                background-color: #f0f9ff;
                border: 1pt solid #1e40af;
                padding: 12pt;
                margin-bottom: 20pt;
                border-radius: 4pt;
            }}
            
            .student-info p {{
                margin: 5pt 0;
                font-size: 10pt;
            }}
            
            .summary {{
                background-color: #eff6ff;
                border-left: 4pt solid #1e40af;
                padding: 12pt;
                margin-bottom: 20pt;
            }}
            
            .summary-row {{
                display: flex;
                justify-content: space-between;
                margin: 5pt 0;
                font-size: 10pt;
            }}
            
            .summary-label {{
                font-weight: bold;
                color: #1e40af;
            }}
            
            .section-title {{
                font-size: 13pt;
                font-weight: bold;
                color: #1e40af;
                background-color: #eff6ff;
                padding: 8pt 12pt;
                margin: 20pt 0 10pt 0;
                border-left: 4pt solid #1e40af;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10pt;
                font-size: 10pt;
            }}
            
            table thead {{
                background-color: #1e40af;
                color: white;
            }}
            
            table th {{
                padding: 10pt;
                text-align: left;
                font-weight: bold;
            }}
            
            table td {{
                padding: 8pt 10pt;
                border-bottom: 1pt solid #e5e7eb;
            }}
            
            table tbody tr:nth-child(even) {{
                background-color: #f9fafb;
            }}
            
            .badge {{
                padding: 3pt 8pt;
                border-radius: 3pt;
                font-size: 9pt;
                font-weight: bold;
                white-space: nowrap;
            }}
            
            .badge-mandatory {{
                background-color: #fee2e2;
                color: #991b1b;
            }}
            
            .badge-optional {{
                background-color: #dcfce7;
                color: #166534;
            }}
            
            .footer {{
                margin-top: 30pt;
                padding-top: 15pt;
                border-top: 1pt solid #e5e7eb;
                text-align: center;
                font-size: 9pt;
                color: #999;
            }}
            
            .course-code {{
                font-weight: bold;
                color: #1e40af;
                font-family: monospace;
            }}
        </style>
    </head>
    <body>
        <!-- HEADER -->
        <div class="header">
            {logo_html}
            <h1>Course Registration</h1>
            <p><strong>{semester} Semester, {academic_year}</strong></p>
        </div>
        
        <!-- STUDENT INFO -->
        <div class="student-info">
            <p><strong>Student Name:</strong> {student.first_name} {student.last_name}</p>
            <p><strong>Student ID:</strong> {student.user_id}</p>
            <p><strong>Programme:</strong> {student.student_profile.current_programme if student.student_profile else 'N/A'}</p>
            <p><strong>Level:</strong> {student.student_profile.programme_level if student.student_profile else 'N/A'}</p>
        </div>
        
        <!-- SUMMARY -->
        <div class="summary">
            <div class="summary-row">
                <span class="summary-label">Total Courses:</span>
                <span><strong>{len(courses)}</strong></span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Mandatory:</span>
                <span><strong>{mandatory_count}</strong></span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Optional:</span>
                <span><strong>{optional_count}</strong></span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Generated:</span>
                <span><strong>{datetime.now().strftime('%d %b %Y')}</strong></span>
            </div>
        </div>
        
        <!-- COURSES TABLE -->
        <div class="section-title">Registered Courses</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 15%;">Code</th>
                    <th style="width: 50%;">Course Name</th>
                    <th style="width: 15%;">Type</th>
                    <th style="width: 20%;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Add each course to the table
    for course in courses:
        course_type = "Mandatory" if course.is_mandatory else "Optional"
        badge_class = "badge-mandatory" if course.is_mandatory else "badge-optional"
        
        html += f"""
                <tr>
                    <td><span class="course-code">{course.code}</span></td>
                    <td>{course.name}</td>
                    <td><span class="badge {badge_class}">{course_type}</span></td>
                    <td>Confirmed</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <!-- FOOTER -->
        <div class="footer">
            <p>This document is officially generated. Keep a copy for your records.</p>
            <p>For questions, contact Student Services.</p>
        </div>
    </body>
    </html>
    """
    
    # Generate Image
    img_file = generate_image_from_html(html, format="png", width=850)
    img_file.seek(0)
    
    return img_file


# Legacy function for backward compatibility
def generate_course_registration_pdf(student, registered_courses, semester, academic_year, logo_path=None):
    """
    LEGACY: Kept for backward compatibility - now generates image.
    """
    return generate_course_registration_image(student, registered_courses, semester, academic_year, logo_path)
