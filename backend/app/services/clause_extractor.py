import re


def clean_line(line: str) -> str:
    line = line.replace("\xa0", " ")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_page_noise(line: str) -> bool:
    text = line.lower().strip()

    if not text:
        return True

    patterns = [
        r"^page\s+\d+$",
        r"^page\s+\d+\s+of\s+\d+$",
        r"^government of india$",
        r"^tender document$",
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def is_clause_start(line: str) -> bool:
    return bool(
        re.match(
            r"^\d+(?:\.\d+)*[\.\):\-]?\s+",
            line
        )
    )


def is_heading(line: str) -> bool:
    text = line.strip().lower()

    headings = [
        "eligibility",
        "eligibility criteria",
        "qualification criteria",
        "technical specifications",
        "schedule of requirements",
        "instructions to bidders",
        "general conditions",
        "special conditions",
    ]

    return text in headings


def extract_clauses(page_number: int, page_text: str) -> list[dict]:

    # Normalize whitespace
    text = re.sub(r"\s+", " ", page_text).strip()

    # Split before numbered clauses such as:
    # 2. Tender documents...
    # 3. Therefore...
    # 7.2 Qualification...
    parts = re.split(
        r"(?=\b\d+(?:\.\d+){0,5}\.\s+)",
        text
    )

    clauses = []

    for part in parts:
        part = part.strip()

        if len(part) < 20:
            continue

        match = re.match(
            r"^(\d+(?:\.\d+){0,5})\.\s+",
            part
        )

        if match:
            clause_number = match.group(1)
        else:
            clause_number = None

        clauses.append({
            "page": page_number,
            "clause": clause_number,
            "text": part,
        })

    return clauses