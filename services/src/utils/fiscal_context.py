"""
Fiscal Calendar Utility.

Generates a fiscal context statement based on the current date.
Fiscal year runs from November 1 to October 31.

Functions:
    get_fiscal_period: Calculate current fiscal year and quarter
    get_quarter_range_str: Get formatted date range string
    get_fiscal_statement: Generate XML fiscal context statement
"""

import logging
from datetime import datetime
from typing import Tuple

logger = logging.getLogger(__name__)

QUARTER_RANGES = {
    1: "November 1st to January 31st",
    2: "February 1st to April 30th",
    3: "May 1st to July 31st",
    4: "August 1st to October 31st",
}


def get_fiscal_period() -> Tuple[int, int]:
    """
    Calculate current fiscal year and quarter.

    Returns:
        Tuple of (fiscal_year, fiscal_quarter).
    """
    current_date = datetime.now()
    current_month = current_date.month
    calendar_year = current_date.year

    fiscal_year = calendar_year + 1 if current_month >= 11 else calendar_year
    month_adjusted = (current_month - 10) % 12
    fiscal_quarter = (month_adjusted - 1) // 3 + 1

    return fiscal_year, fiscal_quarter


def get_quarter_range_str(fiscal_quarter: int) -> str:
    """
    Get a formatted string describing the date range for a fiscal quarter.

    Args:
        fiscal_quarter: The fiscal quarter (1-4).

    Returns:
        Formatted date range string like "November 1st to January 31st".
    """
    return QUARTER_RANGES.get(fiscal_quarter, "Invalid quarter")


def get_fiscal_statement() -> str:
    """
    Generate a natural language statement about the current fiscal period.

    Uses XML-style delimiters for better sectioning in prompts.

    Returns:
        Formatted fiscal statement with XML tags.
    """
    try:
        current_date = datetime.now()
        formatted_date = current_date.strftime("%Y-%m-%d")
        fiscal_year, fiscal_quarter = get_fiscal_period()
        current_quarter_range = get_quarter_range_str(fiscal_quarter)

        fy_definition = "Our fiscal year runs from November 1st through October 31st."
        statement = f"""<FISCAL_CONTEXT>
<CURRENT_DATE>{formatted_date}</CURRENT_DATE>
<FISCAL_YEAR>{fiscal_year} (FY{fiscal_year})</FISCAL_YEAR>
<FISCAL_QUARTER>{fiscal_quarter} (Q{fiscal_quarter})</FISCAL_QUARTER>
<QUARTER_RANGE>{current_quarter_range}</QUARTER_RANGE>
<FISCAL_YEAR_DEFINITION>{fy_definition}</FISCAL_YEAR_DEFINITION>
</FISCAL_CONTEXT>"""

        return statement
    except (ValueError, TypeError, RuntimeError) as exc:
        logger.warning("Error generating fiscal statement: %s", exc)
        fallback = "We operate on a fiscal year from November 1st through October 31st."
        return f"<FISCAL_CONTEXT>{fallback}</FISCAL_CONTEXT>"
