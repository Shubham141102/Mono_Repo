from datetime import date

from core.scheduler import calculate_review_dates


start_date = date(2026, 9, 1)

review_dates = calculate_review_dates(start_date)

print("Start Date:", review_dates["day_1"])
print("Day 4:", review_dates["day_4"])
print("Day 7:", review_dates["day_7"])