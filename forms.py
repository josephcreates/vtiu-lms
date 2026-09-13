from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, PasswordField, SubmitField, SelectField, DateField, TextAreaField, MultipleFileField, SelectMultipleField, BooleanField, IntegerField, FloatField, FieldList, FormField
from wtforms.validators import DataRequired, Length, InputRequired, Email, Optional, NumberRange, EqualTo, ValidationError
from wtforms.fields import DateTimeLocalField, DateTimeField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from utils.helpers import get_programme_choices
from datetime import datetime


class AdminLoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    user_id = StringField("Admin ID", validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class StudentLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    user_id = StringField("Student ID", validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class TeacherLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    user_id = StringField("Teacher ID", validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class ExamLoginForm(FlaskForm):
    user_id = StringField("Student ID", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

"""
Enhanced AdminRegisterForm - Supports both Teacher and Admin registration
Superadmin can create Finance Admins and other admin roles with granular permissions
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, IntegerField, FileField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import InputRequired, Optional, Length, Email, NumberRange, DataRequired
from flask_wtf.file import FileAllowed


class AdminRegisterForm(FlaskForm):
    """Form for Superadmin to create Finance Admin accounts"""
    
    # ============================
    # Core Admin User Fields
    # ============================
    first_name = StringField(
        'First Name',
        validators=[InputRequired(message='First name is required'), Length(min=1, max=100)]
    )
    
    middle_name = StringField(
        'Middle Name',
        validators=[Optional(), Length(max=100)]
    )
    
    last_name = StringField(
        'Last Name',
        validators=[InputRequired(message='Last name is required'), Length(min=1, max=100)]
    )
    
    # Profile picture - optional for admin
    profile_picture = FileField(
        'Profile Picture',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
        ]
    )
    
    # ============================
    # Admin Role Selection
    # ============================
    role = SelectField(
        'Admin Role',
        choices=[
            ('finance_admin', 'Finance Admin'),
            ('admissions_admin', 'Admissions Admin'),
            ('academic_admin', 'Academic Admin'),
        ],
        validators=[InputRequired(message='Please select a role')]
    )
    
    # ============================
    # Login Credentials
    # ============================
    email = StringField(
        'Email (for login)',
        validators=[InputRequired(message='Email is required'), Email(), Length(max=120)]
    )
    
    password = PasswordField(
        'Temporary Password',
        validators=[InputRequired(message='Password is required'), Length(min=8, max=100)]
    )
    
    # ============================
    # Personal Information
    # ============================
    dob = DateField(
        'Date of Birth',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    
    gender = SelectField(
        'Gender',
        choices=[
            ('', '— Select Gender —'),
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other')
        ],
        validators=[Optional()]
    )
    
    phone = StringField(
        'Phone Number',
        validators=[Optional(), Length(max=20)]
    )
    
    nationality = StringField(
        'Nationality',
        validators=[Optional(), Length(max=50)]
    )
    
    # ============================
    # Admin-Specific Information
    # ============================
    admin_id = StringField(
        'Admin ID',
        render_kw={'readonly': True},
        validators=[Optional()]
    )
    
    department = SelectField(
        'Department/Office',
        choices=[
            ('', '— Select Department —'),
            ('Finance', 'Finance'),
            ('Admissions', 'Admissions'),
            ('Academic Affairs', 'Academic Affairs'),
            ('Administration', 'Administration'),
            ('Human Resources', 'Human Resources'),
        ],
        validators=[InputRequired(message='Please select a department')]
    )
    
    office_location = StringField(
        'Office Location',
        validators=[Optional(), Length(max=100)]
    )
    
    job_title = StringField(
        'Job Title',
        validators=[InputRequired(message='Job title is required'), Length(min=1, max=100)]
    )
    
    date_of_appointment = DateField(
        'Date of Appointment',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    
    # ============================
    # Permissions (For Finance Admin)
    # ============================
    can_approve_payments = SelectField(
        'Can Approve Payments?',
        choices=[
            ('', '— Select —'),
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        validators=[Optional()]
    )
    
    can_view_reports = SelectField(
        'Can View Reports?',
        choices=[
            ('', '— Select —'),
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        validators=[Optional()]
    )
    
    can_manage_fees = SelectField(
        'Can Manage Fees?',
        choices=[
            ('', '— Select —'),
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        validators=[Optional()]
    )
    
    # ============================
    # Submit
    # ============================
    submit = SubmitField('Create Admin Account')
        
class ForgotPasswordForm(FlaskForm):
    # Ask the user for the email they registered with (recommended)
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    user_id = StringField('User ID (optional)', validators=[Length(max=20)])
    submit = SubmitField('Send Reset Email')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New password', validators=[DataRequired(), Length(min=8, message='Minimum 8 characters')])
    confirm_password = PasswordField('Confirm password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Set New Password')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message="Password must be at least 6 characters")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message="Passwords must match")
    ])
    submit = SubmitField('Update Password')
    
from wtforms import SelectField, StringField, IntegerField, SubmitField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Optional, NumberRange
from flask_wtf import FlaskForm


class QuizForm(FlaskForm):
    """Form for creating and editing quizzes - tertiary education (programme/level based)"""

    # ✅ Programme and level selection
    assigned_programme = SelectField(
        'Programme',
        choices=[('', '— Select Programme —')],
        validators=[DataRequired(message="Programme is required")]
    )

    programme_level = SelectField(
        'Level',
        choices=[('', '— Select Level —')],
        validators=[DataRequired(message="Level is required")]
    )

    # ✅ Course selection (populated dynamically)
    course_id = HiddenField(validators=[Optional()])
    
    course_name = SelectField(
        'Course Name',
        choices=[('', '— Select Course (Optional) —')],
        validators=[Optional()]  # Changed to Optional since course is optional
    )

    # ✅ Quiz details
    title = StringField(
        'Quiz Title',
        validators=[DataRequired(message="Quiz title is required")],
        render_kw={"placeholder": "Enter quiz title"}
    )

    start_datetime = DateTimeLocalField(
        'Start Date & Time',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired(message="Start date/time is required")]
    )

    end_datetime = DateTimeLocalField(
        'End Date & Time',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired(message="End date/time is required")]
    )

    # ✅ Duration as a SelectField with string values
    duration = SelectField(
        'Duration (minutes)',
        choices=[
            ('', '— Select Duration —'),
            ('15', '15 minutes'),
            ('30', '30 minutes'),
            ('45', '45 minutes'),
            ('60', '1 hour'),
            ('90', '1.5 hours'),
            ('120', '2 hours'),
            ('180', '3 hours')
        ],
        validators=[DataRequired(message="Duration is required")]
    )

    # ✅ Attempts allowed (single-shot quiz = 1 attempt)
    attempts_allowed = IntegerField(
        'Attempts Allowed',
        validators=[
            DataRequired(message="Attempts allowed is required"),
            NumberRange(min=1, message="Must allow at least 1 attempt")
        ],
        default=1,
        render_kw={"min": "1"}
    )

    submit = SubmitField('Save Quiz')
        
class ExamOptionForm(FlaskForm):
    text = StringField("Option Text", validators=[DataRequired()])
    is_correct = BooleanField("Correct")


class ExamQuestionForm(FlaskForm):
    question_text = TextAreaField("Question", validators=[DataRequired()])
    question_type = SelectField(
        "Type",
        choices=[
            ("mcq", "Multiple Choice"),
            ("true_false", "True/False"),
            ("math", "Numeric/Math"),
            ("subjective", "Subjective")
        ],
        validators=[DataRequired()]
    )
    marks = IntegerField("Marks", validators=[DataRequired(), NumberRange(min=1)])
    options = FieldList(FormField(ExamOptionForm), min_entries=2, max_entries=6)
    subjective_rubric = TextAreaField("Expected Answer / Rubric")
    submit = SubmitField("Save")


class ExamSetForm(FlaskForm):
    name = StringField("Set Name", validators=[DataRequired(), Length(min=1, max=50)])
    access_password = StringField('Set Password', validators=[DataRequired()])
    submit = SubmitField("Save")


class ExamForm(FlaskForm):
    """Form for creating and editing exams."""
    
    title = StringField(
        'Exam Title',
        validators=[DataRequired(message="Title is required")],
        render_kw={"placeholder": "Enter exam title"}
    )
    
    programme_name = SelectField(
        'Assign to Programme',
        choices=[],
        validators=[DataRequired(message="Programme is required")],
        render_kw={"id": "programme_name"}
    )
    
    programme_level = SelectField(
        'Programme Level',
        choices=[],
        validators=[DataRequired(message="Level is required")],
        render_kw={"id": "programme_level"}
    )
    
    course_id = SelectField(
        'Course',
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Course is required")],
        render_kw={"id": "course_id"}
    )
    
    start_datetime = DateTimeLocalField(
        'Start Date & Time',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired(message="Start date/time is required")]
    )
    
    end_datetime = DateTimeLocalField(
        'End Date & Time',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired(message="End date/time is required")]
    )
    
    duration_minutes = IntegerField(
        'Duration (minutes)',
        validators=[Optional(), NumberRange(min=1, message="Duration must be at least 1 minute")],
        render_kw={"placeholder": "e.g., 90"}
    )
    
    assignment_mode = SelectField(
        'Assignment Mode',
        choices=[
            ('random', 'Admin: Random set'),
            ('hash', 'Deterministic: hash(student) → set'),
            ('choice', 'Student chooses set'),
        ],
        default='random',
        validators=[DataRequired()]
    )
    
    assignment_seed = StringField(
        'Assignment seed (optional)',
        validators=[Optional()],
        render_kw={"placeholder": "Used only in Hash mode"}
    )
    
    submit = SubmitField('Create Exam')
    
class AssignmentForm(FlaskForm):
    """Form for creating and assigning coursework to programmes and courses"""
    
    programme = SelectField(
        'Assign to Programme', 
        choices=[], 
        validators=[DataRequired(message="Please select a programme")],
        description="Select the programme this assignment applies to"
    )

    programme_level = SelectField(
        'Programme Level',
        choices=[
            ('', '— Select Level —'),
            ('100', 'Level 100'),
            ('200', 'Level 200'),
            ('300', 'Level 300'),
            ('400', 'Level 400')
        ],
        validators=[DataRequired(message="Please select a level")],
        description="Select the level of the programme"
    )

    # ✅ Make course_id Optional - we'll validate it in the route
    course_id = HiddenField(validators=[Optional()])
    
    course_name = SelectField(
        'Course', 
        choices=[('', '— Select Course —')], 
        validators=[DataRequired(message="Please select a course")],
        description="Select the specific course within the programme"
    )

    title = StringField(
        'Assignment Title',
        validators=[DataRequired(message="Assignment title is required")],
        render_kw={"placeholder": "Enter assignment title"}
    )
    
    description = TextAreaField(
        'Description',
        validators=[Optional()],
        description="Brief overview of the assignment",
        render_kw={"placeholder": "Brief overview of the assignment", "rows": 3}
    )
    
    instructions = TextAreaField(
        'Instructions',
        validators=[Optional()],
        description="Detailed instructions for completing the assignment",
        render_kw={"placeholder": "Detailed instructions for students", "rows": 3}
    )
    
    due_date = DateTimeField(
        'Due Date & Time', 
        format='%Y-%m-%dT%H:%M', 
        validators=[DataRequired(message="Due date is required")],
        description="When the assignment is due"
    )
    
    max_score = FloatField(
        'Max Score', 
        validators=[DataRequired(message="Max score is required")],
        description="Total points for this assignment",
        render_kw={"type": "number", "step": "0.5", "min": "0"}
    )
    
    file = FileField(
        'Upload Assignment File (Optional)', 
        validators=[
            FileAllowed(
                ['pdf','doc','docx','ppt','pptx','txt'],
                'Only PDF, Word, PowerPoint, and text files are allowed'
            ),
            Optional()
        ],
        description="Attach a file for students to download"
    )
    
    submit = SubmitField('Create Assignment')

class MaterialForm(FlaskForm):
    title = StringField('Material Title', validators=[DataRequired()])
    programme_name = SelectField('Programme', choices=[], validators=[DataRequired()])
    programme_level = SelectField('Level', choices=[], validators=[DataRequired()])
    course_name = SelectField('Course', choices=[], validators=[DataRequired()])
    files = MultipleFileField('Files', validators=[DataRequired()])
    submit = SubmitField('Upload')

class CourseRegistrationForm(FlaskForm):
    semester = SelectField('Semester', choices=[('First','First'), ('Second','Second')], validators=[DataRequired()])
    academic_year = SelectField('Academic Year', validators=[DataRequired()])
    courses = SelectMultipleField('Optional Courses', coerce=int)
    submit = SubmitField('Register Courses')
    
class CourseForm(FlaskForm):
    name = StringField('Course Name', validators=[DataRequired()])
    code = StringField('Course Code', validators=[DataRequired(), Length(max=20)])
    programme_name = SelectField('Programme', choices=get_programme_choices(), validators=[DataRequired()])
    programme_level = SelectField('Level', choices=[('100','100'),('200','200'),('300','300'),('400','400')], validators=[DataRequired()])
    semester = SelectField('Semester', choices=[('First','First'),('Second','Second')], validators=[DataRequired()])
    credit_hours = IntegerField('Credit Hours', validators=[DataRequired()])
    academic_year = StringField('Academic Year', validators=[DataRequired()])
    is_mandatory = BooleanField('Mandatory?')
    submit = SubmitField('Save Course')

class CourseLimitForm(FlaskForm):
    programme_name  = SelectField('Programme', choices=get_programme_choices(), validators=[DataRequired()])
    programme_level = SelectField('Level', choices=[('100','100'),('200','200'),('300','300'),('400','400')], validators=[DataRequired()])
    semester        = SelectField('Semester', choices=[('First','First'), ('Second','Second')], validators=[DataRequired()])
    academic_year   = StringField('Academic Year', validators=[DataRequired()])
    mandatory_limit = IntegerField('Mandatory Course Limit', validators=[DataRequired(), NumberRange(min=0)])
    optional_limit  = IntegerField('Optional Course Limit', validators=[DataRequired(), NumberRange(min=0)])
    submit          = SubmitField('Save Limits')

class MeetingForm(FlaskForm):
    title = StringField('Meeting Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    scheduled_start = DateTimeLocalField('Start Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    scheduled_end = DateTimeLocalField('End Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    submit = SubmitField('Save Meeting')

class RecordingForm(FlaskForm):
    title = StringField('Recording Title', validators=[DataRequired()])
    file = FileField('Upload Recording', validators=[DataRequired()])
    submit = SubmitField('Upload Recording')
