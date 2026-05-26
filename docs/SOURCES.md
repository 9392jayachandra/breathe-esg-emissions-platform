# SOURCES — Research Behind Each Data Source

---

## 1. SAP — Fuel & Procurement

**Real-world format researched:**
SAP's MM (Materials Management) module stores material movements in table MSEG and document
headers in MKPF. The most common export path for sustainability data is transaction **MB51**
(Material Document List), which exports a flat file with columns including:
- `Posting Date` (Buchungsdatum in German SAP)
- `Quantity` (Menge) and `Unit of Measure` (Mengeneinheit)
- `Material` description and `Plant` code (Werk)
- `Amount in Local Currency` (Betrag in Hauswährung)

German column headers appear by default in German-locale SAP installations, which is common
at multinational companies running SAP ECC or S/4HANA with a German base install.

**What I learned:**
- Units in SAP exports include L, M3, GAL, KG, TON — and sometimes custom UoMs specific to the client
- Plant codes are internal identifiers (e.g. "1000", "BLR1") that mean nothing without a plant
  master data lookup
- Dates appear as DD.MM.YYYY in German locale, YYYY-MM-DD in English locale, or YYYYMMDD in some exports
- Material descriptions are free-text and inconsistent — "HSD Diesel", "Diesel HSD", "HIGH SPEED DIESEL"
  all mean the same thing
- SAP exports from different modules (FI vs MM vs PM) have different structures for the same underlying data

**Why my sample data looks the way it does:**
- Includes German column headers (Buchungsdatum, Menge, Mengeneinheit, Werk) as a realistic default
- Uses plant codes like PLANT_BLR (Bangalore), PLANT_MUM (Mumbai) — simplified vs real SAP codes
- Includes both L (liters) and M3 (cubic meters) and GAL (gallons) to test unit normalization
- Includes a row with 0 quantity (data entry error, should be flagged)
- Includes an implausibly large quantity (200,000 L in a single transaction) to trigger auto-flagging

**What would break in production:**
- Custom units of measure (SAP allows clients to define their own UoMs like "drums", "cylinders")
- Material codes without descriptions — MB51 sometimes exports just the SAP material number (e.g. "000000001234")
- Multi-company SAP installations where plant codes overlap across company codes
- SAP plants mapped to multiple physical locations (one plant = one building vs one plant = one campus)

---

## 2. Utility — Electricity

**Real-world format researched:**
Indian utility portals (BESCOM, MSEDCL, TPDDL, CESC, TNEB) all offer a "consumption history"
CSV download from their customer portals. The format varies but typically includes:
- Meter ID / consumer number
- Billing period start and end dates
- Units consumed (kWh or sometimes in "units" where 1 unit = 1 kWh)
- Tariff category (Commercial HT, Industrial LT, etc.)
- Site/connection name

UK and US utility portals follow similar patterns (Green Button CSV in the US).

**What I learned:**
- Billing periods rarely align to calendar months. BESCOM bills on a ~30-day cycle starting from
  the connection date, not the 1st of the month. A Jan bill might cover Dec 28 – Jan 27.
- "Units" is a common column header in Indian utility exports, where 1 unit = 1 kWh (but this
  is not always stated explicitly)
- Large industrial consumers often have demand charges (kVA) alongside consumption charges (kWh)
  — only kWh is relevant for carbon
- Some portals export in MWh for large consumers (industrial tariff)
- Meter IDs sometimes change when a meter is replaced, breaking time-series continuity

**Why my sample data looks the way it does:**
- Uses realistic meter ID format (MTR-BLR-001)
- Billing periods that cross month boundaries (Dec 28 – Jan 27) to test date handling
- One row in MWh (Chennai Plant on industrial tariff) to test unit conversion
- One implausibly high reading (1,500,000 kWh in one month for a single meter) to trigger flagging
- Multiple sites per upload (HQ, warehouse, branch, lab)

**What would break in production:**
- PDF bills (most SME clients receive PDFs, not portal CSV downloads)
- Utilities that don't offer CSV download at all (some tier-3 utilities in India)
- Time-of-use meters with half-hourly granularity — our model stores one row per billing period
- Solar/net-metering clients where consumption can be negative (export to grid)
- Multiple meters per site with different tariff categories

---

## 3. Corporate Travel — Flights, Hotels, Ground Transport

**Real-world format researched:**
Concur Expense exports (SAP Concur) produce a CSV with columns including:
- Transaction Date
- Expense Type (Air Travel, Hotel, Car Rental, Train, etc.)
- Vendor, Origin, Destination
- Amount, Currency
- Employee Name / Employee ID

Navan (formerly TripActions) exports are similar but use slightly different column names
("Travel Type" vs "Expense Type", "Traveler" vs "Employee Name").

IATA airport codes are used for flight origin/destination (BLR, DEL, LHR, JFK etc.)
Distance is sometimes included in business travel tools (Navan calculates it) but often absent
in older Concur exports where only city names appear.

**What I learned:**
- Flight distance is genuinely absent in many Concur exports — the tool tracks spend, not distance
- "Hotel" records have nights as the meaningful unit, not cost (cost varies wildly by city)
- "Car" entries can mean rental car (distance-based) or taxi (often no distance)
- Business class flights emit ~2x economy class per km — class is often in the expense notes
  but not in a structured field
- Multi-leg trips often appear as separate rows (BLR→DXB and DXB→LHR) with no linking key
- Some platforms export in the employee's home currency, others in the booking currency

**Why my sample data looks the way it does:**
- Includes IATA airport codes for realistic origin/destination (BLR, DEL, LHR, MUM, SIN, JFK)
- Several rows with no distance (flights BLR→DEL, BLR→JFK) to test the missing-distance flag
- Mix of domestic and international travel
- Hotel rows with nights field
- Ground transport mix: car, train, bus
- Multi-currency (INR, GBP, SGD, AED) — stored but not converted (not needed for carbon)

**What would break in production:**
- Airport code pairs not in our lookup — we don't have a lookup at all currently
- Business vs economy class differentiation (our factors assume economy)
- Rail vs car ground transport have different emission factors — we use one ground_transport factor
- Personal car mileage claims (different factor than taxi/fleet)
- Carbon offset purchases that some platforms bundle with travel bookings
