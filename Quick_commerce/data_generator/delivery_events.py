import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

OUTPUT_DIR = Path("data/raw")

ORDERS_FILE = OUTPUT_DIR / "orders.csv"
DELIVERY_PARTNERS_FILE = (
    OUTPUT_DIR / "delivery_partners.csv"
)

OUTPUT_FILE = OUTPUT_DIR / "delivery_events.csv"

SEED = 51


# ---------------------------------------------------------
# Reference data
# ---------------------------------------------------------

EVENT_TYPES = [
    "assigned",
    "picked_up",
    "out_for_delivery",
    "delivered",
]

# Maximum number of events generated for an order.
# We will use all four for delivered orders.
EVENT_INTERVALS = {
    "assigned": (0, 5),
    "picked_up": (5, 15),
    "out_for_delivery": (10, 20),
    "delivered": (10, 30),
}


# ---------------------------------------------------------
# CSV loader
# ---------------------------------------------------------

def load_csv(file_path):
    """Load CSV records into dictionaries."""

    with open(
        file_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        return list(reader)


# ---------------------------------------------------------
# Event timestamp generation
# ---------------------------------------------------------

def generate_event_times(order_timestamp):
    """
    Generate timestamps for the delivery lifecycle.

    The timestamps are sequential.
    """

    order_time = datetime.strptime(
        order_timestamp,
        "%Y-%m-%d %H:%M:%S"
    )

    event_times = {}

    current_time = order_time

    for event_type in EVENT_TYPES:

        minimum_minutes, maximum_minutes = (
            EVENT_INTERVALS[event_type]
        )

        delay_minutes = random.randint(
            minimum_minutes,
            maximum_minutes
        )

        current_time = (
            current_time
            + timedelta(
                minutes=delay_minutes
            )
        )

        event_times[event_type] = current_time

    return event_times


# ---------------------------------------------------------
# Generate simulated coordinates
# ---------------------------------------------------------

def generate_coordinates():
    """
    Generate simulated latitude and longitude.

    These are illustrative coordinates rather than
    real GPS tracking.
    """

    latitude = round(
        random.uniform(
            8.0,
            28.0
        ),
        6
    )

    longitude = round(
        random.uniform(
            72.0,
            88.0
        ),
        6
    )

    return latitude, longitude


# ---------------------------------------------------------
# Delivery event generation
# ---------------------------------------------------------

def generate_delivery_events(
    orders,
    delivery_partners
):
    """
    Generate delivery lifecycle events.

    Each delivered order receives four events.
    Some non-delivered orders receive partial events.
    """

    events = []

    event_counter = 1

    partner_ids = [
        partner["partner_id"]
        for partner in delivery_partners
    ]

    for order in orders:

        order_status = order["order_status"]

        # Cancelled orders don't get a normal
        # delivery lifecycle.
        if order_status == "Cancelled":
            continue

        partner_id = random.choice(
            partner_ids
        )

        event_times = generate_event_times(
            order["order_timestamp"]
        )

        # Delivered orders receive all events.
        if order_status == "Delivered":

            selected_events = EVENT_TYPES

        # Some non-delivered orders receive
        # only partial events.
        else:

            number_of_events = random.randint(
                1,
                3
            )

            selected_events = EVENT_TYPES[
                :number_of_events
            ]

        for event_type in selected_events:

            latitude, longitude = (
                generate_coordinates()
            )

            event = {
                "delivery_event_id": (
                    f"DEL{event_counter:08d}"
                ),

                "order_id": (
                    order["order_id"]
                ),

                "partner_id": partner_id,

                "event_timestamp": (
                    event_times[event_type]
                    .strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),

                "event_type": event_type,

                "latitude": latitude,

                "longitude": longitude,
            }

            events.append(event)

            event_counter += 1

    return events


# ---------------------------------------------------------
# CSV writer
# ---------------------------------------------------------

def save_delivery_events(
    events,
    output_file
):
    """Save delivery events to CSV."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "delivery_event_id",
        "order_id",
        "partner_id",
        "event_timestamp",
        "event_type",
        "latitude",
        "longitude",
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

        writer.writerows(events)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Loading orders...")

    orders = load_csv(
        ORDERS_FILE
    )

    print(
        f"Loaded {len(orders)} orders."
    )

    print("Loading delivery partners...")

    delivery_partners = load_csv(
        DELIVERY_PARTNERS_FILE
    )

    print(
        f"Loaded {len(delivery_partners)} "
        "delivery partners."
    )

    print("Generating delivery events...")

    events = generate_delivery_events(
        orders,
        delivery_partners
    )

    save_delivery_events(
        events,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(events)} "
        "delivery events."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()