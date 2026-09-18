from datetime import date

from core.review_engine import get_due_reviews


learning_items = [
    {
        "id": 1,
        "content": "Python decorators",
        "created_date": "2026-09-16",
        "reviews": {
            "day_1": {
                "date": "2026-09-16",
                "completed": False
            },
            "day_4": {
                "date": "2026-09-19",
                "completed": False
            },
            "day_7": {
                "date": "2026-09-22",
                "completed": False
            }
        }
    }
]


# --------------------------------
# Test 1: Day 1
# --------------------------------

current_date = date(2026, 9, 16)

due_reviews = get_due_reviews(
    learning_items,
    current_date
)

print("Test 1")
print(due_reviews)
print()


# --------------------------------
# Test 2: Day 4
# --------------------------------

current_date = date(2026, 9, 19)

due_reviews = get_due_reviews(
    learning_items,
    current_date
)

print("Test 2")
print(due_reviews)
print()


# --------------------------------
# Test 3: Day 7
# --------------------------------

current_date = date(2026, 9, 22)

due_reviews = get_due_reviews(
    learning_items,
    current_date
)

print("Test 3")
print(due_reviews)
print()


# --------------------------------
# Test 4: Overdue
# --------------------------------

current_date = date(2026, 9, 23)

due_reviews = get_due_reviews(
    learning_items,
    current_date
)

print("Test 4")
print(due_reviews)