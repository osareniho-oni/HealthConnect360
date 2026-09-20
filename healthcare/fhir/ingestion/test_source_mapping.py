from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(
    0,
    str(PROJECT_ROOT / "healthcare" / "fhir" / "ingestion")
)

from source_mapping import (
    load_source_mapping,
    get_source_mapping,
    derive_source_system,
)


mapping = load_source_mapping()

test_organization_ids = [
    "74ab949d-17ac-3309-83a0-13b4405c66aa",
    "17a4bae5-8b64-34d7-8144-b428be027bd0",
    "ab701a70-a658-340e-8f69-ee196a7d40c6",
]

print(f"Loaded mappings: {len(mapping)}")
print()

for organization_id in test_organization_ids:

    result = get_source_mapping(
        organization_id,
        mapping=mapping
    )

    source_system = derive_source_system(result)

    print("Organization ID :", result["source_organization_id"])
    print("Organization     :", result["source_organization_name"])
    print("Service category :", result["service_category"])
    print("Source system    :", source_system)
    print("Facility code    :", result["northstar_facility_code"])
    print("Facility name    :", result["northstar_facility_name"])
    print("Mapping basis    :", result["mapping_basis"])
    print()
