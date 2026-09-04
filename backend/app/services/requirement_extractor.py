import re


def extract_requirements(text: str):
    requirements = []

    patterns = {
        "turnover": r"(?:turnover|annual turnover).*?(?:₹|rs\.?|inr)?\s*([\d,.]+)\s*(crore|lakh)?",
        "gst": r"\bGST(?:IN)?\b",
        "pan": r"\bPAN\b",
        "udyam": r"\bUdyam\b|\bMSME\b",
        "oem": r"\bOEM\b|\bmanufacturer authorization\b",
    }

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        for requirement_type, pattern in patterns.items():

            match = re.search(pattern, line, re.IGNORECASE)

            if match:
                required_value = None

                if requirement_type == "turnover":
                    required_value = match.group(1)

                    if match.group(2):
                        required_value += f" {match.group(2)}"

                requirements.append({
                    "requirement_type": requirement_type,
                    "description": line,
                    "required_value": required_value,
                    "mandatory": True
                })

    return requirements