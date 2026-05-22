from datetime import date
from datetime import datetime
import calendar
import re

class AgeCalculator:
    DATE_FORMAT = "%d.%m.%Y"

    def __init__(self, birth_date: date):
        if not isinstance(birth_date, date):
            raise TypeError("birth_date должен быть объектом datetime.date")
        today = date.today()
        if birth_date > today:
            raise ValueError("Дата рождения не может быть в будущем")
        self.birth_date = birth_date

    @classmethod
    def from_string(cls, date_str: str) -> AgeCalculator:
        date_str = date_str.strip()
        if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", date_str):
            raise ValueError(f"Неверный формат даты. Ожидается ДД.ММ.ГГГГ, получено '{date_str}'")
        try:
            birth_date = datetime.strptime(date_str, cls.DATE_FORMAT).date()
        except ValueError:
            raise ValueError(f"Некорректная дата '{date_str}'")
        return cls(birth_date)

    def calculate(self) -> dict:
        today = date.today()
        years = today.year - self.birth_date.year
        birthday_this_year = self.birth_date.replace(year=today.year)
        if birthday_this_year > today:
            years -= 1
            birthday_this_year = self.birth_date.replace(year=today.year - 1)
        remaining_start = birthday_this_year
        months = 0
        while True:
            m = remaining_start.month + 1
            y = remaining_start.year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            try:
                next_month = remaining_start.replace(year=y, month=m)
            except ValueError:
                last_day = calendar.monthrange(y, m)[1]
                next_month = date(y, m, last_day)
            if next_month > today:
                break
            months += 1
            remaining_start = next_month
        days = (today - remaining_start).days
        total_days = (today - self.birth_date).days
        return {"years": years, "months": months, "days": days, "total_days": total_days}

    def __str__(self) -> str:
        a = self.calculate()
        return (
            f"Дата рождения: {self.birth_date.strftime(self.DATE_FORMAT)}\n"
            f"Возраст: {a['years']} лет, {a['months']} мес., {a['days']} дн.\n"
            f"Всего дней: {a['total_days']}"
        )

def main():
    while True:
        raw = input("Введите дату рождения (ДД.ММ.ГГГГ) или 'выход': ").strip()
        if raw.lower() in ("выход", "exit", "q"):
            break
        try:
            calc = AgeCalculator.from_string(raw)
            print(calc)
        except (ValueError, TypeError) as e:
            print(f"Ошибка: {e}")
        print()

if __name__ == "__main__":
    main()
