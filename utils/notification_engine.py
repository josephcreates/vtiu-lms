# utils/notification_engine.py
"""
Comprehensive Notification Engine for LMS
Handles all notification types, preferences, channels, and delivery
"""

from datetime import datetime
import json
from models import (
    db, Notification, NotificationRecipient, User, StudentProfile, TeacherProfile,
    Admin, Course, Quiz, Assignment, Exam, StudentCourseGrade, AttendanceRecord
)
from flask_login import current_user
from utils.email import send_email
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# NOTIFICATION TYPES & EVENTS
# =============================================================================

NOTIFICATION_TYPES = {
    # Academic Events
    'quiz_created': {'label': 'Quiz Created', 'icon': 'quiz', 'color': '#0d6efd'},
    'quiz_started': {'label': 'Quiz Started', 'icon': 'play', 'color': '#17a2b8'},
    'quiz_reminder': {'label': 'Quiz Reminder', 'icon': 'bell', 'color': '#ffc107'},
    'quiz_ended': {'label': 'Quiz Ended', 'icon': 'stop', 'color': '#dc3545'},
    'quiz_result': {'label': 'Quiz Result Released', 'icon': 'chart', 'color': '#28a745'},
    
    'assignment_created': {'label': 'Assignment Posted', 'icon': 'file-alt', 'color': '#0d6efd'},
    'assignment_reminder': {'label': 'Assignment Due Soon', 'icon': 'bell', 'color': '#ffc107'},
    'assignment_overdue': {'label': 'Assignment Overdue', 'icon': 'exclamation', 'color': '#dc3545'},
    'assignment_graded': {'label': 'Assignment Graded', 'icon': 'check', 'color': '#28a745'},
    
    'exam_scheduled': {'label': 'Exam Scheduled', 'icon': 'calendar', 'color': '#0d6efd'},
    'exam_reminder': {'label': 'Exam Reminder', 'icon': 'bell', 'color': '#ffc107'},
    'exam_result': {'label': 'Exam Result Released', 'icon': 'chart', 'color': '#28a745'},
    
    'material_posted': {'label': 'Course Material Posted', 'icon': 'book', 'color': '#0d6efd'},
    'grade_released': {'label': 'Grade Released', 'icon': 'star', 'color': '#28a745'},
    'course_registration': {'label': 'Course Registration', 'icon': 'registered', 'color': '#0d6efd'},
    'course_deregistration': {'label': 'Course Deregistered', 'icon': 'times', 'color': '#dc3545'},
    
    # Administrative Events
    'fee_assigned': {'label': 'Fee Assigned', 'icon': 'money-bill', 'color': '#0d6efd'},
    'fee_payment_reminder': {'label': 'Fee Payment Due', 'icon': 'bell', 'color': '#ffc107'},
    'fee_overdue': {'label': 'Fee Payment Overdue', 'icon': 'exclamation', 'color': '#dc3545'},
    'fee_payment_confirmed': {'label': 'Payment Confirmed', 'icon': 'check', 'color': '#28a745'},
    
    'attendance_marked': {'label': 'Attendance Recorded', 'icon': 'clipboard-check', 'color': '#28a745'},
    'attendance_warning': {'label': 'Low Attendance Warning', 'icon': 'exclamation', 'color': '#dc3545'},
    
    # User Account Events
    'account_created': {'label': 'Account Created', 'icon': 'user', 'color': '#28a745'},
    'password_reset': {'label': 'Password Reset', 'icon': 'lock', 'color': '#0d6efd'},
    'profile_updated': {'label': 'Profile Updated', 'icon': 'user-edit', 'color': '#17a2b8'},
    
    # Communication
    'message_received': {'label': 'New Message', 'icon': 'envelope', 'color': '#0d6efd'},
    'announcement': {'label': 'Announcement', 'icon': 'bullhorn', 'color': '#0d6efd'},
    'event_reminder': {'label': 'Event Reminder', 'icon': 'calendar-alt', 'color': '#ffc107'},
    
    # System Events
    'promotion': {'label': 'Promotion Eligible', 'icon': 'arrow-up', 'color': '#28a745'},
    'deferment': {'label': 'Deferment Approved', 'icon': 'pause', 'color': '#17a2b8'},
}

# =============================================================================
# NOTIFICATION ENGINE - CORE FUNCTIONS
# =============================================================================

def create_notification(
    notification_type: str,
    title: str,
    message: str,
    recipients: list,
    sender=None,
    related_type=None,
    related_id=None,
    send_email_copy=False,
    priority='normal'
):
    """
    Create a notification and send to recipients.
    
    Args:
        notification_type: Type from NOTIFICATION_TYPES
        title: Notification title
        message: Full message text
        recipients: List of User objects
        sender: User/Admin object creating notification
        related_type: Related entity type (quiz, assignment, etc.)
        related_id: Related entity ID
        send_email_copy: Send email copy to recipients
        priority: 'low', 'normal', or 'high'
    
    Returns:
        Notification object created
    """
    try:
        sender_id = None
        sender_type = 'system'
        
        if sender:
            sender_id = getattr(sender, 'user_id', None) or getattr(sender, 'admin_id', None)
            sender_type = 'admin' if hasattr(sender, 'admin_id') else 'user'
        elif current_user.is_authenticated:
            sender_id = getattr(current_user, 'user_id', None) or getattr(current_user, 'admin_id', None)
            sender_type = 'admin' if hasattr(current_user, 'admin_id') else 'user'
        
        notification = Notification(
            type=notification_type,
            title=title,
            message=message,
            sender_id=sender_id,
            sender_type=sender_type,
            related_type=related_type,
            related_id=related_id,
            priority=priority,
            created_at=datetime.utcnow()
        )
        
        db.session.add(notification)
        db.session.flush()
        
        # Add recipients
        if recipients:
            recipient_objs = [
                NotificationRecipient(notification_id=notification.id, user_id=r.user_id)
                for r in recipients if r and hasattr(r, 'user_id')
            ]
            if recipient_objs:
                db.session.add_all(recipient_objs)
        
        db.session.commit()
        
        # Send email copies if requested
        if send_email_copy and recipients:
            send_notification_email(notification, recipients)
        
        return notification
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        db.session.rollback()
        return None

def send_notification_email(notification, recipients):
    """Send email copies of notification to recipients"""
    try:
        for recipient in recipients:
            if not recipient.email:
                continue
            
            email_body = f"""
<h3>{notification.title}</h3>
<p>{notification.message.replace(chr(10), '<br>')}</p>
<p>
    <a href="{_get_notification_link(notification)}" class="btn btn-primary" style="padding: 10px 20px; background: #0d6efd; color: white; text-decoration: none; border-radius: 5px;">
        View Details
    </a>
</p>
<hr>
<p><small>This is an automated notification from LMS. You can manage your notification preferences in your account settings.</small></p>
            """
            
            send_email(
                to_email=recipient.email,
                subject=f"[LMS] {notification.title}",
                html_body=email_body
            )
    except Exception as e:
        logger.warning(f"Failed to send notification emails: {e}")

def _get_notification_link(notification):
    """Generate link to notification detail/related item"""
    if notification.related_type == 'quiz' and notification.related_id:
        return f"/vclass/quiz-instructions/{notification.related_id}"
    elif notification.related_type == 'assignment' and notification.related_id:
        return f"/vclass/view-assignment/{notification.related_id}"
    elif notification.related_type == 'exam' and notification.related_id:
        return f"/vclass/exam/{notification.related_id}"
    return "/student/notifications"

# =============================================================================
# QUIZ NOTIFICATIONS
# =============================================================================

def notify_quiz_created(quiz, send_email=True):
    """Notify students when quiz is created"""
    students = _get_students_by_programme_level(
        quiz.programme_name,
        quiz.programme_level
    )
    
    if not students:
        return None
    
    message = f"""
New quiz has been created: {quiz.title}

Course: {quiz.course_name or 'General'}
Start: {quiz.start_datetime.strftime('%d %b %Y, %I:%M %p')}
End: {quiz.end_datetime.strftime('%d %b %Y, %I:%M %p')}
Duration: {quiz.duration_minutes} minutes
Attempts Allowed: {quiz.attempts_allowed}

Please review the quiz details and prepare accordingly.
    """
    
    return create_notification(
        notification_type='quiz_created',
        title=f"New Quiz: {quiz.title}",
        message=message,
        recipients=students,
        related_type='quiz',
        related_id=quiz.id,
        send_email_copy=send_email,
        priority='high'
    )

def notify_quiz_reminder(quiz, hours_before=1, send_email=True):
    """Remind students about upcoming quiz"""
    now = datetime.utcnow()
    time_until = (quiz.start_datetime - now).total_seconds() / 3600
    
    if not (hours_before - 0.5 <= time_until <= hours_before + 0.5):
        return None
    
    students = _get_students_by_programme_level(
        quiz.programme_name,
        quiz.programme_level
    )
    
    message = f"""
Reminder: Quiz starting soon!

Quiz: {quiz.title}
Starts in: {hours_before} hour(s)
Start Time: {quiz.start_datetime.strftime('%d %b %Y, %I:%M %p')}

Click the link below to access the quiz.
    """
    
    return create_notification(
        notification_type='quiz_reminder',
        title=f"Quiz Reminder: {quiz.title}",
        message=message,
        recipients=students,
        related_type='quiz',
        related_id=quiz.id,
        send_email_copy=send_email,
        priority='high'
    )

def notify_quiz_result_released(quiz, send_email=True):
    """Notify students when quiz results are released"""
    # Get students who submitted the quiz
    from models import StudentQuizSubmission
    submissions = StudentQuizSubmission.query.filter_by(quiz_id=quiz.id).all()
    student_ids = [s.student_id for s in submissions]
    students = User.query.filter(User.user_id.in_(student_ids)).all() if student_ids else []
    
    message = f"""
Your quiz results are now available!

Quiz: {quiz.title}

Click the link below to view your score and feedback.
    """
    
    return create_notification(
        notification_type='quiz_result',
        title=f"Results Released: {quiz.title}",
        message=message,
        recipients=students,
        related_type='quiz',
        related_id=quiz.id,
        send_email_copy=send_email,
        priority='normal'
    )

# =============================================================================
# ASSIGNMENT NOTIFICATIONS
# =============================================================================

def notify_assignment_created(assignment, send_email=True):
    """Notify students when assignment is posted"""
    students = _get_students_by_programme_level(
        assignment.programme_name,
        assignment.programme_level
    )
    
    if not students:
        return None
    
    due_str = assignment.due_date.strftime('%d %b %Y, %I:%M %p') if assignment.due_date else 'TBA'
    
    message = f"""
New assignment has been posted: {assignment.title}

Course: {assignment.course_name}
Due Date: {due_str}

Description:
{assignment.description or 'N/A'}

Instructions:
{assignment.instructions or 'See assignment details for full instructions'}

Click the link to view the full assignment details.
    """
    
    return create_notification(
        notification_type='assignment_created',
        title=f"New Assignment: {assignment.title}",
        message=message,
        recipients=students,
        related_type='assignment',
        related_id=assignment.id,
        send_email_copy=send_email,
        priority='high'
    )

def notify_assignment_reminder(assignment, days_before=3, send_email=True):
    """Remind students about upcoming assignment due date"""
    now = datetime.utcnow()
    time_until = (assignment.due_date - now).total_seconds() / 86400
    
    if not (days_before - 0.5 <= time_until <= days_before + 0.5):
        return None
    
    students = _get_students_by_programme_level(
        assignment.programme_name,
        assignment.programme_level
    )
    
    due_str = assignment.due_date.strftime('%d %b %Y, %I:%M %p')
    
    message = f"""
Assignment due soon!

Assignment: {assignment.title}
Due Date: {due_str}
Days Remaining: {int(time_until)}

Make sure to submit before the deadline.
    """
    
    return create_notification(
        notification_type='assignment_reminder',
        title=f"Reminder: {assignment.title} due in {int(time_until)} days",
        message=message,
        recipients=students,
        related_type='assignment',
        related_id=assignment.id,
        send_email_copy=send_email,
        priority='normal'
    )

def notify_assignment_graded(assignment_id, student_id, score, feedback, send_email=True):
    """Notify student when assignment is graded"""
    from models import AssignmentSubmission
    student = User.query.filter_by(user_id=student_id).first()
    
    if not student:
        return None
    
    message = f"""
Your assignment has been graded!

Assignment: {assignment_id}
Score: {score}

Feedback:
{feedback or 'See assignment details for feedback'}

Click the link to view your submission and detailed feedback.
    """
    
    return create_notification(
        notification_type='assignment_graded',
        title=f"Assignment Graded",
        message=message,
        recipients=[student],
        related_type='assignment',
        related_id=assignment_id,
        send_email_copy=send_email,
        priority='normal'
    )

# =============================================================================
# EXAM NOTIFICATIONS
# =============================================================================

def notify_exam_scheduled(exam, send_email=True):
    """Notify students when exam is scheduled"""
    students = _get_students_by_programme_level(
        exam.programme_name,
        exam.programme_level
    )
    
    if not students:
        return None
    
    message = f"""
Exam scheduled for you!

Exam: {exam.title}
Course: {exam.course_id}
Date & Time: {exam.start_datetime.strftime('%d %b %Y, %I:%M %p')}
Duration: {exam.duration_minutes} minutes
Location: Check exam timetable for details

Please prepare accordingly and arrive on time.
    """
    
    return create_notification(
        notification_type='exam_scheduled',
        title=f"Exam Scheduled: {exam.title}",
        message=message,
        recipients=students,
        related_type='exam',
        related_id=exam.id,
        send_email_copy=send_email,
        priority='high'
    )

def notify_exam_reminder(exam, hours_before=24, send_email=True):
    """Remind students about upcoming exam"""
    now = datetime.utcnow()
    time_until = (exam.start_datetime - now).total_seconds() / 3600
    
    if not (hours_before - 1 <= time_until <= hours_before + 1):
        return None
    
    students = _get_students_by_programme_level(
        exam.programme_name,
        exam.programme_level
    )
    
    message = f"""
Exam reminder!

Exam: {exam.title}
Starts: {exam.start_datetime.strftime('%d %b %Y, %I:%M %p')}
Time Until: {int(time_until)} hours

Make sure you're prepared and have reviewed all course materials.
    """
    
    return create_notification(
        notification_type='exam_reminder',
        title=f"Exam Reminder: {exam.title}",
        message=message,
        recipients=students,
        related_type='exam',
        related_id=exam.id,
        send_email_copy=send_email,
        priority='high'
    )

# =============================================================================
# GRADE NOTIFICATIONS
# =============================================================================

def notify_grade_released(course_id, programme, level, send_email=True):
    """Notify students when course grades are released"""
    students = _get_students_by_programme_level(programme, level)
    
    course = Course.query.get(course_id)
    course_name = course.name if course else f"Course {course_id}"
    
    message = f"""
Your grade for {course_name} has been released!

Click the link to view your grade, score breakdown, and any feedback.
    """
    
    return create_notification(
        notification_type='grade_released',
        title=f"Grade Released: {course_name}",
        message=message,
        recipients=students,
        related_type='course',
        related_id=course_id,
        send_email_copy=send_email,
        priority='high'
    )

# =============================================================================
# FEE NOTIFICATIONS
# =============================================================================

def notify_fee_assigned(fee_group, send_email=True):
    """Notify students when fee is assigned"""
    students = _get_students_by_programme_level(
        fee_group.programme_name,
        fee_group.programme_level
    )
    
    if not students:
        return None
    
    message = f"""
New fee assigned to your account!

Description: {fee_group.description}
Academic Year: {fee_group.academic_year}
Semester: {fee_group.semester}
Amount: {fee_group.amount} GHS

Payment is due within 14 days. You can pay through the student portal.
    """
    
    return create_notification(
        notification_type='fee_assigned',
        title=f"Fee Assigned: {fee_group.description}",
        message=message,
        recipients=students,
        related_type='fee',
        related_id=fee_group.id,
        send_email_copy=send_email,
        priority='high'
    )

def notify_fee_payment_reminder(days_overdue=7, send_email=True):
    """Remind students about outstanding fees"""
    from models import StudentFeeBalance
    from sqlalchemy import or_
    
    outstanding = StudentFeeBalance.query.filter(
        StudentFeeBalance.balance_due > 0
    ).all()
    
    notified_count = 0
    
    for balance in outstanding:
        student = User.query.filter_by(user_id=balance.student_id).first()
        if not student:
            continue
        
        message = f"""
Payment reminder: Outstanding balance on your student account

Amount Due: {balance.balance_due} GHS
Last Payment Date: {balance.last_payment_date or 'N/A'}

Please process payment at your earliest convenience to avoid suspension of services.
        """
        
        notif = create_notification(
            notification_type='fee_payment_reminder',
            title=f"Payment Reminder: {balance.balance_due} GHS Outstanding",
            message=message,
            recipients=[student],
            related_type='fee',
            related_id=balance.id,
            send_email_copy=send_email,
            priority='high'
        )
        
        if notif:
            notified_count += 1
    
    return notified_count

# =============================================================================
# ATTENDANCE NOTIFICATIONS
# =============================================================================

def notify_attendance_warning(student_id, attendance_percentage, send_email=True):
    """Warn student about low attendance"""
    student = User.query.filter_by(user_id=student_id).first()
    
    if not student:
        return None
    
    message = f"""
Attendance Warning

Your current attendance is {attendance_percentage}%.

According to academic regulations, you must maintain minimum attendance to remain eligible for course credit.

Please attend classes regularly to maintain good standing.
    """
    
    return create_notification(
        notification_type='attendance_warning',
        title=f"Attendance Warning: {attendance_percentage}%",
        message=message,
        recipients=[student],
        send_email_copy=send_email,
        priority='high'
    )

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_students_by_programme_level(programme, level):
    """Get all students in a programme/level"""
    try:
        students = User.query.join(
            StudentProfile,
            StudentProfile.user_id == User.user_id
        ).filter(
            StudentProfile.current_programme == programme,
            StudentProfile.programme_level == int(level)
        ).all()
        return students
    except Exception as e:
        logger.error(f"Error fetching students for {programme}/{level}: {e}")
        return []

def mark_notification_read(notification_id, user_id):
    """Mark a notification as read"""
    try:
        recipient = NotificationRecipient.query.filter_by(
            notification_id=notification_id,
            user_id=user_id
        ).first()
        
        if recipient:
            recipient.is_read = True
            recipient.read_at = datetime.utcnow()
            db.session.commit()
            return True
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
    
    return False

def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user"""
    try:
        NotificationRecipient.query.filter_by(
            user_id=user_id,
            is_read=False
        ).update({'is_read': True, 'read_at': datetime.utcnow()})
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error marking all notifications read: {e}")
    
    return False

def get_unread_notification_count(user_id):
    """Get count of unread notifications for a user"""
    try:
        return NotificationRecipient.query.filter_by(
            user_id=user_id,
            is_read=False
        ).count()
    except Exception as e:
        logger.error(f"Error getting notification count: {e}")
    
    return 0

def delete_notification(notification_id):
    """Delete a notification"""
    try:
        Notification.query.filter_by(id=notification_id).delete()
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
    
    return False
