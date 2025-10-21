"""
Unit tests for deadline normalization utility
"""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from app.utils.deadline_utils import normalize_deadline, format_deadline


class TestNormalizeDeadline:
    """Test cases for normalize_deadline function"""
    
    def setup_method(self):
        """Setup common test data"""
        # Use a fixed reference date for consistent testing
        # October 21, 2023, 10:00 AM UTC (Saturday)
        self.ref_dt = datetime(2023, 10, 21, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
    
    # ===== Ambiguous Cases - Should Return TBD =====
    
    def test_next_week_returns_tbd(self):
        assert normalize_deadline("next week", self.ref_dt) == "TBD"
        assert normalize_deadline("early next week", self.ref_dt) == "TBD"
    
    def test_later_this_month_returns_tbd(self):
        assert normalize_deadline("later this month", self.ref_dt) == "TBD"
    
    def test_this_quarter_returns_tbd(self):
        assert normalize_deadline("this quarter", self.ref_dt) == "TBD"
    
    def test_asap_returns_tbd(self):
        assert normalize_deadline("ASAP", self.ref_dt) == "TBD"
        assert normalize_deadline("asap", self.ref_dt) == "TBD"
    
    def test_immediately_returns_tbd(self):
        assert normalize_deadline("immediately", self.ref_dt) == "TBD"
    
    def test_at_earliest_convenience_returns_tbd(self):
        assert normalize_deadline("at your earliest convenience", self.ref_dt) == "TBD"
    
    def test_by_tomorrow_without_time_returns_tbd(self):
        # "by tomorrow" without specific time is ambiguous
        assert normalize_deadline("by tomorrow", self.ref_dt) == "TBD"
    
    def test_date_ranges_return_tbd(self):
        assert normalize_deadline("Oct 3-5", self.ref_dt) == "TBD"
        assert normalize_deadline("October 3–5", self.ref_dt) == "TBD"
    
    def test_vague_expressions_return_tbd(self):
        assert normalize_deadline("around next Monday", self.ref_dt) == "TBD"
        assert normalize_deadline("sometime this week", self.ref_dt) == "TBD"
        assert normalize_deadline("roughly Friday", self.ref_dt) == "TBD"
    
    # ===== EOD/COB Synonyms - Should Normalize to Today 23:59 =====
    
    def test_eod_normalizes_to_today_eod(self):
        result = normalize_deadline("by EOD", self.ref_dt)
        assert result == "Oct 21, 2023, 23:59"
    
    def test_end_of_day_normalizes(self):
        result = normalize_deadline("by end of day", self.ref_dt)
        assert result == "Oct 21, 2023, 23:59"
    
    def test_cob_normalizes(self):
        result = normalize_deadline("COB", self.ref_dt)
        assert result == "Oct 21, 2023, 23:59"
    
    def test_today_normalizes(self):
        result = normalize_deadline("today", self.ref_dt)
        assert result == "Oct 21, 2023, 23:59"
    
    def test_tonight_normalizes(self):
        result = normalize_deadline("tonight", self.ref_dt)
        assert result == "Oct 21, 2023, 23:59"
    
    def test_today_with_explicit_time_pm(self):
        result = normalize_deadline("today 3pm", self.ref_dt)
        assert result == "Oct 21, 2023, 15:00"
    
    def test_today_with_explicit_time_am(self):
        result = normalize_deadline("today 9am", self.ref_dt)
        assert result == "Oct 21, 2023, 09:00"
    
    def test_today_at_time(self):
        result = normalize_deadline("today at 14:30", self.ref_dt)
        assert result == "Oct 21, 2023, 14:30"
    
    # ===== Tomorrow with Specific Time =====
    
    def test_tomorrow_noon(self):
        result = normalize_deadline("tomorrow noon", self.ref_dt)
        assert result == "Oct 22, 2023, 12:00"
    
    def test_tomorrow_morning(self):
        result = normalize_deadline("tomorrow morning", self.ref_dt)
        assert result == "Oct 22, 2023, 09:00"
    
    def test_tomorrow_evening(self):
        result = normalize_deadline("tomorrow evening", self.ref_dt)
        assert result == "Oct 22, 2023, 18:00"
    
    def test_tomorrow_afternoon(self):
        result = normalize_deadline("tomorrow afternoon", self.ref_dt)
        assert result == "Oct 22, 2023, 15:00"
    
    def test_tomorrow_with_hour(self):
        result = normalize_deadline("tomorrow 5pm", self.ref_dt)
        assert result == "Oct 22, 2023, 17:00"
    
    def test_tomorrow_with_hour_am(self):
        result = normalize_deadline("tomorrow 9am", self.ref_dt)
        assert result == "Oct 22, 2023, 09:00"
    
    def test_tomorrow_with_time_colon(self):
        result = normalize_deadline("tomorrow at 3:30pm", self.ref_dt)
        assert result == "Oct 22, 2023, 15:30"
    
    # ===== Explicit Date with Time =====
    
    def test_explicit_date_with_time_pm(self):
        result = normalize_deadline("by Oct 3, 5pm", self.ref_dt)
        # Oct 3 is before ref date, should use next year
        assert result == "Oct 03, 2024, 17:00"
    
    def test_explicit_date_with_time_am(self):
        result = normalize_deadline("Nov 15, 9am", self.ref_dt)
        assert result == "Nov 15, 2023, 09:00"
    
    def test_explicit_date_with_time_24h(self):
        result = normalize_deadline("December 1, 14:30", self.ref_dt)
        assert result == "Dec 01, 2023, 14:30"
    
    # ===== Explicit Date without Time (Defaults to EOD) =====
    
    def test_explicit_date_no_time(self):
        result = normalize_deadline("by October 10", self.ref_dt)
        # Oct 10 is before ref date, should use next year
        assert result == "Oct 10, 2024, 23:59"
    
    def test_explicit_date_future_no_time(self):
        result = normalize_deadline("November 25", self.ref_dt)
        assert result == "Nov 25, 2023, 23:59"
    
    # ===== Weekday Tests =====
    
    def test_weekday_friday(self):
        # Ref date is Saturday Oct 21, next Friday is Oct 27
        result = normalize_deadline("by Friday", self.ref_dt)
        assert result == "Oct 27, 2023, 23:59"
    
    def test_weekday_monday(self):
        # Ref date is Saturday Oct 21, next Monday is Oct 23
        result = normalize_deadline("Monday", self.ref_dt)
        assert result == "Oct 23, 2023, 23:59"
    
    def test_weekday_with_time(self):
        result = normalize_deadline("Friday 2pm", self.ref_dt)
        assert result == "Oct 27, 2023, 14:00"
    
    def test_weekday_with_time_am(self):
        result = normalize_deadline("Tuesday 10:30am", self.ref_dt)
        assert result == "Oct 24, 2023, 10:30"
    
    def test_next_weekday(self):
        result = normalize_deadline("next Wednesday", self.ref_dt)
        assert result == "Oct 25, 2023, 23:59"
    
    # ===== Edge Cases =====
    
    def test_empty_string_returns_tbd(self):
        assert normalize_deadline("", self.ref_dt) == "TBD"
    
    def test_none_returns_tbd(self):
        assert normalize_deadline(None, self.ref_dt) == "TBD"
    
    def test_whitespace_only_returns_tbd(self):
        assert normalize_deadline("   ", self.ref_dt) == "TBD"
    
    def test_unrecognized_text_returns_tbd(self):
        assert normalize_deadline("whenever you can", self.ref_dt) == "TBD"
        assert normalize_deadline("random text", self.ref_dt) == "TBD"
    
    # ===== Format Tests =====
    
    def test_format_deadline(self):
        dt = datetime(2023, 10, 5, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert format_deadline(dt) == "Oct 05, 2023, 10:00"
    
    def test_format_deadline_with_minutes(self):
        dt = datetime(2023, 12, 25, 14, 30, 0, tzinfo=ZoneInfo("UTC"))
        assert format_deadline(dt) == "Dec 25, 2023, 14:30"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
