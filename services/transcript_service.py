# services/transcript_service.py
"""
Service for generating student transcripts - both semester and full academic history.
"""

from collections import defaultdict
from datetime import datetime
from models import (
    StudentCourseGrade, User, Course, SemesterResultRelease, db
)
from services.grading_calculation_engine import GradingCalculationEngine


class TranscriptService:
    """
    Service for generating and managing student transcripts.
    Provides semester-specific and full academic history views.
    """
    
    @staticmethod
    def generate_semester_transcript(student_id, academic_year, semester):
        """
        Generate transcript data for a specific semester.
        
        Args:
            student_id (int): User.id
            academic_year (str): e.g., "2025"
            semester (str): e.g., "1" or "2"
            
        Returns:
            dict: Structured transcript data including:
                - student: User object
                - academic_year: Year
                - semester: Semester
                - courses: List of StudentCourseGrade objects
                - semester_gpa: GPA for the semester
                - semester_weighted_gpa: GPA weighted by credit hours
                - total_credit_hours: Total credits attempted
                - is_released: Whether results are released to student
        """
        student = User.query.get(student_id)
        if not student:
            return None
        
        # Get all grades for this semester
        grades = GradingCalculationEngine.get_student_grades_for_semester(
            student_id, academic_year, semester
        )
        
        # Calculate GPA metrics
        semester_gpa = GradingCalculationEngine.calculate_gpa(grades)
        semester_weighted_gpa = GradingCalculationEngine.calculate_weighted_gpa(grades)
        
        # Calculate total credit hours
        total_credit_hours = 0
        for grade in grades:
            course = Course.query.get(grade.course_id)
            if course:
                total_credit_hours += course.credit_hours
        
        # Check if results are released
        is_released = TranscriptService._is_semester_released(academic_year, semester)
        
        # Compute cumulative GPA across all semesters for this student (if any)
        try:
            all_grades = GradingCalculationEngine.get_student_all_grades(student_id)
            if all_grades:
                cumulative_gpa = GradingCalculationEngine.calculate_gpa(all_grades)
                cumulative_weighted_gpa = GradingCalculationEngine.calculate_weighted_gpa(all_grades)
            else:
                cumulative_gpa = None
                cumulative_weighted_gpa = None
        except Exception:
            # Safe fallback: don't break if grading engine raises
            cumulative_gpa = None
            cumulative_weighted_gpa = None

        # Build course details with course names and assessment weights
        from models import CourseAssessmentScheme
        course_details = []
        for grade in grades:
            course = Course.query.get(grade.course_id)
            if course:
                # Fetch assessment scheme for this course
                scheme = CourseAssessmentScheme.query.filter_by(course_id=course.id).first()
                
                course_details.append({
                    'course': course,
                    'grade': grade,
                    'course_name': course.name,
                    'course_code': course.code,
                    'credit_hours': course.credit_hours,
                    'final_score': grade.final_score,
                    'grade_letter': grade.grade_letter,
                    'quiz_score': grade.quiz_total_score,
                    'quiz_max': grade.quiz_max_possible,
                    'assignment_score': grade.assignment_total_score,
                    'assignment_max': grade.assignment_max_possible,
                    'exam_score': grade.exam_total_score,
                    'exam_max': grade.exam_max_possible,
                    'quiz_weight': scheme.quiz_weight if scheme else 10.0,
                    'assignment_weight': scheme.assignment_weight if scheme else 30.0,
                    'exam_weight': scheme.exam_weight if scheme else 60.0
                })
        
        return {
            'student': student,
            'student_id': student.user_id,
            'student_name': student.full_name,
            'academic_year': academic_year,
            'semester': semester,
            'courses': course_details,
            'semester_gpa': semester_gpa,
            'semester_weighted_gpa': semester_weighted_gpa,
            'total_credit_hours': total_credit_hours,
            # Include cumulative GPA across all semesters for CGPA display
            'cumulative_gpa': cumulative_gpa,
            'cumulative_weighted_gpa': cumulative_weighted_gpa,
            'is_released': is_released,
            'generated_at': datetime.utcnow()
        }
    
    @staticmethod
    def generate_full_transcript(student_id):
        """
        Generate complete transcript across all semesters.
        
        Args:
            student_id (int): User.id
            
        Returns:
            dict: Full transcript data including:
                - student: User object
                - all_semesters: Dict of {(academic_year, semester): [grades]}
                - cumulative_gpa: GPA across all semesters
                - cumulative_weighted_gpa: Weighted GPA across all semesters
                - total_credit_hours_attempted: Total credits across all semesters
                - total_credit_hours_earned: Credits for passing grades
                - semesters_summary: List of semester summary dicts
        """
        student = User.query.get(student_id)
        if not student:
            return None
        
        # Get all grades for the student
        all_grades = GradingCalculationEngine.get_student_all_grades(student_id)
        
        # Group by (academic_year, semester)
        grouped = defaultdict(list)
        for grade in all_grades:
            key = (grade.academic_year, grade.semester)
            grouped[key].append(grade)
        
        # Sort by academic year and semester
        sorted_keys = sorted(grouped.keys(), key=lambda x: (x[0], x[1]))
        
        # Build semester summaries
        semesters_summary = []
        seen_semesters = set()  # Deduplicate by (academic_year, semester)
        for academic_year, semester in sorted_keys:
            semester_key = (academic_year, semester)
            if semester_key in seen_semesters:
                continue  # Skip duplicate semesters
            seen_semesters.add(semester_key)
            
            grades = grouped[(academic_year, semester)]
            semester_gpa = GradingCalculationEngine.calculate_gpa(grades)
            semester_weighted_gpa = GradingCalculationEngine.calculate_weighted_gpa(grades)
            
            total_credits = 0
            for grade in grades:
                course = Course.query.get(grade.course_id)
                if course:
                    total_credits += course.credit_hours
            
            semesters_summary.append({
                'academic_year': academic_year,
                'semester': semester,
                'gpa': semester_gpa,
                'weighted_gpa': semester_weighted_gpa,
                'credit_hours': total_credits,
                'courses_count': len(grades)
            })
        
        # Calculate cumulative GPA
        cumulative_gpa = GradingCalculationEngine.calculate_gpa(all_grades)
        cumulative_weighted_gpa = GradingCalculationEngine.calculate_weighted_gpa(all_grades)
        
        # Calculate total credit hours
        total_credit_hours_attempted = 0
        total_credit_hours_earned = 0  # Only for passing grades
        
        passing_grades = {'A', 'B', 'C', 'D'}  # Assuming D and above pass
        
        for grade in all_grades:
            course = Course.query.get(grade.course_id)
            if course:
                total_credit_hours_attempted += course.credit_hours
                if grade.grade_letter in passing_grades:
                    total_credit_hours_earned += course.credit_hours
        
        # Build detailed semester data with course information and weights
        from models import CourseAssessmentScheme
        semesters_detailed = {}
        for academic_year, semester in sorted_keys:
            grades = grouped[(academic_year, semester)]
            
            course_details = []
            for grade in grades:
                course = Course.query.get(grade.course_id)
                if course:
                    # Fetch assessment scheme for this course
                    scheme = CourseAssessmentScheme.query.filter_by(course_id=course.id).first()
                    
                    course_details.append({
                        'course': course,
                        'grade': grade,
                        'course_name': course.name,
                        'course_code': course.code,
                        'credit_hours': course.credit_hours,
                        'final_score': grade.final_score,
                        'grade_letter': grade.grade_letter,
                        'quiz_score': grade.quiz_total_score,
                        'quiz_max': grade.quiz_max_possible,
                        'assignment_score': grade.assignment_total_score,
                        'assignment_max': grade.assignment_max_possible,
                        'exam_score': grade.exam_total_score,
                        'exam_max': grade.exam_max_possible,
                        'quiz_weight': scheme.quiz_weight if scheme else 10.0,
                        'assignment_weight': scheme.assignment_weight if scheme else 30.0,
                        'exam_weight': scheme.exam_weight if scheme else 60.0
                    })
            
            is_released = TranscriptService._is_semester_released(academic_year, semester)
            
            semesters_detailed[(academic_year, semester)] = {
                'academic_year': academic_year,
                'semester': semester,
                'courses': course_details,
                'gpa': GradingCalculationEngine.calculate_gpa(grades),
                'is_released': is_released
            }
        
        return {
            'student': student,
            'student_id': student.user_id,
            'student_name': student.full_name,
            'all_semesters': semesters_detailed,
            'semesters_summary': semesters_summary,
            'cumulative_gpa': cumulative_gpa,
            'cumulative_weighted_gpa': cumulative_weighted_gpa,
            'total_credit_hours_attempted': total_credit_hours_attempted,
            'total_credit_hours_earned': total_credit_hours_earned,
            'generated_at': datetime.utcnow()
        }
    
    @staticmethod
    def _is_semester_released(academic_year, semester):
        """
        Check if results for a semester have been released.
        
        Args:
            academic_year (str): e.g., "2025"
            semester (str): e.g., "1" or "2"
            
        Returns:
            bool: True if released, False otherwise
        """
        release = SemesterResultRelease.query.filter_by(
            academic_year=academic_year,
            semester=semester,
            is_released=True
        ).first()
        
        return bool(release)
    
    @staticmethod
    def _format_academic_year(academic_year):
        """
        Format academic year from '2025/2026' to '2026' (extract the end year).
        
        Args:
            academic_year (str): e.g., '2025/2026' or '2026'
            
        Returns:
            str: Formatted year, e.g., '2026'
        """
        if not academic_year:
            return academic_year
        # If it contains a slash, extract the second year
        if '/' in academic_year:
            return academic_year.split('/')[-1].strip()
        return academic_year
    
    @staticmethod
    def get_current_semester_transcript(student_id):
        """
        Get transcript for the most recently released semester.
        
        Args:
            student_id (int): User.id
            
        Returns:
            dict: Semester transcript or None if no released semesters
        """
        # Get latest released semester
        release = (
            SemesterResultRelease.query
            .filter_by(is_released=True)
            .order_by(SemesterResultRelease.released_at.desc())
            .first()
        )
        
        if not release:
            return None
        
        return TranscriptService.generate_semester_transcript(
            student_id, release.academic_year, release.semester
        )
    
    @staticmethod
    def export_semester_transcript_text(transcript_data):
        """
        Export semester transcript as formatted text.
        
        Args:
            transcript_data (dict): Output from generate_semester_transcript()
            
        Returns:
            str: Formatted text transcript
        """
        if not transcript_data:
            return "No transcript data available."
        
        lines = []
        lines.append("=" * 80)
        lines.append("ACADEMIC TRANSCRIPT - SEMESTER REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Student info
        lines.append(f"Student Name: {transcript_data['student_name']}")
        lines.append(f"Student ID: {transcript_data['student_id']}")
        lines.append(f"Academic Year: {transcript_data['academic_year']}")
        lines.append(f"Semester: {transcript_data['semester']}")
        lines.append("")
        
        # Release status
        release_status = "RELEASED" if transcript_data['is_released'] else "NOT RELEASED"
        lines.append(f"Status: {release_status}")
        lines.append("")
        
        # Course details
        lines.append("-" * 80)
        lines.append(f"{'Course Code':<15} {'Course Name':<40} {'Score':<10} {'Grade':<5}")
        lines.append("-" * 80)
        
        for course_detail in transcript_data['courses']:
            code = course_detail['course_code']
            name = course_detail['course_name'][:38]
            score = f"{course_detail['final_score']:.2f}"
            grade = course_detail['grade_letter'] or 'N/A'
            lines.append(f"{code:<15} {name:<40} {score:>10} {grade:>5}")
        
        lines.append("-" * 80)
        lines.append("")
        
        # Summary statistics
        lines.append(f"Total Credit Hours: {transcript_data['total_credit_hours']}")
        lines.append(f"Semester GPA: {transcript_data['semester_gpa']:.2f}")
        lines.append(f"Weighted GPA: {transcript_data['semester_weighted_gpa']:.2f}")
        lines.append("")
        lines.append(f"Generated: {transcript_data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def export_full_transcript_text(transcript_data):
        """
        Export full transcript as formatted text.
        
        Args:
            transcript_data (dict): Output from generate_full_transcript()
            
        Returns:
            str: Formatted text transcript
        """
        if not transcript_data:
            return "No transcript data available."
        
        lines = []
        lines.append("=" * 80)
        lines.append("ACADEMIC TRANSCRIPT - FULL HISTORY")
        lines.append("=" * 80)
        lines.append("")
        
        # Student info
        lines.append(f"Student Name: {transcript_data['student_name']}")
        lines.append(f"Student ID: {transcript_data['student_id']}")
        lines.append("")
        
        # Semester-by-semester details
        for key in sorted(transcript_data['all_semesters'].keys()):
            semester_data = transcript_data['all_semesters'][key]
            
            lines.append("-" * 80)
            lines.append(f"Academic Year: {semester_data['academic_year']} | Semester: {semester_data['semester']}")
            lines.append("-" * 80)
            lines.append(f"{'Course Code':<15} {'Course Name':<40} {'Score':<10} {'Grade':<5}")
            lines.append("-" * 80)
            
            for course_detail in semester_data['courses']:
                code = course_detail['course_code']
                name = course_detail['course_name'][:38]
                score = f"{course_detail['final_score']:.2f}"
                grade = course_detail['grade_letter'] or 'N/A'
                lines.append(f"{code:<15} {name:<40} {score:>10} {grade:>5}")
            
            lines.append("")
            lines.append(f"Semester GPA: {semester_data['gpa']:.2f}")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("CUMULATIVE STATISTICS")
        lines.append("=" * 80)
        lines.append(f"Total Credit Hours Attempted: {transcript_data['total_credit_hours_attempted']}")
        lines.append(f"Total Credit Hours Earned: {transcript_data['total_credit_hours_earned']}")
        lines.append(f"Cumulative GPA: {transcript_data['cumulative_gpa']:.2f}")
        lines.append(f"Cumulative Weighted GPA: {transcript_data['cumulative_weighted_gpa']:.2f}")
        lines.append("")
        lines.append(f"Generated: {transcript_data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_semester_transcript_html(transcript_data):
        """
        Generate HTML representation of semester transcript for PDF export.
        Modern, simple design with school logo and signature section.
        
        Args:
            transcript_data (dict): Output from generate_semester_transcript()
            
        Returns:
            str: HTML string ready for image conversion
        """
        if not transcript_data:
            return "<p>No transcript data available.</p>"
        
        # Build course rows - simplified without assessment breakdown
        course_rows = ""
        for course in transcript_data['courses']:
            course_rows += f"""
            <tr>
                <td>{course['course_code']}</td>
                <td>{course['course_name']}</td>
                <td class="text-center">{course['credit_hours']}</td>
                <td class="text-center"><strong>{course['final_score']:.2f}</strong></td>
                <td class="text-center"><strong>{course['grade_letter']}</strong></td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Semester Transcript</title>
            <style>
                .header-left {{
                    display: flex;
                    align-items: flex-start;
                    gap: 16px;
                }}
                .logo img {{
                    height: 60px;
                    width: auto;
                }}
                .school-details {{
                    font-size: 11px;
                    color: #1a1a1a;
                    line-height: 1.3;
                    font-weight: 500;
                    margin: 0;
                }}
                .school-details p {{
                    margin: 2px 0;
                    white-space: nowrap;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #2c3e50;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .title {{
                    text-align: right;
                }}
                .title h1 {{
                    font-size: 20px;
                    color: #2c3e50;
                    margin-bottom: 5px;
                }}
                .title p {{
                    font-size: 13px;
                    color: #7f8c8d;
                }}
                .student-section {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 16px;
                    margin-bottom: 16px;
                    padding: 12px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }}
                .student-info p {{
                    margin: 8px 0;
                    font-size: 14px;
                }}
                .student-info strong {{
                    color: #2c3e50;
                    width: 120px;
                    display: inline-block;
                }}
                .summary {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 12px;
                    margin: 16px 0;
                }}
                .summary-card {{
                    padding: 8px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 6px;
                    text-align: center;
                    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
                }}
                .summary-card .label {{
                    font-size: 10px;
                    font-weight: 600;
                    text-transform: uppercase;
                    opacity: 0.95;
                    margin-bottom: 6px;
                }}
                .summary-card .value {{
                    font-size: 20px;
                    font-weight: 700;
                }}
                .courses-section {{
                    margin: 20px 0;
                }}
                .courses-section h2 {{
                    font-size: 16px;
                    color: #2c3e50;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #667eea;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th {{
                    background: #2c3e50;
                    color: white;
                    padding: 8px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 600;
                    text-transform: uppercase;
                }}
                td {{
                    padding: 8px;
                    border-bottom: 1px solid #ecf0f1;
                    font-size: 13px;
                }}
                tbody tr:nth-child(odd) {{
                    background: #f8f9fa;
                }}
                tbody tr:hover {{
                    background: #e8eef7;
                }}
                .text-center {{
                    text-align: center;
                }}
                .signature-section {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 2px solid #ecf0f1;
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 30px;
                }}
                .signature-box {{
                    text-align: center;
                }}
                .signature-line {{
                    border-top: 2px solid #2c3e50;
                    margin-bottom: 8px;
                    height: 40px;
                }}
                .signature-box p {{
                    font-size: 12px;
                    color: #7f8c8d;
                    font-weight: 600;
                    text-transform: uppercase;
                }}
                .footer {{
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 1px solid #ecf0f1;
                    text-align: center;
                    font-size: 11px;
                    color: #95a5a6;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-left">
                        <div class="logo"><img src="file:///c:/Users/lampt/Desktop/LMS/LMS/static/VTIU-LOGO.png" alt="School Logo"></div>
                        <div class="school-details">
                            <p><strong>VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY</strong></p>
                            <p>ACADEMIC AFFAIRS OFFICE</p>
                            <p>P.O.Box 12959, Kumasi - Ghana. Contact 0307020844</p>
                            <p>Email: info@vtiu.edu.gh</p>
                        </div>
                    </div>
                    <div class="title">
                        <h1>Semester Report</h1>
                    </div>
                </div>
                
                <div class="student-section">
                    <div class="student-info">
                        <p><strong>Student Name:</strong> {transcript_data['student_name']}</p>
                        <p><strong>Student ID:</strong> {transcript_data['student_id']}</p>
                    </div>
                    <div class="student-info">
                        <p><strong>Academic Year:</strong> {TranscriptService._format_academic_year(transcript_data['academic_year'])}</p>
                        <p><strong>Semester:</strong> {transcript_data['semester']}</p>
                    </div>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <div class="label">GPA</div>
                        <div class="value">{transcript_data['semester_gpa']:.2f}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">Weighted GPA</div>
                        <div class="value">{transcript_data['semester_weighted_gpa']:.2f}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">Credit Hours</div>
                        <div class="value">{transcript_data['total_credit_hours']}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">CGPA</div>
                        <div class="value">{(f"{transcript_data.get('cumulative_gpa'):.2f}" if transcript_data.get('cumulative_gpa') is not None else '-')}</div>
                    </div>
                </div>
                
                <div class="courses-section">
                    <h2>Courses</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Course Code</th>
                                <th>Course Name</th>
                                <th class="text-center">Credits</th>
                                <th class="text-center">Score</th>
                                <th class="text-center">Grade</th>
                            </tr>
                        </thead>
                        <tbody>
                            {course_rows}
                        </tbody>
                    </table>
                </div>
                
                <div class="signature-section">
                    <div class="signature-box">
                        <div class="signature-line"></div>
                        <p>Registrar Signature</p>
                    </div>
                    <div class="signature-box">
                        <div class="signature-line"></div>
                        <p>Date</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an official academic transcript issued by the Institution.</p>
                    <p>Generated: {transcript_data['generated_at'].strftime('%B %d, %Y')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def generate_full_transcript_html(transcript_data):
        """
        Generate HTML representation of full transcript for PDF export.
        Modern, simple design with school logo and signature section.
        
        Args:
            transcript_data (dict): Output from generate_full_transcript()
            
        Returns:
            str: HTML string ready for image conversion
        """
        if not transcript_data:
            return "<p>No transcript data available.</p>"
        
        # Build semester summary table
        semester_rows = ""
        for summary in transcript_data['semesters_summary']:
            semester_rows += f"""
            <tr>
                <td>{TranscriptService._format_academic_year(summary['academic_year'])}</td>
                <td>{summary['semester']}</td>
                <td class="text-center">{summary['courses_count']}</td>
                <td class="text-center"><strong>{summary['gpa']:.2f}</strong></td>
                <td class="text-center"><strong>{summary['weighted_gpa']:.2f}</strong></td>
                <td class="text-center">{summary['credit_hours']}</td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Full Academic Transcript</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    color: #2c3e50;
                    line-height: 1.6;
                    background: white;
                    padding: 30px;
                }}
                .header-left {{
                    display: flex;
                    align-items: flex-start;
                    gap: 16px;
                }}
                .logo img {{
                    height: 60px;
                    width: auto;
                }}
                .school-details {{
                    font-size: 11px;
                    color: #1a1a1a;
                    line-height: 1.3;
                    font-weight: 500;
                    margin: 0;
                }}
                .school-details p {{
                    margin: 2px 0;
                    white-space: nowrap;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #2c3e50;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .title {{
                    text-align: right;
                }}
                .title h1 {{
                    font-size: 20px;
                    color: #2c3e50;
                    margin-bottom: 5px;
                }}
                .title p {{
                    font-size: 13px;
                    color: #7f8c8d;
                }}
                .student-section {{
                    margin-bottom: 16px;
                    padding: 12px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }}
                .student-section p {{
                    margin: 8px 0;
                    font-size: 14px;
                }}
                .student-section strong {{
                    color: #2c3e50;
                    width: 120px;
                    display: inline-block;
                }}
                .summary {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                    margin: 16px 0;
                }}
                .summary-card {{
                    padding: 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                }}
                .summary-card .label {{
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    opacity: 0.9;
                    margin-bottom: 8px;
                }}
                .summary-card .value {{
                    font-size: 24px;
                    font-weight: bold;
                }}
                .semesters-section {{
                    margin: 20px 0;
                }}
                .semesters-section h2 {{
                    font-size: 16px;
                    color: #2c3e50;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #667eea;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th {{
                    background: #2c3e50;
                    color: white;
                    padding: 8px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 600;
                    text-transform: uppercase;
                }}
                td {{
                    padding: 8px;
                    border-bottom: 1px solid #ecf0f1;
                    font-size: 13px;
                }}
                tbody tr:nth-child(odd) {{
                    background: #f8f9fa;
                }}
                tbody tr:hover {{
                    background: #e8eef7;
                }}
                .text-center {{
                    text-align: center;
                }}
                .signature-section {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 2px solid #ecf0f1;
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 30px;
                }}
                .signature-box {{
                    text-align: center;
                }}
                .signature-line {{
                    border-top: 2px solid #2c3e50;
                    margin-bottom: 8px;
                    height: 40px;
                }}
                .signature-box p {{
                    font-size: 12px;
                    color: #7f8c8d;
                    font-weight: 600;
                    text-transform: uppercase;
                }}
                .footer {{
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 1px solid #ecf0f1;
                    text-align: center;
                    font-size: 11px;
                    color: #95a5a6;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-left">
                        <div class="logo"><img src="file:///c:/Users/lampt/Desktop/LMS/LMS/static/VTIU-LOGO.png" alt="School Logo"></div>
                        <div class="school-details">
                            <p><strong>VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY</strong></p>
                            <p>ACADEMIC AFFAIRS OFFICE</p>
                            <p>P.O.Box 12959, Kumasi - Ghana. Contact 0307020844</p>
                            <p>Email: info@vtiu.edu.gh</p>
                        </div>
                    </div>
                    <div class="title">
                        <h1>ACADEMIC TRANSCRIPT</h1>
                        <p>Complete Academic History</p>
                    </div>
                </div>
                
                <div class="student-section">
                    <p><strong>Student Name:</strong> {transcript_data['student_name']}</p>
                    <p><strong>Student ID:</strong> {transcript_data['student_id']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <div class="label">Cumulative GPA</div>
                        <div class="value">{transcript_data['cumulative_gpa']:.2f}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">Weighted GPA</div>
                        <div class="value">{transcript_data['cumulative_weighted_gpa']:.2f}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">Total Credits</div>
                        <div class="value">{transcript_data['total_credit_hours_attempted']}</div>
                    </div>
                </div>
                
                <div class="semesters-section">
                    <h2>Academic History</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Academic Year</th>
                                <th>Semester</th>
                                <th class="text-center">Courses</th>
                                <th class="text-center">GPA</th>
                                <th class="text-center">Weighted GPA</th>
                                <th class="text-center">Credit Hours</th>
                            </tr>
                        </thead>
                        <tbody>
                            {semester_rows}
                        </tbody>
                    </table>
                </div>
                
                <div class="signature-section">
                    <div class="signature-box">
                        <div class="signature-line"></div>
                        <p>Registrar / Director</p>
                    </div>
                    <div class="signature-box">
                        <div class="signature-line"></div>
                        <p>Date</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an official academic transcript issued by the Institution.</p>
                    <p>Generated: {transcript_data['generated_at'].strftime('%B %d, %Y')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    