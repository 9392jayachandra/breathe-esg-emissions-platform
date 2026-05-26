"""
Parsers for each data source type.
Each parser reads a CSV/file, validates rows, normalizes units,
and returns a list of dicts ready to become EmissionRecords.
"""
import pandas as pd
import io
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Unit normalization helpers
# ---------------------------------------------------------------------------

UNIT_CONVERSIONS = {
    # Volume → liters
    'l': 1.0, 'liter': 1.0, 'liters': 1.0, 'litre': 1.0, 'litres': 1.0,
    'ml': 0.001,
    'gal': 3.78541, 'gallon': 3.78541, 'gallons': 3.78541,
    'm3': 1000.0, 'cbm': 1000.0,
    # Energy → kWh
    'kwh': 1.0, 'kw/h': 1.0,
    'mwh': 1000.0,
    'gj': 277.778,
    'mj': 0.277778,
    'btu': 0.000293071,
    # Distance → km
    'km': 1.0, 'kilometer': 1.0, 'kilometers': 1.0,
    'mi': 1.60934, 'mile': 1.60934, 'miles': 1.60934,
    'm': 0.001,
}

# Emission factors (kg CO2e per normalized unit)
EMISSION_FACTORS = {
    'diesel': 2.68,        # kg CO2e per liter
    'petrol': 2.31,        # kg CO2e per liter
    'natural_gas': 2.02,   # kg CO2e per m3 (normalized to liters * 0.001 = m3... use 2020 BEIS)
    'lpg': 1.51,           # kg CO2e per liter
    'electricity': 0.233,  # kg CO2e per kWh (India grid average 2023)
    'flight': 0.255,       # kg CO2e per km (economy class, BEIS 2023)
    'hotel': 31.0,         # kg CO2e per night
    'ground_transport': 0.089,  # kg CO2e per km (average car)
    'procurement': 0.5,    # kg CO2e per USD (rough scope 3 factor)
}

SCOPE_MAP = {
    'diesel': 1, 'petrol': 1, 'natural_gas': 1, 'lpg': 1,
    'electricity': 2,
    'flight': 3, 'hotel': 3, 'ground_transport': 3, 'procurement': 3,
}


def normalize_unit(quantity, unit):
    """Convert any unit to our standard. Returns (normalized_qty, standard_unit)."""
    u = unit.strip().lower()
    factor = UNIT_CONVERSIONS.get(u)
    if factor:
        return round(quantity * factor, 4), _standard_unit(u)
    return quantity, unit  # unknown unit — keep as-is


def _standard_unit(u):
    if u in ('l', 'liter', 'liters', 'litre', 'litres', 'ml', 'gal', 'gallon', 'gallons', 'm3', 'cbm'):
        return 'liters'
    if u in ('kwh', 'kw/h', 'mwh', 'gj', 'mj', 'btu'):
        return 'kWh'
    if u in ('km', 'kilometer', 'kilometers', 'mi', 'mile', 'miles', 'm'):
        return 'km'
    return u


def calculate_co2e(category, normalized_qty, normalized_unit):
    factor = EMISSION_FACTORS.get(category)
    if factor is None:
        return None
    return round(normalized_qty * factor, 4)


def auto_flag(record_dict):
    """Return a flag reason string if the row looks suspicious, else None."""
    qty = record_dict.get('normalized_quantity', 0)
    category = record_dict.get('category', '')

    flags = []
    if qty <= 0:
        flags.append("Zero or negative quantity")
    if category == 'electricity' and qty > 1_000_000:
        flags.append("Unusually high electricity reading (>1M kWh)")
    if category in ('diesel', 'petrol') and qty > 100_000:
        flags.append("Unusually high fuel volume (>100,000 L)")
    if category == 'flight' and qty > 20_000:
        flags.append("Flight distance >20,000 km — check if correct")
    return '; '.join(flags) if flags else None


def parse_date(val):
    """Try multiple date formats."""
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y', '%m/%d/%Y', '%Y%m%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {val}")


# ---------------------------------------------------------------------------
# SAP Parser
# ---------------------------------------------------------------------------
# We handle SAP flat-file CSV exports (the most common format clients send).
# Typical SAP FI/MM export includes: Buchungsdatum (posting date), Menge (qty),
# Mengeneinheit (unit), Material (description), Werk (plant code).
# We support both German and English column headers.

SAP_COLUMN_MAP = {
    # German → internal
    'buchungsdatum': 'date',
    'menge': 'quantity',
    'mengeneinheit': 'unit',
    'material': 'description',
    'werk': 'location',
    'betrag': 'amount_usd',
    # English variants
    'posting date': 'date',
    'posting_date': 'date',
    'quantity': 'quantity',
    'qty': 'quantity',
    'unit': 'unit',
    'uom': 'unit',
    'material description': 'description',
    'material_description': 'description',
    'plant': 'location',
    'plant code': 'location',
    'amount': 'amount_usd',
}

SAP_CATEGORY_KEYWORDS = {
    'diesel': ['diesel', 'hsd', 'high speed diesel'],
    'petrol': ['petrol', 'gasoline', 'ms fuel', 'motor spirit'],
    'natural_gas': ['natural gas', 'cng', 'png', 'gas'],
    'lpg': ['lpg', 'liquefied petroleum'],
    'procurement': ['procurement', 'purchase', 'material', 'supply'],
}


def guess_sap_category(description):
    desc = str(description).lower()
    for cat, keywords in SAP_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in desc:
                return cat
    return 'procurement'  # default for unknown SAP materials


def parse_sap(file_bytes):
    """Parse SAP CSV export. Returns list of normalized record dicts."""
    df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python', dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    # Remap columns
    rename = {col: SAP_COLUMN_MAP[col] for col in df.columns if col in SAP_COLUMN_MAP}
    df = df.rename(columns=rename)

    required = {'date', 'quantity', 'unit'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"SAP file missing required columns: {missing}. Found: {list(df.columns)}")

    records = []
    errors = []
    for i, row in df.iterrows():
        try:
            date = parse_date(row['date'])
            raw_qty = float(str(row['quantity']).replace(',', '.'))
            raw_unit = str(row.get('unit', 'L')).strip()
            description = str(row.get('description', ''))
            location = str(row.get('location', ''))
            category = guess_sap_category(description)

            norm_qty, norm_unit = normalize_unit(raw_qty, raw_unit)
            co2e = calculate_co2e(category, norm_qty, norm_unit)
            scope = SCOPE_MAP.get(category, 1)

            rec = {
                'activity_date': date,
                'category': category,
                'description': description,
                'location': location,
                'raw_quantity': raw_qty,
                'raw_unit': raw_unit,
                'normalized_quantity': norm_qty,
                'normalized_unit': norm_unit,
                'co2e_kg': co2e,
                'scope': scope,
            }
            rec['flag_reason'] = auto_flag(rec)
            records.append(rec)
        except Exception as e:
            errors.append(f"Row {i + 2}: {e}")

    return records, errors


# ---------------------------------------------------------------------------
# Utility (Electricity) Parser
# ---------------------------------------------------------------------------
# We handle portal CSV exports — the most common way facilities teams get data.
# Typical columns: meter_id, billing_period_start, billing_period_end,
# consumption_kwh, tariff, site_name.
# Bill periods often don't align to calendar months, so we use period_start as date.

UTILITY_COLUMN_MAP = {
    'meter id': 'meter_id', 'meter_id': 'meter_id', 'meterid': 'meter_id',
    'billing period start': 'date', 'period_start': 'date', 'start date': 'date', 'start_date': 'date',
    'billing period end': 'period_end', 'period_end': 'period_end',
    'consumption (kwh)': 'quantity', 'consumption_kwh': 'quantity', 'kwh': 'quantity',
    'consumption': 'quantity', 'units consumed': 'quantity',
    'unit': 'unit', 'units': 'unit',
    'site': 'location', 'site name': 'location', 'site_name': 'location', 'facility': 'location',
    'tariff': 'tariff',
}


def parse_utility(file_bytes):
    """Parse utility portal CSV. Returns list of normalized record dicts."""
    df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python', dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    rename = {col: UTILITY_COLUMN_MAP[col] for col in df.columns if col in UTILITY_COLUMN_MAP}
    df = df.rename(columns=rename)

    if 'quantity' not in df.columns:
        raise ValueError(f"Utility file missing consumption column. Found: {list(df.columns)}")
    if 'date' not in df.columns:
        raise ValueError(f"Utility file missing date/period column. Found: {list(df.columns)}")

    records = []
    errors = []
    for i, row in df.iterrows():
        try:
            date = parse_date(row['date'])
            raw_qty = float(str(row['quantity']).replace(',', ''))
            raw_unit = str(row.get('unit', 'kWh')).strip() or 'kWh'
            location = str(row.get('location', ''))
            meter_id = str(row.get('meter_id', ''))
            tariff = str(row.get('tariff', ''))
            description = f"Meter: {meter_id} | Tariff: {tariff}".strip(' |')

            norm_qty, norm_unit = normalize_unit(raw_qty, raw_unit)
            co2e = calculate_co2e('electricity', norm_qty, norm_unit)

            rec = {
                'activity_date': date,
                'category': 'electricity',
                'description': description,
                'location': location,
                'raw_quantity': raw_qty,
                'raw_unit': raw_unit,
                'normalized_quantity': norm_qty,
                'normalized_unit': norm_unit,
                'co2e_kg': co2e,
                'scope': 2,
            }
            rec['flag_reason'] = auto_flag(rec)
            records.append(rec)
        except Exception as e:
            errors.append(f"Row {i + 2}: {e}")

    return records, errors


# ---------------------------------------------------------------------------
# Corporate Travel Parser
# ---------------------------------------------------------------------------
# Modeled after Concur/Navan expense export CSV.
# Key fields: trip_date, travel_type (flight/hotel/car), origin, destination,
# distance_km (sometimes absent — we estimate from airport codes), nights, amount.
# When distance is absent for flights, we flag the row for manual review.

TRAVEL_COLUMN_MAP = {
    'date': 'date', 'trip date': 'date', 'travel_date': 'date', 'transaction date': 'date',
    'type': 'travel_type', 'travel type': 'travel_type', 'expense type': 'travel_type',
    'category': 'travel_type',
    'origin': 'origin', 'from': 'origin', 'departure': 'origin',
    'destination': 'destination', 'to': 'destination', 'arrival': 'destination',
    'distance (km)': 'distance_km', 'distance_km': 'distance_km', 'distance': 'distance_km',
    'nights': 'nights', 'hotel nights': 'nights',
    'amount (usd)': 'amount', 'amount': 'amount', 'cost': 'amount',
    'currency': 'currency',
    'employee': 'employee', 'traveler': 'employee', 'name': 'employee',
}

TRAVEL_TYPE_MAP = {
    'flight': 'flight', 'air': 'flight', 'airline': 'flight', 'fly': 'flight',
    'hotel': 'hotel', 'accommodation': 'hotel', 'lodging': 'hotel',
    'car': 'ground_transport', 'taxi': 'ground_transport', 'cab': 'ground_transport',
    'train': 'ground_transport', 'rail': 'ground_transport', 'bus': 'ground_transport',
    'ground': 'ground_transport', 'rental': 'ground_transport',
}


def guess_travel_category(travel_type_raw):
    t = str(travel_type_raw).lower().strip()
    for key, val in TRAVEL_TYPE_MAP.items():
        if key in t:
            return val
    return 'ground_transport'


def parse_travel(file_bytes):
    """Parse corporate travel CSV. Returns list of normalized record dicts."""
    df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python', dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    rename = {col: TRAVEL_COLUMN_MAP[col] for col in df.columns if col in TRAVEL_COLUMN_MAP}
    df = df.rename(columns=rename)

    if 'date' not in df.columns:
        raise ValueError(f"Travel file missing date column. Found: {list(df.columns)}")

    records = []
    errors = []
    for i, row in df.iterrows():
        try:
            date = parse_date(row['date'])
            travel_type_raw = str(row.get('travel_type', 'flight'))
            category = guess_travel_category(travel_type_raw)
            origin = str(row.get('origin', ''))
            destination = str(row.get('destination', ''))
            employee = str(row.get('employee', ''))

            if category == 'hotel':
                # Unit = nights
                raw_qty = float(str(row.get('nights', '1')).replace(',', '') or '1')
                raw_unit = 'nights'
                norm_qty = raw_qty
                norm_unit = 'nights'
            else:
                # Unit = km
                dist_raw = str(row.get('distance_km', '')).strip()
                if dist_raw and dist_raw not in ('', 'nan', 'None'):
                    raw_qty = float(dist_raw.replace(',', ''))
                    raw_unit = 'km'
                else:
                    # Distance unknown — use 0 and flag
                    raw_qty = 0.0
                    raw_unit = 'km'
                norm_qty, norm_unit = normalize_unit(raw_qty, raw_unit)

            co2e = calculate_co2e(category, norm_qty, norm_unit)
            description = f"{origin} → {destination} | {employee}".strip(' |→')

            rec = {
                'activity_date': date,
                'category': category,
                'description': description,
                'location': origin,
                'raw_quantity': raw_qty,
                'raw_unit': raw_unit,
                'normalized_quantity': norm_qty,
                'normalized_unit': norm_unit,
                'co2e_kg': co2e,
                'scope': 3,
            }
            flag = auto_flag(rec)
            if raw_qty == 0 and category != 'hotel':
                flag = (flag + '; ' if flag else '') + 'Distance missing — needs manual entry'
            rec['flag_reason'] = flag
            records.append(rec)
        except Exception as e:
            errors.append(f"Row {i + 2}: {e}")

    return records, errors
