# utils/promotion.py - Updated for Tertiary Education

PROGRAMME_LEVELS = {
    100: "Level 100",
    200: "Level 200",
    300: "Level 300",
    400: "Level 400"
}

# Progression sequence
LEVEL_PROGRESSION = [100, 200, 300, 400]


def promote_student(student, final_score):
    """
    Promote a student to the next academic level based on their final score.
    Progression: Level 100 → Level 200 → Level 300 → Level 400 → Graduated
    
    Args:
        student: Student object with current_level attribute
        final_score: Final score/GPA for the current level
    
    Returns:
        Dictionary with promotion details
    """
    current_level = student.current_level  # Should be 100, 200, 300, or 400
    
    if final_score >= 50:
        status = "Promoted"
        next_level = get_next_level(current_level)
        
        if next_level is None:
            # Student has completed Level 400
            status = "Graduated"
            next_level = current_level
    
    elif 45 <= final_score < 50:
        status = "Probation"
        next_level = current_level  # Repeat the current level
    
    else:
        status = "Repeat"
        next_level = current_level  # Repeat the current level

    # Update student record
    if status == "Promoted" and next_level != current_level:
        student.last_level_completed = current_level
    
    student.current_level = next_level
    student.academic_status = status
    student.last_score = final_score
    
    return {
        'status': status,
        'current_level': current_level,
        'next_level': next_level,
        'programme': student.programme,
        'score': final_score
    }


def get_next_level(current_level):
    """
    Get the next academic level in the progression.
    
    Args:
        current_level: Current level (100, 200, 300, or 400)
    
    Returns:
        Next level (int) or None if student has graduated (completed Level 400)
    """
    try:
        current_index = LEVEL_PROGRESSION.index(current_level)
        
        # Check if there's a next level
        if current_index + 1 < len(LEVEL_PROGRESSION):
            return LEVEL_PROGRESSION[current_index + 1]
        
        # No more levels - student graduated
        return None
    
    except (ValueError, IndexError):
        return None