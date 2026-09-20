# HealthConnect360 --- Source-to-Target Mapping Specification

> **Status:** Draft v1.0\
> **Phase:** Phase 1B --- Healthcare Source Integration & FHIR
> Foundation\
> **Target:** `NS_Health_LH_Bronze`\
> **Data:** Synthetic healthcare data only

## 1. Purpose

This document defines how HealthConnect360 receives synthetic FHIR
resources from the Synthea/HAPI FHIR integration flow and represents
them in the Microsoft Fabric Bronze layer.

The mapping is designed to preserve source fidelity, source-system
lineage, incremental processing, patient identity, FHIR references,
auditability, replayability, and a stable handoff to PySpark/Silver.

Bronze is **not** the clinical analytical model. Clinical parsing,
standardization, deduplication, terminology normalization, and
referential-integrity validation occur downstream.

## 2. Architecture Context

``` text
Synthea
   |
   | FHIR transaction bundles
   v
Python ingestion
   |
   | source classification + batch metadata
   v
HAPI FHIR
   |
   | FHIR REST extraction
   v
Microsoft Fabric
   |
   v
NS_Health_LH_Bronze
   |
   +--> bronze_fhir_resource
   |
   +--> bronze_ingestion_control
   |
   v
PySpark / DQ
   |
   v
NS_Health_LH_Silver
```

The three Northstar facilities are modeled as independent logical source
systems:

-   `NORTHSTAR_GENERAL_HOSPITAL`
-   `NORTHSTAR_COMMUNITY_CLINIC`
-   `NORTHSTAR_DIAGNOSTIC_CENTRE`

The original Synthea organization identity remains available for
provenance.

## 3. Bronze Design Principles

### 3.1 Preserve source fidelity

The original FHIR resource is retained as `raw_fhir_json`. Bronze must
not silently rewrite, clean, standardize, or discard source attributes.

### 3.2 Separate source identity from business classification

Example:

``` text
source_organization_name
    CAPE COD HOSPITAL INC

northstar_facility
    Northstar General Hospital
```

The second value is a HealthConnect360 classification for the synthetic
integration scenario; it does not replace the original source identity.

### 3.3 Preserve patient identity

The source patient identifier and enterprise HealthConnect360 patient
identifier are separate:

``` text
source_patient_id
        |
        v
Patient Identity Map
        |
        v
hc360_patient_id
```

### 3.4 Preserve FHIR relationships

FHIR references such as Patient, Practitioner, Organization, Location,
Encounter, and MedicationRequest references remain available for
downstream resolution.

## 4. Bronze Common Metadata Mapping

  -------------------------------------------------------------------------------------------------------------------
  Target field                 Source                   Transformation          Required       Purpose
  ---------------------------- ------------------------ ----------------------- -------------- ----------------------
  `batch_id`                   Pipeline execution       Generate once per       Yes            Groups records from
                                                        pipeline run                           one execution

  `source_system`              Source mapping           Lookup/classify source  Yes            Logical Northstar
                                                        organization                           source

  `northstar_facility`         Source mapping           Lookup/classification   Where          Business facility
                                                                                determinable   

  `source_organization_id`     FHIR                     Resolve original source Conditional    Source provenance
                               Organization/reference   organization ID                        

  `source_organization_name`   FHIR Organization        Preserve original name  Conditional    Source provenance

  `source_file`                Synthea filesystem       Preserve originating    Yes for        File lineage
                                                        bundle filename         Synthea        

  `source_patient_id`          `Patient.id` / patient   Resolve and preserve    Conditional    Source patient
                               reference                source patient ID                      identity

  `hc360_patient_id`           Patient Identity Map     Lookup existing or      Conditional    Enterprise
                                                        create enterprise ID                   longitudinal identity

  `resource_type`              FHIR `resourceType`      Preserve exactly        Yes            FHIR resource
                                                                                               classification

  `resource_id`                FHIR `id`                Preserve exactly        Yes            Source resource
                                                                                               identity

  `record_hash`                Full resource            SHA-256 of canonical    Yes            Deduplication/change
                                                        serialized resource                    detection

  `ingestion_timestamp`        Pipeline                 UTC timestamp           Yes            Audit

  `ingestion_status`           Pipeline                 `SUCCESS`, `FAILED`,    Yes            Processing status
                                                        `QUARANTINED`, etc.                    

  `raw_fhir_json`              Entire FHIR resource     Preserve source payload Yes            Source fidelity/replay
  -------------------------------------------------------------------------------------------------------------------

## 5. Patient Mapping

Primary source identity:

``` text
Patient.id
```

Target fields include `resource_type`, `resource_id`,
`source_patient_id`, `hc360_patient_id`, `raw_fhir_json`, `record_hash`,
and `source_file`.

Identity rule:

``` text
Synthea Patient UUID
        |
        v
Patient Identity Map
        |
        v
P000001
```

If the same patient later appears through another Northstar source
system, identity resolution should reuse the existing HC360 patient
rather than create another enterprise patient.

## 6. Organization Mapping

Relevant FHIR fields:

``` text
Organization.id
Organization.identifier
Organization.name
Organization.type
```

Map to:

-   `resource_type`
-   `resource_id`
-   `source_organization_id`
-   `source_organization_name`
-   `source_system`
-   `northstar_facility`
-   `raw_fhir_json`

Example:

``` text
source_organization_id
497f39dd-280e-3d58-af5b-c5e3a3a09b10

source_organization_name
CAPE COD HOSPITAL INC

source_system
NORTHSTAR_GENERAL_HOSPITAL

northstar_facility
Northstar General Hospital
```

The source organization itself is not renamed.

## 7. Practitioner Mapping

Relevant source fields:

``` text
Practitioner.id
Practitioner.identifier
Practitioner.name
Practitioner.gender
```

Map to:

-   `resource_type`
-   `resource_id`
-   `source_practitioner_npi` where the identifier system is NPI
-   `raw_fhir_json`
-   `record_hash`

Practitioner-to-Organization relationships remain in the FHIR structures
and are resolved downstream.

## 8. Encounter Mapping

Relevant fields:

``` text
Encounter.id
Encounter.status
Encounter.class
Encounter.subject
Encounter.participant
Encounter.serviceProvider
Encounter.location
Encounter.period
```

Map:

  --------------------------------------------------------------------------------
  Target field               FHIR source                   Transformation
  -------------------------- ----------------------------- -----------------------
  `resource_type`            `Encounter.resourceType`      Preserve

  `resource_id`              `Encounter.id`                Preserve

  `source_patient_id`        `Encounter.subject`           Resolve patient
                                                           reference

  `hc360_patient_id`         Patient Identity Map          Lookup

  `source_organization_id`   `Encounter.serviceProvider`   Resolve source
                                                           organization

  `source_system`            Source mapping                Lookup

  `northstar_facility`       Source mapping                Lookup

  `raw_fhir_json`            Entire Encounter              Preserve
  --------------------------------------------------------------------------------

The complete FHIR reference structure remains in `raw_fhir_json`.

## 9. Condition Mapping

Relevant fields:

``` text
Condition.id
Condition.subject
Condition.encounter
Condition.code
Condition.clinicalStatus
Condition.verificationStatus
Condition.onset
```

Map:

-   `resource_type`
-   `resource_id`
-   `source_patient_id`
-   `hc360_patient_id`
-   `source_reference` where needed
-   `source_system`
-   `northstar_facility`
-   `raw_fhir_json`

Clinical terminology is not standardized in Bronze.

## 10. Observation Mapping

Relevant fields:

``` text
Observation.id
Observation.status
Observation.subject
Observation.encounter
Observation.code
Observation.value[x]
Observation.effective[x]
Observation.referenceRange
```

Map:

-   `resource_type`
-   `resource_id`
-   `source_patient_id`
-   `hc360_patient_id`
-   `source_system`
-   `northstar_facility`
-   `raw_fhir_json`
-   `record_hash`

Observation code/value/unit parsing belongs in Silver.

## 11. MedicationRequest Mapping

Relevant fields:

``` text
MedicationRequest.id
MedicationRequest.status
MedicationRequest.subject
MedicationRequest.encounter
MedicationRequest.requester
MedicationRequest.medication[x]
MedicationRequest.authoredOn
```

Map:

-   `resource_type`
-   `resource_id`
-   `source_patient_id`
-   `hc360_patient_id`
-   `source_system`
-   `northstar_facility`
-   `raw_fhir_json`

Medication terminology and status validation belong downstream.

## 12. FHIR Reference Handling

FHIR references must not be discarded.

Examples include:

``` text
urn:uuid:<id>
```

``` text
Practitioner?identifier=http://hl7.org/fhir/sid/us-npi|9999992198
```

``` text
Organization?identifier=https://github.com/synthetichealth/synthea|497f39dd-280e-3d58-af5b-c5e3a3a09b10
```

### Bronze rule

Preserve the original reference. Do not replace it with an analytical
foreign key in Bronze.

### Silver rule

Resolve the reference into the appropriate source or enterprise key.

``` text
FHIR reference
      |
      v
Reference resolution
      |
      v
source_organization_id
      |
      v
source_system
      |
      v
northstar_facility
```

## 13. Patient Identity Resolution

Target structure:

``` text
Patient_Identity_Map
----------------------------
hc360_patient_id
source_system
source_patient_id
source_identifier_system
source_identifier_value
match_method
match_confidence
first_seen_at
last_seen_at
status
```

For the current Synthea implementation, exact source identifier matching
is the initial method.

## 14. Source-System Classification

The classification flow is:

``` text
Synthea Organization
        |
        v
source_system_mapping
        |
        +--> service_category
        |
        +--> facility_code
        |
        +--> facility_name
```

The original Synthea organization remains unchanged.

The Diagnostic Centre classification will be introduced through
controlled routing/classification rather than by modifying Synthea's
native organizations.

## 15. Record Hash / Idempotency

Conceptually:

``` text
canonical FHIR resource
        |
        v
SHA-256
        |
        v
record_hash
```

The hash supports duplicate detection, change detection, incremental
processing, and replay.

The source resource ID remains the primary source identity.

## 16. Ingestion Control

A separate control structure records pipeline execution:

``` text
bronze_ingestion_control
----------------------------
batch_id
source_system
source_file
patient_source_id
resource_count
ingestion_started_at
ingestion_completed_at
status
error_message
```

This allows the pipeline to answer which batch was processed, which
source produced it, how many resources were received, whether it
succeeded, and when it started and finished.

## 17. Bronze-to-Silver Handoff

Bronze:

``` text
Raw FHIR
+
Provenance
+
Ingestion metadata
+
Source identity
```

Silver:

``` text
Parsed FHIR
+
Standardized structures
+
Resolved references
+
Enterprise patient identity
+
DQ classification
+
Deduplication
```

Example:

``` text
Bronze Encounter
        |
        v
PySpark
        |
        +--> Patient reference resolution
        +--> Practitioner resolution
        +--> Organization resolution
        +--> Date validation
        +--> Status validation
        +--> Duplicate detection
        |
        v
silver_encounter
```

## 18. MVP Resource Mapping Summary

  --------------------------------------------------------------------------------------------------
  FHIR resource              Bronze status     Primary identity                Patient relationship
  -------------------------- ----------------- ------------------------------- ---------------------
  Patient                    MVP               `Patient.id`                    Self

  Practitioner               MVP               `Practitioner.id` / NPI         None directly

  Organization               MVP               `Organization.id`               None

  Encounter                  MVP               `Encounter.id`                  `subject`

  Condition                  MVP               `Condition.id`                  `subject`

  Observation                MVP               `Observation.id`                `subject`

  MedicationRequest          MVP               `MedicationRequest.id`          `subject`

  Procedure                  Later             `Procedure.id`                  `subject`

  DiagnosticReport           Later             `DiagnosticReport.id`           `subject`

  ImagingStudy               Later             `ImagingStudy.id`               `subject`

  Medication                 Later             `Medication.id`                 Reference-dependent

  MedicationAdministration   Later             `MedicationAdministration.id`   `subject`

  CareTeam                   Later             `CareTeam.id`                   `subject`

  CarePlan                   Later             `CarePlan.id`                   `subject`
  --------------------------------------------------------------------------------------------------

## 19. Implementation Sequence

``` text
1. Common Bronze metadata
       ↓
2. Source-system mapping
       ↓
3. Patient identity resolution
       ↓
4. FHIR resource extraction
       ↓
5. Record hashing
       ↓
6. Bronze write
       ↓
7. Ingestion control
       ↓
8. Incremental/idempotent processing
       ↓
9. PySpark/Silver
```

## 20. Definition of Done

-   Every Bronze record has a batch ID.
-   Source-system classification is captured where determinable.
-   Original source organization identity is preserved.
-   Source patient identity is preserved.
-   An enterprise HC360 patient identity can be resolved.
-   FHIR resource type and ID are retained.
-   Raw FHIR payload is preserved.
-   Deterministic record hashing is implemented.
-   Ingestion status and timestamp are captured.
-   FHIR references remain available.
-   Ingestion batches are auditable.
-   Duplicate/replay processing does not create uncontrolled duplicates.
-   Bronze can be replayed into downstream processing.

## 21. Design Boundary

This specification does not define:

-   Silver physical schemas;
-   Gold dimensional models;
-   OMOP mappings;
-   DICOM mappings;
-   Power BI semantic models;
-   clinical terminology transformations;
-   production healthcare security controls.

Those belong to later project phases.

**Bronze's responsibility is source fidelity, provenance, ingestion
metadata, identity preservation, and replayability.**

------------------------------------------------------------------------

## HealthConnect360

**Healthcare Integration • Patient 360 • Data Engineering • Microsoft
Fabric • Business Analysis**

> Synthetic healthcare data --- not for clinical use.
