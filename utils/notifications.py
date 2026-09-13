# utils/notifications.py
from datetime import datetime
import json
from models import db, Notification, NotificationRecipient, User, StudentProfile
from flask_login import current_user

def create_assignment_notification(assignment):
    """Create notification for new assignment (tertiary: by programme/level)"""
    due_str = assignment.due_date.strftime('%d %B %Y, %I:%M %p') if assignment.due_date else 'No due date'

    notice = Notification(
        type='assignment',
        title=f"New Assignment: {assignment.title}",
        message=(
            f"A new assignment has been posted for {assignment.course_name}.\n\n"
            f"Due Date: {due_str}\n\n"
            f"Please check the Assignments section."
        ),
        created_at=datetime.utcnow(),
        related_type='assignment',
        related_id=assignment.id,
        sender_id=getattr(current_user, 'user_id', None) or getattr(current_user, 'admin_id', None)
    )

    db.session.add(notice)
    db.session.flush()

    # TERTIARY: Find all students in the programme/level
    students = User.query.join(StudentProfile).filter(
        StudentProfile.current_programme == assignment.programme_name,
        StudentProfile.programme_level == int(assignment.programme_level)
    ).all()

    recipients = [
        NotificationRecipient(notification_id=notice.id, user_id=s.user_id)
        for s in students if s.user_id
    ]
    if recipients:
        db.session.add_all(recipients)

    db.session.commit()
    return notice

def create_fee_notification(fee_group, sender=None):
    """Create notification for new fee assignment (tertiary: by programme/level)"""
    if sender is None:
        sender = current_user

    sender_id = getattr(sender, 'user_id', None) or getattr(sender, 'admin_id', None)
    sender_type = 'admin' if getattr(sender, 'is_admin', False) else 'user'

    # Build message text
    try:
        items = json.loads(fee_group.items) if isinstance(fee_group.items, str) else fee_group.items
    except Exception:
        items = []

    items_text = "\n".join([f"• {i.get('description', '')}: {i.get('amount', 0)} GHS" for i in items])
    message = (
        f"New fee assigned for {fee_group.programme_name} - Level {fee_group.programme_level}\n"
        f"Year: {fee_group.academic_year}, Semester: {fee_group.semester}\n"
        f"Total: {fee_group.amount} GHS\n\nBreakdown:\n{items_text}"
    )

    notification = Notification(
        type='fee',
        title=f"Fee Assigned: {fee_group.description}",
        message=message,
        sender_id=sender_id,
        sender_type=sender_type,
        related_type='fee',
        related_id=fee_group.id,
        created_at=datetime.utcnow()
    )
    db.session.add(notification)
    db.session.flush()

    # TERTIARY: Get all students in the programme/level
    students = User.query.join(StudentProfile).filter(
        StudentProfile.current_programme == fee_group.programme_name,
        StudentProfile.programme_level == int(fee_group.programme_level)
    ).all()

    if not students:
        db.session.rollback()
        raise ValueError("No student recipients found!")

    recipients = [
        NotificationRecipient(notification_id=notification.id, user_id=student.user_id, is_read=False)
        for student in students
    ]
    db.session.add_all(recipients)
    db.session.commit()

    return notification

def create_missed_call_notification(caller_name, target_user_id, conversation_id):
    """Create notification for missed call"""
    notice = Notification(
        type='call',
        title="Missed Call",
        message=f"You missed a call from {caller_name}.",
        created_at=datetime.utcnow(),
        related_type='conversation',
        related_id=conversation_id,
        sender_id=getattr(current_user, 'user_id', None) or getattr(current_user, 'admin_id', None)
    )

    db.session.add(notice)
    db.session.flush()

    recipient = NotificationRecipient(notification_id=notice.id, user_id=target_user_id)
    db.session.add(recipient)

    db.session.commit()
    return notice