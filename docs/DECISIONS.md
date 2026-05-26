# DECISIONS — BreatheESG Emissions Ingestion Platform

Every ambiguity I resolved, what I chose, and why.

---

## SAP: Which export format?

**Ambiguity:** SAP exposes data via IDoc (EDI-style XML), OData (REST API), BAPI (RFC function calls),
or flat file CSV/XLS. Each has very different integration complexity.

**Decision:** Flat-file CSV export.

**Why:** For an enterprise client onboarding scenario, flat-file CSV is by far the most realistic
first step. Clients typically don't grant API access to their SAP systems immediately — there are
security reviews, IT approvals, and VPN setup involved. The facilities or sustainability lead
can export a CSV from SAP transaction MB51 (material document list) or ME2M (purchase orders)
in 5 minutes without IT involvement.

OData/BAPI would be the right long-term choice for automated ingestion, but for a prototype
that needs to work in 4 days with real client data, CSV wins.

**What I chose to handle:**
- SAP FI/MM flat-file export with German and English column headers
- Columns: Buchungsdatum/posting date, Menge/quantity, Mengeneinheit/unit, Material, Werk/plant
- Fuel categories: diesel, petrol, natural gas, LPG, with keyword detection from material description
- Default fallback to 'procurement' category for unknown materials

**What I ignored:**
- IDoc format (complex XML, requires middleware)
- OData v4 (requires SAP API credentials and network access)
- BAPI/RFC (requires SAP GUI or JCo connector)
- SAP cost center / GL account mapping
- Multi-currency procurement amounts (stored as raw USD equivalent)
- Plant code lookup tables (stored as raw string)

**What I'd ask the PM:**
- Do clients typically export from MB51 (material movements) or MM60 (consumption)?
- Are plant codes mapped to locations in their master data, or do we need to maintain a lookup?
- Will they ever send IDoc format, or is CSV always available?

---

## Utility: Which ingestion mode?

**Ambiguity:** Utility data comes as portal CSV export, PDF bill, or API (if the utility offers one).

**Decision:** Portal CSV export.

**Why:** PDF bills require OCR which is fragile and format-dependent — every utility has a
different layout. Utility APIs exist (e.g. Green Button API in the US, some BESCOM/TPDDL portals
in India) but require per-utility integration work. Portal CSV is the middle ground: most utility
portals (BESCOM, MSEDCL, TPDDL etc.) have a "download consumption data" option that exports
a structured CSV. It's reliable, doesn't require OCR, and doesn't require API credentials.

**What I chose to handle:**
- CSV with meter ID, billing period start, consumption in kWh or MWh, site name
- Handles MWh → kWh conversion
- Billing periods that don't align to calendar months (uses period_start as activity_date)
- Multiple meters per upload

**What I ignored:**
- PDF bill parsing (OCR)
- Reactive power / power factor data (not relevant for carbon)
- Tariff breakdown (we store tariff as a string but don't parse it)
- Time-of-use (ToU) data at sub-hourly granularity
- Renewable energy certificates (RECs) and grid decarbonization factors per meter

**What I'd ask the PM:**
- Which utility portals do their clients actually use? (BESCOM, MSEDCL, TPDDL, etc.)
- Do they have sub-metering at the equipment level, or only building-level meters?
- Do they track renewable energy certificates separately?

---

## Travel: Concur vs Navan vs other?

**Ambiguity:** Corporate travel platforms include Concur (SAP), Navan, TravelPerk, Egencia, etc.

**Decision:** Generic CSV modeled after Concur expense export.

**Why:** Concur is the most common enterprise travel platform and its CSV export is
well-documented. Navan's export format is similar enough that our column mapping handles both.
Rather than building a platform-specific API integration, we accept any CSV that has the
required columns — this is more resilient to platform changes and doesn't require OAuth setup.

**What I chose to handle:**
- Flight, hotel, ground transport (car/taxi/train/bus)
- Distance in km when provided; flagged as missing when absent
- Airport code pairs stored as origin/destination strings
- Hotel nights as the unit (not room cost)

**What I ignored:**
- Distance calculation from airport code pairs (requires a geo-distance lookup table or API)
- Class of travel (economy vs business — factors differ by ~2x)
- Connecting flights (a BLR→LHR via DXB shows as two legs, or one combined)
- Personal vs corporate card spend split
- Travel policy compliance flags

**What I'd ask the PM:**
- What percentage of their client's travel records include distance? (Concur often omits it for hotel/car)
- Do they want business class vs economy differentiated in emission factors?
- Is the travel platform API available, or only CSV export?

---

## Review workflow: who can approve?

**Decision:** Any named analyst can approve. No authentication system.

**Why:** This is a prototype. Building auth (JWT, sessions, role-based access) would take a day
and doesn't demonstrate the core emissions logic. The `reviewed_by` field stores the analyst's name
as a string. In production, this becomes a ForeignKey to a User model with roles.

---

## Deployment target

**Decision:** Railway for backend (Django + SQLite → PostgreSQL), Vercel for frontend (React).

**Why:** Railway auto-detects Django apps, provides managed PostgreSQL, and deploys from GitHub
in under 5 minutes. Vercel handles React builds with zero config. Both have free tiers sufficient
for a prototype.

---

## CO2e emission factors: which standard?

**Decision:** UK BEIS 2023 Greenhouse Gas Conversion Factor tables as the baseline.

**Why:** BEIS factors are publicly available, updated annually, cover all the categories we handle
(fuel combustion, electricity, air travel, hotels, ground transport), and are widely used by
carbon accounting platforms globally. For the India grid electricity factor, we use CEA's
2022-23 national average (0.233 kg CO2e/kWh) as BEIS doesn't publish India-specific grid factors.

In production: factors would be a database table, versioned by year, region, and standard
(BEIS, EPA, IEA, GHG Protocol), configurable per tenant.
