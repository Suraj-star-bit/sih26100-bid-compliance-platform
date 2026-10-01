from types import SimpleNamespace

from app.services.compliance_engine import evaluate_requirement


requirement = SimpleNamespace(
    requirement_type="registration",
    description="Bidder must be registered under GST",
    required_value=None,
)


evidence = SimpleNamespace(
    id=1,
    extracted_value="GST registered",
)


result = evaluate_requirement(
    requirement,
    [evidence],
)


print("COMPLIANCE RESULT")
print("------------------")
print("Status:", result["status"])
print("Score:", result["score"])
print("Reason:", result["reason"])
print("Evidence ID:", result["evidence_id"])