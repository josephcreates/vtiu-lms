from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, IntegerField, StringField, PasswordField, SubmitField, DateField, SelectField, FileField, FloatField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange, Regexp

# ==============================
# 1️⃣ Registration Form
# ==============================
class ApplicantRegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


# ==============================
# 2️⃣ Login Form
# ==============================
class ApplicantLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class PersonalInfoForm(FlaskForm):
    title = SelectField(
        'Title',
        choices=[('Miss', 'Miss'), ('Mr', 'Mr'), ('Mrs', 'Mrs')],
        validators=[DataRequired()]
    )

    surname = StringField('Last Name (Surname)', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    other_names = StringField('Other / Middle Names', validators=[Optional()])

    gender = SelectField(
        'Gender',
        choices=[('Female', 'Female'), ('Male', 'Male')],
        validators=[DataRequired()]
    )

    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])

    nationality = StringField('Nationality', validators=[DataRequired()])  # <- ADD THIS

    marital_status = SelectField(
        'Marital Status',
        choices=[('Single', 'Single'), ('Married', 'Married')],
        validators=[DataRequired()]
    )

    home_region = SelectField(
        'Home Region',
        choices=[
            ('Greater Accra', 'Greater Accra'),
            ('Ashanti', 'Ashanti'),
            ('Central', 'Central'),
            ('Eastern', 'Eastern'),
            ('Volta', 'Volta'),
            ('Western', 'Western'),
            ('Northern', 'Northern'),
            ('Upper East', 'Upper East'),
            ('Upper West', 'Upper West'),
            ('Bono', 'Bono'),
            ('Ahafo', 'Ahafo'),
            ('Oti', 'Oti'),
            ('Savannah', 'Savannah'),
            ('North East', 'North East')
        ],
        validators=[DataRequired()]
    )

    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    postal_address = TextAreaField('Postal Address', validators=[DataRequired()])

    submit = SubmitField('Save & Continue')


class GuardianForm(FlaskForm):
    name = StringField('Guardian Name', validators=[DataRequired()])
    relation = StringField('Relation to Applicant', validators=[DataRequired()])
    occupation = StringField('Occupation', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email Address', validators=[Optional(), Email()])
    address = TextAreaField('Residential Address', validators=[DataRequired()])

    submit = SubmitField('Save & Continue')


# Programme lists with a blank first option
CERTIFICATE_PROGRAMMES = [
    ('', '— Select Programmes —'),  # Blank line
    ('Cyber Security', 'Cyber Security'),
    ('Early Childhood Education', 'Early Childhood Education'),
    ('Dispensing Technician II & III', 'Dispensing Technician II & III'),
    ('Diagnostic Medical Sonography', 'Diagnostic Medical Sonography'),
    ('Medical Laboratory Technology', 'Medical Laboratory Technology'),
    ('Dispensing Assistant', 'Dispensing Assistant'),
    ('Health Information Management', 'Health Information Management'),
    ('Optical Technician', 'Optical Technician')
]

DIPLOMA_PROGRAMMES = [
    ('Early Childhood Education', 'Early Childhood Education'),
    ('Midwifery', 'Midwifery'),
    ('Ophthalmic Dispensing', 'Ophthalmic Dispensing'),
    ('Medical Laboratory Technology', 'Medical Laboratory Technology'),
    ('HND Dispensing Technology', 'HND Dispensing Technology'),
    ('Health Information Management', 'Health Information Management'),
    ('Diploma in Early Childhood Education', 'Diploma in Early Childhood Education')
]

VOCATIONAL_PROGRAMMES = [
    ('Plumbing & Gas Fitting', 'Plumbing & Gas Fitting'),
    ('Electrical Installation', 'Electrical Installation'),
    ('Welding & Fabrication', 'Welding & Fabrication'),
    ('Refrigeration & Air Conditioning', 'Refrigeration & Air Conditioning'),
    ('Carpentry & Joinery', 'Carpentry & Joinery'),
    ('Masonry & Bricklaying', 'Masonry & Bricklaying'),
    ('Painting & Decoration', 'Painting & Decoration'),
    ('Motor Vehicle Mechanics', 'Motor Vehicle Mechanics'),
    ('Automotive Electronics', 'Automotive Electronics'),
    ('Heavy Equipment Operation', 'Heavy Equipment Operation'),
    ('Building Construction', 'Building Construction'),
    ('Surveying & Mapping', 'Surveying & Mapping'),
    ('Hairdressing & Beauty', 'Hairdressing & Beauty'),
    ('Tailoring & Fashion Design', 'Tailoring & Fashion Design'),
    ('Food Preparation & Catering', 'Food Preparation & Catering'),
    ('Hospitality Management', 'Hospitality Management'),
    ('Tourism & Travel Services', 'Tourism & Travel Services'),
    ('Agriculture & Crop Production', 'Agriculture & Crop Production'),
    ('Livestock & Animal Husbandry', 'Livestock & Animal Husbandry'),
    ('Industrial Maintenance', 'Industrial Maintenance'),
    ('Graphic Design', 'Graphic Design')
]

# Study formats - Regular and Online only
STUDY_FORMATS = [
    ('', '— Select Format —'),
    ('Regular', 'Regular: Admissions process only, no LMS features'),
    ('Online', 'Online: Access to quizzes, assignments, exams, materials, chat')
]

class ProgrammeChoiceForm(FlaskForm):
    # 1st Choice
    first_choice = SelectField(
        '1st Choice Programme',
        choices=CERTIFICATE_PROGRAMMES + DIPLOMA_PROGRAMMES + VOCATIONAL_PROGRAMMES,
        validators=[DataRequired(message="Please select your first choice programme.")]
    )
    first_stream = SelectField(
        'Study Format',
        choices=STUDY_FORMATS,
        validators=[DataRequired(message="Please select a study format.")]
    )

    # 2nd Choice
    second_choice = SelectField(
        '2nd Choice Programme',
        choices=CERTIFICATE_PROGRAMMES + DIPLOMA_PROGRAMMES + VOCATIONAL_PROGRAMMES,
        validators=[Optional()]
    )
    second_stream = SelectField(
        'Study Format',
        choices=STUDY_FORMATS,
        validators=[Optional()]
    )

    # 3rd Choice
    third_choice = SelectField(
        '3rd Choice Programme',
        choices=CERTIFICATE_PROGRAMMES + DIPLOMA_PROGRAMMES + VOCATIONAL_PROGRAMMES,
        validators=[Optional()]
    )
    third_stream = SelectField(
        'Study Format',
        choices=STUDY_FORMATS,
        validators=[Optional()]
    )

    # Sponsor Details
    sponsor_name = StringField(
        'Name of Sponsor',
        validators=[DataRequired(message="Sponsor name is required.")]
    )
    sponsor_relation = StringField(
        'Relationship to Candidate',
        validators=[DataRequired(message="Please specify relationship.")]
    )

    def validate_first_choice(form, field):
        if field.data == '':
            raise ValidationError("Please select your first choice programme.")

    def validate_first_stream(form, field):
        if field.data == '':
            raise ValidationError("Please select a study format.")

    submit = SubmitField('Save & Continue')


class EducationForm(FlaskForm):
    institution = StringField('Institution Attended', validators=[DataRequired()])
    programme = StringField('Programme Pursued', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])

    submit = SubmitField('Save & Continue')


class ExamInfoForm(FlaskForm):
    exam_type = SelectField(
        'Exam Type',
        choices=[('', '— Select exam —'), ('WASSCE', 'WASSCE (Ghanaian)'), ('SSSCE', 'SSSCE')],
        validators=[DataRequired(message="Please select an exam type.")]
    )

    sitting = SelectField(
        'Sitting',
        choices=[('', '— Select —'), ('May/June', 'May/June (School)'), ('Nov/Dec', 'Nov/Dec (Private)')],
        validators=[DataRequired(message="Please select a sitting.")]
    )

    # First sitting — required
    first_index = StringField('First Index Number', validators=[
        DataRequired(message="Please enter the first sitting index number."),
        Length(min=6, max=20, message="Index looks too short/long.")
    ])
    first_year = StringField('First Year', validators=[
        DataRequired(message="Please enter the year for the first sitting."),
        Regexp(r'^\d{4}$', message="Enter a 4-digit year, e.g. 2018.")
    ])

    # Second sitting — optional
    second_index = StringField('Second Index Number', validators=[Optional(), Length(min=6, max=20)])
    second_year = StringField('Second Year', validators=[Optional(), Regexp(r'^\d{4}$', message="Use YYYY")])

    # Third sitting — optional
    third_index = StringField('Third Index Number', validators=[Optional(), Length(min=6, max=20)])
    third_year = StringField('Third Year', validators=[Optional(), Regexp(r'^\d{4}$', message="Use YYYY")])

    submit = SubmitField('Save & Continue')


class ExamResultForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired()])
    grade = SelectField(
        'Grade',
        choices=[
            ('A1', 'A1'), ('B2', 'B2'), ('B3', 'B3'),
            ('C4', 'C4'), ('C5', 'C5'), ('C6', 'C6'),
            ('D7', 'D7'), ('E8', 'E8'), ('F9', 'F9')
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField('Add Result')


class PassportUploadForm(FlaskForm):
    passport = FileField(
        'Upload Passport Photograph',
        validators=[DataRequired()]
    )
    submit = SubmitField('Upload & Continue')


class DeclarationForm(FlaskForm):
    accept_terms = BooleanField('I declare that all information provided is true and complete', validators=[DataRequired(message="You must accept the declaration.")])
    agree_policy = BooleanField('I agree to abide by the institution’s policies', validators=[DataRequired(message="You must agree to the policies.")])
    submit = SubmitField('Submit Application')
    
class VoucherAuthenticationForm(FlaskForm):
    voucher_pin = StringField('Voucher PIN', validators=[DataRequired(), Length(min=6, max=20)])
    serial_number = StringField('Serial Number', validators=[DataRequired(), Length(min=6, max=20)])
    submit = SubmitField('Authenticate Voucher')

class PurchaseVoucherForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = EmailField('Email Address', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    amount = IntegerField('Amount (GHS)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Proceed to Payment')