import csv
import random
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_ARCHIVE_CUSTOMERS = 5_000

OUTPUT_DIR = Path("data/raw")

OUTPUT_FILE = (
    OUTPUT_DIR / "archive_customers.csv"
)

SEED = 52


# ---------------------------------------------------------
# Reference data
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
    "Bengaluru",
    "Hyderabad",
    "Mumbai",
    "Pune",
    "Chennai",
    "Delhi",
    "Kolkata",
]

SEGMENTS = [
    "Standard",
    "Premium",
    "VIP",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def random_date(start_date, end_date):
    """Generate a random date."""

    days_difference = (
        end_date - start_date
    ).days

    random_days = random.randint(
        0,
        days_difference
    )

    return (
        start_date
        + timedelta(days=random_days)
    )


def generate_phone():
    """Generate a phone number."""

    first_digit = random.choice(
        "6789"
    )

    remaining_digits = "".join(
        random.choices(
            "0123456789",
            k=9
        )
    )

    return first_digit + remaining_digits


# ---------------------------------------------------------
# Generate archive customers
# ---------------------------------------------------------

def generate_archive_customers(
    num_customers
):
    """Generate historical customer records."""

    customers = []

    start_date = date(
        2019,
        1,
        1
    )

    end_date = date(
        2021,
        12,
        31
    )

    for i in range(
        1,
        num_customers + 1
    ):

        first_name = random.choice(
            FIRST_NAMES
        )

        last_name = random.choice(
            LAST_NAMES
        )

        city = random.choice(
            CITIES
        )

        customer = {
            "customer_id": (
                f"ARCH_CUST{i:06d}"
            ),

            "full_name": (
                f"{first_name} {last_name}"
            ),

            "email": (
                f"{first_name.lower()}."
                f"{last_name.lower()}"
                f".arch{i}@example.com"
            ),

            "phone": generate_phone(),

            "city": city,

            "registration_date": (
                random_date(
                    start_date,
                    end_date
                ).isoformat()
            ),

            "segment": random.choice(
                SEGMENTS
            ),

            "status": random.choice(
                [
                    "Active",
                    "Inactive"
                ]
            ),
        }

        customers.append(customer)

    return customers


# ---------------------------------------------------------
# Save CSV
# ---------------------------------------------------------

def save_archive_customers(
    customers,
    output_file
):
    """Save archive customers."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "customer_id",
        "full_name",
        "email",
        "phone",
        "city",
        "registration_date",
        "segment",
        "status",
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

    print(
        "Generating archive customers..."
    )

    customers = generate_archive_customers(
        NUM_ARCHIVE_CUSTOMERS
    )

    save_archive_customers(
        customers,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(customers)} "
        "archive customers."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
