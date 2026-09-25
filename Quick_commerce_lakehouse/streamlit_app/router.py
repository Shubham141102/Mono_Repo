def classify_question(question):

    q = question.lower()

    ml_keywords = [
        "predict",
        "prediction",
        "predicted demand",
        "forecast",
        "forecasted demand",
        "next day demand",
        "expected demand"
    ]

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