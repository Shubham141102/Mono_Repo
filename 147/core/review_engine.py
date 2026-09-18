from datetime import date
from typing import List


def get_due_reviews(
    learning_items: List[dict],
    current_date: date
) -> List[dict]:
    """
    Return all reviews that are due on or before the current date
    and have not yet been completed.

    Args:
        learning_items: All saved learning items.
        current_date: Date against which reviews are checked.

    Returns:
        A list of due review records.
    """

    due_reviews = []

    for item in learning_items:

        reviews = item.get("reviews", {})

        for review_day, review_data in reviews.items():

            review_date = date.fromisoformat(
                review_data["date"]
            )

            completed = review_data.get(
                "completed",
                False
            )

            # Review is due if:
            # 1. It has not been completed
            # 2. Its scheduled date is today or earlier
            if not completed and review_date <= current_date:

                due_reviews.append(
                    {
                        "learning_id": item["id"],
                        "content": item["content"],
                        "review_day": review_day,
                        "review_date": review_data["date"],
                        "completed": completed
                    }
                )

    return due_reviews