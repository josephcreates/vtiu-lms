# routes/student_transcript_routes.py
"""
Student routes for viewing and downloading transcripts.
Add these routes to your student blueprint.
"""

from flask import Blueprint, render_template, abort, flash, redirect, url_for, request, jsonify, send_file, make_response
from flask_login import login_required, current_user
from io import BytesIO
from datetime import datetime
from utils.image_generator import generate_image_from_html

from services.transcript_service import TranscriptService
from services.semester_grading_service import SemesterGradingService


def create_student_transcript_blueprint():
    """Create and return the student transcript blueprint."""
    
    transcript_bp = Blueprint('student_transcript', __name__, url_prefix='/student/transcript')
    
    @transcript_bp.route('/current')
    @login_required
    def current_semester():
        """
        View current semester transcript.
        Shows the most recently released semester results.
        """
        if not current_user.is_student:
            abort(403)
        
        # Get transcript for current/latest released semester
        transcript = TranscriptService.get_current_semester_transcript(current_user.id)
        
        if not transcript:
            return render_template('student/transcript_unified.html', transcript=None, mode='current')

        return render_template('student/transcript_unified.html', transcript=transcript, mode='current')
    
    @transcript_bp.route('/semester/<path:academic_year>/<semester>')
    @login_required
    def semester_specific(academic_year, semester):
        """
        View transcript for a specific semester.
        
        URL: /student/transcript/semester/2024%2F2025/1
        """
        if not current_user.is_student:
            abort(403)
        
        # URL decode academic_year if needed
        from urllib.parse import unquote
        academic_year = unquote(academic_year)
        
        transcript = TranscriptService.generate_semester_transcript(
            current_user.id, academic_year, semester
        )
        
        if not transcript:
            flash("Transcript not found for this semester.", "warning")
            return redirect(url_for('student_transcript.current_semester'))

        if not transcript['is_released']:
            flash("Results for this semester have not been released yet.", "info")

        return render_template('student/transcript_unified.html', transcript=transcript, mode='semester')
    
    @transcript_bp.route('/full')
    @login_required
    def full_transcript():
        """
        View complete academic transcript across all semesters.
        """
        if not current_user.is_student:
            abort(403)
        
        transcript = TranscriptService.generate_full_transcript(current_user.id)
        
        if not transcript or not transcript['semesters_summary']:
            return render_template('student/transcript_unified.html', transcript=None, mode='full')

        return render_template('student/transcript_unified.html', transcript=transcript, mode='full')
    
    @transcript_bp.route('/download/pdf/semester/<path:academic_year>/<semester>')
    @login_required
    def download_semester_pdf(academic_year, semester):
        """
        Download semester transcript as PNG image.
        """
        if not current_user.is_student:
            abort(403)
        
        from urllib.parse import unquote
        academic_year = unquote(academic_year)
        
        transcript = TranscriptService.generate_semester_transcript(
            current_user.id, academic_year, semester
        )
        
        if not transcript:
            flash("Transcript not found.", "warning")
            return redirect(url_for('student_transcript.current_semester'))
        
        # Generate HTML
        html_content = TranscriptService.generate_semester_transcript_html(transcript)
        
        # Convert HTML to image
        try:
            img_data = generate_image_from_html(html_content, format="png", width=1000)
            
            filename = f"Transcript_{academic_year.replace('/', '-')}_Sem{semester}.png"
            
            response = make_response(img_data.getvalue())
            response.headers['Content-Type'] = 'image/png'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as e:
            flash(f"Error generating image: {str(e)}", "danger")
            return redirect(url_for('student_transcript.semester_specific', 
                                  academic_year=academic_year, semester=semester))
    
    @transcript_bp.route('/download/pdf/full')
    @login_required
    def download_full_pdf():
        """
        Download full transcript as PNG image.
        """
        if not current_user.is_student:
            abort(403)
        
        transcript = TranscriptService.generate_full_transcript(current_user.id)
        
        if not transcript:
            flash("Transcript not found.", "warning")
            return redirect(url_for('student_transcript.current_semester'))
        
        # Generate HTML
        html_content = TranscriptService.generate_full_transcript_html(transcript)
        
        # Convert HTML to image
        try:
            img_data = generate_image_from_html(html_content, format="png", width=1000)
            
            student_name = current_user.full_name.replace(' ', '_')
            filename = f"Full_Transcript_{student_name}.png"
            
            response = make_response(img_data.getvalue())
            response.headers['Content-Type'] = 'image/png'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as e:
            flash(f"Error generating image: {str(e)}", "danger")
            return redirect(url_for('student_transcript.full_transcript'))
    
    @transcript_bp.route('/api/semester/<path:academic_year>/<semester>')
    @login_required
    def api_semester(academic_year, semester):
        """
        API endpoint to get semester transcript as JSON.
        Useful for AJAX requests.
        """
        if not current_user.is_student:
            abort(403)
        
        from urllib.parse import unquote
        academic_year = unquote(academic_year)
        
        transcript = TranscriptService.generate_semester_transcript(
            current_user.id, academic_year, semester
        )
        
        if not transcript:
            return jsonify({'error': 'Transcript not found'}), 404
        
        # Serialize transcript to JSON-friendly format
        return jsonify({
            'student_id': transcript['student_id'],
            'student_name': transcript['student_name'],
            'academic_year': transcript['academic_year'],
            'semester': transcript['semester'],
            'is_released': transcript['is_released'],
            'gpa': transcript['semester_gpa'],
            'weighted_gpa': transcript['semester_weighted_gpa'],
            'total_credits': transcript['total_credit_hours'],
            'courses': [
                {
                    'code': c['course_code'],
                    'name': c['course_name'],
                    'credits': c['credit_hours'],
                    'score': c['final_score'],
                    'grade': c['grade_letter']
                }
                for c in transcript['courses']
            ]
        })
    
    @transcript_bp.route('/api/full')
    @login_required
    def api_full():
        """
        API endpoint to get full transcript as JSON.
        """
        if not current_user.is_student:
            abort(403)
        
        transcript = TranscriptService.generate_full_transcript(current_user.id)
        
        if not transcript:
            return jsonify({'error': 'Transcript not found'}), 404
        
        # Serialize to JSON
        semesters = []
        for key, semester_data in transcript['all_semesters'].items():
            semesters.append({
                'academic_year': semester_data['academic_year'],
                'semester': semester_data['semester'],
                'gpa': semester_data['gpa'],
                'courses': [
                    {
                        'code': c['course_code'],
                        'name': c['course_name'],
                        'credits': c['credit_hours'],
                        'score': c['final_score'],
                        'grade': c['grade_letter']
                    }
                    for c in semester_data['courses']
                ]
            })
        
        return jsonify({
            'student_id': transcript['student_id'],
            'student_name': transcript['student_name'],
            'cumulative_gpa': transcript['cumulative_gpa'],
            'weighted_gpa': transcript['cumulative_weighted_gpa'],
            'total_credits_attempted': transcript['total_credit_hours_attempted'],
            'total_credits_earned': transcript['total_credit_hours_earned'],
            'semesters': semesters
        })
    
    return transcript_bp
