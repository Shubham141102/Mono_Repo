from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"


# =========================================================
# LOAD DOCUMENTS
# =========================================================

documents = []

for file_path in KNOWLEDGE_DIR.glob("*.txt"):

    text = file_path.read_text(
        encoding="utf-8"
    )

    documents.append(
        {
            "source": file_path.name,
            "text": text,
        }
    )


print("=" * 70)
print("DOCUMENT RETRIEVER")
print("=" * 70)

print(f"Documents loaded : {len(documents)}")

for document in documents:
    print(f"  - {document['source']}")


# =========================================================
# CREATE TF-IDF VECTORS
# =========================================================

corpus = [
    document["text"]
    for document in documents
]

vectorizer = TfidfVectorizer(
    stop_words="english"
)

document_vectors = vectorizer.fit_transform(
    corpus
)


# =========================================================
# RETRIEVAL FUNCTION
# =========================================================

def retrieve_documents(
    query,
    top_k=2
):

    query_vector = vectorizer.transform(
        [query]
    )

    similarities = cosine_similarity(
        query_vector,
        document_vectors
    )[0]

    ranked_indices = similarities.argsort()[::-1]

    results = []

    for index in ranked_indices[:top_k]:

        results.append(
            {
                "source": documents[index]["source"],
                "score": float(similarities[index]),
                "text": documents[index]["text"],
            }
        )

    return results


# =========================================================
# TEST RETRIEVAL
# =========================================================

if __name__ == "__main__":

    test_queries = [
        "Which products need inventory replenishment?",
        "Why are orders being cancelled?",
        "How should delivery performance be evaluated?",
        "How should discounts and promotions be evaluated?",
    ]

    for query in test_queries:

        print()
        print("=" * 70)
        print(f"QUERY: {query}")
        print("=" * 70)

        results = retrieve_documents(
            query,
            top_k=2
        )

        for result in results:

            print(
                f"\nSource: {result['source']}"
            )

            print(
                f"Score : {result['score']:.4f}"
            )