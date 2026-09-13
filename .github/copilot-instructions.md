# AI Coding Agent Instructions for LMS

## Project Overview
**My LMS** is a comprehensive educational management system built with Flask, SQLAlchemy, and modern frontend tech. It manages students, teachers, courses, exams, grading, finance, admissions, virtual classrooms, and notifications.

## Architecture at a Glance
```
app.py (Flask factory) 
  ├─→ models.py (SQLAlchemy ORM - 2000+ lines)
  ├─→ services/ (Business logic engines)
  │   ├─ grading_calculation_engine.py (PRIMARY for grades)
  │   ├─ semester_grading_service.py
  │   ├─ transcript_service.py
  │   └─ result_builder.py
  ├─→ *_routes.py (10+ blueprints - student, teacher, admin, exam, finance, etc.)
  ├─→ utils/ (30+ helper modules - auth, email, PDF, notifications)
  └─→ templates/ (Jinja2, Bootstrap 5, Chart.js for dashboards)
```

## Critical Architecture Patterns

### 1. **Multi-Role Authentication System**
- **Three parallel auth systems**: `User` (student/teacher), `Admin` (separate table), `StudentProfile`
- **Admin roles**: superadmin, finance_admin, academic_admin, admissions_admin
- **Access control**: Use decorators `@require_admin()`, `@require_permission('can_edit_finances')`
- **Key detail**: Admin.role is a DATABASE COLUMN, not @property—access as `admin.role`
- **Permission-based**: Check explicit permission flags (`can_view_finances`, `can_edit_academics`, etc.)

### 2. **Grading System - Complex Multi-Service Architecture**
The grading system has a specific calculation hierarchy (understanding this is CRITICAL):
```
GradingCalculationEngine (services/grading_calculation_engine.py)
  ├─→ Aggregates quiz, assignment, exam scores
  ├─→ Applies assessment scheme weights (quiz%, assignment%, exam%)
  ├─→ Calculates final numeric score
  └─→ Maps to GradingScale for letter grade

GradeService (services/grade_service.py)
  └─→ Simple lookup: percent → GradingScale object

SemesterGradingService / TranscriptService / ResultBuilder
  └─→ All delegate to GradingCalculationEngine for calculations
```
**When touching grades**: Always work through `GradingCalculationEngine.calculate_course_grade()` — DO NOT calculate grades directly in route handlers.

### 3. **Financial System - Permissions Required**
- Finance operations require `@require_permission('can_view_finances')` or `can_edit_finances`
- Models: `StudentFeeTransaction`, `StudentFeeBalance`, `ProgrammeFeeStructure`
- Routes: `finance_routes.py` has helpers like `get_daily_revenue()`, `get_department_breakdown()`
- **Pattern**: Finance admins can view/approve/manage fees; only superadmins can modify structures

### 4. **Blueprint-Based Routing**
Register new routes as blueprints in `app.py` (lines 160-172):
```python
from my_routes import create_my_blueprint
my_bp = create_my_blueprint()
app.register_blueprint(my_bp, url_prefix="/myprefix")
```
Blueprints: admin, teacher, student, auth, exam, vclass, chat, admissions, notification, grading, results, finance.

### 5. **Database Configuration - SQLite by Default, PostgreSQL in Production**
```python
# app.py, lines 44-45
if db_url:
    SQLALCHEMY_DATABASE_URI = db_url.replace("postgres://", "postgresql://")
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///instance/lms.db"
```
- Local dev: SQLite in `instance/lms.db`
- Railway production: PostgreSQL via environment variable
- Always test migration compatibility with both

### 6. **Email System - Flask-Mailman with Gmail**
- SMTP config in `config.py` (Gmail SMTP server)
- Setup: `MAIL_USERNAME` and `MAIL_PASSWORD` (app password, not account password)
- Send via: `utils/email.py` helpers (don't call mail directly in routes)
- Used for: admissions, password resets, notifications, transcripts

### 7. **File Upload Handling**
Separate folders in `config.py` and `app.py`:
```python
UPLOAD_FOLDER → /uploads/assignments (student work)
MATERIALS_FOLDER → /uploads/materials (course materials)
PAYMENT_PROOF_FOLDER → payment proofs
RECEIPT_FOLDER → generated receipts
PROFILE_PICS_FOLDER → student/admin avatars
```
Use `werkzeug.utils.secure_filename()` before saving; validate file types in routes.

### 8. **SocketIO for Real-Time Features**
- Initialized in `app.py` with async_mode: `eventlet` (production) or `threading` (dev)
- Used for: virtual classroom, chat, notifications
- Imported from `utils.extensions.socketio`
- Pattern: Emit events via `socketio.emit()` in route handlers

### 9. **PDF Generation - ReportLab + WeasyPrint**
- ReportLab for structured PDFs (ID cards, transcripts, certificates)
- WeasyPrint for HTML-to-PDF (complex layouts)
- GTK runtime required on Windows (patched in `app.py` lines 1-11)
- Helpers: `utils/id_card.py`, `utils/pdf_generator.py`, `utils/course_registration_pdf.py`

### 10. **Notification System - Multi-Channel**
- Models: `Notification`, `NotificationRecipient`, `NotificationTemplate`
- Routes: `utils/notification_routes.py`, `utils/notification_engine.py`
- Channels: In-app, email, SMS (extensible)
- Pattern: Create notification → engine handles routing

## Critical Files Reference

| File | Purpose | Key Functions/Classes |
|------|---------|----------------------|
| `models.py` (2059 lines) | All data models | User, Admin, StudentProfile, Course, Grade, StudentFeeTransaction, etc. |
| `services/grading_calculation_engine.py` | Grade calculations | `GradingCalculationEngine.calculate_course_grade()` |
| `student_routes.py` (1526 lines) | Student portal | Dashboard, courses, results, profile, downloads |
| `admin_routes.py` | Admin dashboard | User management, system stats |
| `finance_routes.py` | Financial reports | Daily/weekly/monthly revenue, transaction logs |
| `exam_routes.py` | Exam management | Create, submit, grade exams |
| `teacher_routes.py` | Teacher tools | Course materials, grading, assessments |
| `utils/decorators.py` | Auth decorators | `@email_verified_required` |
| `utils/permission_decorators.py` | RBAC decorators | `@require_permission('can_edit_finances')` |
| `templates/base.html` | Layout template | Navigation, user menu, CSRF tokens |

## Common Development Tasks

### Adding a New Admin Feature
1. Create route in `admin_*_routes.py`
2. Add `@require_permission('can_...')` decorator
3. Check `admin.is_superadmin` if needed
4. Update `Admin` model if new permission needed
5. Render template from `templates/admin/`

### Modifying Grade Calculations
1. **DO NOT** edit `GradeService`—it's a lookup-only service
2. Work in `services/grading_calculation_engine.py`
3. Methods: `_get_quiz_totals()`, `_get_assignment_totals()`, `_get_exam_totals()`
4. Update `_calculate_weighted_score()` if changing weights
5. Test with `test_finance_fixes.py` or create new test file

### Adding a New Route
1. Create blueprint function: `def create_my_blueprint(): bp = Blueprint(...)`
2. Register in `app.py` around line 160
3. Use consistent patterns from existing routes
4. Template path convention: `templates/{feature}/{action}.html`
5. JSON responses use `jsonify()` for AJAX endpoints

### Sending Email
1. Import: `from utils.email import send_email` (or specific helper)
2. Call with: `send_email(to_email, subject, body, html=True)`
3. Templates in `templates/emails/` (if used)
4. Test locally with debug output; use Gmail test credentials

## Code Patterns & Conventions

### Query Pattern
```python
# DON'T: Load all then filter
users = User.query.all()
admins = [u for u in users if u.role == 'admin']

# DO: Filter at database level
admins = User.query.filter_by(role='admin').all()
admin = User.query.filter_by(user_id=id).first_or_404()
```

### Error Handling
```python
# Always use flask abort() for HTTP errors
from flask import abort
abort(403)  # Forbidden
abort(404)  # Not found
# Errors handled by @app.errorhandler in app.py
```

### CSRF Protection
- Already enabled via `CSRFProtect(app)` in app.py
- All forms auto-protected
- AJAX: Include `{{ csrf_token() }}` in request headers
- Override: `@csrf.exempt` (sparingly, dangerous)

### Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info("User logged in: %s", user_id)
logger.warning("Failed login attempt")
logger.error("Database error", exc_info=True)
```

### Testing & Validation
- Check `test_finance_fixes.py`, `VERIFICATION_REPORT.py` for test patterns
- Validation: Use WTForms in `forms.py` for input validation
- Database integrity: Use `check_db.py` to verify data consistency

## Deployment Considerations
- ✅ Environment variables: `SECRET_KEY`, `DATABASE_URL`, `MAIL_USERNAME`, etc. (see `config.py`)
- ✅ Production: Set `FLASK_ENV=production` (triggers Gunicorn + eventlet)
- ✅ Migrations: Run `flask db upgrade` after schema changes
- ✅ Static files: Served from `/static/`, CSS/JS minified in production
- ✅ See `DEPLOYMENT_CHECKLIST.md` for full deployment guide

## When Stuck
1. Check existing route in same category (e.g., `student_routes.py` for student features)
2. Look at error logs in terminal and `logger` calls
3. Review `GRADING_SYSTEM_ARCHITECTURE.md` for grade-related issues
4. Check `FINANCE_REPORTS_ARCHITECTURE.txt` for finance features
5. Run `check_db.py` to verify database integrity
6. Test routes with Postman or curl; use browser DevTools for frontend

## Key External Dependencies
- **Flask 2.x** (with Flask-Login, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF, Flask-SocketIO)
- **SQLAlchemy 1.4+** (ORM)
- **Jinja2** (templating)
- **Bootstrap 5** (frontend framework)
- **Chart.js 3.9.1** (analytics dashboards)
- **ReportLab** + **WeasyPrint** (PDF generation)
- **eventlet** (production async)
