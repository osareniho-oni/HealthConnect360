import json
from datetime import datetime, timezone
from pathlib import Path

import requests


# ============================================================
# HealthConnect360
# Synthea → HAPI FHIR Ingestion Engine
#
# STEP 5
# Incremental / idempotent patient-bundle ingestion
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SYNTHEA_FHIR_DIR = (
    PROJECT_ROOT
    / "synthea"
    / "output"
    / "fhir"
)

HAPI_BASE_URL = "http://localhost:8080/fhir"

STATE_FILE = (
    Path(__file__).resolve().parent
    / "ingestion_state.json"
)

HEADERS = {
    "Accept": "application/fhir+json",
    "Content-Type": "application/fhir+json",
}

REQUEST_TIMEOUT = 900


# ============================================================
# Utility functions
# ============================================================

def utc_now():
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def load_json(file_path: Path):
    """Load JSON from disk."""
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, file_path: Path):
    """Save JSON state to disk."""
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_state():
    """
    Load the ingestion manifest.

    If it does not exist, create an empty state.
    """

    if not STATE_FILE.exists():
        return {
            "version": 1,
            "bundles": {}
        }

    return load_json(STATE_FILE)


def get_patient_from_bundle(bundle):
    """Return the Patient resource from a transaction Bundle."""

    patients = [
        entry.get("resource")
        for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType")
        == "Patient"
    ]

    if len(patients) != 1:
        raise ValueError(
            f"Expected exactly one Patient resource; "
            f"found {len(patients)}."
        )

    return patients[0]


def get_synthea_patient_identifier(patient):
    """
    Return the Synthea UUID from the Patient resource.

    Synthea uses:
    https://github.com/synthetichealth/synthea
    """

    expected_system = (
        "https://github.com/synthetichealth/synthea"
    )

    for identifier in patient.get("identifier", []):

        if identifier.get("system") == expected_system:
            return identifier.get("value")

    return None


# ============================================================
# HAPI checks
# ============================================================

def check_hapi():
    """Confirm that HAPI FHIR is available."""

    response = requests.get(
        f"{HAPI_BASE_URL}/metadata",
        headers={
            "Accept": "application/fhir+json"
        },
        timeout=30,
    )

    response.raise_for_status()

    return True


def find_patient_in_hapi(patient_identifier):
    """
    Search HAPI for a Patient using the Synthea identifier.

    Returns the matching resources.
    """

    system = (
        "https://github.com/synthetichealth/synthea"
    )

    response = requests.get(
        f"{HAPI_BASE_URL}/Patient",
        params={
            "identifier": f"{system}|{patient_identifier}",
            "_count": 100,
        },
        headers=HEADERS,
        timeout=60,
    )

    response.raise_for_status()

    bundle = response.json()

    return [
        entry.get("resource")
        for entry in bundle.get("entry", [])
    ]


# ============================================================
# Bundle discovery
# ============================================================

def find_patient_bundles():
    """
    Discover Synthea patient transaction bundles.

    Excludes:
      hospitalInformation*.json
      practitionerInformation*.json
    """

    bundles = []

    for file_path in SYNTHEA_FHIR_DIR.glob("*.json"):

        if file_path.name.startswith(
            "hospitalInformation"
        ):
            continue

        if file_path.name.startswith(
            "practitionerInformation"
        ):
            continue

        try:
            data = load_json(file_path)

        except json.JSONDecodeError:
            continue

        if (
            data.get("resourceType") == "Bundle"
            and data.get("type") == "transaction"
        ):
            bundles.append(file_path)

    return sorted(bundles)


# ============================================================
# Bundle submission
# ============================================================

def submit_bundle(file_path):
    """
    Submit one transaction Bundle to HAPI.
    """

    file_size = file_path.stat().st_size

    print(
        f"    File size: "
        f"{file_size / (1024 * 1024):.2f} MB"
    )

    with file_path.open("rb") as file:

        response = requests.post(
            HAPI_BASE_URL,
            data=file,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

    response.raise_for_status()

    result = response.json()

    if result.get("resourceType") != "Bundle":
        raise RuntimeError(
            "HAPI response was not a FHIR Bundle."
        )

    if result.get("type") != "transaction-response":
        raise RuntimeError(
            "HAPI response was not a transaction-response."
        )

    return result


# ============================================================
# Main ingestion
# ============================================================

def main():

    print("=" * 70)
    print("HealthConnect360")
    print("Synthea → HAPI FHIR Incremental Ingestion")
    print("=" * 70)

    # --------------------------------------------------------
    # Validate environment
    # --------------------------------------------------------

    print("\nChecking Synthea directory...")

    if not SYNTHEA_FHIR_DIR.exists():

        raise FileNotFoundError(
            f"Synthea FHIR directory not found:\n"
            f"{SYNTHEA_FHIR_DIR}"
        )

    print("Synthea directory: OK")

    print("\nChecking HAPI FHIR...")

    check_hapi()

    print("HAPI FHIR: ONLINE")

    # --------------------------------------------------------
    # Load ingestion state
    # --------------------------------------------------------

    state = load_state()

    print(
        f"\nIngestion state file:"
    )
    print(STATE_FILE)

    # --------------------------------------------------------
    # Discover bundles
    # --------------------------------------------------------

    bundles = find_patient_bundles()

    print(
        f"\nPatient transaction bundles discovered: "
        f"{len(bundles)}"
    )

    if not bundles:

        print("No patient bundles found.")
        return

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    processed = 0
    skipped = 0
    failed = 0

    # --------------------------------------------------------
    # Process bundles
    # --------------------------------------------------------

    for index, file_path in enumerate(
        bundles,
        start=1
    ):

        print("\n")
        print("-" * 70)
        print(
            f"[{index}/{len(bundles)}] "
            f"{file_path.name}"
        )
        print("-" * 70)

        # ----------------------------------------------------
        # Load bundle
        # ----------------------------------------------------

        try:

            bundle = load_json(file_path)

            patient = get_patient_from_bundle(
                bundle
            )

            patient_identifier = (
                get_synthea_patient_identifier(
                    patient
                )
            )

            if not patient_identifier:

                raise ValueError(
                    "Synthea Patient identifier "
                    "was not found."
                )

            entry_count = len(
                bundle.get("entry", [])
            )

            print(
                f"    Patient source ID: "
                f"{patient_identifier}"
            )

            print(
                f"    FHIR entries: "
                f"{entry_count}"
            )

        except Exception as error:

            failed += 1

            print(
                f"    FAILED during inspection: "
                f"{error}"
            )

            continue

        # ----------------------------------------------------
        # Check local ingestion state
        # ----------------------------------------------------

        existing_state = state[
            "bundles"
        ].get(file_path.name)

        if existing_state:

            if existing_state.get("status") == "success":

                skipped += 1

                print(
                    "    SKIPPED"
                )

                print(
                    "    Reason: bundle already "
                    "recorded as successfully ingested."
                )

                continue

        # ----------------------------------------------------
        # Check HAPI
        # ----------------------------------------------------

        try:

            existing_patients = (
                find_patient_in_hapi(
                    patient_identifier
                )
            )

            if existing_patients:

                skipped += 1

                print(
                    "    SKIPPED"
                )

                print(
                    "    Reason: patient already "
                    "exists in HAPI."
                )

                print(
                    f"    Matching HAPI patients: "
                    f"{len(existing_patients)}"
                )

                # Record this discovery so future runs
                # do not repeatedly search and report it.
                state["bundles"][
                    file_path.name
                ] = {
                    "status": "skipped_existing",
                    "patient_source_id":
                        patient_identifier,
                    "fhir_entry_count":
                        entry_count,
                    "matching_hapi_patients":
                        len(existing_patients),
                    "checked_at":
                        utc_now()
                }

                save_json(
                    state,
                    STATE_FILE
                )

                continue

        except Exception as error:

            failed += 1

            print(
                f"    FAILED during HAPI "
                f"duplicate check: {error}"
            )

            continue

        # ----------------------------------------------------
        # Submit to HAPI
        # ----------------------------------------------------

        print(
            "    Patient not found in HAPI."
        )

        print(
            "    Submitting transaction..."
        )

        try:

            response_bundle = (
                submit_bundle(
                    file_path
                )
            )

            response_entries = len(
                response_bundle.get(
                    "entry",
                    []
                )
            )

            state["bundles"][
                file_path.name
            ] = {
                "status": "success",
                "patient_source_id":
                    patient_identifier,
                "fhir_entry_count":
                    entry_count,
                "response_entry_count":
                    response_entries,
                "ingested_at":
                    utc_now()
            }

            save_json(
                state,
                STATE_FILE
            )

            processed += 1

            print(
                "    SUCCESS"
            )

            print(
                f"    Response entries: "
                f"{response_entries}"
            )

        except Exception as error:

            failed += 1

            state["bundles"][
                file_path.name
            ] = {
                "status": "failed",
                "patient_source_id":
                    patient_identifier,
                "fhir_entry_count":
                    entry_count,
                "error":
                    str(error),
                "failed_at":
                    utc_now()
            }

            save_json(
                state,
                STATE_FILE
            )

            print(
                f"    FAILED: {error}"
            )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)

    print(
        f"Bundles discovered : {len(bundles)}"
    )

    print(
        f"Processed           : {processed}"
    )

    print(
        f"Skipped             : {skipped}"
    )

    print(
        f"Failed              : {failed}"
    )

    print(
        f"State file          : {STATE_FILE}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()