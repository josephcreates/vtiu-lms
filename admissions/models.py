from datetime import datetime, timedelta
from flask import url_for
from utils.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Applicant(db.Model, UserMixin):
    __tablename__ = 'applicant'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    email_verified = db.Column(db.Boolean, default=False)
    email_verification_code = db.Column(db.String(6))
    email_verification_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    application = db.relationship('Application', backref='applicant', uselist=False, cascade='all, delete-orphan')
    payments = db.relationship('ApplicationPayment', backref='applicant', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Application(db.Model):
    __tablename__ = 'application'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False, unique=True)

    # -------------------
    # Personal info
    # -------------------
    title = db.Column(db.String(10))
    surname = db.Column(db.String(100))        # LAST NAME
    first_name = db.Column(db.String(100))    # FIRST NAME  <-- ADD
    other_names = db.Column(db.String(150))   # MIDDLE / OTHER
    gender = db.Column(db.String(10))
    dob = db.Column(db.Date)
    nationality = db.Column(db.String(50))
    marital_status = db.Column(db.String(20))
    home_region = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    postal_address = db.Column(db.String(255))

    # -------------------
    # Guardian info
    # -------------------
    guardian_name = db.Column(db.String(150))
    guardian_relation = db.Column(db.String(50))
    guardian_occupation = db.Column(db.String(100))
    guardian_phone = db.Column(db.String(20))
    guardian_email = db.Column(db.String(120))
    guardian_address = db.Column(db.String(255))

    # -------------------
    # Programme choices
    # -------------------
    first_choice = db.Column(db.String(100))
    first_stream = db.Column(db.String(50))

    second_choice = db.Column(db.String(100))
    second_stream = db.Column(db.String(50))

    third_choice = db.Column(db.String(100))
    third_stream = db.Column(db.String(50))

    # -------------------
    # Sponsor info
    # -------------------
    sponsor_name = db.Column(db.String(150))
    sponsor_relation = db.Column(db.String(50))

    # -------------------
    # Exam info (SSSCE / WASSCE)
    # -------------------
    exam_type = db.Column(db.String(20))      # WASSCE / SSSCE
    sitting = db.Column(db.String(30))        # May/June, Nov/Dec

    # First sitting (required)
    first_index = db.Column(db.String(50))
    first_year = db.Column(db.String(4))

    # Second sitting (optional)
    second_index = db.Column(db.String(50))
    second_year = db.Column(db.String(4))

    # Third sitting (optional)
    third_index = db.Column(db.String(50))
    third_year = db.Column(db.String(4))

    # -------------------
    # Application lifecycle
    # -------------------
    status = db.Column(db.String(30), default='draft')
    submitted_at = db.Column(db.DateTime)

    # Admin decision
    admitted_programme = db.Column(db.String(100))  # what they were offered
    admitted_stream = db.Column(db.String(50))
    admitted_academic_year = db.Column(db.String(20))
    admitted_semester = db.Column(db.String(10))
    admission_letter_generated = db.Column(db.Boolean, default=False)
    acceptance_letter_generated = db.Column(db.Boolean, default=False)

    # -------------------
    # Relationships
    # -------------------
    documents = db.relationship('ApplicationDocument', backref='application', cascade='all, delete-orphan')

    exam_results = db.relationship('ApplicationResult', backref='application', cascade='all, delete-orphan')

    @property
    def full_name(self):
        parts = [self.surname, self.first_name, self.other_names]
        return " ".join([p for p in parts if p])

    @property
    def profile_picture_url(self):
        """Get URL for applicant's profile picture from documents"""
        # Look for photo document in related documents
        for doc in self.documents:
            if doc.document_type == 'photo' and doc.file_path:
                url = url_for('static', filename=doc.file_path)
                print(f"DEBUG: Found photo document, URL: {url}")
                return url
        
        # Return default avatar if no photo found
        default_url = url_for('static', filename='uploads/profile_pictures/default_avatar.png')
        print(f"DEBUG: No photo found, using default: {default_url}")
        return default_url

class ApplicationDocument(db.Model):
    __tablename__ = 'application_document'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    document_type = db.Column(db.String(50))  # transcript, certificate, photo
    file_path = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdmissionVoucher(db.Model):
    __tablename__ = 'admission_voucher'
    id = db.Column(db.Integer, primary_key=True)
    pin = db.Column(db.String(20), unique=True, nullable=False)
    serial = db.Column(db.String(20), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    is_used = db.Column(db.Boolean, default=False)
    used_by = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=True)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)
    purchaser_email = db.Column(db.String(120), nullable=True)

    def mark_as_used(self, applicant_id):
        """Mark voucher as used by this applicant"""
        self.is_used = True
        self.used_by = applicant_id
        if not self.used_at:
            self.used_at = datetime.utcnow()
        if not self.valid_until:
            self.valid_until = datetime.utcnow() + timedelta(days=180)

    def is_available_for(self, applicant_id):
        """
        Check if voucher can be used:
        - Either unused, or already used by this applicant
        """
        if not self.is_used:
            return True
        if self.used_by == applicant_id:
            return True
        return False


class ApplicationResult(db.Model):
    __tablename__ = 'application_result'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)

    exam_type = db.Column(db.String(50))  # WASSCE, A-Level, IB, etc.
    index_number = db.Column(db.String(50))
    exam_year = db.Column(db.String(10))
    school_name = db.Column(db.String(150))

    subject = db.Column(db.String(100))
    grade = db.Column(db.String(5))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ApplicationPayment(db.Model):
    __tablename__ = 'application_payment'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50))  # momo, card, voucher
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
