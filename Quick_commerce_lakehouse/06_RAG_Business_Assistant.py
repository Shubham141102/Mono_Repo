# Databricks notebook source
from pyspark.sql import functions as F

print("RAG Business Assistant started.")

# COMMAND ----------

business_documents = [
    {
        "document_id": "DOC001",
        "title": "Cancellation Policy",
        "content": """
        Customers can cancel an order before the order enters the dispatched
        stage. Once an order has been dispatched, cancellation may not be
        available. For cancelled orders, the payment status and refund process
        should be checked before confirming the refund to the customer.
        """
    },
    {
        "document_id": "DOC002",
        "title": "Delivery Policy",
        "content": """
        Quick-commerce orders are expected to be delivered within the standard
        delivery window defined for the customer's store. Orders may become
        delayed because of operational issues, inventory availability,
        delivery-partner constraints, or high order volume.
        """
    },
    {
        "document_id": "DOC003",
        "title": "Inventory Policy",
        "content": """
        Products with stock quantity equal to zero are considered out of stock.
        Products whose stock quantity is below the reorder level are considered
        low stock. Store teams should prioritize replenishment of low-stock
        products according to operational requirements.
        """
    },
    {
        "document_id": "DOC004",
        "title": "Promotion Policy",
        "content": """
        Promotions may be associated with individual products and contain a
        discount percentage together with a start date and end date.
        A promotion should only be considered active when the current date falls
        within its defined promotion period.
        """
    },
    {
        "document_id": "DOC005",
        "title": "Demand Forecasting",
        "content": """
        Demand forecasting uses historical product-store sales information,
        previous sales, rolling sales windows, average daily sales, inventory
        information, discounts, product attributes, and store attributes.
        Forecast results are stored in the gold demand predictions table.
        """
    }
]

print("Documents created:", len(business_documents))

# COMMAND ----------

documents_df = spark.createDataFrame(business_documents)

display(documents_df)

# COMMAND ----------

documents_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("gold.business_documents")

print("gold.business_documents created.")

# COMMAND ----------

spark.table("gold.business_documents").count()

# COMMAND ----------

daily_sales = spark.table("gold.daily_sales")

product_performance = spark.table("gold.product_performance")

store_performance = spark.table("gold.store_performance")

customer_metrics = spark.table("gold.customer_metrics")

inventory_metrics = spark.table("gold.inventory_metrics")

demand_predictions = spark.table("gold.demand_predictions")

# COMMAND ----------

print("Gold tables loaded:")
print("daily_sales:", daily_sales.count())
print("product_performance:", product_performance.count())
print("store_performance:", store_performance.count())
print("customer_metrics:", customer_metrics.count())
print("inventory_metrics:", inventory_metrics.count())
print("demand_predictions:", demand_predictions.count())

# COMMAND ----------

documents = (
    spark.table("gold.business_documents")
    .select(
        "document_id",
        "title",
        "content"
    )
    .collect()
)

print("Documents loaded:", len(documents))

# COMMAND ----------

document_corpus = [
    {
        "document_id": row["document_id"],
        "title": row["title"],
        "content": row["content"]
    }
    for row in documents
]

for doc in document_corpus:
    print(
        doc["document_id"],
        "->",
        doc["title"]
    )

# COMMAND ----------

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

document_texts = [
    doc["title"] + " " + doc["content"]
    for doc in document_corpus
]

vectorizer = TfidfVectorizer(
    stop_words="english"
)

document_vectors = vectorizer.fit_transform(document_texts)

print("TF-IDF document matrix shape:", document_vectors.shape)

# COMMAND ----------

def retrieve_documents(query, top_k=2):
    
    query_vector = vectorizer.transform([query])
    
    similarities = cosine_similarity(
        query_vector,
        document_vectors
    )[0]
    
    ranked_indices = similarities.argsort()[::-1][:top_k]
    
    results = []
    
    for idx in ranked_indices:
        results.append({
            "document_id": document_corpus[idx]["document_id"],
            "title": document_corpus[idx]["title"],
            "content": document_corpus[idx]["content"],
            "score": float(similarities[idx])
        })
    
    return results

# COMMAND ----------

results = retrieve_documents(
    "What happens when a customer wants to cancel an order?"
)

for result in results:
    print("=" * 60)
    print("Document:", result["document_id"])
    print("Title:", result["title"])
    print("Score:", round(result["score"], 4))
    print("Content:", result["content"].strip())

# COMMAND ----------

results = retrieve_documents(
    "How do we identify products that need replenishment?"
)

for result in results:
    print("=" * 60)
    print("Document:", result["document_id"])
    print("Title:", result["title"])
    print("Score:", round(result["score"], 4))

# COMMAND ----------

results = retrieve_documents(
    "Can a customer cancel an order after it has been dispatched?"
)

for result in results:
    print("=" * 60)
    print("Document:", result["document_id"])
    print("Title:", result["title"])
    print("Score:", round(result["score"], 4))
    print("Content:", result["content"].strip())

# COMMAND ----------

results = retrieve_documents(
    "Why might a customer's delivery be delayed?"
)

for result in results:
    print("=" * 60)
    print("Document:", result["document_id"])
    print("Title:", result["title"])
    print("Score:", round(result["score"], 4))

# COMMAND ----------

import importlib.util

packages = [
    "sentence_transformers",
    "sklearn",
    "transformers",
    "torch"
]

for package in packages:
    print(
        package,
        "->",
        "AVAILABLE" if importlib.util.find_spec(package) else "NOT AVAILABLE"
    )

# COMMAND ----------

document_corpus = [
    {
        "document_id": "DOC001",
        "title": "Cancellation Policy",
        "keywords": "cancel cancellation order dispatched refund payment",
        "content": """
        Customers can cancel an order before the order enters the dispatched
        stage. Once an order has been dispatched, cancellation may not be
        available. For cancelled orders, the payment status and refund process
        should be checked before confirming the refund to the customer.
        """
    },
    {
        "document_id": "DOC002",
        "title": "Delivery Policy",
        "keywords": "delivery delayed late dispatch delivery partner order",
        "content": """
        Quick-commerce orders are expected to be delivered within the standard
        delivery window defined for the customer's store. Orders may become
        delayed because of operational issues, inventory availability,
        delivery-partner constraints, or high order volume.
        """
    },
    {
        "document_id": "DOC003",
        "title": "Inventory Policy",
        "keywords": "inventory stock out of stock low stock reorder replenishment",
        "content": """
        Products with stock quantity equal to zero are considered out of stock.
        Products whose stock quantity is below the reorder level are considered
        low stock. Store teams should prioritize replenishment of low-stock
        products according to operational requirements.
        """
    },
    {
        "document_id": "DOC004",
        "title": "Promotion Policy",
        "keywords": "promotion discount product start date end date active",
        "content": """
        Promotions may be associated with individual products and contain a
        discount percentage together with a start date and end date.
        A promotion should only be considered active when the current date falls
        within its defined promotion period.
        """
    },
    {
        "document_id": "DOC005",
        "title": "Demand Forecasting",
        "keywords": "demand forecast prediction sales product store inventory discount",
        "content": """
        Demand forecasting uses historical product-store sales information,
        previous sales, rolling sales windows, average daily sales, inventory
        information, discounts, product attributes, and store attributes.
        Forecast results are stored in the gold demand predictions table.
        """
    }
]

print("Documents:", len(document_corpus))

# COMMAND ----------

document_texts = [
    (
        doc["title"] + " " +
        doc["keywords"] + " " +
        doc["content"]
    )
    for doc in document_corpus
]

vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2)
)

document_vectors = vectorizer.fit_transform(document_texts)

print("TF-IDF matrix:", document_vectors.shape)

# COMMAND ----------

def retrieve_documents(query, top_k=2):

    query_vector = vectorizer.transform([query])

    similarities = cosine_similarity(
        query_vector,
        document_vectors
    )[0]

    ranked_indices = similarities.argsort()[::-1][:top_k]

    results = []

    for idx in ranked_indices:
        results.append({
            "document_id": document_corpus[idx]["document_id"],
            "title": document_corpus[idx]["title"],
            "content": document_corpus[idx]["content"],
            "score": float(similarities[idx])
        })

    return results

# COMMAND ----------

results = retrieve_documents(
    "Can a customer cancel an order after it has been dispatched?"
)

for result in results:
    print("=" * 60)
    print("Document:", result["document_id"])
    print("Title:", result["title"])
    print("Score:", round(result["score"], 4))

# COMMAND ----------

def classify_question(question):

    q = question.lower()

    # ML / demand prediction questions
    ml_keywords = [
        "predict",
        "prediction",
        "predicted demand",
        "forecast",
        "forecasted demand",
        "next day demand",
        "expected demand"
    ]

    # Structured analytics questions
    data_keywords = [
        "revenue",
        "sales",
        "orders",
        "customers",
        "customer",
        "store",
        "stores",
        "product",
        "products",
        "inventory",
        "stock",
        "units sold",
        "top selling",
        "highest",
        "lowest",
        "average",
        "performance"
    ]

    # Business-document questions
    document_keywords = [
        "policy",
        "policies",
        "cancel",
        "cancellation",
        "refund",
        "delivery policy",
        "promotion policy",
        "replenishment",
        "reorder",
        "how do we",
        "what happens",
        "what is the process"
    ]

    if any(keyword in q for keyword in ml_keywords):
        return "ML"

    if any(keyword in q for keyword in data_keywords):
        return "DATA"

    if any(keyword in q for keyword in document_keywords):
        return "DOCUMENT"

    return "UNKNOWN"

# COMMAND ----------

test_questions = [
    "What is the cancellation policy?",
    "Which product generated the highest revenue?",
    "Which store has the most sales?",
    "What is the predicted demand for product P0034?",
    "How are low stock products identified?",
    "Why can deliveries be delayed?"
]

for question in test_questions:
    print(f"{question}")
    print(f"Route: {classify_question(question)}")
    print("-" * 70)

# COMMAND ----------

