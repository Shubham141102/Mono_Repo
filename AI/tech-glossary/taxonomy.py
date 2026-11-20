"""The fixed learning taxonomy: Area > Topic. Terms must be filed under one of these.

Edit this file to change your hierarchy. Tools (Docker, LangChain, MySQL...) are TERMS,
not topics: they live under the topic that describes them.
"""

TAXONOMY: dict[str, list[str]] = {
    "01 Programming": ["Python", "C++", "Java", "C", "Concepts"],
    "02 DSA": ["Complexity", "Arrays & Strings", "Linked Lists", "Stacks & Queues", "Hashing",
               "Trees & Heaps", "Graphs", "Recursion & Backtracking", "Dynamic Programming",
               "Greedy", "Advanced"],
    "03 Core CS": ["Operating Systems", "Computer Networks", "Computer Architecture", "Compilers"],
    "04 Databases": ["Concepts", "SQL", "NoSQL", "Database Design", "Vector DBs"],
    "05 Web Development": ["Frontend", "Backend", "APIs", "Full-Stack"],
    "06 Data Engineering": ["Pipelines & ETL", "Big Data", "Streaming", "Warehousing & Lakehouse",
                            "Data Quality"],
    "07 AI / ML": ["Mathematics", "Statistics", "Machine Learning", "Deep Learning",
                   "Computer Vision", "NLP", "LLMs & GenAI"],
    "08 AI Engineering": ["RAG", "Agents", "Memory", "Evaluation", "Prompt Engineering",
                          "Frameworks", "Protocols"],
    "09 Systems": ["Concurrency", "Distributed Systems", "System Design", "Linux"],
    "10 DevOps & Cloud": ["Containers", "Orchestration", "CI/CD", "Cloud Platforms", "MLOps"],
    "11 Dev Tools": ["Git & GitHub", "Editors & IDEs", "Developer Tools"],
    "12 Security": ["AppSec", "Auth", "Network Security"],
}

UNSORTED = "Unsorted"
SEP = " › "

# Flat list the model must choose from, e.g. "06 Data Engineering › Streaming"
PLACEMENTS: list[str] = [f"{a}{SEP}{t}" for a, ts in TAXONOMY.items() for t in ts] + [UNSORTED]


def split(placement: str) -> tuple[str, str]:
    if placement == UNSORTED or SEP not in placement:
        return UNSORTED, UNSORTED
    area, topic = placement.split(SEP, 1)
    return area, topic


def display_area(area: str) -> str:
    """'06 Data Engineering' -> 'Data Engineering'."""
    head, _, rest = area.partition(" ")
    return rest if head.isdigit() and rest else area


def is_valid(area: str, topic: str) -> bool:
    return topic in TAXONOMY.get(area, [])
