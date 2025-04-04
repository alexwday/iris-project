# global_prompts/fiscal_calendar.py
"""
Fiscal Calendar Utility

Generates a fiscal context statement based on the current date.
Fiscal year runs from November 1 to October 31.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_fiscal_period() -> Tuple[int, int]:
    """
    Calculate current fiscal year and quarter.

    Returns:
        Tuple[int, int]: Fiscal year and quarter
    """
    current_date = datetime.now()
    current_month = current_date.month
    calendar_year = current_date.year

    # If we're in Nov or Dec, we're in the next fiscal year
    fiscal_year = calendar_year + 1 if current_month >= 11 else calendar_year

    # Calculate fiscal quarter (Nov-Jan = Q1, Feb-Apr = Q2, May-Jul = Q3, Aug-Oct = Q4)
    month_adjusted = (current_month - 10) % 12  # Shift months to align with fiscal year
    fiscal_quarter = (month_adjusted - 1) // 3 + 1

    return fiscal_year, fiscal_quarter


def get_quarter_dates(fiscal_year: int, fiscal_quarter: int) -> Dict[str, datetime]:
    """
    Calculate the start and end dates for a given fiscal quarter.

    Args:
        fiscal_year (int): The fiscal year
        fiscal_quarter (int): The fiscal quarter (1-4)

    Returns:
        Dict[str, datetime]: Dictionary containing start and end dates
    """
    if fiscal_quarter < 1 or fiscal_quarter > 4:
        raise ValueError(
            f"Invalid fiscal quarter: {fiscal_quarter}. Must be between 1 and 4."
        )

    # Calculate the calendar year for the start date
    calendar_start_year = fiscal_year - 1 if fiscal_quarter == 1 else fiscal_year

    # Map fiscal quarters to their start months in the calendar year
    quarter_start_months = {
        1: 11,  # Nov (previous calendar year)
        2: 2,  # Feb
        3: 5,  # May
        4: 8,  # Aug
    }

    # Map fiscal quarters to their end months in the calendar year
    quarter_end_months = {
        1: 1,  # Jan
        2: 4,  # Apr
        3: 7,  # Jul
        4: 10,  # Oct
    }

    # Calculate start date (first day of the quarter's first month)
    start_month = quarter_start_months[fiscal_quarter]
    start_year = calendar_start_year
    start_date = datetime(start_year, start_month, 1)

    # Calculate end date (last day of the quarter's last month)
    end_month = quarter_end_months[fiscal_quarter]
    end_year = fiscal_year

    # Get the last day of the month
    if end_month == 12:
        end_date = datetime(end_year, end_month, 31)
    else:
        # Get the first day of next month and subtract one day
        next_month = end_month + 1
        next_month_year = end_year
        if next_month > 12:
            next_month = 1
            next_month_year += 1
        end_date = datetime(next_month_year, next_month, 1) - timedelta(days=1)

    return {"start_date": start_date, "end_date": end_date}


def get_quarter_range_str(fiscal_quarter: int) -> str:
    """
    Get a formatted string describing the date range for a fiscal quarter.

    Args:
        fiscal_quarter (int): The fiscal quarter (1-4)

    Returns:
        str: Formatted date range string
    """
    quarter_ranges = {
        1: "November 1st to January 31st",
        2: "February 1st to April 30th",
        3: "May 1st to July 31st",
        4: "August 1st to October 31st",
    }

    return quarter_ranges.get(fiscal_quarter, "Invalid quarter")


def get_fiscal_statement() -> str:
    """
    Generate a natural language statement about the current fiscal period.

    Returns:
        str: Formatted fiscal statement
    """
    try:
        current_date = datetime.now()
        formatted_date = current_date.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD
        fiscal_year, fiscal_quarter = get_fiscal_period()
        current_quarter_range = get_quarter_range_str(fiscal_quarter)

        statement = f"""Today's date is {formatted_date}. We are currently operating in Fiscal Year {fiscal_year} (FY{fiscal_year}), Quarter {fiscal_quarter} (Q{fiscal_quarter}), which spans {current_quarter_range}. Our fiscal year runs from November 1st through October 31st."""

        return statement
    except Exception as e:
        logger.error(f"Error generating fiscal statement: {str(e)}")
        # Fallback statement in case of errors
        return "We operate on a fiscal year that runs from November 1st through October 31st."
