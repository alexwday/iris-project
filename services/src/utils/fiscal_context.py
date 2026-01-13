"""Fiscal calendar utilities for generating fiscal context statements."""

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


def calculate_current_fiscal_period() -> Tuple[int, int]:
    """Calculate the current fiscal year and quarter.

    Returns:
        Tuple[int, int]: Fiscal year and fiscal quarter.
    """
    current_date = datetime.now()
    current_month = current_date.month
    calendar_year = current_date.year

    fiscal_year = calendar_year + 1 if current_month >= 11 else calendar_year
    month_offset = (current_month - 11) % 12
    fiscal_quarter = month_offset // 3 + 1

    return fiscal_year, fiscal_quarter


def format_fiscal_quarter_range(fiscal_quarter: int) -> str:
    """Return the date range covered by a fiscal quarter.

    Args:
        fiscal_quarter (int): Fiscal quarter (1-4).

    Returns:
        str: Formatted date range (e.g., "November 1st to January 31st").
    """
    return QUARTER_RANGES.get(fiscal_quarter, "Invalid quarter")


def generate_fiscal_context_statement() -> str:
    """Generate an XML-formatted statement about the current fiscal period.

    Returns:
        str: Fiscal statement with XML tags.
    """
    try:
        current_date = datetime.now()
        formatted_date = current_date.strftime("%Y-%m-%d")
        fiscal_year, fiscal_quarter = calculate_current_fiscal_period()
        current_quarter_range = format_fiscal_quarter_range(fiscal_quarter)

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
