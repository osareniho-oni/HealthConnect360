
from pathlib import Path
import csv
from urllib.parse import unquote


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "source_system_mapping.csv"
)


class SourceMappingError(Exception):
    """Raised when source-system mapping cannot be resolved."""
    pass


def load_source_mapping():
    """
    Load the Synthea Organization -> Northstar facility mapping.

    Returns:
        dict[str, dict]: Mapping keyed by source_organization_id.
    """

    if not MAPPING_FILE.exists():
        raise SourceMappingError(
            f"Source mapping file not found: {MAPPING_FILE}"
        )

    mapping = {}

    with MAPPING_FILE.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "source_organization_id",
            "source_organization_name",
            "service_category",
            "northstar_facility_code",
            "northstar_facility_name",
            "mapping_basis",
            "active",
        }

        actual_columns = set(reader.fieldnames or [])
        missing_columns = required_columns - actual_columns

        if missing_columns:
            raise SourceMappingError(
                "Missing required mapping columns: "
                + ", ".join(sorted(missing_columns))
            )

        for row in reader:

            organization_id = row["source_organization_id"].strip()

            if not organization_id:
                raise SourceMappingError(
                    "Found mapping row with empty source_organization_id."
                )

            if organization_id in mapping:
                raise SourceMappingError(
                    f"Duplicate source_organization_id: {organization_id}"
                )

            mapping[organization_id] = {
                "source_organization_id": organization_id,
                "source_organization_name":
                    row["source_organization_name"].strip(),
                "service_category":
                    row["service_category"].strip(),
                "northstar_facility_code":
                    row["northstar_facility_code"].strip(),
                "northstar_facility_name":
                    row["northstar_facility_name"].strip(),
                "mapping_basis":
                    row["mapping_basis"].strip(),
                "active":
                    row["active"].strip().lower() == "true",
            }

    return mapping


def get_source_mapping(
    source_organization_id,
    mapping=None
):
    """
    Resolve a source Organization identifier.

    Args:
        source_organization_id: Synthea Organization identifier.
        mapping: Optional pre-loaded mapping dictionary.

    Returns:
        dict containing source and Northstar classification.
    """

    if not source_organization_id:
        raise SourceMappingError(
            "source_organization_id is required."
        )

    if mapping is None:
        mapping = load_source_mapping()

    source_organization_id = source_organization_id.strip()

    result = mapping.get(source_organization_id)

    if result is None:
        raise SourceMappingError(
            "No active Northstar mapping found for "
            f"source organization: {source_organization_id}"
        )

    if not result["active"]:
        raise SourceMappingError(
            "Source organization mapping is inactive: "
            f"{source_organization_id}"
        )

    return result


def derive_source_system(source_mapping):
    """
    Derive the logical HealthConnect360 source system
    from the Northstar facility classification.
    """

    return source_mapping["northstar_facility_code"]


def parse_organization_reference(reference):
    """
    Parse a FHIR Organization reference.

    Supported forms:

        Organization/<id>

    and:

        Organization?identifier=<system>|<value>

    Returns:
        dict containing reference_type, system, and value.
    """

    if not reference:
        raise SourceMappingError(
            "Organization reference is empty."
        )

    reference = unquote(reference.strip())

    if reference.startswith("Organization/"):
        organization_id = reference.split(
            "Organization/",
            1
        )[1]

        if not organization_id:
            raise SourceMappingError(
                f"Invalid Organization reference: {reference}"
            )

        return {
            "reference_type": "resource",
            "system": None,
            "value": organization_id,
        }

    if reference.startswith("Organization?identifier="):

        identifier = reference.split(
            "Organization?identifier=",
            1
        )[1]

        if "|" not in identifier:
            raise SourceMappingError(
                "Identifier-based Organization reference does not "
                f"contain system|value: {reference}"
            )

        system, value = identifier.split("|", 1)

        if not value:
            raise SourceMappingError(
                f"Organization identifier value is empty: {reference}"
            )

        return {
            "reference_type": "identifier",
            "system": system,
            "value": value,
        }

    raise SourceMappingError(
        f"Unsupported Organization reference: {reference}"
    )


def resolve_organization_reference(
    reference,
    mapping=None
):
    """
    Parse and resolve a FHIR Organization reference.

    Returns:
        A combined dictionary containing:

        - original reference
        - reference type
        - identifier system
        - source organization ID
        - source organization name
        - service category
        - source system
        - Northstar facility
    """

    parsed = parse_organization_reference(reference)

    result = get_source_mapping(
        parsed["value"],
        mapping=mapping
    )

    return {
        "source_reference": reference,
        "reference_type": parsed["reference_type"],
        "source_identifier_system": parsed["system"],
        "source_organization_id":
            result["source_organization_id"],
        "source_organization_name":
            result["source_organization_name"],
        "service_category":
            result["service_category"],
        "source_system":
            derive_source_system(result),
        "northstar_facility_code":
            result["northstar_facility_code"],
        "northstar_facility_name":
            result["northstar_facility_name"],
        "mapping_basis":
            result["mapping_basis"],
    }


if __name__ == "__main__":

    mapping = load_source_mapping()

    print(f"Loaded mappings: {len(mapping)}")

    test_references = [
        (
            "Organization?identifier="
            "https://github.com/synthetichealth/synthea"
            "|497f39dd-280e-3d58-af5b-c5e3a3a09b10"
        ),
        (
            "Organization?identifier="
            "https://github.com/synthetichealth/synthea"
            "|0d24cc89-3256-330c-b36d-d8de8babef84"
        ),
        (
            "Organization/497f39dd-280e-3d58-af5b-c5e3a3a09b10"
        ),
    ]

    print("\nReference resolution tests:\n")

    for reference in test_references:

        result = resolve_organization_reference(
            reference,
            mapping=mapping
        )

        print("Reference       :", result["source_reference"])
        print("Reference type  :", result["reference_type"])
        print("Identifier sys  :", result["source_identifier_system"])
        print("Organization ID  :", result["source_organization_id"])
        print("Organization     :", result["source_organization_name"])
        print("Source system    :", result["source_system"])
        print("Facility         :", result["northstar_facility_name"])
        print()