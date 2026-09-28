import csv
import random
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_STORES = 20

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "stores.csv"

SEED = 44


# ---------------------------------------------------------
# Store reference data
# ---------------------------------------------------------

LOCATIONS = [
    {
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincodes": ["560034", "560038", "560095"],
        "latitude_range": (12.90, 13.05),
        "longitude_range": (77.55, 77.70),
    },
    {
        "city": "Hyderabad",
        "state": "Telangana",
        "pincodes": ["500034", "500081", "500032"],
        "latitude_range": (17.35, 17.50),
        "longitude_range": (78.35, 78.55),
    },
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincodes": ["400050", "400053", "400070"],
        "latitude_range": (18.90, 19.20),
        "longitude_range": (72.80, 72.95),
    },
    {
        "city": "Pune",
        "state": "Maharashtra",
        "pincodes": ["411001", "411014", "411038"],
        "latitude_range": (18.45, 18.60),
        "longitude_range": (73.75, 73.95),
    },
    {
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincodes": ["600018", "600028", "600040"],
        "latitude_range": (12.95, 13.10),
        "longitude_range": (80.15, 80.30),
    },
    {
        "city": "Delhi",
        "state": "Delhi",
        "pincodes": ["110001", "110016", "110029"],
        "latitude_range": (28.55, 28.70),
        "longitude_range": (77.10, 77.30),
    },
    {
        "city": "Kolkata",
        "state": "West Bengal",
        "pincodes": ["700019", "700029", "700091"],
        "latitude_range": (22.50, 22.65),
        "longitude_range": (88.30, 88.45),
    },
]


STORE_AREA_NAMES = [
    "Central",
    "North",
    "South",
    "East",
    "West",
    "Main",
    "Market",
    "Tech Park",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def random_date(start_date, end_date):
    """Generate a random date between two dates."""

    days_difference = (end_date - start_date).days

    random_days = random.randint(
        0,
        days_difference
    )

    return start_date + timedelta(
        days=random_days
    )


# ---------------------------------------------------------
# Store generation
# ---------------------------------------------------------

def generate_stores(num_stores):
    """Generate store records."""

    stores = []

    start_date = date(2022, 1, 1)
    end_date = date(2025, 12, 31)

    for i in range(1, num_stores + 1):

        location = random.choice(LOCATIONS)

        city = location["city"]
        state = location["state"]

        area = random.choice(
            STORE_AREA_NAMES
        )

        latitude = round(
            random.uniform(
                *location["latitude_range"]
            ),
            6
        )

        longitude = round(
            random.uniform(
                *location["longitude_range"]
            ),
            6
        )

        store = {
            "store_id": f"STORE{i:03d}",

            "store_name": (
                f"{city} {area}"
            ),

            "city": city,

            "state": state,

            "pincode": random.choice(
                location["pincodes"]
            ),

            "latitude": latitude,

            "longitude": longitude,

            "opened_date": random_date(
                start_date,
                end_date
            ).isoformat(),

            "is_active": random.choice(
                [True, True, True, False]
            ),
        }

        stores.append(store)

    return stores


# ---------------------------------------------------------
# CSV writer
# ---------------------------------------------------------

def save_stores(stores, output_file):
    """Save store records to CSV."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "store_id",
        "store_name",
        "city",
        "state",
        "pincode",
        "latitude",
        "longitude",
        "opened_date",
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

        writer.writerows(stores)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Generating stores...")

    stores = generate_stores(
        NUM_STORES
    )

    save_stores(
        stores,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(stores)} stores."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
