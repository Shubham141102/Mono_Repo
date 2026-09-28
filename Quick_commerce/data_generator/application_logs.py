import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_LOGS = 100_000

OUTPUT_FILE = Path("data/raw/application_logs.csv")


SERVICES = [
    "api_gateway",
    "order_service",
    "payment_service",
    "delivery_service",
    "inventory_service",
    "customer_service",
]

ENDPOINTS = [
    "/api/orders",
    "/api/orders/{order_id}",
    "/api/payments",
    "/api/customers",
    "/api/products",
    "/api/inventory",
    "/api/delivery",
]

LOG_LEVELS = [
    "INFO",
    "INFO",
    "INFO",
    "INFO",
    "WARNING",
    "ERROR",
]

HTTP_STATUS_CODES = [
    200,
    200,
    200,
    201,
    400,
    404,
    500,
]

ERROR_MESSAGES = [
    "Request processed successfully",
    "Order created successfully",
    "Payment processed successfully",
    "Customer data retrieved",
    "Product information retrieved",
    "Inventory updated",
    "Delivery status updated",
    "Invalid request parameters",
    "Resource not found",
    "Internal server error",
    "Payment processing failed",
    "Database connection timeout",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def random_timestamp():
    """
    Generate a timestamp within the last year.
    """
    start = datetime(2025, 1, 1)
    end = datetime(2025, 12, 31)

    random_seconds = random.randint(
        0,
        int((end - start).total_seconds())
    )

    return start + timedelta(seconds=random_seconds)


def generate_log_message(level, status_code):
    """
    Generate a message based on log level and HTTP status.
    """

    if level == "ERROR":
        return random.choice([
            "Internal server error",
            "Payment processing failed",
            "Database connection timeout",
        ])

    if status_code == 404:
        return "Resource not found"

    if status_code == 400:
        return "Invalid request parameters"

    return random.choice([
        "Request processed successfully",
        "Order created successfully",
        "Payment processed successfully",
        "Customer data retrieved",
        "Product information retrieved",
        "Inventory updated",
        "Delivery status updated",
    ])


# ---------------------------------------------------------
# Main generation
# ---------------------------------------------------------

def generate_logs():

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = []

    for i in range(1, NUM_LOGS + 1):

        timestamp = random_timestamp()

        service = random.choice(SERVICES)

        endpoint = random.choice(ENDPOINTS)

        level = random.choice(LOG_LEVELS)

        status_code = random.choice(HTTP_STATUS_CODES)

        latency_ms = random.randint(20, 3000)

        message = generate_log_message(
            level,
            status_code
        )

        rows.append({
            "log_id": f"LOG{i:08d}",
            "timestamp": timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "level": level,
            "service": service,
            "endpoint": endpoint,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "message": message,
        })

    # Sort logs chronologically
    rows.sort(key=lambda x: x["timestamp"])

    fieldnames = [
        "log_id",
        "timestamp",
        "level",
        "service",
        "endpoint",
        "status_code",
        "latency_ms",
        "message",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    print("Application log generation completed.")
    print(f"Records generated: {len(rows)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_logs()
