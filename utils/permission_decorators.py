"""
PERMISSION DECORATORS AND UTILITIES
Role-based access control for admin routes
"""

from functools import wraps
from flask import abort, current_app
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


# ============================================================
# PERMISSION DECORATORS
# ============================================================

def require_admin():
    """
    Require user to be an admin (any role)
    Usage: @login_required @require_admin
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role != 'admin':
                logger.warning(f"Access denied to non-admin: {current_user.user_id}")
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(permission_name):
    """
    Require admin to have specific permission
    
    Usage:
        @login_required
        @require_permission('can_view_finances')
        def view_finances():
            pass
    
    Permissions:
    - can_view_finances
    - can_edit_finances
    - can_view_academics
    - can_edit_academics
    - can_view_admissions
    - can_edit_admissions
    - can_manage_users
    - can_view_reports
    - can_export_data
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check user is authenticated
            if not current_user.is_authenticated:
                abort(401)
            
            # Check user is admin
            if current_user.role != 'admin':
                logger.warning(f"Non-admin attempted access to {f.__name__}: {current_user.user_id}")
                abort(403)
            
            # Check permission
            from models import Admin
            admin = Admin.query.filter_by(user_id=current_user.user_id).first()
            
            if not admin:
                logger.error(f"Admin record not found for user: {current_user.user_id}")
                abort(403)
            
            # ✅ Superadmin has all permissions
            if admin.is_superadmin:
                return f(*args, **kwargs)
            
            has_permission = getattr(admin, permission_name, False)
            if not has_permission:
                logger.warning(
                    f"Permission denied for {current_user.user_id}: "
                    f"requires {permission_name}, has {has_permission}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_superadmin():
    """
    Require user to be superadmin
    Usage: @login_required @require_superadmin
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role != 'admin':
                abort(403)
            
            from models import Admin
            admin = Admin.query.filter_by(user_id=current_user.user_id).first()
            
            if not admin or not admin.is_superadmin:
                logger.warning(f"Superadmin access denied: {current_user.user_id}")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_any_permission(*permissions):
    """
    Require admin to have ANY of the specified permissions
    
    Usage:
        @login_required
        @require_any_permission('can_view_finances', 'can_view_reports')
        def view_dashboard():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if current_user.role != 'admin':
                abort(403)
            
            from models import Admin
            admin = Admin.query.filter_by(user_id=current_user.user_id).first()
            
            if not admin:
                abort(403)
            
            # ✅ Superadmin has all permissions
            if admin.is_superadmin:
                return f(*args, **kwargs)
            
            has_any = any(getattr(admin, perm, False) for perm in permissions)
            if not has_any:
                logger.warning(
                    f"Permission denied for {current_user.user_id}: "
                    f"requires any of {permissions}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_all_permissions(*permissions):
    """
    Require admin to have ALL of the specified permissions
    
    Usage:
        @login_required
        @require_all_permissions('can_view_finances', 'can_edit_finances')
        def approve_payment():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if current_user.role != 'admin':
                abort(403)
            
            from models import Admin
            admin = Admin.query.filter_by(user_id=current_user.user_id).first()
            
            if not admin:
                abort(403)
            
            # ✅ Superadmin has all permissions
            if admin.is_superadmin:
                return f(*args, **kwargs)
            
            has_all = all(getattr(admin, perm, False) for perm in permissions)
            if not has_all:
                logger.warning(
                    f"Permission denied for {current_user.user_id}: "
                    f"requires all of {permissions}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_current_admin():
    """Get the current admin object (if user is admin)"""
    if not current_user.is_authenticated or current_user.role != 'admin':
        return None
    
    from models import Admin
    return Admin.query.filter_by(user_id=current_user.user_id).first()


def current_admin_has_permission(permission_name):
    """Check if current admin has specific permission"""
    admin = get_current_admin()
    if not admin:
        return False
    return getattr(admin, permission_name, False)


def get_admin_permissions(user_id):
    """Get all permissions for a specific admin"""
    from models import Admin
    admin = Admin.query.filter_by(user_id=user_id).first()
    
    if not admin:
        return {}
    
    permissions = {
        'can_view_finances': admin.can_view_finances,
        'can_edit_finances': admin.can_edit_finances,
        'can_view_academics': admin.can_view_academics,
        'can_edit_academics': admin.can_edit_academics,
        'can_view_admissions': admin.can_view_admissions,
        'can_edit_admissions': admin.can_edit_admissions,
        'can_manage_users': admin.can_manage_users,
        'can_view_reports': admin.can_view_reports,
        'can_export_data': admin.can_export_data,
    }
    
    return permissions


def get_admin_accessible_sections(user_id):
    """Get list of sections an admin can access"""
    perms = get_admin_permissions(user_id)
    sections = []
    
    if perms.get('can_view_finances'):
        sections.append('finances')
    if perms.get('can_view_academics'):
        sections.append('academics')
    if perms.get('can_view_admissions'):
        sections.append('admissions')
    if perms.get('can_manage_users'):
        sections.append('users')
    if perms.get('can_view_reports'):
        sections.append('reports')
    
    return sections


def grant_permission(user_id, permission_name):
    """Grant a permission to an admin"""
    from models import Admin, db
    
    admin = Admin.query.filter_by(user_id=user_id).first()
    if not admin:
        logger.error(f"Admin not found: {user_id}")
        return False
    
    try:
        setattr(admin, permission_name, True)
        db.session.commit()
        logger.info(f"Granted {permission_name} to {user_id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error granting permission: {e}")
        return False


def revoke_permission(user_id, permission_name):
    """Revoke a permission from an admin"""
    from models import Admin, db
    
    admin = Admin.query.filter_by(user_id=user_id).first()
    if not admin:
        logger.error(f"Admin not found: {user_id}")
        return False
    
    try:
        setattr(admin, permission_name, False)
        db.session.commit()
        logger.info(f"Revoked {permission_name} from {user_id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error revoking permission: {e}")
        return False


def set_permissions_from_preset(user_id, preset_name):
    """
    Set permissions based on a preset role
    
    Presets: finance_admin, academic_admin, admissions_admin, superadmin
    """
    from models import Admin, db
    
    admin = Admin.query.filter_by(user_id=user_id).first()
    if not admin:
        logger.error(f"Admin not found: {user_id}")
        return False
    
    presets = {
        'finance_admin': {
            'can_view_finances': True,
            'can_edit_finances': True,
            'can_view_academics': False,
            'can_edit_academics': False,
            'can_view_admissions': False,
            'can_edit_admissions': False,
            'can_manage_users': False,
            'can_view_reports': True,
            'can_export_data': True,
        },
        'academic_admin': {
            'can_view_finances': False,
            'can_edit_finances': False,
            'can_view_academics': True,
            'can_edit_academics': True,
            'can_view_admissions': False,
            'can_edit_admissions': False,
            'can_manage_users': False,
            'can_view_reports': True,
            'can_export_data': True,
        },
        'admissions_admin': {
            'can_view_finances': False,
            'can_edit_finances': False,
            'can_view_academics': True,
            'can_edit_academics': False,
            'can_view_admissions': True,
            'can_edit_admissions': True,
            'can_manage_users': False,
            'can_view_reports': True,
            'can_export_data': True,
        },
        'superadmin': {
            'can_view_finances': True,
            'can_edit_finances': True,
            'can_view_academics': True,
            'can_edit_academics': True,
            'can_view_admissions': True,
            'can_edit_admissions': True,
            'can_manage_users': True,
            'can_view_reports': True,
            'can_export_data': True,
        }
    }
    
    if preset_name not in presets:
        logger.error(f"Unknown preset: {preset_name}")
        return False
    
    try:
        perms = presets[preset_name]
        for perm_name, value in perms.items():
            setattr(admin, perm_name, value)
        db.session.commit()
        logger.info(f"Applied preset '{preset_name}' to {user_id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error applying preset: {e}")
        return False


# ============================================================
# TEMPLATE FILTERS (for use in Jinja2)
# ============================================================

def register_permission_filters(app):
    """Register permission filters for templates"""
    
    @app.template_filter('has_permission')
    def has_permission_filter(user_id, permission_name):
        """Use in template: {% if user_id|has_permission('can_view_finances') %}"""
        from models import Admin
        admin = Admin.query.filter_by(user_id=user_id).first()
        if not admin:
            return False
        return getattr(admin, permission_name, False)
    
    @app.template_filter('admin_role_badge')
    def admin_role_badge_filter(role):
        """Use in template: {{ admin.role|admin_role_badge }}"""
        badges = {
            'finance_admin': '💰 Finance Admin',
            'academic_admin': '📚 Academic Admin',
            'admissions_admin': '👥 Admissions Admin',
            'superadmin': '⭐ Super Admin',
            'teacher': '👨‍🏫 Teacher'
        }
        return badges.get(role, role)


# ============================================================
# USAGE EXAMPLES IN ROUTES
# ============================================================

"""

# Example 1: Simple permission check
@admin_bp.route('/finances/payments')
@login_required
@require_permission('can_view_finances')
def view_payments():
    return render_template('admin/payments.html')


# Example 2: Edit requires both view and edit permissions
@admin_bp.route('/finances/approve/<int:txn_id>', methods=['POST'])
@login_required
@require_all_permissions('can_view_finances', 'can_edit_finances')
def approve_payment(txn_id):
    # Approve logic here
    return jsonify({'success': True})


# Example 3: Multiple permissions (any one)
@admin_bp.route('/reports')
@login_required
@require_any_permission('can_view_finances', 'can_view_academics', 'can_view_reports')
def view_reports():
    return render_template('admin/reports.html')


# Example 4: Using utility in route
@admin_bp.route('/dashboard')
@login_required
@require_admin()
def admin_dashboard():
    sections = get_admin_accessible_sections(current_user.user_id)
    return render_template('admin/dashboard.html', sections=sections)


# Example 5: Check permission inline
@admin_bp.route('/admin/settings')
@login_required
@require_superadmin()
def admin_settings():
    if not current_admin_has_permission('can_manage_users'):
        flash("You don't have permission to manage users", "danger")
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/settings.html')
"""