# HealthConnect360
## Healthcare Integration, Patient 360 & Analytics Platform

> **Synthetic healthcare data — not for clinical use.**

HealthConnect360 is a portfolio-grade healthcare data engineering and analytics platform designed to demonstrate how fragmented healthcare information can be integrated, governed, transformed, and analyzed across a fictional multi-facility healthcare network.

The platform uses **Synthea** for synthetic clinical data generation, **HAPI FHIR** as the FHIR interoperability/API layer, and **Microsoft Fabric** for ingestion, orchestration, data quality, transformation, analytical modeling, and Power BI.

---

## 1. Project Vision

> **Create a trusted healthcare data platform that connects clinical information, improves visibility across Northstar Health Network, and provides role-appropriate insights through a governed Microsoft Fabric data platform.**

HealthConnect360 demonstrates both:

- **Business analysis:** requirements, stakeholders, scope, process models, KPIs, acceptance criteria, risks, traceability, and governance.
- **Data engineering:** APIs, FHIR, orchestration, Lakehouse medallion architecture, PySpark, SQL, data quality, lineage, analytical modeling, and Power BI.

---

# 2. Business Context

## Fictional Organization

**Northstar Health Network**

Northstar operates three facilities:

1. **Northstar General Hospital** — acute care, emergency/inpatient services, specialist services.
2. **Northstar Community Clinic** — family and primary care, chronic disease management, follow-up care.
3. **Northstar Diagnostic Centre** — laboratory services, diagnostic imaging, radiology.

### Departments

- Emergency & Urgent Care
- Family & Primary Care
- Cardiology
- Radiology & Diagnostic Imaging
- Laboratory Services
- Pharmacy

---

# 3. Business Problems

HealthConnect360 addresses:

- **Fragmented Patient Information:** information is distributed across multiple systems and facilities.
- **Limited Operational Visibility:** leadership needs unified views of patient volumes, encounters, provider activity, wait times, utilization, and departments.
- **Difficult Population Health Analysis:** analysts need consistent structures for cohorts, conditions, observations, medication exposure, procedures, and diagnostics.
- **Data Quality Issues:** duplicates, missing references, invalid dates/statuses, missing practitioners, inconsistent terminology, and late-arriving records.
- **Interoperability Challenges:** different healthcare systems need a standardized way to exchange clinical information.

---

# 4. Target Architecture

```text
                         NORTHSTAR HEALTH NETWORK
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
       Hospital EHR        Community EHR       Diagnostic LIS/RIS
       Source System       Source System        Source System
              │                   │                   │
              │ FHIR/API          │ FHIR/API          │ FHIR/API
              └───────────────────┼───────────────────┘
                                  ▼
                         Integration Layer
                          & Orchestration
                                  │
                                  ▼
                           HAPI FHIR Server
                          FHIR REST Interface
                                  │
                                  ▼
                     Microsoft Fabric Pipelines
                                  │
                                  ▼
                         Bronze Lakehouse
                      NS_Health_LH_Bronze
                                  │
                                  ▼
                         PySpark / Spark SQL
                   Validation • DQ • Deduplication
                                  │
                                  ▼
                          Silver Lakehouse
                      NS_Health_LH_Silver
                                  │
                                  ▼
                         Gold / SQL Warehouse
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
         Patient 360          Power BI          Future App/API
```

### Architectural Principle

The three facilities are modeled as **independent logical source systems**, but HealthConnect360 does not require three separate HAPI servers.

> **Three logical source systems → standardized FHIR integration → centralized HAPI FHIR interoperability layer → Microsoft Fabric analytics platform.**

This demonstrates multi-source integration and orchestration without unnecessary infrastructure.

---

# 5. Technology Stack

### Healthcare Data & Interoperability
- FHIR R4
- Synthea
- HAPI FHIR
- FHIR REST API
- JSON / NDJSON
- Future: OMOP CDM
- Future: DICOM / imaging metadata

### Data Engineering
- Microsoft Fabric
- Fabric Data Pipelines
- Lakehouse
- Fabric Warehouse
- PySpark
- Spark SQL
- T-SQL
- Python

### Database / Infrastructure
- PostgreSQL 16
- Docker
- Docker Compose

### Analytics
- Power BI
- Semantic models
- DAX

### Governance / Engineering
- Data quality rules
- Quarantine processing
- Audit metadata
- Batch tracking
- Source-system lineage
- RBAC concepts
- Synthetic-data privacy by design
- Git / GitHub

---

# 6. Current Implementation Status

## Phase 0 — Business Analysis & Solution Definition
**Status: Complete**

Completed: business context, vision/objectives, stakeholders, scope, requirements, user stories, acceptance criteria, use cases, DQ, NFRs, KPIs, risks, traceability, and target architecture.

## Phase 1A — Fabric Foundation
**Status: Complete**

Workspace:

```text
HealthConnect360
```

Lakehouses:

```text
NS_Health_LH_Bronze
NS_Health_LH_Silver
```

Setup notebook:

```text
NS_Health_Setup
```

## Phase 1B — Synthetic Healthcare & FHIR Foundation
**Status: In Progress**

### Completed
- Synthea installed
- Java 21 LTS validated
- Synthetic FHIR data generated and inspected
- Docker validated
- HAPI FHIR image downloaded
- HAPI/PostgreSQL Docker Compose configuration created
- Docker Compose configuration validated

### Next
- Start PostgreSQL 16
- Start HAPI FHIR
- Validate FHIR metadata endpoint
- Establish HAPI development environment
- Define three logical source systems
- Map source-system ownership
- Build source-specific integration/orchestration
- Ingest into Bronze

---

# 7. Synthetic Data Strategy

HealthConnect360 uses **Synthea** to generate realistic but synthetic healthcare histories.

The project separates clean source data from controlled data-quality test data.

```text
Clean source-of-truth:
Synthea → Clean synthetic FHIR → HAPI FHIR

Controlled DQ testing:
Synthetic defects → Fabric DQ testing
```

Deliberate defects will not be used to corrupt the clean source system.

---

# 8. Multi-Source Integration Strategy

The three Northstar facilities will behave as independent logical source systems.

## Source System 1 — Hospital EHR

```text
NORTHSTAR_GENERAL_HOSPITAL
```

Primary focus: Emergency, inpatient, cardiology, pharmacy.

Expected data: Patient, Practitioner, Encounter, Condition, Observation, MedicationRequest, Procedure, DiagnosticReport.

## Source System 2 — Community EHR

```text
NORTHSTAR_COMMUNITY_CLINIC
```

Primary focus: Primary care, chronic disease, follow-up.

Expected data: Patient, Practitioner, Encounter, Condition, Observation, MedicationRequest.

## Source System 3 — Diagnostic System

```text
NORTHSTAR_DIAGNOSTIC_CENTRE
```

Primary focus: Laboratory, radiology, diagnostic imaging.

Expected data: Patient, Practitioner, Observation, DiagnosticReport, ImagingStudy.

---

# 9. Why Three Source Systems?

The three-source design allows HealthConnect360 to demonstrate:

- Multi-source ingestion
- Source-system identification
- API integration
- Orchestration
- Incremental loading
- Cross-system patient identity
- Referential integrity
- Data reconciliation
- Source-specific data quality
- Late-arriving data
- Lineage
- Patient 360 across facilities

Example:

```text
Patient P000123
       │
       ├── Community Clinic
       │      └── Primary-care encounter
       ├── General Hospital
       │      └── Emergency encounter
       └── Diagnostic Centre
              ├── Laboratory observation
              └── Diagnostic report
```

---

# 10. HAPI FHIR Role

HAPI FHIR provides the project's development FHIR interoperability layer.

```text
Northstar Source Systems
          │
          ▼
     FHIR Integration
          │
          ▼
     HAPI FHIR Server
          │
          ▼
 Microsoft Fabric
```

HAPI FHIR is not intended to represent three separate transactional hospital databases. The three facilities are modeled through source-system identifiers, Organizations, Locations, resource ownership, source metadata, integration pipelines, and extraction logic.

---

# 11. FHIR Resources

### MVP
- Patient
- Practitioner
- Organization
- Encounter
- Condition
- Observation
- MedicationRequest

### Later
- Procedure
- DiagnosticReport
- ImagingStudy
- Medication
- MedicationAdministration
- AllergyIntolerance
- CareTeam
- CarePlan

Synthea produces a richer resource set than the initial MVP; expansion will therefore be controlled by release phase.

---

# 12. Bronze Layer

Lakehouse: `NS_Health_LH_Bronze`

Bronze contains raw/near-raw source data and ingestion metadata.

Expected metadata:

```text
source_system
source_endpoint
resource_type
resource_id
batch_id
ingestion_timestamp
source_filename
record_hash
ingestion_status
```

> **Do not clean the source data in Bronze.**

Bronze preserves source fidelity and supports auditability and replay.

---

# 13. Silver Layer

Lakehouse: `NS_Health_LH_Silver`

Expected tables:

```text
silver_patient
silver_practitioner
silver_organization
silver_encounter
silver_condition
silver_observation
silver_procedure
silver_medication
silver_diagnostic_report
```

Processing will include schema enforcement, FHIR parsing, standardization, deduplication, referential integrity, date/status validation, reference validation, terminology normalization, and DQ classification.

---

# 14. Data Quality & Quarantine

| Rule | Example |
|---|---|
| Patient ID | Required |
| Patient uniqueness | No duplicate active identity |
| Resource type | Must be supported |
| Patient reference | Must resolve |
| Practitioner reference | Must resolve where required |
| Encounter dates | Must parse |
| Status | Must be valid |
| Duplicate records | Detect and classify |
| Required attributes | Must exist |
| Late-arriving records | Track |

Failed records will be captured in `dq_quarantine` with fields such as:

```text
batch_id
source_system
resource_type
resource_id
error_type
error_message
raw_record
detected_at
```

---

# 15. Gold Analytical Layer

The Gold layer will use SQL-based analytical structures.

### Dimensions
- DimPatient
- DimPractitioner
- DimOrganization
- DimLocation
- DimDate
- DimCondition
- DimMedication

### Facts
- FactEncounter
- FactObservation
- FactProcedure
- FactMedication
- FactDiagnostic

---

# 16. Patient 360

Patient 360 is a core business outcome.

```text
Patient
├── Demographics
├── Primary Provider
├── Facilities Used
├── Active Conditions
├── Medications
├── Encounters
├── Laboratory Results
├── Procedures
├── Diagnostic Reports
└── Care Timeline
```

The cross-facility history demonstrates how information from independent source systems can be consolidated into one analytical view.

---

# 17. Power BI Analytics

### Executive Dashboard
Patient volume, encounter volume, facility utilization, department activity, wait times, provider activity.

### Population Health
Condition prevalence, age distribution, cohorts, medication exposure, encounter patterns.

### Data Engineering / DQ
Records processed/failed, DQ failure rate, duplicates, pipeline duration, late-arriving records, source-system volume.

### Research
Cohort size, condition distribution, treatment exposure, outcomes.

---

# 18. OMOP CDM

OMOP will be introduced after the clinical FHIR analytical model is stable.

```text
FHIR → Silver Clinical Model → OMOP CDM → Population / Research Analytics
```

Planned terminology standards include SNOMED CT, LOINC, and RxNorm.

---

# 19. DICOM & Imaging

DICOM will be introduced later, initially focusing on imaging metadata rather than large medical-image files.

```text
Patient → Encounter → DiagnosticReport → ImagingStudy → Imaging Metadata
```

Potential modalities: CT, MRI, X-Ray, Ultrasound.

---

# 20. Future Real-Time Architecture

```text
Emergency Event
      │
      ▼
Eventstream
      │
      ▼
Eventhouse
      │
      ▼
Real-Time Analytics
      │
      ▼
Operational Dashboard
```

Potential use cases include emergency activity, patient arrival events, lab-result events, and utilization monitoring.

---

# 21. Future AI Capability

A later phase may demonstrate AI-assisted clinical information summarization using synthetic data.

```text
FHIR / Patient 360 → AI Summarization → Practitioner-oriented summary
```

> **Decision-support prototype — not medical advice.**

Potential audit/evaluation metadata includes prompt/model information, timestamp, patient context, evaluation results, and output audit information.

---

# 22. Security & RBAC

| Role | Access Concept |
|---|---|
| Patient | Own synthetic records |
| Practitioner | Assigned/authorized patients |
| Administrator | Operational information |
| Analyst | Aggregated/approved analytical data |
| Researcher | De-identified research data |
| Data Engineer | Technical, DQ and audit information |

Eventual application/API architecture:

```text
User → Web Application → API / Backend → Operational Data / Fabric Analytics
```

Power BI/Fabric is not intended to function as the transactional patient-management application.

---

# 23. Business Analysis Artifacts

The project maintains professional BA documentation covering executive summary, business context, vision/objectives, stakeholders, scope, assumptions, business/functional requirements, user stories, acceptance criteria, use cases, process models, data requirements, DQ rules, NFRs, security/access, KPIs, release plan, risks, RTM, glossary, BA-to-Fabric handoff, and Definition of Done.

---

# 24. Business Requirements

| ID | Requirement | Priority |
|---|---|---|
| BR-001 | Provide an integrated analytical patient history | Must |
| BR-002 | Identify and manage data-quality failures | Must |
| BR-003 | Provide operational healthcare visibility | Must |
| BR-004 | Provide role-appropriate access | Must |
| BR-005 | Maintain source and ingestion traceability | Must |
| BR-006 | Standardize clinical analytical structures | Must |
| BR-007 | Support future OMOP analytics | Should |
| BR-008 | Support future imaging/DICOM integration | Should |
| BR-009 | Support future real-time and AI capabilities | Could |

---

# 25. Functional Requirements

| ID | Requirement |
|---|---|
| FR-001 | Ingest valid FHIR resources |
| FR-002 | Capture batch IDs and ingestion timestamps |
| FR-003 | Validate resource IDs and resource types |
| FR-004 | Validate resource references |
| FR-005 | Validate dates and statuses |
| FR-006 | Quarantine invalid records |
| FR-007 | Detect and manage duplicates |
| FR-008 | Create cleaned Silver structures |
| FR-009 | Create analytical fact/dimension structures |
| FR-010 | Provide Patient 360 |
| FR-011 | Provide operational KPIs |
| FR-012 | Provide data-quality KPIs |
| FR-013 | Support role-based access concepts |
| FR-014 | Maintain audit metadata |
| FR-015 | Prepare OMOP transformation |
| FR-016 | Link diagnostic and imaging information |

---

# 26. Release Roadmap

## MVP-0 — BA & Solution Definition
**Complete**

## MVP-1A — Source Systems & FHIR Foundation
**In Progress**

- Synthea
- Three logical source systems
- HAPI FHIR
- FHIR resources
- Organization/location/source mappings

## MVP-1B — Integration & Bronze

- FHIR/API extraction
- Source-specific orchestration
- Fabric pipelines
- Incremental ingestion
- Batch control
- Audit metadata
- Bronze Lakehouse

## MVP-2 — Data Quality & Silver

- PySpark
- Schema validation
- Deduplication
- Referential integrity
- Quarantine
- Standardization
- Silver Lakehouse

## MVP-3 — Gold & SQL

- Dimensions
- Facts
- SQL transformations
- Analytical model
- Data reconciliation

## MVP-4 — Power BI

- Executive dashboard
- Population-health dashboard
- Data-engineering/DQ dashboard
- Research analytics

## MVP-5 — Patient 360

- Cross-facility patient timeline
- Clinical summary
- Facility utilization
- Patient-level analytical view

## V2 — OMOP

- Clinical-to-OMOP mapping
- Standard vocabulary concepts
- Research analytics

## V3 — DICOM

- Imaging metadata
- Diagnostic linkage

## V4 — Application & RBAC

- Web application
- API/backend
- Role-based access
- Patient/practitioner/admin experiences

## V5 — Real-Time

- Eventstream
- Eventhouse
- Real-time operational analytics

## V6 — AI & Observability

- AI-assisted summaries
- Evaluation
- OpenTelemetry
- LangSmith/observability concepts
- Auditability

---

# 27. Repository Structure

```text
healthconnect360/
│
├── README.md
├── architecture/
│   ├── architecture.png
│   ├── data-flow.png
│   ├── fhir-model.png
│   └── security-model.png
│
├── data/
│   ├── synthetic/
│   │   └── fhir/
│   │       ├── patient/
│   │       ├── practitioner/
│   │       ├── organization/
│   │       ├── encounter/
│   │       ├── condition/
│   │       ├── observation/
│   │       └── medicationrequest/
│   ├── schemas/
│   └── terminology/
│
├── fabric/
│   ├── pipelines/
│   ├── notebooks/
│   ├── sql/
│   └── semantic-model/
│
├── healthcare/
│   ├── fhir/
│   ├── omop/
│   └── dicom/
│
├── app/
│   ├── frontend/
│   ├── backend/
│   └── auth/
│
├── powerbi/
├── data-quality/
├── docs/
│   ├── requirements.md
│   ├── data-dictionary.md
│   ├── terminology.md
│   └── security.md
└── tests/
```

---

# 28. Target Synthetic Data Volumes

| Resource | Target |
|---|---:|
| Patients | 10,000 |
| Practitioners | 300 |
| Organizations | 5 |
| Encounters | 75,000 |
| Conditions | 40,000 |
| Observations | 500,000 |
| Procedures | 25,000 |
| MedicationRequests | 60,000 |
| DiagnosticReports | 20,000 |

Actual Synthea output may exceed the MVP resource scope. Resource expansion will therefore be controlled by release phase.

---

# 29. Data Quality Test Scenarios

Controlled test data will eventually include:

- Duplicate observations
- Duplicate patients
- Missing patient references
- Missing practitioner references
- Invalid dates
- Invalid statuses
- Missing required attributes
- Inconsistent terminology
- Late-arriving records

```text
Valid
  │
  ├──► Process
  └──► Analytical layer

Invalid
  │
  └──► Quarantine → DQ reporting
```

---

# 30. Privacy & Responsible Use

HealthConnect360 uses synthetic healthcare data. It is **not** intended for clinical use and does not process real patient information.

The project follows data-minimization principles wherever practical. Synthetic identifiers that are not required for an analytical use case should not automatically be propagated into Gold or Patient 360.

---

# 31. Definition of Done

A release is considered complete when:

- Requirements are documented
- Architecture is updated
- Implementation is reproducible
- Data quality is validated
- Errors are handled
- Lineage is captured
- Tests are documented
- Analytical outputs reconcile to source data
- Documentation reflects the actual implementation
- Portfolio evidence is captured where appropriate

---

# 32. Portfolio Demonstration Story

```text
Business Problem
      │
      ▼
Business Analysis
      │
      ▼
Healthcare Source Systems
      │
      ▼
FHIR Interoperability
      │
      ▼
API Integration
      │
      ▼
Fabric Orchestration
      │
      ▼
Bronze
      │
      ▼
PySpark + Data Quality
      │
      ▼
Silver
      │
      ▼
SQL / Gold
      │
      ▼
Patient 360
      │
      ▼
Power BI
```

The project combines **healthcare interoperability, data engineering, analytics, business analysis, governance, and future application development** in one coherent portfolio solution.

---

# 33. Current Environment

## Microsoft Fabric

Workspace:

```text
HealthConnect360
```

Lakehouses:

```text
NS_Health_LH_Bronze
NS_Health_LH_Silver
```

Notebook:

```text
NS_Health_Setup
```

## Local Development

```text
HealthConnect360/
├── synthea/
└── hapi-fhir/
```

Current database configuration:

```text
PostgreSQL 16
```

Planned local HAPI development endpoint:

```text
http://localhost:8080/fhir/
```

> The endpoint is for the local development environment and is not a production healthcare service.

---

# 34. Project Status

**Current phase: Phase 1B — Healthcare Source Integration & FHIR Foundation**

### Completed

- Business analysis foundation
- Fabric workspace
- Bronze Lakehouse
- Silver Lakehouse
- Setup notebook
- Synthea installation
- Synthetic FHIR generation
- FHIR resource inspection
- Docker environment
- HAPI FHIR image
- HAPI/PostgreSQL Compose configuration

### In Progress

- PostgreSQL/HAPI runtime
- FHIR server validation
- Multi-source integration design

### Next Major Milestone

> **Establish a functioning HAPI FHIR server and implement the first Northstar source-system integration into Microsoft Fabric Bronze.**

---

# 35. Disclaimer

HealthConnect360 is an educational and portfolio project.

All healthcare data is synthetic and intended solely for demonstrating data engineering, interoperability, analytics, business analysis, and software architecture concepts.

**Synthetic healthcare data — not for clinical use.**
