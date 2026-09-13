"""
Grade Lookup Service
====================
Converts numeric scores to letter grades using the GradingScale model.
This service provides simple lookups - all calculation logic is in GradingCalculationEngine.
"""

from models import GradingScale


class GradeService:
    """
    Service for looking up letter grades based on numeric scores.
    Uses the GradingScale model for configurable grading boundaries.
    """

    @staticmethod
    def get_grade(percent):
        """
        Get letter grade object for a percentage score.
        
        Args:
            percent: Score as percentage (0-100)
            
        Returns:
            GradingScale object with grade details, or None if no match
            
        Example:
            85.4 → GradingScale(grade_letter='B+', grade_point=3.3, min_score=85, max_score=89)
        """
        if percent is None:
            return None

        return (
            GradingScale.query
            .filter(GradingScale.min_score <= percent)
            .filter(GradingScale.max_score >= percent)
            .first()
        )

    @staticmethod
    def get_all_grades():
        """
        Get all grading scale entries ordered by score (highest first).
        Useful for displaying all grading boundaries to users.
        
        Returns:
            List of GradingScale objects ordered by min_score descending
        """
        return GradingScale.query.order_by(GradingScale.min_score.desc()).all()

    @staticmethod
    def get_grade_by_letter(letter):
        """
        Get grading scale entry by letter grade.
        
        Args:
            letter: Grade letter (e.g., 'A', 'B+', 'C')
            
        Returns:
            GradingScale object or None if not found
        """
        return GradingScale.query.filter_by(grade_letter=letter).first()
