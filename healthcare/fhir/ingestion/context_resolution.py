from pathlib import Path
import json
import re

from source_mapping import (
    load_source_mapping,
    resolve_organization_reference,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def normalize_reference(reference):
    """Convert common FHIR references into a normalized resource ID."""
    if not reference:
        return None

    if reference.startswith("urn:uuid:"):
        return reference.replace("urn:uuid:", "", 1)

    if "/" in reference and "?" not in reference:
        return reference.rsplit("/", 1)[-1]

    return reference


def get_reference(resource, path):
    """Safely navigate dictionaries and lists."""
    current = resource

    for key in path:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list):
            try:
                current = current[int(key)]
            except (ValueError, IndexError):
                return None
        else:
            return None

    return current


def load_patient_bundle():
    fhir_dir = PROJECT_ROOT / "synthea" / "output" / "fhir"

    files = [
        file for file in fhir_dir.glob("*.json")
        if not file.name.startswith("hospitalInformation")
        and not file.name.startswith("practitionerInformation")
    ]

    if not files:
        raise FileNotFoundError("No Synthea patient bundles found.")

    file = sorted(files)[0]

    with file.open("r", encoding="utf-8") as handle:
        return file, json.load(handle)


def build_indexes(bundle):
    """Build lookup indexes from resources in the bundle."""

    encounters = {}

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})

        if resource.get("resourceType") != "Encounter":
            continue

        encounter_id = resource.get("id")

        if encounter_id:
            encounters[encounter_id] = {
                "organization_reference": get_reference(
                    resource,
                    ["serviceProvider", "reference"]
                )
            }

    return encounters


def resolve_resource_context(resource, encounters, mapping):
    """Resolve patient and organization context for a FHIR resource."""

    resource_type = resource.get("resourceType")

    patient_reference = (
        get_reference(resource, ["subject", "reference"])
        or get_reference(resource, ["patient", "reference"])
    )

    patient_id = normalize_reference(patient_reference)

    organization_reference = None
    context_source = "none"

    # Direct organization context
    if resource_type == "Encounter":
        organization_reference = get_reference(
            resource,
            ["serviceProvider", "reference"]
        )

        if organization_reference:
            context_source = "direct"

    # Resources that may contain their own organization reference
    if not organization_reference:
        organization_reference = (
            get_reference(resource, ["performer", "0", "actor", "reference"])
            if resource_type in {"Observation", "DiagnosticReport"}
            else None
        )

    # Derive organization through Encounter
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
        "resource_type": resource_type,
        "resource_id": resource.get("id"),
        "patient_id": patient_id,
        "organization_reference": organization_reference,
        "context_source": context_source,
        "organization": organization,
    }


def main():
    file, bundle = load_patient_bundle()
    mapping = load_source_mapping()
    encounters = build_indexes(bundle)

    total = 0
    patient_context = 0
    organization_context = 0
    direct_context = 0
    encounter_context = 0
    unresolved_context = 0

    resource_types = {}

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})

        if not resource:
            continue

        total += 1

        resource_type = resource.get("resourceType", "UNKNOWN")
        resource_types[resource_type] = resource_types.get(resource_type, 0) + 1

        context = resolve_resource_context(
            resource,
            encounters,
            mapping
        )

        if context["patient_id"]:
            patient_context += 1

        if context["organization"]:
            organization_context += 1

            if context["context_source"] == "direct":
                direct_context += 1
            elif context["context_source"] == "encounter":
                encounter_context += 1
        else:
            unresolved_context += 1

    print()
    print("=" * 70)
    print("HEALTHCONNECT360 CONTEXT RESOLUTION")
    print("=" * 70)
    print(f"Bundle              : {file.name}")
    print(f"FHIR resources      : {total:,}")
    print(f"Encounter index     : {len(encounters):,}")
    print()
    print(f"Patient context     : {patient_context:,}")
    print(f"Organization context: {organization_context:,}")
    print(f"  Direct            : {direct_context:,}")
    print(f"  Via Encounter     : {encounter_context:,}")
    print(f"Unresolved org      : {unresolved_context:,}")
    print()
    print("Resource types:")
    for resource_type, count in sorted(
        resource_types.items(),
        key=lambda x: (-x[1], x[0])
    ):
        print(f"  {resource_type:<30} {count:>7,}")

    print("=" * 70)


if __name__ == "__main__":
    main()
