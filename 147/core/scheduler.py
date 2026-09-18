from datetime import date, timedelta


def calculate_review_dates(start_date: date) -> dict:
    """
    Calculate the Day 1, Day 4 and Day 7 review dates.

    Args:
        start_date: The date on which the material was learned.

    Returns:
        A dictionary containing the three review dates.
    """

    return {
        "day_1": start_date,
        "day_4": start_date + timedelta(days=3),
        "day_7": start_date + timedelta(days=6),
    }