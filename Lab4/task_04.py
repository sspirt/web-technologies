from datetime import date, datetime, timedelta
import calendar

class SmartDate:
    value: date

    def __init__(self, value: str | date | datetime) -> None:
        self.value = self._parse_date(value)

    @staticmethod
    def _parse_date(value: str | date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            value = value.strip()
            for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(value, pattern).date()
                except ValueError:
                    continue
            raise ValueError("Unsupported date format, use YYYY-MM-DD, DD-MM-YYYY or DD.MM.YYYY")
        raise TypeError("Value must be a string, date, or datetime")

    def is_weekend(self) -> bool:
        return self.value.weekday() >= 5

    def distance_from_today(self, unit: str = "days") -> int | float:
        if not isinstance(unit, str):
            raise TypeError("Unit must be a string")
        unit = unit.strip().lower()
        delta: timedelta = self.value - date.today()
        days = delta.days
        conversions = {
            "days": days,
            "weeks": days / 7,
            "months": days / 30.44,
            "years": days / 365.25,
        }
        if unit not in conversions:
            raise ValueError("Unit must be one of: days, weeks, months, years")
        return conversions[unit]

    def is_leap_year(self) -> bool:
        return calendar.isleap(self.value.year)

if __name__ == "__main__":
    smart_date = SmartDate("29.02.2020")
    print("Weekend:", smart_date.is_weekend())
    print("Distance in days:", smart_date.distance_from_today())
    print("Leap year:", smart_date.is_leap_year())