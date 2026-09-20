from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import uuid

from source_mapping import load_source_mapping, resolve_organization_reference
from context_resolution import (
    load_patient_bundle,
    build_indexes,
    normalize_reference,
    get_reference,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_DIR = PROJECT_ROOT / "data" / "bronze_prepared"
OUTPUT_FILE = OUTPUT_DIR / "fhir_resources.ndjson"


def serialize_json(value):
    """Create stable JSON for hashing and Bronze storage."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def calculate_record_hash(resource):
    """Create a deterministic SHA-256 hash of the FHIR resource."""
    payload = serialize_json(resource)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_patient_id(resource):
    """Extract and normalize the source patient reference."""

    reference = (
        get_reference(resource, ["subject", "reference"])
        or get_reference(resource, ["patient", "reference"])
    )

    if resource.get("resourceType") == "Patient":
        return resource.get("id")

    return normalize_reference(reference)


def resolve_context(resource, encounters, mapping):
    """
    Resolve organization and Northstar facility context.

    Rule:
    1. Direct organization context.
    2. Organization through Encounter.
    3. Otherwise leave context null.
    """

    resource_type = resource.get("resourceType")

    organization_reference = None
    context_source = None

    # Encounter has direct organization context.
    if resource_type == "Encounter":
        organization_reference = get_reference(
            resource,
            ["serviceProvider", "reference"]
        )

        if organization_reference:
            context_source = "direct"

    # For resources that explicitly contain an organization reference.
    if not organization_reference:
        organization_reference = get_reference(
            resource,
            ["organization", "reference"]
        )

        if organization_reference:
            context_source = "direct"

    # Derive organization through Encounter.
    if not organization_reference:
        encounter_reference = get_reference(
            resource,
            ["encounter", "reference"]
        )

        encounter_id = normalize_reference(encounter_reference)

        if encounter_id and encounter_id in encounters:
            organization_reference = encounters[
                encounter_id
            ].get("organization_reference")

            if organization_reference:
                context_source = "encounter"

    organization = None

    if organization_reference:
        organization = resolve_organization_reference(
            organization_reference,
            mapping
        )

    return {
        "organization_reference": organization_reference,
        "context_source": context_source,
        "organization": organization,
    }


def build_bronze_record(
    resource,
    source_file,
    batch_id,
    ingestion_timestamp,
    encounters,
    mapping,
):
    """Build one HealthConnect360 Bronze envelope."""

    resource_type = resource.get("resourceType")
    resource_id = resource.get("id")

    patient_id = extract_patient_id(resource)

    context = resolve_context(
        resource,
        encounters,
        mapping,
    )

    organization = context["organization"]

    source_system = None
    northstar_facility = None
    source_organization_id = None
    source_organization_name = None

    if organization:
        source_system = organization.get("source_system")
        northstar_facility = organization.get(
            "northstar_facility_name"
        )
        source_organization_id = organization.get(
            "source_organization_id"
        )
        source_organization_name = organization.get(
            "source_organization_name"
        )

    record = {
        "batch_id": batch_id,
        "source_system": source_system,
        "northstar_facility": northstar_facility,
        "source_organization_id": source_organization_id,
        "source_organization_name": source_organization_name,
        "source_file": source_file,
        "source_patient_id": patient_id,
        "hc360_patient_id": None,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "record_hash": calculate_record_hash(resource),
        "ingestion_timestamp": ingestion_timestamp,
        "ingestion_status": "READY",
        "raw_fhir_json": resource,
    }

    return record


def main():

    source_file, bundle = load_patient_bundle()

    mapping = load_source_mapping()
    encounters = build_indexes(bundle)

    batch_id = f"BATCH-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"

    ingestion_timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    records = []

    for entry in bundle.get("entry", []):

        resource = entry.get("resource")

        if not resource:
            continue

        record = build_bronze_record(
            resource=resource,
            source_file=source_file.name,
            batch_id=batch_id,
            ingestion_timestamp=ingestion_timestamp,
            encounters=encounters,
            mapping=mapping,
        )

        records.append(record)

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        for record in records:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

    # Validation statistics
    with_context = sum(
        1
        for r in records
        if r["source_organization_id"]
    )

    without_context = len(records) - with_context

    resource_types = {}

    for record in records:
        resource_type = record["resource_type"]

        resource_types[resource_type] = (
            resource_types.get(resource_type, 0) + 1
        )

    print()
    print("=" * 70)
    print("HEALTHCONNECT360 BRONZE PREPARATION")
    print("=" * 70)
    print(f"Source file          : {source_file.name}")
    print(f"Batch ID             : {batch_id}")
    print(f"Resources prepared   : {len(records):,}")
    print(f"With organization    : {with_context:,}")
    print(f"Without organization : {without_context:,}")
    print(f"Output file          : {OUTPUT_FILE}")
    print()

    print("Resource counts:")
    for resource_type, count in sorted(
        resource_types.items(),
        key=lambda x: (-x[1], x[0])
    ):
        print(
            f"  {resource_type:<30} {count:>7,}"
        )

    print()
    print("Sample Bronze record:")

    print(
        json.dumps(
            records[0],
            indent=2,
            ensure_ascii=False,
        )[:4000]
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
