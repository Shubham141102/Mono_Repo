import streamlit as st
from datetime import date

from core.scheduler import calculate_review_dates
from core.review_engine import get_due_reviews
from utils.storage import add_learning_item, get_learning_items


# -----------------------------
# Page Configuration
# -----------------------------

st.set_page_config(
    page_title="147 Memory System",
    page_icon="🧠",
    layout="centered"
)


# -----------------------------
# Application Title
# -----------------------------

st.title("🧠 147 Memory System")

st.subheader("Learn → Review → Remember")

st.write(
    "Enter something you learned today, "
    "and we'll schedule it using the 1-4-7 method."
)


# -----------------------------
# Learning Input
# -----------------------------

learning_content = st.text_area(
    "What did you learn today?",
    placeholder=(
        "Example: Python decorators allow us to "
        "modify the behavior of functions..."
    )
)


# -----------------------------
# Add Learning Material
# -----------------------------

if st.button("➕ Add to 147 Schedule"):

    if learning_content.strip():

        # Today's date
        start_date = date.today()

        # Calculate Day 1, Day 4 and Day 7
        review_dates = calculate_review_dates(start_date)

        # Create learning item
        learning_item = {
            "content": learning_content.strip(),
            "created_date": start_date.isoformat(),
            "reviews": {
                "day_1": {
                    "date": review_dates["day_1"].isoformat(),
                    "completed": False
                },
                "day_4": {
                    "date": review_dates["day_4"].isoformat(),
                    "completed": False
                },
                "day_7": {
                    "date": review_dates["day_7"].isoformat(),
                    "completed": False
                }
            }
        }

        # Save item
        saved_item = add_learning_item(learning_item)

        st.success(
            f"Learning item #{saved_item['id']} "
            "added successfully!"
        )

    else:

        st.warning(
            "Please enter something you learned today."
        )


# -----------------------------
# Today's Reviews
# -----------------------------

st.divider()

st.header("📅 Today's Reviews")

# Get today's date
today = date.today()

# Get all saved learning items
learning_items = get_learning_items()

# Find due reviews
due_reviews = get_due_reviews(
    learning_items,
    today
)


if not due_reviews:

    st.success("🎉 No reviews due today!")

else:

    st.warning(
        f"🔔 You have {len(due_reviews)} "
        f"review(s) due today."
    )

    for review in due_reviews:

        st.write(
            f"### 🧠 {review['content']}"
        )

        st.write(
            f"**{review['review_day'].replace('_', ' ').title()}**"
        )

        st.write(
            f"Scheduled: **{review['review_date']}**"
        )

        st.divider()


# -----------------------------
# Display Saved Learning
# -----------------------------

st.header("📚 Saved Learning")

if not learning_items:

    st.info("No learning items saved yet.")

else:

    for item in learning_items:

        st.write(
            f"### #{item['id']} — {item['content']}"
        )

        st.write(
            f"Learned on: **{item['created_date']}**"
        )

        st.write("📅 Review Schedule")

        col1, col2, col3 = st.columns(3)

        with col1:

            st.write(
                f"**Day 1**\n\n"
                f"{item['reviews']['day_1']['date']}"
            )

        with col2:

            st.write(
                f"**Day 4**\n\n"
                f"{item['reviews']['day_4']['date']}"
            )

        with col3:

            st.write(
                f"**Day 7**\n\n"
                f"{item['reviews']['day_7']['date']}"
            )

        st.divider()