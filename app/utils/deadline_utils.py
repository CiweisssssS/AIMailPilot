"""
Deadline Normalization Utility

Normalizes deadline expressions to "Mon DD, YYYY, HH:mm" format or "TBD"
Follows strict rules for what should be normalized vs. marked as ambiguous.
"""

import re
from datetime import datetime, timedelta
from typing import Optional
import logging
from zoneinfo import ZoneInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


def normalize_deadline(
    text: Optional[str],
    ref_datetime: Optional[datetime] = None,
    tz: str = "UTC",
    sent_date: Optional[datetime] = None
) -> str:
    """
    Normalize deadline text to "Mon DD, YYYY, HH:mm" format or "TBD"
    
    Args:
        text: Raw deadline text (e.g., "by EOD", "Friday 5pm", "Oct 3, 5pm")
        ref_datetime: Reference datetime for relative dates (defaults to now)
        tz: Timezone string (e.g., "America/Los_Angeles", "UTC")
        sent_date: Email sent date for year inference (defaults to ref_datetime)
    
    Returns:
        Normalized deadline string in format "Mon DD, YYYY, HH:mm" or "TBD"
    
    Examples:
        >>> normalize_deadline("by Oct 3, 5pm", ref_datetime, "UTC")
        "Oct 03, 2023, 17:00"
        
        >>> normalize_deadline("by EOD")
        "Oct 21, 2023, 17:00"
        
        >>> normalize_deadline("next week")
        "TBD"
    """
    if not text or not isinstance(text, str):
        return "TBD"
    
    # Get reference datetime with timezone
    if ref_datetime is None:
        try:
            timezone = ZoneInfo(tz)
        except Exception:
            timezone = ZoneInfo("UTC")
        ref_datetime = datetime.now(timezone)
    elif ref_datetime.tzinfo is None:
        try:
            timezone = ZoneInfo(tz)
            ref_datetime = ref_datetime.replace(tzinfo=timezone)
        except Exception:
            ref_datetime = ref_datetime.replace(tzinfo=ZoneInfo("UTC"))
    
    # Use sent_date for year inference if provided, otherwise use ref_datetime
    year_ref = sent_date if sent_date is not None else ref_datetime
    if year_ref.tzinfo is None:
        year_ref = year_ref.replace(tzinfo=ref_datetime.tzinfo)
    
    text = text.strip().lower()
    
    # Check for ambiguous expressions - return TBD immediately
    # Note: Exclude "end of ..." variants which are now handled explicitly
    ambiguous_patterns = [
        r'(?<!end\s+of\s)\bnext\s+week\b',  # Exclude "end of next week"
        r'\bearly\s+next\s+week\b',
        r'(?<!end\s+of\s)\blater\s+this\s+month\b',  # Exclude "end of this month" context
        r'(?<!end\s+of\s)(?<!end\s+of\s+the\s)\bthis\s+quarter\b',  # Exclude "end of this quarter"
        r'\basap\b',
        r'\bimmediately\b',
        r'\bat\s+your\s+earliest\s+convenience\b',
        r'\baround\b',
        r'\bsometime\b',
        r'\broughly\b',
        r'\d+[-–]\d+',  # date ranges like "Oct 3-5" or "3–5"
        r'\bby\s+tomorrow\b(?!\s+(morning|afternoon|evening|noon|\d))',  # "by tomorrow" without time
    ]
    
    for pattern in ambiguous_patterns:
        if re.search(pattern, text):
            logger.debug(f"Ambiguous deadline detected: '{text}' matches pattern '{pattern}'")
            return "TBD"
    
    # Check for "today" with explicit time BEFORE EOD patterns
    # Pattern 1: "today 3pm", "today at 15:00", etc. (today first)
    today_time_match = re.search(
        r'\btoday\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
        text
    )
    # Pattern 2: "3pm today", "4pm today", "by 4pm today" (time first)
    if not today_time_match:
        today_time_match = re.search(
            r'(?:by\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+today\b',
            text
        )
    
    if today_time_match:
        hour = int(today_time_match.group(1))
        minute = int(today_time_match.group(2)) if today_time_match.group(2) else 0
        modifier = today_time_match.group(3)
        
        if modifier == "pm" and hour < 12:
            hour += 12
        elif modifier == "am" and hour == 12:
            hour = 0
        
        deadline = ref_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
        logger.info(f"Matched time + today: text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # EOD/COB synonyms - today at work_end_hour (only if no explicit time)
    eod_patterns = [
        r'\beod\b', r'\bend\s+of\s+day\b', r'\bcob\b', 
        r'\bclose\s+of\s+business\b', r'\btonight\b'
    ]
    # Only match "today" if it's standalone (no time follows)
    if re.search(r'\btoday\b(?!\s+\d)', text):
        deadline = ref_datetime.replace(hour=settings.work_end_hour, minute=0, second=0, microsecond=0)
        return format_deadline(deadline)
    
    for pattern in eod_patterns:
        if re.search(pattern, text):
            deadline = ref_datetime.replace(hour=settings.work_end_hour, minute=0, second=0, microsecond=0)
            return format_deadline(deadline)
    
    # "End of ..." patterns (handle before generic tomorrow/week patterns)
    # 1. End of today
    if re.search(r'\bend\s+of\s+today\b', text) or re.search(r'\bby\s+the\s+end\s+of\s+today\b', text):
        deadline = ref_datetime.replace(hour=settings.work_end_hour, minute=0, second=0, microsecond=0)
        logger.info(f"Matched 'end of today': text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # 2. End of tomorrow / tomorrow EOD
    if (re.search(r'\bend\s+of\s+tomorrow\b', text) or 
        re.search(r'\bby\s+the\s+end\s+of\s+tomorrow\b', text) or
        re.search(r'\btomorrow\s+eod\b', text)):
        tomorrow = ref_datetime + timedelta(days=1)
        deadline = tomorrow.replace(hour=settings.work_end_hour, minute=0, second=0, microsecond=0)
        logger.info(f"Matched 'end of tomorrow': text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # 3. End of <weekday> (e.g., "end of Friday", "by Friday EOD")
    end_of_weekday_match = re.search(
        r'(?:end\s+of\s+|by\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+eod\b',
        text
    )
    if not end_of_weekday_match:
        end_of_weekday_match = re.search(
            r'\bend\s+of\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            text
        )
    
    if end_of_weekday_match:
        weekday_name = end_of_weekday_match.group(1)
        target_weekday = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }.get(weekday_name)
        
        if target_weekday is not None:
            current_weekday = ref_datetime.weekday()
            days_ahead = (target_weekday - current_weekday) % 7
            
            if days_ahead == 0:
                days_ahead = 7  # Next occurrence
            
            target_date = ref_datetime + timedelta(days=days_ahead)
            deadline = target_date.replace(hour=settings.work_end_hour, minute=0, second=0, microsecond=0)
            logger.info(f"Matched 'end of weekday': text='{text}' -> {format_deadline(deadline)}")
            return format_deadline(deadline)
    
    # 4. End of this week / EOW
    if (re.search(r'\bend\s+of\s+this\s+week\b', text) or 
        re.search(r'\bby\s+the\s+end\s+of\s+this\s+week\b', text) or
        re.search(r'\beow\b', text) or
        re.search(r'\bbefore\s+the\s+week\s+ends\b', text)):
        deadline = calculate_end_of_week(ref_datetime, weeks_ahead=0)
        logger.info(f"Matched 'end of this week': text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # 5. End of next week
    if re.search(r'\bend\s+of\s+next\s+week\b', text):
        deadline = calculate_end_of_week(ref_datetime, weeks_ahead=1)
        logger.info(f"Matched 'end of next week': text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # 6. End of this month
    if (re.search(r'\bend\s+of\s+this\s+month\b', text) or 
        re.search(r'\bby\s+the\s+end\s+of\s+this\s+month\b', text)):
        deadline = calculate_end_of_month(ref_datetime, months_ahead=0)
        logger.info(f"Matched 'end of this month': text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # 7. End of next month
    if (re.search(r'\bend\s+of\s+next\s+month\b', text) or 
        re.search(r'\bby\s+the\s+end\s+of\s+next\s+month\b', text)):
        deadline = calculate_end_of_month(ref_datetime, months_ahead=1)
        logger.info(f"Matched 'end of next month': text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # 8. End of this quarter / end of the quarter
    if (re.search(r'\bend\s+of\s+this\s+quarter\b', text) or 
        re.search(r'\bend\s+of\s+the\s+quarter\b', text) or
        re.search(r'\bby\s+the\s+end\s+of\s+this\s+quarter\b', text)):
        deadline = calculate_end_of_quarter(ref_datetime)
        logger.info(f"Matched 'end of quarter': text='{text}' -> {format_deadline(deadline)}")
        return format_deadline(deadline)
    
    # Tomorrow with specific time
    # Pattern 1: "tomorrow 3pm" (tomorrow first)
    tomorrow_time_match = re.search(
        r'\btomorrow\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|noon|morning|afternoon|evening)?',
        text
    )
    # Pattern 2: "3pm tomorrow", "by 4pm tomorrow" (time first)
    if not tomorrow_time_match:
        tomorrow_time_match = re.search(
            r'(?:by\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+tomorrow\b',
            text
        )
    
    if tomorrow_time_match:
        hour = int(tomorrow_time_match.group(1))
        minute = int(tomorrow_time_match.group(2)) if tomorrow_time_match.group(2) else 0
        modifier = tomorrow_time_match.group(3)
        
        if modifier == "pm" and hour < 12:
            hour += 12
        elif modifier == "am" and hour == 12:
            hour = 0
        
        tomorrow = ref_datetime + timedelta(days=1)
        deadline = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return format_deadline(deadline)
    
    # Tomorrow with time-of-day (morning/noon/evening)
    tomorrow_tod_match = re.search(r'\btomorrow\s+(morning|noon|afternoon|evening)\b', text)
    if tomorrow_tod_match:
        tod = tomorrow_tod_match.group(1)
        hour = {
            'morning': 9,
            'noon': 12,
            'afternoon': 15,
            'evening': 18
        }.get(tod, 12)
        
        tomorrow = ref_datetime + timedelta(days=1)
        deadline = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
        return format_deadline(deadline)
    
    # Explicit date with time: "Oct 3, 5pm", "Oct 27 at 10am", "October 10, 17:00", "by Oct 3, 5pm"
    # Pattern 1: "Month DD at HH:mm" or "Month DD at HH am/pm"
    date_time_match = re.search(
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
        text
    )
    # Pattern 2: "Month DD, HH:mm" or "Month DD HH:mm" (no "at")
    if not date_time_match:
        date_time_match = re.search(
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:,?\s+|,\s+)(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
            text
        )
    
    if date_time_match:
        month_abbr = date_time_match.group(1)
        day = int(date_time_match.group(2))
        hour = int(date_time_match.group(3))
        minute = int(date_time_match.group(4)) if date_time_match.group(4) else 0
        am_pm = date_time_match.group(5)
        
        if am_pm == "pm" and hour < 12:
            hour += 12
        elif am_pm == "am" and hour == 12:
            hour = 0
        
        month = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }.get(month_abbr, ref_datetime.month)
        
        # Determine year - use year_ref (email sent date) for comparison
        year = year_ref.year
        try:
            deadline = ref_datetime.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if deadline < year_ref:
                deadline = deadline.replace(year=year + 1)
        except ValueError:
            return "TBD"
        
        return format_deadline(deadline)
    
    # Explicit date without time: "by October 10", "Oct 15"
    date_only_match = re.search(
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b',
        text
    )
    if date_only_match:
        month_abbr = date_only_match.group(1)
        day = int(date_only_match.group(2))
        
        month = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }.get(month_abbr, ref_datetime.month)
        
        # Default to work_end_hour
        year = year_ref.year
        try:
            deadline = ref_datetime.replace(year=year, month=month, day=day, hour=settings.work_end_hour, minute=0, second=0, microsecond=0)
            if deadline < year_ref:
                deadline = deadline.replace(year=year + 1)
        except ValueError:
            return "TBD"
        
        return format_deadline(deadline)
    
    # Weekday: "by Friday", "Friday 5pm", "next Friday"
    # Pattern 1: "Friday 5pm" (weekday first)
    weekday_match = re.search(
        r'(?:by\s+|next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?',
        text
    )
    # Pattern 2: "5pm Friday", "by 4pm Friday" (time first)
    if not weekday_match:
        weekday_match = re.search(
            r'(?:by\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            text
        )
        # If matched, reorder groups to match the expected format
        # Group 1 becomes the weekday, groups 2-4 become time components
        if weekday_match:
            # Extract values
            hour_val = weekday_match.group(1)
            minute_val = weekday_match.group(2)
            am_pm_val = weekday_match.group(3)
            weekday_val = weekday_match.group(4)
            # Create a mock match object with reordered groups
            class MockMatch:
                def __init__(self, weekday, hour, minute, am_pm):
                    self._groups = (weekday, hour, minute, am_pm)
                def group(self, n):
                    return self._groups[n-1] if 1 <= n <= len(self._groups) else None
            weekday_match = MockMatch(weekday_val, hour_val, minute_val, am_pm_val)
    
    if weekday_match:
        weekday_name = weekday_match.group(1)
        target_weekday = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }.get(weekday_name) if weekday_name else None
        
        if target_weekday is not None:
            current_weekday = ref_datetime.weekday()
            days_ahead = (target_weekday - current_weekday) % 7
            
            # If today is the target weekday and it's still early, use today
            # Otherwise use next occurrence
            if days_ahead == 0:
                days_ahead = 7
            
            target_date = ref_datetime + timedelta(days=days_ahead)
            
            # Check if time is specified
            hour_str = weekday_match.group(2)
            if hour_str:
                hour = int(hour_str)
                minute_str = weekday_match.group(3)
                minute = int(minute_str) if minute_str else 0
                am_pm = weekday_match.group(4)
                
                if am_pm == "pm" and hour < 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0
                
                deadline = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # No time specified - default to work_end_hour
                deadline = target_date.replace(hour=settings.work_end_hour, minute=0, second=0, microsecond=0)
            
            return format_deadline(deadline)
    
    # If no pattern matched, return TBD
    logger.debug(f"No pattern matched for deadline: '{text}'")
    return "TBD"


def calculate_end_of_week(ref_dt: datetime, weeks_ahead: int = 0) -> datetime:
    """
    Calculate Friday at WORK_END_HOUR for the target week.
    
    Args:
        ref_dt: Reference datetime
        weeks_ahead: 0 for this week, 1 for next week
    
    Returns:
        Friday of target week at WORK_END_HOUR
    """
    current_weekday = ref_dt.weekday()  # Monday=0, Sunday=6
    friday = 4  # Friday
    
    # Days until Friday of this week
    days_to_friday = (friday - current_weekday) % 7
    if days_to_friday == 0 and current_weekday != friday:
        days_to_friday = 0  # We're on Friday
    
    # Add weeks
    total_days = days_to_friday + (weeks_ahead * 7)
    
    target_date = ref_dt + timedelta(days=total_days)
    return target_date.replace(hour=settings.work_end_hour, minute=0, second=0, microsecond=0)


def calculate_end_of_month(ref_dt: datetime, months_ahead: int = 0) -> datetime:
    """
    Calculate last day of target month at WORK_END_HOUR.
    
    Args:
        ref_dt: Reference datetime
        months_ahead: 0 for this month, 1 for next month
    
    Returns:
        Last day of target month at WORK_END_HOUR
    """
    import calendar
    
    # Calculate target month and year
    target_month = ref_dt.month + months_ahead
    target_year = ref_dt.year
    
    while target_month > 12:
        target_month -= 12
        target_year += 1
    
    # Get last day of target month
    last_day = calendar.monthrange(target_year, target_month)[1]
    
    return ref_dt.replace(
        year=target_year,
        month=target_month,
        day=last_day,
        hour=settings.work_end_hour,
        minute=0,
        second=0,
        microsecond=0
    )


def calculate_end_of_quarter(ref_dt: datetime) -> datetime:
    """
    Calculate last day of current quarter at WORK_END_HOUR.
    
    Quarters:
    - Q1: Jan-Mar (ends Mar 31)
    - Q2: Apr-Jun (ends Jun 30)
    - Q3: Jul-Sep (ends Sep 30)
    - Q4: Oct-Dec (ends Dec 31)
    
    Args:
        ref_dt: Reference datetime
    
    Returns:
        Last day of current quarter at WORK_END_HOUR
    """
    current_month = ref_dt.month
    
    # Determine quarter end month and day
    if current_month <= 3:
        # Q1
        end_month, end_day = 3, 31
    elif current_month <= 6:
        # Q2
        end_month, end_day = 6, 30
    elif current_month <= 9:
        # Q3
        end_month, end_day = 9, 30
    else:
        # Q4
        end_month, end_day = 12, 31
    
    return ref_dt.replace(
        month=end_month,
        day=end_day,
        hour=settings.work_end_hour,
        minute=0,
        second=0,
        microsecond=0
    )


def format_deadline(dt: datetime) -> str:
    """
    Format datetime to "Mon DD, YYYY, HH:mm"
    
    Args:
        dt: datetime object
    
    Returns:
        Formatted string like "Oct 21, 2023, 17:00"
    """
    return dt.strftime("%b %d, %Y, %H:%M")
