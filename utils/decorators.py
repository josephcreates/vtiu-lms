from flask import redirect, url_for
from flask_login import current_user
from functools import wraps

def email_verified_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.email_verified:
            return redirect(url_for('admissions.verify_email'))
        return f(*args, **kwargs)
    return wrapper
