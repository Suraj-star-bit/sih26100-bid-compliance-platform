from app.services.requirement_extractor import extract_requirements


pages = [
    {
        "page_number": 1,
        "text": """
        The bidder must have an annual turnover of Rs. 10 Crore.
        The bidder must possess a valid GST registration.
        """
    },
    {
        "page_number": 2,
        "text": """
        The bidder must submit PAN details.
        OEM authorization certificate is mandatory.
        """
    }
]


requirements = extract_requirements(pages)

for requirement in requirements:
    print(requirement)