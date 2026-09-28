from pathlib import Path

from document_retriever import retrieve_documents
from structured_retriever import retrieve_inventory


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"


# ============================================================
# LOAD BUSINESS DOCUMENTS
# ============================================================

def load_business_documents():

    documents = {}

    for file_path in KNOWLEDGE_DIR.glob("*.txt"):

        documents[file_path.name] = (
            file_path.read_text(
                encoding="utf-8"
            )
        )

    return documents


# ============================================================
# BUILD HYBRID CONTEXT
# ============================================================

def build_inventory_context(
    query,
    top_k_documents=1,
    top_k_products=10
):

    documents = load_business_documents()

    # --------------------------------------------------------
    # 1. Retrieve relevant business policy
    # --------------------------------------------------------

    policy_results = retrieve_documents(
        query,
        top_k=top_k_documents
    )

    # --------------------------------------------------------
    # 2. Retrieve actual business data
    # --------------------------------------------------------

    inventory_results = retrieve_inventory(
        top_k=top_k_products
    )

    # --------------------------------------------------------
    # 3. Build context
    # --------------------------------------------------------

    context_parts = []

    context_parts.append(
        "BUSINESS QUESTION\n"
        f"{query}\n"
    )

    context_parts.append(
        "\nRELEVANT BUSINESS POLICY\n"
    )

    for result in policy_results:

        context_parts.append(
            f"Source: {result['source']}\n"
            f"Similarity: {result['score']:.4f}\n"
            f"{result['text']}\n"
        )

    context_parts.append(
        "\nCURRENT INVENTORY DATA\n"
    )

    context_parts.append(
        inventory_results.to_string(
            index=False
        )
    )

    return "\n".join(
        context_parts
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    query = (
        "Which products currently need "
        "inventory attention?"
    )

    print("=" * 70)
    print("HYBRID RAG CONTEXT")
    print("=" * 70)

    context = build_inventory_context(
        query=query,
        top_k_documents=1,
        top_k_products=10
    )

    print()
    print(context)