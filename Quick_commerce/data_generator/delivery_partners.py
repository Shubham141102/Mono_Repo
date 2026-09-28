import csv
import random
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_DELIVERY_PARTNERS = 100

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "delivery_partners.csv"

SEED = 45


# ---------------------------------------------------------
# Reference data
# ---------------------------------------------------------

FIRST_NAMES = [
    "Amit",
    "Rahul",
    "Rohan",
    "Vikram",
    "Arjun",
    "Karan",
    "Suresh",
    "Manoj",
    "Akash",
    "Nikhil",
    "Varun",
    "Ravi",
]

LAST_NAMES = [
    "Kumar",
    "Sharma",
    "Singh",
    "Patel",
    "Reddy",
    "Gupta",
    "Verma",
    "Yadav",
    "Mehta",
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

VEHICLE_TYPES = [
    "Bike",
    "Scooter",
    "Electric Bike",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def generate_phone():
    """Generate a 10-digit Indian-style phone number."""

    first_digit = random.choice("6789")

    remaining_digits = "".join(
        random.choices(
            "0123456789",
            k=9
        )
    )

    return first_digit + remaining_digits


def random_date(start_date, end_date):
    """Generate a random date between two dates."""

    days_difference = (
        end_date - start_date
    ).days

    random_days = random.randint(
        0,
        days_difference
    )

    return start_date + timedelta(
        days=random_days
    )


def generate_rating():
    """Generate a delivery partner rating."""

    return round(
        random.uniform(3.0, 5.0),
        1
    )


# ---------------------------------------------------------
# Delivery partner generation
# ---------------------------------------------------------

def generate_delivery_partners(
    num_delivery_partners
):
    """Generate delivery partner records."""

    partners = []

    start_date = date(2022, 1, 1)
    end_date = date(2025, 12, 31)

    for i in range(
        1,
        num_delivery_partners + 1
    ):

        first_name = random.choice(
            FIRST_NAMES
        )

        last_name = random.choice(
            LAST_NAMES
        )

        partner = {
            "partner_id": f"DP{i:06d}",

            "first_name": first_name,

            "last_name": last_name,

            "phone": generate_phone(),

            "city": random.choice(
                CITIES
            ),

            "vehicle_type": random.choice(
                VEHICLE_TYPES
            ),

            "joining_date": random_date(
                start_date,
                end_date
            ).isoformat(),

            "rating": generate_rating(),

            "is_active": random.choice(
                [True, True, True, False]
            ),
        }

        partners.append(partner)

    return partners


# ---------------------------------------------------------
# CSV writer
# ---------------------------------------------------------

def save_delivery_partners(
    partners,
    output_file
):
    """Save delivery partner records to CSV."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "partner_id",
        "first_name",
        "last_name",
        "phone",
        "city",
        "vehicle_type",
        "joining_date",
        "rating",
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

        writer.writerows(partners)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print(
        "Generating delivery partners..."
    )

    partners = generate_delivery_partners(
        NUM_DELIVERY_PARTNERS
    )

    save_delivery_partners(
        partners,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(partners)} "
        "delivery partners."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
