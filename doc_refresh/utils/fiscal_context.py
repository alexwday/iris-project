"""Fiscal calendar utilities for generating fiscal context statements."""

from datetime import datetime

QUARTER_RANGES = {
    1: "November 1st to January 31st",
    2: "February 1st to April 30th",
    3: "May 1st to July 31st",
    4: "August 1st to October 31st",
}


def _get_fiscal_period() -> tuple[int, int]:
    """Return current (fiscal_year, fiscal_quarter)."""
    now = datetime.now()
    fiscal_year = now.year + 1 if now.month >= 11 else now.year
    fiscal_quarter = ((now.month - 11) % 12) // 3 + 1
    return fiscal_year, fiscal_quarter


def generate_fiscal_context_statement() -> str:
    """Generate XML-formatted statement about current fiscal period."""
    now = datetime.now()
    fy, fq = _get_fiscal_period()
    return f"""<FISCAL_CONTEXT>
<CURRENT_DATE>{now.strftime('%Y-%m-%d')}</CURRENT_DATE>
<FISCAL_YEAR>{fy} (FY{fy})</FISCAL_YEAR>
<FISCAL_QUARTER>{fq} (Q{fq})</FISCAL_QUARTER>
<QUARTER_RANGE>{QUARTER_RANGES[fq]}</QUARTER_RANGE>
<FISCAL_YEAR_DEFINITION>Our fiscal year runs from November 1st through October 31st.</FISCAL_YEAR_DEFINITION>
</FISCAL_CONTEXT>"""
