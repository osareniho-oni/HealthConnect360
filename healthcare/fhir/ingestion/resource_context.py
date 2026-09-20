from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_reference(resource, path):
    """
    Safely retrieve a FHIR reference from a nested resource.

    Supports both dictionary keys and numeric list indexes.
    """
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


def extract_resource_context(resource):
    """
    Extract the identifiers and references needed for Bronze metadata.

    This function does not modify the original FHIR resource.
    """

    if not isinstance(resource, dict):
        raise ValueError("FHIR resource must be a dictionary.")

    resource_type = resource.get("resourceType")
    resource_id = resource.get("id")

    context = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_patient_id": None,
        "organization_reference": None,
        "practitioner_reference": None,
        "encounter_reference": None,
    }

    if resource_type == "Patient":
        context["source_patient_id"] = resource_id

    elif resource_type == "Encounter":

        context["source_patient_id"] = get_reference(
            resource,
            ["subject", "reference"]
        )

        context["organization_reference"] = get_reference(
            resource,
            ["serviceProvider", "reference"]
        )

        context["practitioner_reference"] = get_reference(
            resource,
            ["participant", "0", "individual", "reference"]
        )

    elif resource_type in {
        "Observation",
        "Condition",
        "Procedure",
        "DiagnosticReport",
        "MedicationRequest",
        "MedicationAdministration",
        "CarePlan",
        "CareTeam",
        "AllergyIntolerance",
        "Immunization",
        "Claim",
    }:

        context["source_patient_id"] = (
            get_reference(resource, ["subject", "reference"])
            or get_reference(resource, ["patient", "reference"])
        )

        context["encounter_reference"] = get_reference(
            resource,
            ["encounter", "reference"]
        )

    return context


def load_first_patient_bundle():

    fhir_dir = PROJECT_ROOT / "synthea" / "output" / "fhir"

    files = [
        file for file in fhir_dir.glob("*.json")
        if not file.name.startswith("hospitalInformation")
        and not file.name.startswith("practitionerInformation")
    ]

    if not files:
        raise FileNotFoundError(
            f"No Synthea patient bundles found in {fhir_dir}"
        )

    file = sorted(files)[0]

    with file.open(
        "r",
        encoding="utf-8"
    ) as handle:
        bundle = json.load(handle)

    return file, bundle


if __name__ == "__main__":

    file, bundle = load_first_patient_bundle()

    print("Patient bundle:", file.name)
    print("Bundle type   :", bundle.get("type"))
    print("FHIR entries  :", len(bundle.get("entry", [])))

    print("\nResource context samples:\n")

    sample_types = {
        "Patient",
        "Encounter",
        "Observation",
        "Condition",
        "MedicationRequest",
    }

    shown = 0

    for entry in bundle.get("entry", []):

        resource = entry.get("resource", {})

        if resource.get("resourceType") not in sample_types:
            continue

        context = extract_resource_context(resource)

        print("Resource type       :", context["resource_type"])
        print("Resource ID         :", context["resource_id"])
        print("Patient reference   :", context["source_patient_id"])
        print("Organization ref    :", context["organization_reference"])
        print("Practitioner ref    :", context["practitioner_reference"])
        print("Encounter ref       :", context["encounter_reference"])
        print("-" * 70)

        shown += 1

        if shown >= 8:
            break
