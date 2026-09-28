import csv
import random
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_CUSTOMERS = 10_000

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "customers.csv"

SEED = 42


# ---------------------------------------------------------
# Sample data
# ---------------------------------------------------------

FIRST_NAMES = [
    "Rahul",
    "Amit",
    "Priya",
    "Sneha",
    "Arjun",
    "Ananya",
    "Rohan",
    "Neha",
    "Vikram",
    "Kavya",
]

LAST_NAMES = [
    "Sharma",
    "Kumar",
    "Patel",
    "Singh",
    "Reddy",
    "Gupta",
    "Verma",
    "Mehta",
    "Iyer",
    "Nair",
]

CITIES = [
    ("Bengaluru", "Karnataka"),
    ("Hyderabad", "Telangana"),
    ("Mumbai", "Maharashtra"),
    ("Pune", "Maharashtra"),
    ("Chennai", "Tamil Nadu"),
    ("Delhi", "Delhi"),
    ("Kolkata", "West Bengal"),
]

CUSTOMER_SEGMENTS = [
    "Standard",
    "Premium",
    "VIP",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def random_date(start_date, end_date):
    """Generate a random date between two dates."""

    days_difference = (end_date - start_date).days

    random_days = random.randint(0, days_difference)

    return start_date + timedelta(days=random_days)


def generate_phone():
    """Generate a simple 10-digit Indian-style phone number."""

    first_digit = random.choice("6789")

    remaining_digits = "".join(
        random.choices("0123456789", k=9)
    )

    return first_digit + remaining_digits


# ---------------------------------------------------------
# Customer generation
# ---------------------------------------------------------

def generate_customers(num_customers):
    """Generate customer records."""

    customers = []

    start_date = date(2022, 1, 1)
    end_date = date(2025, 12, 31)

    for i in range(1, num_customers + 1):

        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

        city, state = random.choice(CITIES)

        customer = {
            "customer_id": f"CUST{i:06d}",
            "first_name": first_name,
            "last_name": last_name,
            "email": (
                f"{first_name.lower()}."
                f"{last_name.lower()}"
                f"{i}@example.com"
            ),
            "phone": generate_phone(),
            "city": city,
            "state": state,
            "signup_date": random_date(
                start_date,
                end_date
            ).isoformat(),
            "customer_segment": random.choice(
                CUSTOMER_SEGMENTS
            ),
            "is_active": random.choice(
                [True, True, True, False]
            ),
        }

        customers.append(customer)

    return customers


# ---------------------------------------------------------
# CSV writer
# ---------------------------------------------------------

def save_customers(customers, output_file):
    """Save customer records to CSV."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "customer_id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "city",
        "state",
        "signup_date",
        "customer_segment",
        "is_active",
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(customers)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Generating customers...")

    customers = generate_customers(
        NUM_CUSTOMERS
    )

    save_customers(
        customers,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(customers)} customers."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
