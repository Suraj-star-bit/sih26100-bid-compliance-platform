import re


def clean_line(line: str) -> str:
    """
    Clean extracted PDF text without changing its meaning.
    """

    line = line.replace("\xa0", " ")

    # Remove excessive whitespace
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def is_header_or_footer(line: str) -> bool:
    """
    Detect common repeated PDF headers and footers.
    """

    text = line.lower().strip()

    if not text:
        return True

    patterns = [
        r"^page\s+\d+$",
        r"^page\s+\d+\s+of\s+\d+$",
        r"^\d+\s+of\s+\d+$",
        r"^government of india$",
        r"^tender document$",
    ]

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def is_heading(line: str) -> bool:
    """
    Detect likely tender section headings.
    """

    text = line.strip()

    if not text:
        return False

    patterns = [
        r"^section\s+[ivxlcdm\d]+",
        r"^part\s+[ivxlcdm\d]+",
        r"^chapter\s+\d+",
        r"^schedule\s+of",
        r"^technical\s+specifications",
        r"^qualification\s+criteria",
        r"^eligibility",
        r"^instructions\s+to\s+bidders",
        r"^special\s+conditions",
        r"^general\s+conditions",
        r"^terms\s+and\s+conditions",
    ]

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def build_text_blocks(page_text: str) -> list[str]:
    """
    Convert raw PDF lines into meaningful text blocks.

    A block represents a logical piece of tender text that can
    later be analyzed as a possible requirement.
    """

    raw_lines = page_text.splitlines()

    blocks = []
    current_block = []

    for raw_line in raw_lines:

        line = clean_line(raw_line)

        # Ignore empty lines
        if not line:
            if current_block:
                blocks.append(" ".join(current_block))
                current_block = []

            continue

        # Ignore common headers/footers
        if is_header_or_footer(line):
            continue

        # Headings should become their own block
        if is_heading(line):

            if current_block:
                blocks.append(" ".join(current_block))
                current_block = []

            continue

        current_block.append(line)

    # Add remaining text
    if current_block:
        blocks.append(" ".join(current_block))

    # Remove extremely short blocks
    cleaned_blocks = [
        block.strip()
        for block in blocks
        if len(block.strip()) >= 20
    ]

    return cleaned_blocks
