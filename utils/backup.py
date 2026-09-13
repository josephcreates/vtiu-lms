# =====================================================================
# BACKUP UTILITIES (Updated for Tertiary)
# =====================================================================

# utils/backup.py
import csv
import os
from datetime import datetime
from models import StudentProfile, User, Quiz, ExamSubmission

def generate_quiz_csv_backup(quiz_data, questions_data, backup_dir='backups'):
    """Backup quiz questions and metadata"""
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    csv_filename = f"quiz_backup_{quiz_data['title'].replace(' ', '_')}_{timestamp}.csv"
    csv_path = os.path.join(backup_dir, csv_filename)

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # Write metadata
        writer.writerow(['Title', 'Course', 'Programme', 'Level', 'Start', 'End', 'Duration', 'Attempts', 'Content File'])
        writer.writerow([
            quiz_data['title'],
            quiz_data.get('course_name', 'N/A'),
            quiz_data.get('programme_name', 'N/A'),
            quiz_data.get('programme_level', 'N/A'),
            quiz_data.get('start_datetime', ''),
            quiz_data.get('end_datetime', ''),
            quiz_data.get('duration_minutes', ''),
            quiz_data.get('content_file', '')
        ])
        writer.writerow([])  # Blank line
        writer.writerow(['Question', 'Option Text', 'Is Correct'])

        # Write each question and its options
        for q in questions_data:
            for opt in q.get('options', []):
                writer.writerow([q.get('text', ''), opt.get('text', ''), 'Yes' if opt.get('is_correct') else 'No'])

    return csv_path


def backup_students_to_csv(backup_dir='backups', programme=None, level=None):
    """
    Backup student data to CSV (tertiary version).
    Can filter by programme/level if provided.
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    
    # Build filename
    if programme and level:
        filename = f'student_backup_{programme}_Level{level}_{timestamp}.csv'
    else:
        filename = f'student_backup_{timestamp}.csv'
    
    path = os.path.join(backup_dir, filename)

    # Build query
    query = StudentProfile.query
    if programme and level:
        query = query.filter(
            StudentProfile.current_programme == programme,
            StudentProfile.programme_level == int(level)
        )
    
    students = query.all()

    with open(path, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # TERTIARY HEADERS
        writer.writerow([
            'User ID', 'Full Name', 'Email', 'Index Number', 'Programme', 'Level',
            'Study Format', 'Gender', 'Date of Birth', 'Admission Date', 'Academic Status'
        ])

        for s in students:
            writer.writerow([
                s.user_id,
                s.user.full_name if hasattr(s, 'user') else '',
                s.user.email if hasattr(s, 'user') else '',
                s.index_number or '',
                s.current_programme or '',
                s.programme_level or '',
                s.study_format or 'Regular',
                s.gender or '',
                s.dob.strftime('%Y-%m-%d') if s.dob else '',
                s.admission_date.strftime('%Y-%m-%d') if s.admission_date else '',
                s.academic_status or 'Active',
            ])

    return filename


def backup_exam_results_to_csv(backup_dir='backups', programme=None, level=None):
    """
    Backup exam results to CSV (tertiary version).
    Can filter by programme/level if provided.
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    
    if programme and level:
        filename = f'exam_results_{programme}_Level{level}_{timestamp}.csv'
    else:
        filename = f'exam_results_{timestamp}.csv'
    
    path = os.path.join(backup_dir, filename)

    # Build query
    query = ExamSubmission.query.join(User, ExamSubmission.student_id == User.id) \
                               .join(StudentProfile, StudentProfile.user_id == User.user_id)
    
    if programme and level:
        query = query.filter(
            StudentProfile.current_programme == programme,
            StudentProfile.programme_level == int(level)
        )
    
    submissions = query.all()

    with open(path, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'Student ID', 'Index Number', 'Programme', 'Level',
            'Exam Title', 'Score', 'Max Score', 'Submitted At'
        ])

        for sub in submissions:
            user = sub.student if hasattr(sub, 'student') else User.query.get(sub.student_id)
            profile = user.student_profile if user and hasattr(user, 'student_profile') else None
            exam = sub.exam if hasattr(sub, 'exam') else None
            
            writer.writerow([
                user.user_id if user else '',
                profile.index_number if profile else '',
                profile.current_programme if profile else '',
                profile.programme_level if profile else '',
                exam.title if exam else '',
                sub.score or '',
                exam.max_score if exam else '',
                sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if sub.submitted_at else '',
            ])

    return filename


def backup_quiz_submissions_to_csv(backup_dir='backups', programme=None, level=None):
    """
    Backup quiz submissions to CSV (tertiary version).
    Can filter by programme/level if provided.
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    
    if programme and level:
        filename = f'quiz_submissions_{programme}_Level{level}_{timestamp}.csv'
    else:
        filename = f'quiz_submissions_{timestamp}.csv'
    
    path = os.path.join(backup_dir, filename)

    # Import here to avoid circular imports
    from models import StudentQuizSubmission
    
    query = StudentQuizSubmission.query.join(User, StudentQuizSubmission.student_id == User.id) \
                                       .join(StudentProfile, StudentProfile.user_id == User.user_id)
    
    if programme and level:
        query = query.filter(
            StudentProfile.current_programme == programme,
            StudentProfile.programme_level == int(level)
        )
    
    submissions = query.all()

    with open(path, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'Student ID', 'Index Number', 'Programme', 'Level',
            'Quiz Title', 'Score', 'Max Score', 'Submitted At'
        ])

        for sub in submissions:
            user = User.query.get(sub.student_id)
            profile = user.student_profile if user and hasattr(user, 'student_profile') else None
            quiz = sub.quiz if hasattr(sub, 'quiz') else None
            
            writer.writerow([
                user.user_id if user else '',
                profile.index_number if profile else '',
                profile.current_programme if profile else '',
                profile.programme_level if profile else '',
                quiz.title if quiz else '',
                sub.score or '',
                quiz.max_score if quiz else '',
                sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if sub.submitted_at else '',
            ])

    return filename