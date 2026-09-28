import csv
import random
import string
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

OUTPUT_DIR = Path("data/raw")

ORDERS_FILE = OUTPUT_DIR / "orders.csv"
OUTPUT_FILE = OUTPUT_DIR / "payments.csv"

SEED = 48


# ---------------------------------------------------------
# Reference data
# ---------------------------------------------------------

PAYMENT_METHODS = [
    "UPI",
    "Credit Card",
    "Debit Card",
    "Cash",
    "Wallet",
]

PAYMENT_STATUSES = [
    "Success",
    "Success",
    "Success",
    "Success",
    "Failed",
    "Pending",
    "Refunded",
]


# ---------------------------------------------------------
# Load orders
# ---------------------------------------------------------

def load_orders(file_path):
    """Load orders from CSV."""

    with open(
        file_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        return list(reader)


# ---------------------------------------------------------
# Transaction reference
# ---------------------------------------------------------

def generate_transaction_reference():
    """Generate a simulated payment transaction reference."""

    characters = string.ascii_uppercase + string.digits

    random_part = "".join(
        random.choices(
            characters,
            k=12
        )
    )

    return f"TXN{random_part}"


# ---------------------------------------------------------
# Payment timestamp
# ---------------------------------------------------------

def generate_payment_timestamp(order_timestamp):
    """
    Generate a payment timestamp close to the
    order timestamp.
    """

    order_time = datetime.strptime(
        order_timestamp,
        "%Y-%m-%d %H:%M:%S"
    )

    # Payment occurs within 0-10 minutes
    # of the order.
    delay_seconds = random.randint(
        0,
        600
    )

    payment_time = (
        order_time
        + timedelta(seconds=delay_seconds)
    )

    return payment_time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ---------------------------------------------------------
# Payment generation
# ---------------------------------------------------------

def generate_payments(orders):
    """
    Generate one payment record for every order.
    """

    payments = []

    for index, order in enumerate(
        orders,
        start=1
    ):

        payment = {
            "payment_id": (
                f"PAY{index:08d}"
            ),

            "order_id": order["order_id"],

            "payment_timestamp": (
                generate_payment_timestamp(
                    order["order_timestamp"]
                )
            ),

            "payment_method": (
                order["payment_method"]
            ),

            "payment_status": random.choice(
                PAYMENT_STATUSES
            ),

            "amount": float(
                order["total_amount"]
            ),

            "transaction_reference": (
                generate_transaction_reference()
            ),
        }

        payments.append(payment)

    return payments


# ---------------------------------------------------------
# Save CSV
# ---------------------------------------------------------

def save_payments(
    payments,
    output_file
):
    """Save payment records to CSV."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "payment_id",
        "order_id",
        "payment_timestamp",
        "payment_method",
        "payment_status",
        "amount",
        "transaction_reference",
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

        writer.writerows(payments)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Loading orders...")

    orders = load_orders(
        ORDERS_FILE
    )

    print(
        f"Loaded {len(orders)} orders."
    )

    print("Generating payments...")

    payments = generate_payments(
        orders
    )

    save_payments(
        payments,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(payments)} payments."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()