# TRADEOFFS — Three Things I Deliberately Did Not Build

---

## 1. Authentication and Role-Based Access Control

**What it would look like:** JWT or session-based login, analyst vs admin vs auditor roles,
per-tenant user management, approval workflows that require sign-off from a specific named user.

**Why I didn't build it:**
Authentication is well-understood infrastructure, not the hard part of this problem.
Building it correctly (password hashing, token refresh, role enforcement at the API layer)
would consume roughly a day of the 4-day window, crowding out the data model and ingestion
logic that actually demonstrates ESG domain understanding.

The prototype uses `reviewed_by` as a plain string input. The data model is designed so that
switching to a `ForeignKey(User)` requires changing one field and no structural rethink.

**What breaks in production:** Anyone can approve or reject any record. There's no separation
between analyst (can review) and auditor (can lock for final sign-off).

---

## 2. Distance Calculation from Airport Codes

**What it would look like:** When a travel record has `origin=BLR, destination=LHR` but no
distance, calculate the great-circle distance using a geo-distance library or lookup table
of IATA airport coordinates. Emit a calculated distance (with a flag indicating it was
derived, not provided).

**Why I didn't build it:**
The data model is ready for it — `flag_reason` already marks "Distance missing — needs manual entry."
The calculation itself is straightforward (haversine formula + IATA airport coordinate DB).
But embedding a 10,000-row airport coordinate lookup table is infrastructure overhead that
doesn't change the architecture. The analyst review workflow handles the gap: flagged rows
appear prominently and can be corrected manually.

**What breaks in production:** All travel records without explicit distances have `co2e_kg = 0`
until manually corrected. For a client with heavy international travel, this understates
Scope 3 significantly until review is complete.

---

## 3. Configurable Emission Factors per Tenant

**What it would look like:** An `EmissionFactor` model with fields for category, year, region,
standard (BEIS/EPA/GHG Protocol), and CO2e value. Tenants can select which factor set applies
to them (a US client might prefer EPA factors; a EU client might prefer DEFRA). Factors are
versioned — historical records retain the factor that was in use when they were created.

**Why I didn't build it:**
This is the right long-term design, but it adds a layer of complexity that would make the
prototype harder to explain in a review. Hardcoded factors in `parsers.py` are visible,
debuggable, and easy to reason about. The factors I chose (BEIS 2023, CEA grid) are documented
in DECISIONS.md so reviewers understand the source.

**What breaks in production:** Clients in different geographies get the same grid emission
factor (India CEA) regardless of where their facilities are. A client with US facilities
would use India's grid factor for their electricity — significantly wrong.
US grid average is ~0.386 kg CO2e/kWh vs India's 0.233 kg CO2e/kWh.
