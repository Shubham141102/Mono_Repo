from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DOCUMENT_CORPUS = [
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


DOCUMENT_TEXTS = [
    doc["title"] + " " +
    doc["keywords"] + " " +
    doc["content"]
    for doc in DOCUMENT_CORPUS
]


VECTORIZER = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2)
)

DOCUMENT_VECTORS = VECTORIZER.fit_transform(DOCUMENT_TEXTS)


def retrieve_documents(query, top_k=2):

    query_vector = VECTORIZER.transform([query])

    similarities = cosine_similarity(
        query_vector,
        DOCUMENT_VECTORS
    )[0]

    ranked_indices = similarities.argsort()[::-1][:top_k]

    results = []

    for idx in ranked_indices:

        results.append({
            "document_id": DOCUMENT_CORPUS[idx]["document_id"],
            "title": DOCUMENT_CORPUS[idx]["title"],
            "content": DOCUMENT_CORPUS[idx]["content"],
            "score": float(similarities[idx])
        })

    return results