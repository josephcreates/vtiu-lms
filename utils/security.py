# utils/security.py
import random
from datetime import datetime, timedelta
from utils.extensions import db

def generate_email_verification(applicant):
    code = str(random.randint(100000, 999999))
    applicant.email_verification_code = code
    applicant.email_verification_expires = datetime.utcnow() + timedelta(minutes=15)
    db.session.commit()
    return code


def verify_email_code(applicant, submitted_code):
    if applicant.email_verified:
        return False, "Email already verified."

    if not applicant.email_verification_code:
        return False, "No verification code found."

    if applicant.email_verification_expires < datetime.utcnow():
        return False, "Verification code has expired."

    if applicant.email_verification_code != submitted_code:
        return False, "Invalid verification code."

    applicant.email_verified = True
    applicant.email_verification_code = None
    applicant.email_verification_expires = None
    db.session.commit()

    return True, "Email verified successfully."


def has_lms_access(study_format):
    """
    Check if user has LMS access based on study format.
    
    Args:
        study_format (str): 'Regular' or 'Online'
    
    Returns:
        bool: True if Online format, False if Regular format
    """
    return study_format == 'Online'


def get_study_format_features(study_format):
    """
    Get available features based on study format.
    
    Args:
        study_format (str): 'Regular' or 'Online'
    
    Returns:
        dict: Available features for the format
    """
    if study_format == 'Online':
        return {
            'lms_access': True,
            'quizzes': True,
            'assignments': True,
            'exams': True,
            'materials': True,
            'chat': True,
            'description': 'Full LMS access with all features'
        }
    elif study_format == 'Regular':
        return {
            'lms_access': False,
            'quizzes': False,
            'assignments': False,
            'exams': False,
            'materials': False,
            'chat': False,
            'description': 'Admissions process only, no LMS features'
        }
    else:
        return {
            'lms_access': False,
            'quizzes': False,
            'assignments': False,
            'exams': False,
            'materials': False,
            'chat': False,
            'description': 'Invalid study format'
        }
