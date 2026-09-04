from app.services.requirement_extractor import extract_requirements

text = """
The bidder must have an annual turnover of Rs. 10 Crore.
The bidder must possess a valid GST registration.
The bidder must submit PAN details.
The bidder should have a valid Udyam MSME registration.
OEM authorization certificate is mandatory.
"""

requirements = extract_requirements(text)

for requirement in requirements:
    print(requirement)