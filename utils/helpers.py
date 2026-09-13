# utils/helpers.py

from models import Course
from utils.extensions import db


def get_programme_choices():
    """Return a list of available programmes for SelectFields."""
    # Certificate Programmes
    certificate_programmes = [
        'Cyber Security',
        'Early Childhood Education',
        'Dispensing Technician II & III',
        'Diagnostic Medical Sonography',
        'Medical Laboratory Technology',
        'Dispensing Assistant',
        'Health Information Management',
        'Optical Technician'
    ]

    # Diploma Programmes
    diploma_programmes = [
        'Early Childhood Education',
        'Midwifery',
        'Ophthalmic Dispensing',
        'Medical Laboratory Technology',
        'HND Dispensing Technology',
        'Health Information Management',
        'Diploma in Early Childhood Education'
    ]

    # Vocational & Technical Programmes
    vocational_programmes = [
        'Plumbing & Gas Fitting',
        'Electrical Installation',
        'Welding & Fabrication',
        'Refrigeration & Air Conditioning',
        'Carpentry & Joinery',
        'Masonry & Bricklaying',
        'Painting & Decoration',
        'Motor Vehicle Mechanics',
        'Automotive Electronics',
        'Heavy Equipment Operation',
        'Building Construction',
        'Surveying & Mapping',
        'Hairdressing & Beauty',
        'Tailoring & Fashion Design',
        'Food Preparation & Catering',
        'Hospitality Management',
        'Tourism & Travel Services',
        'Agriculture & Crop Production',
        'Livestock & Animal Husbandry',
        'Industrial Maintenance',
        'Graphic Design'
    ]

    # Combine, remove duplicates, and return as list of tuples for WTForms
    all_programmes = sorted(set(certificate_programmes + diploma_programmes + vocational_programmes))
    return [(p, p) for p in all_programmes]

def get_level_choices():
    # Collect distinct levels from courses
    levels = db.session.query(Course.programme_level)\
        .distinct()\
        .order_by(Course.programme_level)\
        .all()

    return [(str(l[0]), f"Level {l[0]}") for l in levels if l[0] is not None]

def get_course_choices(programme, level):
    courses = Course.query.filter_by(
        programme_name=programme,
        programme_level=level
    ).order_by(Course.course_name).all()

    return [(c.course_name, c.course_name) for c in courses]

def get_class_choices():
    """
    Return a list of default class choices.
    Each item is a tuple (display_name, display_name) for select fields.
    """
    return [
        ('Primary 1', 'Primary 1'),
        ('Primary 2', 'Primary 2'),
        ('Primary 3', 'Primary 3'),
        ('Primary 4', 'Primary 4'),
        ('Primary 5', 'Primary 5'),
        ('Primary 6', 'Primary 6'),
        ('JHS 1', 'JHS 1'),
        ('JHS 2', 'JHS 2'),
        ('JHS 3', 'JHS 3'),
        ('SHS 1', 'SHS 1'),
        ('SHS 2', 'SHS 2'),
        ('SHS 3', 'SHS 3'),
    ]
