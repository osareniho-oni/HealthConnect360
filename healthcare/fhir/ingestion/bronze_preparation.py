from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import uuid

from source_mapping import (
    load_source_mapping,
    resolve_organization_reference
)

from context_resolution import (
    load_patient_bundle,
    build_indexes,
    normalize_reference,
    get_reference,
)


# =========================================================
# Project paths
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "bronze_prepared"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "fhir_resources.ndjson"
)

SYNTHETIC_FHIR_DIR = (
    PROJECT_ROOT
    / "synthea"
    / "output"
    / "fhir"
)


# =========================================================
# JSON helpers
# =========================================================

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

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def load_json_bundle(file_path):
    """Load a FHIR Bundle from a JSON file."""

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(handle)


# =========================================================
# Patient reference helper
# =========================================================

def extract_patient_id(resource):
    """Extract and normalize the source patient reference."""

    reference = (
        get_reference(
            resource,
            ["subject", "reference"]
        )
        or get_reference(
            resource,
            ["patient", "reference"]
        )
    )

    if resource.get("resourceType") == "Patient":

        return resource.get("id")

    return normalize_reference(
        reference
    )


# =========================================================
# Organization / facility context
# =========================================================

def resolve_context(
    resource,
    encounters,
    mapping,
):
    """
    Resolve organization and Northstar facility context.

    Rules:
    1. Organization resource resolves itself.
    2. Encounter has direct organization context.
    3. Resources with explicit organization context.
    4. Location uses managingOrganization.
    5. Organization through Encounter.
    6. Otherwise leave context null.
    """

    resource_type = resource.get(
        "resourceType"
    )

    organization_reference = None
    context_source = None

    # -----------------------------------------------------
    # Organization resource represents itself
    # -----------------------------------------------------
    if resource_type == "Organization":

        organization_id = resource.get(
            "id"
        )

        if organization_id:

            organization_reference = (
                f"Organization/{organization_id}"
            )

            context_source = "self"

    # -----------------------------------------------------
    # Encounter has direct organization context
    # -----------------------------------------------------
    if (
        not organization_reference
        and resource_type == "Encounter"
    ):

        organization_reference = get_reference(
            resource,
            ["serviceProvider", "reference"]
        )

        if organization_reference:

            context_source = "direct"

    # -----------------------------------------------------
    # Resources with explicit organization
    # -----------------------------------------------------
    if not organization_reference:

        organization_reference = get_reference(
            resource,
            ["organization", "reference"]
        )

        if organization_reference:

            context_source = "direct"

    # -----------------------------------------------------
    # Location managing organization
    # -----------------------------------------------------
    if not organization_reference:

        organization_reference = get_reference(
            resource,
            ["managingOrganization", "reference"]
        )

        if organization_reference:

            context_source = "direct"

    # -----------------------------------------------------
    # Derive organization through Encounter
    # -----------------------------------------------------
    if not organization_reference:

        encounter_reference = get_reference(
            resource,
            ["encounter", "reference"]
        )

        encounter_id = normalize_reference(
            encounter_reference
        )

        if (
            encounter_id
            and encounter_id in encounters
        ):

            organization_reference = encounters[
                encounter_id
            ].get(
                "organization_reference"
            )

            if organization_reference:

                context_source = "encounter"

    organization = None

    if organization_reference:

        organization = (
            resolve_organization_reference(
                organization_reference,
                mapping
            )
        )

    return {
        "organization_reference":
            organization_reference,

        "context_source":
            context_source,

        "organization":
            organization,
    }


# =========================================================
# Bronze envelope
# =========================================================

def build_bronze_record(
    resource,
    source_file,
    batch_id,
    ingestion_timestamp,
    encounters,
    mapping,
):
    """Build one HealthConnect360 Bronze envelope."""

    resource_type = resource.get(
        "resourceType"
    )

    resource_id = resource.get(
        "id"
    )

    patient_id = extract_patient_id(
        resource
    )

    context = resolve_context(
        resource,
        encounters,
        mapping,
    )

    organization = context[
        "organization"
    ]

    source_system = None
    northstar_facility = None
    source_organization_id = None
    source_organization_name = None

    if organization:

        source_system = organization.get(
            "source_system"
        )

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

        "batch_id":
            batch_id,

        "source_system":
            source_system,

        "northstar_facility":
            northstar_facility,

        "source_organization_id":
            source_organization_id,

        "source_organization_name":
            source_organization_name,

        "source_file":
            source_file,

        "source_patient_id":
            patient_id,

        "hc360_patient_id":
            None,

        "resource_type":
            resource_type,

        "resource_id":
            resource_id,

        "record_hash":
            calculate_record_hash(
                resource
            ),

        "ingestion_timestamp":
            ingestion_timestamp,

        "ingestion_status":
            "READY",

        "raw_fhir_json":
            resource,
    }

    return record


# =========================================================
# Main
# =========================================================

def main():

    # =====================================================
    # 1. Load patient transaction bundle
    # =====================================================

    patient_source_file, patient_bundle = (
        load_patient_bundle()
    )

    # =====================================================
    # 2. Load Practitioner master bundle
    # =====================================================

    practitioner_files = sorted(
        SYNTHETIC_FHIR_DIR.glob(
            "practitionerInformation*.json"
        )
    )

    if not practitioner_files:

        raise FileNotFoundError(
            "No practitionerInformation*.json "
            "file found in "
            f"{SYNTHETIC_FHIR_DIR}"
        )

    practitioner_source_file = (
        practitioner_files[0]
    )

    practitioner_bundle = load_json_bundle(
        practitioner_source_file
    )

    # =====================================================
    # 3. Load Hospital master bundle
    # =====================================================

    hospital_files = sorted(
        SYNTHETIC_FHIR_DIR.glob(
            "hospitalInformation*.json"
        )
    )

    if not hospital_files:

        raise FileNotFoundError(
            "No hospitalInformation*.json "
            "file found in "
            f"{SYNTHETIC_FHIR_DIR}"
        )

    hospital_source_file = (
        hospital_files[0]
    )

    hospital_bundle = load_json_bundle(
        hospital_source_file
    )

    # =====================================================
    # 4. Load source mapping and encounter indexes
    # =====================================================

    mapping = load_source_mapping()

    encounters = build_indexes(
        patient_bundle
    )

    # =====================================================
    # 5. Generate batch metadata
    # =====================================================

    batch_id = (
        f"BATCH-"
        f"{datetime.now(timezone.utc):%Y%m%d%H%M%S}-"
        f"{uuid.uuid4().hex[:8]}"
    )

    ingestion_timestamp = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    records = []

    # =====================================================
    # 6. Process patient transaction resources
    # =====================================================

    for entry in patient_bundle.get(
        "entry",
        []
    ):

        resource = entry.get(
            "resource"
        )

        if not resource:
            continue

        record = build_bronze_record(

            resource=resource,

            source_file=
                patient_source_file.name,

            batch_id=batch_id,

            ingestion_timestamp=
                ingestion_timestamp,

            encounters=encounters,

            mapping=mapping,
        )

        records.append(
            record
        )

    patient_resource_count = len(
        records
    )

    # =====================================================
    # 7. Process Practitioner master resources
    # =====================================================

    practitioner_start_index = len(
        records
    )

    for entry in practitioner_bundle.get(
        "entry",
        []
    ):

        resource = entry.get(
            "resource"
        )

        if not resource:
            continue

        record = build_bronze_record(

            resource=resource,

            source_file=
                practitioner_source_file.name,

            batch_id=batch_id,

            ingestion_timestamp=
                ingestion_timestamp,

            encounters={},

            mapping=mapping,
        )

        records.append(
            record
        )

    practitioner_resource_count = (
        len(records)
        - practitioner_start_index
    )

    # =====================================================
    # 8. Process Hospital master resources
    # =====================================================

    hospital_start_index = len(
        records
    )

    for entry in hospital_bundle.get(
        "entry",
        []
    ):

        resource = entry.get(
            "resource"
        )

        if not resource:
            continue

        record = build_bronze_record(

            resource=resource,

            source_file=
                hospital_source_file.name,

            batch_id=batch_id,

            ingestion_timestamp=
                ingestion_timestamp,

            encounters={},

            mapping=mapping,
        )

        records.append(
            record
        )

    hospital_resource_count = (
        len(records)
        - hospital_start_index
    )

    # =====================================================
    # 9. Write Bronze NDJSON
    # =====================================================

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

    # =====================================================
    # 10. Validation statistics
    # =====================================================

    with_context = sum(
        1
        for record in records
        if record[
            "source_organization_id"
        ]
    )

    without_context = (
        len(records)
        - with_context
    )

    resource_types = {}

    for record in records:

        resource_type = record[
            "resource_type"
        ]

        resource_types[
            resource_type
        ] = (
            resource_types.get(
                resource_type,
                0
            )
            + 1
        )

    # =====================================================
    # 11. Print validation summary
    # =====================================================

    print()

    print("=" * 70)

    print(
        "HEALTHCONNECT360 BRONZE PREPARATION"
    )

    print("=" * 70)

    print(
        f"Patient source file       : "
        f"{patient_source_file.name}"
    )

    print(
        f"Practitioner source file  : "
        f"{practitioner_source_file.name}"
    )

    print(
        f"Hospital source file      : "
        f"{hospital_source_file.name}"
    )

    print(
        f"Batch ID                  : "
        f"{batch_id}"
    )

    print(
        f"Patient resources         : "
        f"{patient_resource_count:,}"
    )

    print(
        f"Practitioner master       : "
        f"{practitioner_resource_count:,}"
    )

    print(
        f"Hospital master           : "
        f"{hospital_resource_count:,}"
    )

    print(
        f"Total resources prepared  : "
        f"{len(records):,}"
    )

    print(
        f"With organization         : "
        f"{with_context:,}"
    )

    print(
        f"Without organization      : "
        f"{without_context:,}"
    )

    print(
        f"Output file               : "
        f"{OUTPUT_FILE}"
    )

    print()

    print(
        "Resource counts:"
    )

    for resource_type, count in sorted(
        resource_types.items(),
        key=lambda x: (-x[1], x[0])
    ):

        print(
            f"  {resource_type:<30}"
            f"{count:>7,}"
        )

    print()

    print(
        "Sample Bronze record:"
    )

    if records:

        print(
            json.dumps(
                records[0],
                indent=2,
                ensure_ascii=False,
            )[:4000]
        )

    print("=" * 70)


# =========================================================
# Entry point
# =========================================================

if __name__ == "__main__":
    main()