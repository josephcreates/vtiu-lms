"""
Index Number Generator
Format: PPYYSSS
- PP = Programme Code (2 digits)
- YY = Year of admission (last 2 digits)
- SSS = Student serial number (001-999)

Example: 0126001 = Early Childhood (01), 2026 (26), 1st student (001)
"""

from datetime import datetime
from sqlalchemy import func
from models import StudentProfile, db

# =====================================================
# PROGRAMME CODES (2 DIGITS EACH)
# =====================================================
PROGRAMME_CODES = {
    'Early Childhood Education': '01',
    'Dispensing Technician II & III': '02',
    'Diagnostic Medical Sonography': '03',
    'Medical Laboratory Technology': '04',
    'Dispensing Assistant': '05',
    'Health Information Management': '06',
    'Optical Technician': '07',
    'Cyber Security': '08',
    'Midwifery': '09',
    'Ophthalmic Dispensing': '10',
    'HND Dispensing Technology': '11',
    'Diploma in Early Childhood Education': '12',
    'Plumbing & Gas Fitting': '13',
    'Electrical Installation': '14',
    'Welding & Fabrication': '15',
    'Refrigeration & Air Conditioning': '16',
    'Carpentry & Joinery': '17',
    'Masonry & Bricklaying': '18',
    'Painting & Decoration': '19',
    'Motor Vehicle Mechanics': '20',
    'Automotive Electronics': '21',
    'Heavy Equipment Operation': '22',
    'Building Construction': '23',
    'Surveying & Mapping': '24',
    'Hairdressing & Beauty': '25',
    'Tailoring & Fashion Design': '26',
    'Food Preparation & Catering': '27',
    'Hospitality Management': '28',
    'Tourism & Travel Services': '29',
    'Agriculture & Crop Production': '30',
    'Livestock & Animal Husbandry': '31',
    'Industrial Maintenance': '32',
    'Graphic Design': '33',
}


def get_programme_code(programme_name):
    """
    Get the 2-digit code for a programme.
    
    Args:
        programme_name: Full programme name
    
    Returns:
        str: 2-digit code (e.g., '01')
    """
    code = PROGRAMME_CODES.get(programme_name, '99')  # 99 = unknown
    return code


def get_admission_year(admission_date=None):
    """
    Get the last 2 digits of admission year.
    
    Args:
        admission_date: datetime.date object (default: today)
    
    Returns:
        str: 2-digit year (e.g., '26' for 2026)
    """
    if admission_date is None:
        admission_date = datetime.utcnow().date()
    
    year_str = str(admission_date.year)[-2:]  # Get last 2 digits
    return year_str


def get_next_serial_number(programme_code, year):
    """
    Get the next available serial number for a programme and year.
    
    Args:
        programme_code: 2-digit code (e.g., '01')
        year: 2-digit year (e.g., '26')
    
    Returns:
        str: 3-digit serial number (e.g., '001', '042', '999')
    """
    # Build index number prefix to search for
    prefix = f"{programme_code}{year}"
    
    # Find all students with this prefix
    existing = StudentProfile.query.filter(
        StudentProfile.index_number.like(f"{prefix}%")
    ).all()
    
    # Get serial numbers from existing indices
    serials = []
    for student in existing:
        if student.index_number and len(student.index_number) == 7:
            try:
                serial = int(student.index_number[4:7])  # Get last 3 digits
                serials.append(serial)
            except (ValueError, IndexError):
                pass
    
    # Find next available serial
    if serials:
        next_serial = max(serials) + 1
    else:
        next_serial = 1
    
    # Ensure we don't exceed 999
    if next_serial > 999:
        raise ValueError(f"Maximum index numbers reached for {prefix}xxx")
    
    # Format as 3-digit with leading zeros
    return f"{next_serial:03d}"


def generate_index_number(programme_name, admission_date=None):
    """
    Generate a unique 7-digit index number.
    
    Format: PPYYSSS
    - PP = Programme Code (2 digits)
    - YY = Year of admission (last 2 digits)
    - SSS = Student serial number (001-999)
    
    Args:
        programme_name: Full programme name (e.g., 'Early Childhood Education')
        admission_date: datetime.date object (default: today)
    
    Returns:
        str: 7-digit index number (e.g., '0126001')
    
    Raises:
        ValueError: If programme code not found or max serials exceeded
    """
    if not programme_name:
        raise ValueError("Programme name required")
    
    # Get programme code
    programme_code = get_programme_code(programme_name)
    
    # Get admission year
    year = get_admission_year(admission_date)
    
    # Get next serial number
    serial = get_next_serial_number(programme_code, year)
    
    # Combine into 7-digit index
    index_number = f"{programme_code}{year}{serial}"
    
    return index_number


def parse_index_number(index_number):
    """
    Parse a 7-digit index number into its components.
    
    Args:
        index_number: 7-digit string (e.g., '0126001')
    
    Returns:
        dict: {
            'programme_code': '01',
            'year': '26',
            'serial': '001',
            'full': '0126001'
        }
    
    Raises:
        ValueError: If format is invalid
    """
    if not index_number or len(str(index_number)) != 7:
        raise ValueError(f"Invalid index number format: {index_number}")
    
    index_str = str(index_number)
    
    try:
        return {
            'programme_code': index_str[0:2],
            'year': index_str[2:4],
            'serial': index_str[4:7],
            'full': index_str
        }
    except Exception as e:
        raise ValueError(f"Failed to parse index number: {e}")


def reverse_lookup_programme(programme_code):
    """
    Find programme name by its code.
    
    Args:
        programme_code: 2-digit code (e.g., '01')
    
    Returns:
        str: Programme name or 'Unknown'
    """
    for name, code in PROGRAMME_CODES.items():
        if code == programme_code:
            return name
    return 'Unknown'


# Example usage:
if __name__ == '__main__':
    # Generate index number
    idx = generate_index_number('Early Childhood Education', datetime(2026, 1, 15).date())
    print(f"Generated: {idx}")  # Output: 0126001
    
    # Parse index number
    parsed = parse_index_number(idx)
    print(f"Parsed: {parsed}")
    
    # Reverse lookup
    programme = reverse_lookup_programme('01')
    print(f"Programme: {programme}")  # Output: Early Childhood Education
    