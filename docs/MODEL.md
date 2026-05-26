# DATA MODEL — BreatheESG Emissions Ingestion Platform

## Overview

The model has four tables: `Tenant`, `DataSource`, `EmissionRecord`, and `AuditLog`.
Each layer answers a different question:

- **Tenant** — whose data is this?
- **DataSource** — where did this batch come from, and when?
- **EmissionRecord** — what was the emission event, normalized and classified?
- **AuditLog** — what changed, who changed it, and when?

---

## Tables

### Tenant
Represents a client company. Every record in the system belongs to a tenant.
Multi-tenancy is enforced at the application layer — all queries filter by `tenant_id`.
We chose application-level rather than row-level security (PostgreSQL RLS) because:
- It's simpler to reason about for a prototype
- The analyst UI is not multi-user in this version
- RLS can be added later without schema changes

Fields: `id` (UUID), `name`, `slug`, `created_at`

---

### DataSource
One row per upload event. This is the provenance layer.
Every `EmissionRecord` has a foreign key to its `DataSource`, so you can always answer:
"Which file produced this row? When was it uploaded? Did it fail?"

This matters for audits: auditors want to know the chain of custody for each number.

Fields: `id`, `tenant`, `source_type` (SAP/UTILITY/TRAVEL), `uploaded_file`, `original_filename`, `uploaded_at`, `status`, `row_count`, `error_message`

Status transitions: PENDING → PROCESSING → DONE / FAILED

---

### EmissionRecord
The normalized emission event. One row = one measurable activity.

**Why we store both raw and normalized values:**
Raw values are immutable — they represent exactly what the client sent. We never modify them.
Normalized values are our interpretation. If our conversion factor was wrong and we re-process,
we can update `normalized_quantity` while `raw_quantity` stays as evidence.

**Scope classification:**
- Scope 1: Direct emissions from owned/controlled sources (diesel, petrol, natural gas, LPG combustion)
- Scope 2: Indirect emissions from purchased electricity
- Scope 3: Value chain emissions (business travel, procurement)

Scope is set at ingestion time based on category, not re-derived. This means if an analyst
reclassifies a record, the scope field reflects their judgment, and the `AuditLog` records the change.

**Review workflow states:**
```
PENDING → APPROVED (locked)
PENDING → FLAGGED → APPROVED or REJECTED
PENDING → REJECTED
```

Once a record is APPROVED, `is_locked = True` prevents further edits.
This is the "sign-off before audit" requirement.

**Auto-flagging logic:**
The parser automatically flags rows where:
- Quantity is zero or negative
- Electricity reading > 1,000,000 kWh (unusually large for a single meter)
- Fuel quantity > 100,000 L (unusually large for a single transaction)
- Flight distance > 20,000 km (longer than any real flight)
- Flight distance is missing entirely (common in travel exports)

Flagged rows appear in the review dashboard with the flag reason. The analyst decides
whether to approve, reject, or request correction.

**Unit normalization:**
All quantities are normalized to a standard unit per category:
- Fuel: liters
- Electricity: kWh
- Distance: km
- Hotel stays: nights

Conversion factors are in `parsers.py`. Unknown units are kept as-is and flagged.

**CO2e calculation:**
We use UK BEIS 2023 emission factors as the baseline:
- Diesel: 2.68 kg CO2e/L
- Petrol: 2.31 kg CO2e/L
- Natural gas: 2.02 kg CO2e/m3
- LPG: 1.51 kg CO2e/L
- Electricity (India grid): 0.233 kg CO2e/kWh (CEA 2022-23 annual report)
- Flights (economy): 0.255 kg CO2e/km (BEIS passenger km, includes radiative forcing)
- Hotels: 31 kg CO2e/night (BEIS hotel stay factor)
- Ground transport: 0.089 kg CO2e/km (average car, BEIS)

In a production system, these would be configurable per tenant and updated annually.

---

### AuditLog
Immutable append-only log. One row per field change.
Records: which record changed, which field, old value, new value, who made the change, when.
Actions: UPDATE (field edit), APPROVE, REJECT, FLAG.

We do not delete audit log entries. This is the legal trail for GHG reporting.

---

## Design Decisions

**UUIDs as primary keys:**
Avoids sequential ID guessing in multi-tenant APIs. Also safer for external-facing URLs.

**Source type on DataSource, not EmissionRecord:**
Each upload is one source type. The source type is a property of the batch, not each row.
If a row needs a different scope than its default, the analyst can flag it.

**No soft-deletes:**
Deleted records would complicate audit trails. We use REJECTED status instead of deletion.

**SQLite for development, PostgreSQL for production:**
Settings auto-detect `DATABASE_URL` environment variable.
SQLite is fine for the prototype; Railway/Render provide PostgreSQL.

---

## What's NOT in this model (and why)

1. **Emission factors as a table:** In production, `EmissionFactor` would be its own model,
   versioned by year and region. We hardcoded them to ship faster.

2. **User authentication model:** We use `reviewed_by` as a plain string (name).
   Production would have `ForeignKey(User)`.

3. **Partial period proration for utility bills:** Billing periods that don't align with
   calendar months (e.g. Dec 28 – Jan 27) are stored with `activity_date = period_start`.
   Production would prorate across months.
