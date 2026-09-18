import json
from pathlib import Path
from typing import List, Optional


# Location of our JSON database
DATA_FILE = Path(__file__).parent.parent / "data" / "study_data.json"


def _ensure_data_file():
    """
    Make sure the data directory and JSON file exist.
    """

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def get_learning_items() -> List[dict]:
    """
    Retrieve all learning items from storage.
    """

    _ensure_data_file()

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_learning_items(items: List[dict]):
    """
    Save all learning items to storage.
    """

    _ensure_data_file()

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(items, file, indent=4)


def add_learning_item(item: dict) -> dict:
    """
    Add a new learning item to storage.
    """

    items = get_learning_items()

    # Generate the next ID
    if items:
        new_id = max(existing["id"] for existing in items) + 1
    else:
        new_id = 1

    item["id"] = new_id

    items.append(item)

    save_learning_items(items)

    return item


def get_learning_item(item_id: int) -> Optional[dict]:
    """
    Retrieve a single learning item by ID.
    """

    items = get_learning_items()

    for item in items:
        if item["id"] == item_id:
            return item

    return None


def update_learning_item(item_id: int, updated_item: dict) -> Optional[dict]:
    """
    Update an existing learning item.
    """

    items = get_learning_items()

    for index, item in enumerate(items):

        if item["id"] == item_id:

            updated_item["id"] = item_id

            items[index] = updated_item

            save_learning_items(items)

            return updated_item

    return None


def delete_learning_item(item_id: int) -> bool:
    """
    Delete a learning item by ID.
    """

    items = get_learning_items()

    for index, item in enumerate(items):

        if item["id"] == item_id:

            items.pop(index)

            save_learning_items(items)

            return True

    return False