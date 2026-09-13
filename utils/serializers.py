# utils/serializers.py

def serialize_admin(admin):
    """Serialize an Admin object to a dictionary."""
    return {
        'id': admin.id,
        'username': admin.username,
        'admin_id': admin.admin_id
    }


def serialize_user(user):
    """Serialize a User object to a dictionary."""
    return {
        'user_id': user.user_id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role
    }

def serialize_student(student):
    """Serialize a StudentProfile object to a dictionary (tertiary-style)."""
    return {
        'user_id': student.user_id,
        'current_programme': getattr(student, 'current_programme', None),
        'programme_level': getattr(student, 'programme_level', None),
        'guardian_name': getattr(student, 'guardian_name', None),
        'guardian_phone': getattr(student, 'guardian_phone', None),
        'guardian_email': getattr(student, 'guardian_email', None),
        'guardian_relation': getattr(student, 'guardian_relation', None),
        'guardian_address': getattr(student, 'guardian_address', None)
    }


def serialize_quiz(quiz):
    """Serialize a Quiz object to a dictionary."""
    return {
        'id': quiz.id,
        'title': quiz.title,
        'assigned_class': quiz.assigned_class,
        'date': quiz.date.strftime('%Y-%m-%d') if quiz.date else None,
        'duration_minutes': quiz.duration_minutes
    }


def serialize_question(question):
    """Serialize a Question object to a dictionary."""
    return {
        'id': question.id,
        'quiz_id': question.quiz_id,
        'question_text': question.question_text,
        'marks': question.marks
    }


def serialize_option(option):
    """Serialize an Option object to a dictionary."""
    return {
        'id': option.id,
        'question_id': option.question_id,
        'option_text': option.option_text,
        'is_correct': option.is_correct
    }


def serialize_submission(submission):
    """Serialize a Submission object to a dictionary."""
    return {
        "id": submission.id,
        "student_id": submission.student_id,
        "student_username": submission.student.username if submission.student else "N/A",
        "quiz_title": submission.quiz.title if submission.quiz else "N/A",
        "score": submission.score,
        "submitted_at": submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if submission.submitted_at else None
    }


def serialize_message(message):
    """Serialize a Message object to a dictionary."""
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "sender_id": message.sender_id,
        "sender_role": message.sender_role,
        "sender_name": message.sender_name,  # resolve from role if needed
    }
