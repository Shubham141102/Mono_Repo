from pathlib import Path
import os

from dotenv import load_dotenv
from google import genai

from document_retriever import retrieve_documents

from structured_retriever import (
    retrieve_inventory,
    retrieve_delivery,
    retrieve_sales,
    retrieve_customers,
    # retrieve_cancellations,
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


# ============================================================
# PATHS
# ============================================================

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. "
            "Please add it to the .env file."
        )

    return genai.Client(api_key=api_key)


# ============================================================
# LOAD BUSINESS DOCUMENTS
# ============================================================

def load_business_documents():

    documents = {}

    for file_path in KNOWLEDGE_DIR.glob("*.txt"):

        documents[file_path.name] = file_path.read_text(
            encoding="utf-8"
        )

    return documents


# ============================================================
# DETECT BUSINESS DOMAIN
# ============================================================

def detect_domain(query):

    q = query.lower()

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    inventory_keywords = [
        "inventory",
        "stock",
        "stockout",
        "out of stock",
        "reorder",
        "restock",
        "replenishment",
        "low stock",
        "quantity on hand",
    ]

    # --------------------------------------------------------
    # DELIVERY
    # --------------------------------------------------------

    delivery_keywords = [
        "delivery",
        "deliveries",
        "delivery time",
        "delivery duration",
        "delivery performance",
        "p95",
        "slow delivery",
        "late delivery",
        "delivery partner",
    ]

    # --------------------------------------------------------
    # CANCELLATION
    # --------------------------------------------------------

    cancellation_keywords = [
        "cancel",
        "cancelled",
        "cancellation",
        "cancellation rate",
    ]

    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    customer_keywords = [
        "customer",
        "customers",
        "highest spending",
        "customer spend",
        "customer spending",
        "orders per customer",
        "average customer",
        "customer aov",
        "highest order",
        "largest order",
        "biggest order",
    ]

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    sales_keywords = [
        "sales",
        "revenue",
        "product sales",
        "store sales",
        "category sales",
        "top product",
        "top products",
        "top store",
        "top stores",
        "average order value",
        "aov",
        "order volume",
        "total orders",
    ]

    if any(keyword in q for keyword in inventory_keywords):
        return "inventory"

    if any(keyword in q for keyword in delivery_keywords):
        return "delivery"

    if any(keyword in q for keyword in cancellation_keywords):
        return "cancellation"

    if any(keyword in q for keyword in customer_keywords):
        return "customer"

    if any(keyword in q for keyword in sales_keywords):
        return "sales"

    return "sales"


# ============================================================
# RETRIEVE STRUCTURED BUSINESS DATA
# ============================================================

def retrieve_structured_data(
    query,
    top_k=10
):

    domain = detect_domain(query)

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    if domain == "inventory":

        data = retrieve_inventory(
            query=query,
            top_k=top_k
        )

        return domain, data

    # --------------------------------------------------------
    # DELIVERY
    # --------------------------------------------------------

    if domain == "delivery":

        data = retrieve_delivery(
            query=query,
            top_k=top_k
        )

        return domain, data

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if domain == "sales":

        data = retrieve_sales(
            query=query,
            top_k=top_k
        )

        return domain, data

    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    if domain == "customer":

        data = retrieve_customers(
            query=query,
            top_k=top_k
        )

        return domain, data

    # --------------------------------------------------------
    # CANCELLATION
    # --------------------------------------------------------

    if domain == "cancellation":

        data = retrieve_cancellations(
            query=query,
            top_k=top_k
        )

        return domain, data

    return domain, None


# ============================================================
# BUILD HYBRID CONTEXT
# ============================================================

def build_business_context(
    query,
    top_k_documents=1,
    top_k_results=10
):

    # --------------------------------------------------------
    # 1. DETECT DOMAIN
    # --------------------------------------------------------

    domain = detect_domain(query)

    # --------------------------------------------------------
    # 2. RETRIEVE BUSINESS POLICY
    # --------------------------------------------------------

    policy_results = retrieve_documents(
        query,
        top_k=top_k_documents
    )

    # --------------------------------------------------------
    # 3. RETRIEVE STRUCTURED DATA
    # --------------------------------------------------------

    detected_domain, structured_results = retrieve_structured_data(
        query=query,
        top_k=top_k_results
    )

    # --------------------------------------------------------
    # 4. BUILD CONTEXT
    # --------------------------------------------------------

    context_parts = []

    context_parts.append(
        "BUSINESS QUESTION\n"
        f"{query}\n"
    )

    context_parts.append(
        "\nDETECTED BUSINESS DOMAIN\n"
        f"{domain}\n"
    )

    # --------------------------------------------------------
    # POLICY
    # --------------------------------------------------------

    context_parts.append(
        "\nRELEVANT BUSINESS POLICY\n"
    )

    for result in policy_results:

        context_parts.append(
            f"Source: {result['source']}\n"
            f"Similarity: {result['score']:.4f}\n"
            f"{result['text']}\n"
        )

    # --------------------------------------------------------
    # STRUCTURED DATA
    # --------------------------------------------------------

    context_parts.append(
        "\nCURRENT BUSINESS DATA\n"
    )

    context_parts.append(
        f"Data Domain: {detected_domain}\n"
    )

    if structured_results is not None:

        if hasattr(structured_results, "empty"):

            if structured_results.empty:

                context_parts.append(
                    "No matching structured data was found."
                )

            else:

                context_parts.append(
                    structured_results.to_string(
                        index=False
                    )
                )

        else:

            context_parts.append(
                str(structured_results)
            )

    else:

        context_parts.append(
            "No structured data was retrieved."
        )

    return "\n".join(context_parts)


# ============================================================
# BACKWARD-COMPATIBLE FUNCTION
# ============================================================

def build_inventory_context(
    query,
    top_k_documents=1,
    top_k_products=10
):

    return build_business_context(
        query=query,
        top_k_documents=top_k_documents,
        top_k_results=top_k_products
    )


# ============================================================
# GENERATE BUSINESS ANSWER
# ============================================================

def generate_business_answer(
    query,
    top_k_documents=1,
    top_k_products=10
):

    # --------------------------------------------------------
    # 1. BUILD HYBRID CONTEXT
    # --------------------------------------------------------

    context = build_business_context(
        query=query,
        top_k_documents=top_k_documents,
        top_k_results=top_k_products
    )

    # --------------------------------------------------------
    # 2. GEMINI CLIENT
    # --------------------------------------------------------

    client = get_gemini_client()

    # --------------------------------------------------------
    # 3. BUSINESS SYSTEM INSTRUCTION
    # --------------------------------------------------------

    system_prompt = """
You are a Business Intelligence Assistant for a
quick-commerce company.

Answer business questions using ONLY the provided
business policy and retrieved business data.

Rules:

1. Do not invent data.
2. Do not make claims that are not supported by the context.
3. Use the retrieved structured business data as the
   primary source for numerical answers.
4. Use business policies to explain recommendations
   and operational guidance.
5. Clearly distinguish current business data from
   policy guidance.
6. If the retrieved data is insufficient, explicitly
   say so.
7. Keep answers concise and business-oriented.
8. When useful, mention specific products, stores,
   customers, order values, revenue, delivery metrics,
   cancellation metrics, inventory levels, and demand.
9. Explain WHY something requires attention when the
   policy and retrieved data support such an explanation.
10. Do not expose internal retrieval scores unless useful.
11. Never fabricate missing fields or metrics.
12. If a question asks for a specific metric, answer that
    metric directly before providing additional context.

Format the response clearly.

Use sections such as:

- Summary
- Key Findings
- Recommended Action

when appropriate.
"""

    # --------------------------------------------------------
    # 4. CALL GEMINI
    # --------------------------------------------------------

    response = client.models.generate_content(

        model="gemini-3.6-flash",

        contents=f"""
SYSTEM INSTRUCTIONS:

{system_prompt}

BUSINESS CONTEXT:

{context}

USER QUESTION:

{query}
"""
    )

    return response.text


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_questions = [

        "Which products currently need inventory attention and why?",

        "What is the average delivery time for Pune stores?",

        "Which category has the highest revenue?",

        "Who are the highest spending customers?",

        "What is the cancellation rate?",

    ]

    print("=" * 70)
    print("MULTI-DOMAIN BUSINESS ASSISTANT")
    print("=" * 70)

    for query in test_questions:

        print("\n")
        print("=" * 70)
        print(f"QUESTION: {query}")
        print("=" * 70)

        domain = detect_domain(query)

        print(f"DETECTED DOMAIN: {domain}")

        answer = generate_business_answer(
            query=query,
            top_k_documents=1,
            top_k_products=10
        )

        print("\nBUSINESS ANSWER\n")
        print(answer)