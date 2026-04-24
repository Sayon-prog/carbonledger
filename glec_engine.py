"""
CarbonLedger — GLEC v3.0 / ISO 14083 Calculation Engine
India-specific emission factors. Deterministic math only.
No AI in the calculation chain.
"""

# ─────────────────────────────────────────────────────────────────────────────
# EMISSION FACTORS — India specific (kg CO2e per unit of fuel)
# Sources: MoPNG 2023, IPCC AR6, CEA 2023-24
# ─────────────────────────────────────────────────────────────────────────────

# Tank-to-Wheel (TTW) factors — combustion only
TTW_FACTORS = {
    "diesel":    2.68,   # kg CO2e per litre  — MoPNG / IPCC
    "petrol":    2.31,   # kg CO2e per litre
    "cng":       2.13,   # kg CO2e per kg
    "lpg":       1.61,   # kg CO2e per litre
    "electric":  0.0,    # handled separately via grid factor
    "unknown":   2.68,   # default to diesel (conservative)
}

# Well-to-Tank (WTT) uplift factors — production + transport of fuel
# WTT_CO2e = TTW_CO2e * WTT_UPLIFT
WTT_UPLIFT = {
    "diesel":    0.20,
    "petrol":    0.22,
    "cng":       0.30,
    "lpg":       0.24,
    "electric":  0.0,    # included in grid factor
    "unknown":   0.20,
}

# India national grid emission factor — CEA 2023-24
# kg CO2e per kWh consumed at plug (includes T&D losses)
INDIA_GRID_FACTOR = 0.716   # national average
# State-wise factors for accuracy (use when state is known)
STATE_GRID_FACTORS = {
    "maharashtra": 0.82, "gujarat": 0.79, "rajasthan": 0.85,
    "delhi": 0.71, "haryana": 0.75, "punjab": 0.61,
    "karnataka": 0.55, "tamil_nadu": 0.65, "andhra_pradesh": 0.68,
    "telangana": 0.72, "uttar_pradesh": 0.86, "madhya_pradesh": 0.83,
    "west_bengal": 0.78, "odisha": 0.88, "jharkhand": 0.90,
    "himachal_pradesh": 0.22, "kerala": 0.40, "goa": 0.68,
}

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT VEHICLE FUEL CONSUMPTION (litres per 100 km)
# Source: ARAI India, GLEC v3.0 default factors
# Used when actual fuel data is unavailable (Level 2 method)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CONSUMPTION_L_PER_100KM = {
    # Heavy vehicles
    "hgv_40t":      38.0,   # Heavy Goods Vehicle >40T GVW
    "hgv_32t":      35.0,   # HGV 32-40T
    "hgv_24t":      30.0,   # HGV 24-32T
    "hgv_16t":      26.0,   # HGV 16-24T
    # Medium vehicles
    "mgv_12t":      22.0,   # Medium Goods Vehicle 7.5-16T
    "mgv_7t":       18.0,   # MGV 3.5-7.5T
    # Light vehicles
    "lgv_van":      12.0,   # Light Goods Vehicle / Van <3.5T
    "lgv_pickup":   10.0,   # Pickup truck
    # Small vehicles
    "car_diesel":    6.0,
    "car_petrol":    8.0,
    "car_cng":       5.5,   # kg per 100km for CNG
    "suv":          10.0,
    # 2/3 wheelers
    "3w_auto":       4.0,
    "2w":            3.0,
    # Electric (kWh per 100km — separate calculation path)
    "ev_lgv":       25.0,   # kWh/100km
    "ev_car":       15.0,
    "ev_2w":         3.5,
}

# Average payload tonnes per vehicle type
# Used for tonne-km intensity calculation when weight not provided
DEFAULT_PAYLOAD_TONNES = {
    "hgv_40t": 20.0, "hgv_32t": 16.0, "hgv_24t": 12.0, "hgv_16t": 8.0,
    "mgv_12t": 6.0,  "mgv_7t":  3.0,
    "lgv_van": 1.0,  "lgv_pickup": 0.8,
    "car_diesel": 0.3, "car_petrol": 0.3, "car_cng": 0.3, "suv": 0.3,
    "3w_auto": 0.3, "2w": 0.05,
    "ev_lgv": 1.0, "ev_car": 0.3, "ev_2w": 0.05,
}

# Human-readable vehicle labels
VEHICLE_LABELS = {
    "hgv_40t": "Heavy Truck (>40T)",    "hgv_32t": "Heavy Truck (32-40T)",
    "hgv_24t": "Heavy Truck (24-32T)",  "hgv_16t": "Heavy Truck (16-24T)",
    "mgv_12t": "Medium Truck (7.5-16T)","mgv_7t":  "Medium Truck (3.5-7.5T)",
    "lgv_van": "Light Van (<3.5T)",     "lgv_pickup": "Pickup Truck",
    "car_diesel": "Car (Diesel)",        "car_petrol": "Car (Petrol)",
    "car_cng":  "Car (CNG)",            "suv": "SUV/MUV",
    "3w_auto":  "3-Wheeler Auto",       "2w": "2-Wheeler",
    "ev_lgv":   "EV Light Van",         "ev_car": "EV Car",
    "ev_2w":    "EV 2-Wheeler",
}

# Fuel labels
FUEL_LABELS = {
    "diesel": "Diesel", "petrol": "Petrol", "cng": "CNG",
    "lpg": "LPG", "electric": "Electric", "unknown": "Unknown (assumed Diesel)"
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE CALCULATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def calculate_trip_emissions(
    distance_km: float,
    vehicle_type: str,
    fuel_type: str,
    load_tonnes: float = None,
    fuel_consumed: float = None,   # litres (or kg for CNG, kWh for EV)
    state: str = None,
) -> dict:
    """
    Calculate GHG emissions for a single trip.
    Implements GLEC v3.0 / ISO 14083 methodology.

    Three-tier fallback:
    - Level 3 (Best):    actual fuel_consumed provided
    - Level 2 (Good):    distance × default consumption factor
    - Level 1 (Worst):   spend-based (not implemented here — needs price data)

    Returns dict with CO2e_kg, intensity_g_per_tkm, method, and breakdown.
    """
    vtype = vehicle_type.lower().strip()
    ftype = fuel_type.lower().strip()

    if vtype not in DEFAULT_CONSUMPTION_L_PER_100KM:
        vtype = "mgv_7t"   # safe default

    if ftype not in TTW_FACTORS:
        ftype = "unknown"

    is_electric = (ftype == "electric")

    # ── Determine fuel consumed ──────────────────────────────────────────────
    if fuel_consumed and fuel_consumed > 0:
        method = "Level 3 (Actual fuel data)"
        fuel_qty = fuel_consumed
    else:
        method = "Level 2 (Distance × default factor)"
        default_rate = DEFAULT_CONSUMPTION_L_PER_100KM.get(vtype, 22.0)
        fuel_qty = (distance_km / 100.0) * default_rate

    # ── Calculate CO2e ───────────────────────────────────────────────────────
    if is_electric:
        # Electric: use grid emission factor
        kwh = fuel_qty   # already in kWh
        if state and state.lower() in STATE_GRID_FACTORS:
            grid_factor = STATE_GRID_FACTORS[state.lower()]
        else:
            grid_factor = INDIA_GRID_FACTOR

        ttw_co2e  = 0.0          # no tailpipe emissions
        wtt_co2e  = kwh * grid_factor   # upstream grid emissions
        total_co2e = wtt_co2e
        fuel_unit = "kWh"
    else:
        ttw_co2e  = fuel_qty * TTW_FACTORS[ftype]
        wtt_co2e  = ttw_co2e * WTT_UPLIFT[ftype]
        total_co2e = ttw_co2e + wtt_co2e
        fuel_unit = "kg" if ftype == "cng" else "litres"

    # ── Emission intensity ───────────────────────────────────────────────────
    if load_tonnes is None or load_tonnes <= 0:
        load_tonnes = DEFAULT_PAYLOAD_TONNES.get(vtype, 1.0)
        weight_assumed = True
    else:
        weight_assumed = False

    tonne_km = load_tonnes * distance_km
    intensity_g_tkm = (total_co2e * 1000 / tonne_km) if tonne_km > 0 else 0

    return {
        "distance_km":        round(distance_km, 2),
        "vehicle_type":       vtype,
        "vehicle_label":      VEHICLE_LABELS.get(vtype, vtype),
        "fuel_type":          ftype,
        "fuel_label":         FUEL_LABELS.get(ftype, ftype),
        "fuel_qty":           round(fuel_qty, 2),
        "fuel_unit":          fuel_unit,
        "load_tonnes":        round(load_tonnes, 3),
        "weight_assumed":     weight_assumed,
        "tonne_km":           round(tonne_km, 2),
        "ttw_co2e_kg":        round(ttw_co2e, 4),
        "wtt_co2e_kg":        round(wtt_co2e, 4),
        "total_co2e_kg":      round(total_co2e, 4),
        "intensity_g_tkm":    round(intensity_g_tkm, 2),
        "method":             method,
        "standard":           "GLEC v3.0 / ISO 14083",
    }


def calculate_portfolio(trips: list[dict]) -> dict:
    """
    Process a list of trip dicts and return aggregated results.
    Each trip dict needs: distance_km, vehicle_type, fuel_type,
    and optionally: load_tonnes, fuel_consumed, carrier, route, date
    """
    results = []
    errors  = []

    for i, trip in enumerate(trips):
        try:
            result = calculate_trip_emissions(
                distance_km   = float(trip.get("distance_km", 0)),
                vehicle_type  = str(trip.get("vehicle_type", "mgv_7t")),
                fuel_type     = str(trip.get("fuel_type", "diesel")),
                load_tonnes   = float(trip["load_tonnes"]) if trip.get("load_tonnes") else None,
                fuel_consumed = float(trip["fuel_consumed"]) if trip.get("fuel_consumed") else None,
                state         = str(trip.get("state", "")),
            )
            # carry through metadata
            result["trip_id"] = trip.get("trip_id", f"TRIP-{i+1:04d}")
            result["carrier"] = trip.get("carrier", "Unknown")
            result["route"]   = trip.get("route", f"{trip.get('origin','?')} → {trip.get('destination','?')}")
            result["date"]    = trip.get("date", "")
            results.append(result)
        except Exception as e:
            errors.append({"trip_index": i, "error": str(e), "data": trip})

    if not results:
        return {"error": "No valid trips processed", "raw_errors": errors}

    # ── Aggregations ─────────────────────────────────────────────────────────
    total_co2e      = sum(r["total_co2e_kg"] for r in results)
    total_distance  = sum(r["distance_km"]   for r in results)
    total_tkm       = sum(r["tonne_km"]      for r in results)
    total_ttw       = sum(r["ttw_co2e_kg"]   for r in results)
    total_wtt       = sum(r["wtt_co2e_kg"]   for r in results)

    portfolio_intensity = (total_co2e * 1000 / total_tkm) if total_tkm > 0 else 0

    # Per-carrier breakdown
    carriers = {}
    for r in results:
        c = r["carrier"]
        if c not in carriers:
            carriers[c] = {"trips": 0, "co2e_kg": 0, "distance_km": 0, "tonne_km": 0}
        carriers[c]["trips"]       += 1
        carriers[c]["co2e_kg"]     += r["total_co2e_kg"]
        carriers[c]["distance_km"] += r["distance_km"]
        carriers[c]["tonne_km"]    += r["tonne_km"]
    for c in carriers:
        tkm = carriers[c]["tonne_km"]
        carriers[c]["intensity_g_tkm"] = round(
            carriers[c]["co2e_kg"] * 1000 / tkm, 2) if tkm > 0 else 0

    # By vehicle type
    by_vehicle = {}
    for r in results:
        v = r["vehicle_label"]
        if v not in by_vehicle:
            by_vehicle[v] = {"trips": 0, "co2e_kg": 0}
        by_vehicle[v]["trips"]   += 1
        by_vehicle[v]["co2e_kg"] += r["total_co2e_kg"]

    # By fuel type
    by_fuel = {}
    for r in results:
        f = r["fuel_label"]
        if f not in by_fuel:
            by_fuel[f] = {"trips": 0, "co2e_kg": 0}
        by_fuel[f]["trips"]   += 1
        by_fuel[f]["co2e_kg"] += r["total_co2e_kg"]

    # Method quality
    level3 = sum(1 for r in results if "Level 3" in r["method"])
    level2 = sum(1 for r in results if "Level 2" in r["method"])

    # GLEC benchmark comparison
    avg_intensity = portfolio_intensity
    benchmark_hgv  = 75.0   # g CO2e/tkm — GLEC India road freight benchmark
    vs_benchmark   = round(((avg_intensity - benchmark_hgv) / benchmark_hgv) * 100, 1)

    return {
        "trips":                results,
        "errors":               errors,
        "summary": {
            "total_trips":          len(results),
            "failed_trips":         len(errors),
            "total_co2e_tonnes":    round(total_co2e / 1000, 4),
            "total_co2e_kg":        round(total_co2e, 2),
            "total_distance_km":    round(total_distance, 2),
            "total_tonne_km":       round(total_tkm, 2),
            "ttw_co2e_tonnes":      round(total_ttw / 1000, 4),
            "wtt_co2e_tonnes":      round(total_wtt / 1000, 4),
            "portfolio_intensity_g_tkm": round(portfolio_intensity, 2),
            "benchmark_g_tkm":      benchmark_hgv,
            "vs_benchmark_pct":     vs_benchmark,
            "data_quality_level3_pct": round(level3 / len(results) * 100, 1),
            "data_quality_level2_pct": round(level2 / len(results) * 100, 1),
        },
        "by_carrier":   carriers,
        "by_vehicle":   by_vehicle,
        "by_fuel":      by_fuel,
        "methodology": {
            "framework":        "GLEC Framework v3.0",
            "standard":         "ISO 14083:2023",
            "emission_factors": "MoPNG 2023, IPCC AR6, CEA 2023-24",
            "boundary":         "Well-to-Wheel (WTW) including TTW + WTT",
            "scope":            "Scope 3 Category 4 (Upstream Transport)",
            "ghg_included":     "CO2, CH4, N2O (expressed as CO2e, AR6 GWPs)",
        }
    }


def normalise_column_names(df):
    """
    Map common column name variations to standard schema.
    This is deterministic string matching — NOT AI.
    AI (Claude) is called separately only for anomaly edge cases.
    """
    import pandas as pd

    COL_MAP = {
        # distance
        "distance":          "distance_km",
        "dist":              "distance_km",
        "km":                "distance_km",
        "kilometers":        "distance_km",
        "distance (km)":     "distance_km",
        "actual_gps_km":     "distance_km",
        "billed_km":         "distance_km",
        "trip_distance":     "distance_km",

        # vehicle
        "vehicle":           "vehicle_type",
        "vehicle type":      "vehicle_type",
        "veh_type":          "vehicle_type",
        "truck_type":        "vehicle_type",
        "mode":              "vehicle_type",

        # fuel
        "fuel":              "fuel_type",
        "fuel type":         "fuel_type",
        "fuel_category":     "fuel_type",
        "energy_type":       "fuel_type",

        # load
        "weight":            "load_tonnes",
        "load":              "load_tonnes",
        "tonnes":            "load_tonnes",
        "weight_tonnes":     "load_tonnes",
        "cargo_weight":      "load_tonnes",
        "payload":           "load_tonnes",

        # fuel consumed
        "fuel_litres":       "fuel_consumed",
        "fuel_consumed_l":   "fuel_consumed",
        "litres":            "fuel_consumed",
        "fuel_qty":          "fuel_consumed",

        # carrier
        "vendor":            "carrier",
        "vendor_name":       "carrier",
        "transporter":       "carrier",
        "logistics_partner": "carrier",
        "3pl":               "carrier",

        # route
        "from":              "origin",
        "start":             "origin",
        "source":            "origin",
        "start_location":    "origin",
        "to":                "destination",
        "end":               "destination",
        "destination":       "destination",
        "end_location":      "destination",

        # trip id
        "trip":              "trip_id",
        "id":                "trip_id",
        "trip_no":           "trip_id",
        "shipment_id":       "trip_id",
        "lr_number":         "trip_id",
    }

    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns={k: v for k, v in COL_MAP.items() if k in df.columns})

    # Normalise fuel type values
    FUEL_VAL_MAP = {
        "hsd": "diesel", "high speed diesel": "diesel", "bs6 diesel": "diesel",
        "ms": "petrol", "gasoline": "petrol", "mogas": "petrol",
        "cng": "cng", "compressed natural gas": "cng",
        "lpg": "lpg", "autogas": "lpg",
        "ev": "electric", "electricity": "electric", "battery": "electric",
    }
    if "fuel_type" in df.columns:
        df["fuel_type"] = df["fuel_type"].str.lower().str.strip().map(
            lambda x: FUEL_VAL_MAP.get(x, x) if pd.notna(x) else "diesel"
        )

    # Normalise vehicle type values
    VEH_VAL_MAP = {
        "truck": "hgv_32t", "lorry": "hgv_32t", "trailer": "hgv_40t",
        "container": "hgv_40t", "artic": "hgv_40t",
        "medium truck": "mgv_12t", "mini truck": "mgv_7t",
        "lcv": "lgv_van", "van": "lgv_van", "tempo": "lgv_van",
        "pickup": "lgv_pickup",
        "car": "car_diesel", "sedan": "car_diesel", "cab": "car_diesel",
        "suv": "suv", "muv": "suv",
        "auto": "3w_auto", "3w": "3w_auto", "rickshaw": "3w_auto",
        "bike": "2w", "motorcycle": "2w", "scooter": "2w", "2w": "2w",
        "ev": "ev_car", "electric": "ev_car",
    }
    if "vehicle_type" in df.columns:
        df["vehicle_type"] = df["vehicle_type"].str.lower().str.strip().map(
            lambda x: VEH_VAL_MAP.get(x, x) if pd.notna(x) else "mgv_7t"
        )

    return df
