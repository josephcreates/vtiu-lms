from flask import current_app, url_for
import logging
import requests
import re

# Global session for connection reuse
session = requests.Session()
session.headers.update({
    'User-Agent': 'VTIU-LMS/1.0'
})

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_sender_email():
    """Get validated sender email"""
    sender = current_app.config.get("MAIL_DEFAULT_SENDER")
    if not sender or '@' not in sender:
        logging.error("MAIL_DEFAULT_SENDER not properly configured")
        return None
    return sender

def send_email(to_email, subject, body, is_html=True, max_retries=2):
    """
    Send email using Brevo HTTPS API with proper error handling and retries.
    """
    # Validate inputs
    if not validate_email(to_email):
        logging.error(f"Invalid recipient email: {to_email}")
        return False
    
    sender = get_sender_email()
    if not sender:
        logging.error("No valid sender email configured")
        return False
    
    api_key = current_app.config.get("BREVO_API_KEY")
    if not api_key:
        logging.error("BREVO_API_KEY not configured")
        return False
    
    # Test API key once per application lifecycle
    if not hasattr(current_app, '_brevo_key_tested'):
        test_result = test_brevo_api_key()
        current_app._brevo_key_tested = True
        current_app._brevo_key_valid = test_result
        
        if not test_result:
            logging.error("Brevo API key validation failed - attempting to send anyway")
            # Don't return False here - try to send anyway
    
    # Retry logic
    for attempt in range(max_retries):
        try:
            result = _send_via_brevo(to_email, subject, body, sender, is_html)
            if result:
                return True
                
        except requests.exceptions.RequestException as e:
            logging.warning(f"Brevo API attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                continue
            else:
                logging.error(f"All {max_retries} attempts failed for {to_email}")
                return False
                
        except Exception as e:
            logging.error(f"Unexpected error sending to {to_email}: {str(e)}")
            return False
    
    return False

def _send_via_brevo(to_email, subject, body, sender, is_html=True):
    """Send email using Brevo HTTPS API with proper content handling"""
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "api-key": current_app.config.get("BREVO_API_KEY"),
            "content-type": "application/json"
        }
        
        # Prepare content based on type
        if is_html:
            content = {"htmlContent": body}
        else:
            content = {"textContent": body}
        
        payload = {
            "sender": {
                "email": sender,
                "name": "VTIU LMS"
            },
            "to": [{"email": to_email}],
            "subject": subject,
            **content
        }
        
        response = session.post(url, json=payload, headers=headers, timeout=10)
        
        # Handle multiple success codes
        if response.status_code in [200, 201, 202]:
            response_data = response.json()
            message_id = response_data.get('messageId', 'unknown')
            logging.info(f"✅ Email sent via Brevo to {to_email} - ID: {message_id}")
            return True
        elif response.status_code == 401:
            logging.error(f"❌ Brevo API authentication failed (401) - Check API key")
            return False
        elif response.status_code == 429:
            logging.warning(f"⚠️ Brevo rate limit exceeded for {to_email}")
            return False
        else:
            logging.error(f"❌ Brevo API error: {response.status_code} - {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        logging.error(f"❌ Brevo API timeout for {to_email}")
        return False
    except requests.exceptions.ConnectionError as e:
        logging.error(f"❌ Brevo connection error for {to_email}: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"❌ Brevo sending failed to {to_email}: {str(e)}")
        return False

def test_brevo_api_key():
    """Test if Brevo API key is valid with detailed error logging"""
    try:
        api_key = current_app.config.get("BREVO_API_KEY")
        if not api_key:
            logging.error("❌ BREVO_API_KEY is not configured in environment")
            return False
        
        # Log first/last 4 chars for debugging (never log full key)
        key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        logging.info(f"🔑 Testing Brevo API key: {key_preview}")
            
        url = "https://api.brevo.com/v3/account"
        headers = {
            "api-key": api_key,
            "accept": "application/json"
        }
        
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            account_info = response.json()
            email = account_info.get('email', 'N/A')
            logging.info(f"✅ Brevo API key validation successful - Account: {email}")
            return True
        elif response.status_code == 401:
            logging.error(f"❌ Brevo API key is invalid (401 Unauthorized)")
            return False
        elif response.status_code == 403:
            logging.error(f"❌ Brevo API key lacks required permissions (403 Forbidden)")
            return False
        else:
            logging.warning(f"⚠️ Brevo API key test returned {response.status_code}: {response.text[:200]}")
            # Don't fail completely on unexpected status codes - allow emails to attempt
            return True
        
    except requests.exceptions.Timeout:
        logging.warning("⚠️ Brevo API key validation timed out - assuming valid and will retry on actual send")
        return True  # Don't block emails due to timeout
    except requests.exceptions.ConnectionError as e:
        logging.warning(f"⚠️ Brevo API connection error during validation: {str(e)} - assuming valid")
        return True  # Don't block emails due to network issues
    except Exception as e:
        logging.error(f"❌ Brevo API key test failed with unexpected error: {str(e)}")
        # Log the full traceback for debugging
        import traceback
        logging.error(traceback.format_exc())
        return True  # Don't block emails due to unexpected errors

def _get_applicant_name(applicant):
    """
    Safely resolve applicant name.
    Falls back to email if personal info is not yet filled.
    """
    try:
        if applicant.application and applicant.application.surname:
            return f"{applicant.application.surname} {applicant.application.other_names or ''}".strip()
    except Exception:
        pass

    return applicant.email


def send_password_reset_email(applicant, token):
    reset_url = url_for(
        'vclass.reset_password',
        token=token,
        _external=True
    )

    name = _get_applicant_name(applicant)

    subject = "Password Reset – Online Admissions Portal"

    body = f"""
Dear {name},

A request has been received to reset the password for your Online Admissions Portal account.

To proceed, please click the secure link below to set a new password.
This link will expire in 1 hour.

{reset_url}

If you did not initiate this request, please ignore this email.
No changes will be made to your account.

Admissions Office
Online Admissions Portal
"""

    return send_email(applicant.email, subject, body, is_html=False)


# ------------------------------------------------------------------
# TEMPORARY PASSWORD EMAIL (ADMIN RESET)
# ------------------------------------------------------------------

def send_temporary_password_email(applicant, temp_password):
    name = _get_applicant_name(applicant)

    subject = "Temporary Password – Online Admissions Portal"

    body = f"""
Dear {name},

Your account password has been reset by the Admissions Office.

Your temporary password is:

{temp_password}

Please log in immediately and change your password to keep your account secure.

Admissions Office
Online Admissions Portal
"""

    return send_email(applicant.email, subject, body, is_html=False)


# ------------------------------------------------------------------
# EMAIL VERIFICATION (KNUST-STYLE)
# ------------------------------------------------------------------

def send_email_verification(applicant, verification_code):
    name = _get_applicant_name(applicant)

    subject = "Verify Your Email Address – Online Admissions"

    body = f"""
Dear {name},

Thank you for creating an account on the Online Admissions Portal.

To complete your registration, please verify your email address
using the verification code below:

VERIFICATION CODE: {verification_code}

This code will expire shortly.
Do not share this code with anyone.

Admissions Office
Online Admissions Portal
"""

    return send_email(applicant.email, subject, body, is_html=False)

# ------------------------------------------------------------------
# APPLICATION COMPLETION EMAIL
# ------------------------------------------------------------------

def send_application_completed_email(applicant):
    name = _get_applicant_name(applicant)

    subject = "Admission Application Successfully Submitted"

    body = f"""
Dear {name},

Your admission application has been successfully submitted.

Our admissions team will review your application.
If additional information is required, you will be contacted via this email address.

You may log into the Online Admissions Portal at any time to track your application status.

Thank you for choosing our institution.

Admissions Office
Online Admissions Portal
"""

    return send_email(applicant.email, subject, body, is_html=False)

def send_approval_credentials_email(applicant, username, student_id, temp_password, fees_info=None):
    name = _get_applicant_name(applicant)

    subject = "Your Student Account is Ready – Online Admissions Portal"

    fees_section = ""
    if fees_info:
        fees_section = f"""
    <hr>
    <h3>Programme Fees</h3>
    <p><b>Programme:</b> {fees_info.get('programme_name', 'N/A')}</p>
    <table style="border-collapse: collapse; width: 100%; margin-top: 10px;">
        <tr style="background-color: #f2f2f2;">
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Fee Component</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Amount (GHS)</th>
        </tr>
"""
        total_fees = 0
        for fee in fees_info.get('fees', []):
            try:
                amount = float(fee.get('amount', 0))
                total_fees += amount
            except (ValueError, TypeError):
                logging.warning(f"Invalid fee amount: {fee.get('amount')}")
                amount = 0.0
            fees_section += f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;">{fee.get('description', 'Fee')}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{amount:,.2f}</td>
        </tr>
"""
        fees_section += f"""
        <tr style="background-color: #f2f2f2; font-weight: bold;">
            <td style="border: 1px solid #ddd; padding: 8px;">Total</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{total_fees:,.2f}</td>
        </tr>
    </table>
    <p style="margin-top: 10px;">You will be prompted to pay these fees upon login to your student portal.</p>
        """

    body = f"""
    <p>Dear {name},</p>

    <p>Congratulations! Your admission application has been approved.</p>

    <p>Your student account has been created with the following credentials:</p>

    <ul>
        <li><b>Username:</b> {username}</li>
        <li><b>Student ID:</b> {student_id}</li>
        <li><b>Temporary Password:</b> {temp_password}</li>
    </ul>

    <p>
        Please log in immediately at
        <a href="{url_for('admissions.login', _external=True)}">Online Admissions Portal</a>
        and change your password.
    </p>

    {fees_section}

    <p>Admissions Office<br>Online Admissions Portal</p>
    """

    try:
        return send_email(applicant.email, subject, body, is_html=True)
    except Exception as e:
        logging.error(
            f"Failed to send approval credentials email to {applicant.email}: {str(e)}"
        )
        return False


# ------------------------------------------------------------------
# TEACHER REGISTRATION CREDENTIALS EMAIL
# ------------------------------------------------------------------

def send_teacher_registration_email(email, first_name, last_name, username, user_id, employee_id, temp_password):
    """
    Send registration credentials to newly created teacher
    """
    name = f"{first_name} {last_name}"
    
    subject = "Your Teacher Account is Ready – VTIU LMS"
    
    body = f"""
Dear {name},

Your teacher account has been successfully created at VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY.

Your login credentials are:
- Username: {username}
- User ID: {user_id}
- Employee ID: {employee_id}
- Temporary Password: {temp_password}

Please log in immediately at the Teacher Portal and change your password to keep your account secure.

Login URL: {url_for('teacher.teacher_login', _external=True)}

Important:
- Keep your credentials confidential
- Change your password on first login
- Contact IT support if you have any issues

Best regards,
VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY
IT Department
"""

    return send_email(email, subject, body, is_html=False)


# ------------------------------------------------------------------
# ADMIN REGISTRATION CREDENTIALS EMAIL
# ------------------------------------------------------------------

def send_admin_registration_email(email, first_name, last_name, username, admin_id, role, temp_password):
    """
    Send registration credentials to newly created admin
    """
    name = f"{first_name} {last_name}"
    
    role_display = {
        'finance_admin': 'Finance Admin',
        'academic_admin': 'Academic Admin', 
        'admissions_admin': 'Admissions Admin',
        'superadmin': 'Super Admin'
    }.get(role, role.replace('_', ' ').title())
    
    subject = f"Your {role_display} Account is Ready – VTIU LMS"
    
    body = f"""
Dear {name},

Your {role_display} account has been successfully created at VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY.

Your login credentials are:
- Username: {username}
- Admin ID: {admin_id}
- Role: {role_display}
- Temporary Password: {temp_password}

Please log in immediately at the Admin Portal and change your password to keep your account secure.

Login URL: {url_for('admin.admin_login', _external=True)}

Important:
- Keep your credentials confidential
- Change your password on first login
- Contact IT support if you have any issues
- Your role permissions have been configured accordingly

Best regards,
    VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY
System Administration
"""

    return send_email(email, subject, body, is_html=False)


def send_continuing_student_credentials_email(email, first_name, last_name, username, student_id, index_number, temp_password, programme, level):
    """
    Send registration credentials to newly created continuing student
    """
    name = f"{first_name} {last_name}"
    
    subject = "Your Student Account is Ready – VTIU LMS Portal"
    
    body = f"""
Dear {name},

Your continuing student account has been successfully created at VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY.

Your login credentials are:
- Username: {username}
- Student ID: {student_id}
- Index Number: {index_number}
- Temporary Password: {temp_password}
- Programme: {programme}
- Level: {level}

Please log in immediately at the Student Portal and change your password to keep your account secure.

Login URL: {url_for('vclass.vclass_login', _external=True)}

Important:
- Keep your credentials confidential
- Change your password on first login
- Complete your profile information
- Contact IT support if you have any issues
- Your academic records have been updated for the new level

Best regards,
    VOCATIONAL & TECHNICAL INSPIRED UNIVERSITY
Student Administration
"""

    return send_email(email, subject, body, is_html=False)
    