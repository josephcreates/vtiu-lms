# utils/notification_routes.py
"""
Blueprint for notification management and preferences
Provides routes for viewing, marking read, and managing notification preferences
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Notification, NotificationRecipient, NotificationPreference
from utils.notification_engine import mark_notification_read, mark_all_notifications_read, get_unread_notification_count
from datetime import datetime
import json

notification_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

# =============================================================================
# MAIN NOTIFICATION ROUTES
# =============================================================================

@notification_bp.route('/')
@login_required
def list_notifications():
    """Display all notifications for current user (paginated)"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = NotificationRecipient.query.filter_by(
        user_id=current_user.user_id
    ).join(Notification).order_by(
        Notification.created_at.desc()
    )
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return render_template(
        'notifications/list.html',
        notifications=paginated.items,
        pagination=paginated,
        unread_count=get_unread_notification_count(current_user.user_id)
    )

@notification_bp.route('/unread')
@login_required
def list_unread():
    """Display only unread notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = NotificationRecipient.query.filter_by(
        user_id=current_user.user_id,
        is_read=False
    ).join(Notification).order_by(
        Notification.created_at.desc()
    )
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return render_template(
        'notifications/list.html',
        notifications=paginated.items,
        pagination=paginated,
        title='Unread Notifications',
        unread_count=get_unread_notification_count(current_user.user_id)
    )

@notification_bp.route('/<int:notification_id>')
@login_required
def view_notification(notification_id):
    """View a single notification"""
    recipient = NotificationRecipient.query.filter_by(
        notification_id=notification_id,
        user_id=current_user.user_id
    ).first_or_404()
    
    notification = recipient.notification
    
    # Mark as read
    if not recipient.is_read:
        mark_notification_read(notification_id, current_user.user_id)
    
    return render_template(
        'notifications/detail.html',
        notification=notification,
        recipient=recipient
    )

@notification_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark notification as read (AJAX)"""
    mark_notification_read(notification_id, current_user.user_id)
    return jsonify({'success': True})

@notification_bp.route('/read-all', methods=['POST'])
@login_required
def read_all():
    """Mark all notifications as read"""
    mark_all_notifications_read(current_user.user_id)
    return jsonify({'success': True})

@notification_bp.route('/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        recipient = NotificationRecipient.query.filter_by(
            notification_id=notification_id,
            user_id=current_user.user_id
        ).first_or_404()
        
        db.session.delete(recipient)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# =============================================================================
# NOTIFICATION PREFERENCES
# =============================================================================

@notification_bp.route('/preferences')
@login_required
def preferences():
    """Display notification preferences"""
    pref = NotificationPreference.query.filter_by(
        user_id=current_user.user_id
    ).first()
    
    if not pref:
        pref = NotificationPreference(user_id=current_user.user_id)
        db.session.add(pref)
        db.session.commit()
    
    # Parse enabled types
    try:
        enabled_types = json.loads(pref.enabled_types) if pref.enabled_types else {}
    except:
        enabled_types = {}
    
    return render_template(
        'notifications/preferences.html',
        preferences=pref,
        enabled_types=enabled_types
    )

@notification_bp.route('/preferences/update', methods=['POST'])
@login_required
def update_preferences():
    """Update notification preferences"""
    pref = NotificationPreference.query.filter_by(
        user_id=current_user.user_id
    ).first()
    
    if not pref:
        pref = NotificationPreference(user_id=current_user.user_id)
        db.session.add(pref)
        db.session.flush()
    
    try:
        # Channel preferences
        pref.email_enabled = request.form.get('email_enabled') == 'on'
        pref.in_app_enabled = request.form.get('in_app_enabled') == 'on'
        
        # Digest settings
        pref.digest_enabled = request.form.get('digest_enabled') == 'on'
        pref.digest_time = request.form.get('digest_time', '08:00')
        
        # Quiet hours
        pref.quiet_hours_enabled = request.form.get('quiet_hours_enabled') == 'on'
        pref.quiet_start = request.form.get('quiet_start', '22:00')
        pref.quiet_end = request.form.get('quiet_end', '08:00')
        
        # Notification type preferences
        enabled_types = {}
        for key in request.form:
            if key.startswith('type_'):
                notif_type = key.replace('type_', '')
                enabled_types[notif_type] = True
        
        pref.enabled_types = json.dumps(enabled_types)
        pref.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Notification preferences updated successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating preferences: {str(e)}', 'danger')
    
    return redirect(url_for('notifications.preferences'))

@notification_bp.route('/preferences/mute', methods=['POST'])
@login_required
def mute_notifications():
    """Mute all notifications for a specified period"""
    pref = NotificationPreference.query.filter_by(
        user_id=current_user.user_id
    ).first()
    
    if not pref:
        pref = NotificationPreference(user_id=current_user.user_id)
        db.session.add(pref)
        db.session.flush()
    
    hours = request.form.get('hours', 1, type=int)
    mute_until = datetime.utcnow() + timedelta(hours=hours)
    pref.muted_until = mute_until
    
    db.session.commit()
    
    flash(f'Notifications muted for {hours} hour(s).', 'info')
    return redirect(url_for('notifications.preferences'))

# =============================================================================
# API ENDPOINTS FOR REAL-TIME UPDATES
# =============================================================================

@notification_bp.route('/api/count')
@login_required
def api_unread_count():
    """Get unread notification count (for AJAX/real-time updates)"""
    count = get_unread_notification_count(current_user.user_id)
    return jsonify({'count': count})

@notification_bp.route('/api/recent')
@login_required
def api_recent_notifications():
    """Get recent unread notifications (for dropdown)"""
    limit = request.args.get('limit', 5, type=int)
    
    recipients = NotificationRecipient.query.filter_by(
        user_id=current_user.user_id,
        is_read=False
    ).join(Notification).order_by(
        Notification.created_at.desc()
    ).limit(limit).all()
    
    notifications = []
    for r in recipients:
        notifications.append({
            'id': r.notification.id,
            'type': r.notification.type,
            'title': r.notification.title,
            'message': r.notification.message[:100] + '...' if len(r.notification.message) > 100 else r.notification.message,
            'created_at': r.notification.created_at.isoformat(),
            'priority': r.notification.priority
        })
    
    return jsonify({'notifications': notifications, 'count': len(notifications)})

@notification_bp.route('/api/filter')
@login_required
def api_filter_notifications():
    """Filter notifications by type"""
    notif_type = request.args.get('type')
    limit = request.args.get('limit', 10, type=int)
    
    query = NotificationRecipient.query.filter_by(
        user_id=current_user.user_id
    ).join(Notification)
    
    if notif_type:
        query = query.filter(Notification.type == notif_type)
    
    recipients = query.order_by(
        Notification.created_at.desc()
    ).limit(limit).all()
    
    notifications = []
    for r in recipients:
        notifications.append({
            'id': r.notification.id,
            'type': r.notification.type,
            'title': r.notification.title,
            'message': r.notification.message[:100] + '...',
            'created_at': r.notification.created_at.isoformat(),
            'is_read': r.is_read,
            'priority': r.notification.priority
        })
    
    return jsonify({'notifications': notifications})

# =============================================================================
# STATS & ANALYTICS
# =============================================================================

@notification_bp.route('/stats')
@login_required
def notification_stats():
    """Display notification statistics and summary"""
    from datetime import datetime, timedelta
    
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Count by type
    type_counts = db.session.query(
        Notification.type,
        db.func.count(NotificationRecipient.id).label('count')
    ).join(NotificationRecipient).filter(
        NotificationRecipient.user_id == current_user.user_id
    ).group_by(Notification.type).all()
    
    # Unread count
    unread = get_unread_notification_count(current_user.user_id)
    
    # Today's notifications
    today_count = NotificationRecipient.query.filter_by(
        user_id=current_user.user_id
    ).join(Notification).filter(
        db.func.date(Notification.created_at) == today
    ).count()
    
    # This week
    week_count = NotificationRecipient.query.filter_by(
        user_id=current_user.user_id
    ).join(Notification).filter(
        Notification.created_at >= datetime.combine(week_ago, datetime.min.time())
    ).count()
    
    return render_template(
        'notifications/stats.html',
        type_counts=type_counts,
        unread_count=unread,
        today_count=today_count,
        week_count=week_count
    )

from datetime import timedelta
