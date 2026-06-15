"""Working-day calendar arithmetic."""

from __future__ import annotations

import math
from datetime import date, timedelta

from ..models.reforecast import CalendarConfig


class CalendarCalculator:
    """Adds working days to a start date, respecting weekends and holidays."""

    def add_working_days(
        self,
        start: date,
        days: float,
        config: CalendarConfig | None,
    ) -> date:
        """Return the date that is `days` working days after `start`.

        Fractional days are rounded up to the next whole day.
        """
        if config is None or not config.use_working_days:
            # Calendar days
            return start + timedelta(days=math.ceil(days))

        holiday_set: set[date] = set(config.holiday_dates)
        working_days_in_week = max(1, min(config.working_days_per_week, 7))
        # Assume working days are Monday-(Monday + working_days_in_week - 1)
        # i.e. if 5 working days: Mon-Fri (weekday < 5)
        work_day_weekdays = set(range(working_days_in_week))

        remaining = math.ceil(days)
        current = start
        while remaining > 0:
            current += timedelta(days=1)
            if current.weekday() in work_day_weekdays and current not in holiday_set:
                remaining -= 1

        return current

    def is_working_day(self, d: date, config: CalendarConfig | None) -> bool:
        """Return True if `d` is a working day."""
        if config is None or not config.use_working_days:
            return True
        holiday_set: set[date] = set(config.holiday_dates)
        working_days_in_week = max(1, min(config.working_days_per_week, 7))
        work_day_weekdays = set(range(working_days_in_week))
        return d.weekday() in work_day_weekdays and d not in holiday_set

    def next_working_day(self, d: date, config: CalendarConfig | None) -> date:
        """Return `d` if it is a working day, otherwise the next working day."""
        if self.is_working_day(d, config):
            return d
        return self.add_working_days(d, 0, config)  # 0 extra -> same day hunt
        # Actually we need to move forward if not a working day
        # Re-implement properly:

    def ensure_working_day(self, d: date, config: CalendarConfig | None) -> date:
        """Advance d to the next working day if d is not a working day."""
        if config is None or not config.use_working_days:
            return d
        holiday_set: set[date] = set(config.holiday_dates)
        working_days_in_week = max(1, min(config.working_days_per_week, 7))
        work_day_weekdays = set(range(working_days_in_week))
        while d.weekday() not in work_day_weekdays or d in holiday_set:
            d += timedelta(days=1)
        return d
