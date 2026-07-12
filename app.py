"""
CarbonLedger — Streamlit Demo App
GLEC v3.0 / ISO 14083 Scope 3 Transport Emissions Calculator
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import json
import os
from io import BytesIO, StringIO
from datetime import datetime

# Local modules
from glec_engine import (
    calculate_portfolio, normalise_column_names,
    VEHICLE_LABELS, FUEL_LABELS, DEFAULT_CONSUMPTION_L_PER_100KM
)
from report_generator import generate_report

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CarbonLedger — Scope 3 Transport",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .block-container { padding-top: 1.5rem; }

    .kpi-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .kpi-val      { font-size: 2rem; font-weight: 700; color: #0D1B2A; margin: 0; }
    .kpi-val-red  { font-size: 2rem; font-weight: 700; color: #C0392B; margin: 0; }
    .kpi-val-grn  { font-size: 2rem; font-weight: 700; color: #1A6B3C; margin: 0; }
    .kpi-label    { font-size: 0.78rem; color: #64748B; margin: 0; }

    .section-header {
        font-size: 1.1rem; font-weight: 700; color: #0D1B2A;
        border-left: 4px solid #C0392B;
        padding-left: 10px; margin: 1.2rem 0 0.6rem 0;
    }
    .badge-red    { background: #FEF2F2; color: #C0392B; padding: 2px 8px;
                    border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-grn    { background: #F0FDF4; color: #1A6B3C; padding: 2px 8px;
                    border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-amb    { background: #FDF3E7; color: #B8620A; padding: 2px 8px;
                    border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .methodology-box {
        background: #F1F5F9; border-radius: 8px; padding: 14px 16px;
        font-size: 0.82rem; color: #475569; line-height: 1.6;
        border: 1px solid #E2E8F0;
    }
    .brsr-box {
        background: #FEF2F2; border-left: 4px solid #C0392B;
        border-radius: 0 8px 8px 0; padding: 12px 16px;
        font-size: 0.85rem; color: #0D1B2A; margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE DATA
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_TRIPS = [
    {"trip_id":"TRP-001","date":"01-Apr-24","carrier":"Sharma Logistics",
     "origin":"Mumbai","destination":"Pune","distance_km":148,
     "vehicle_type":"hgv_32t","fuel_type":"diesel","load_tonnes":12},
    {"trip_id":"TRP-002","date":"02-Apr-24","carrier":"Reddy Transport",
     "origin":"Delhi","destination":"Jaipur","distance_km":272,
     "vehicle_type":"hgv_40t","fuel_type":"diesel","load_tonnes":18},
    {"trip_id":"TRP-003","date":"03-Apr-24","carrier":"Patel Roadways",
     "origin":"Ahmedabad","destination":"Surat","distance_km":264,
     "vehicle_type":"mgv_12t","fuel_type":"diesel","load_tonnes":6},
    {"trip_id":"TRP-004","date":"04-Apr-24","carrier":"Nandkishor Log.",
     "origin":"Mumbai","destination":"Delhi","distance_km":1422,
     "vehicle_type":"hgv_40t","fuel_type":"diesel","load_tonnes":20},
    {"trip_id":"TRP-005","date":"05-Apr-24","carrier":"Sharma Logistics",
     "origin":"Bangalore","destination":"Chennai","distance_km":346,
     "vehicle_type":"hgv_32t","fuel_type":"diesel","load_tonnes":14,
     "fuel_consumed":121.0},
    {"trip_id":"TRP-006","date":"07-Apr-24","carrier":"GreenFleet India",
     "origin":"Mumbai","destination":"Nashik","distance_km":168,
     "vehicle_type":"ev_lgv","fuel_type":"electric","load_tonnes":1.5},
    {"trip_id":"TRP-007","date":"08-Apr-24","carrier":"Reddy Transport",
     "origin":"Hyderabad","destination":"Vijayawada","distance_km":274,
     "vehicle_type":"mgv_12t","fuel_type":"cng","load_tonnes":5},
    {"trip_id":"TRP-008","date":"09-Apr-24","carrier":"Nandkishor Log.",
     "origin":"Ahmedabad","destination":"Mumbai","distance_km":528,
     "vehicle_type":"hgv_40t","fuel_type":"diesel","load_tonnes":19},
    {"trip_id":"TRP-009","date":"10-Apr-24","carrier":"Patel Roadways",
     "origin":"Pune","destination":"Goa","distance_km":442,
     "vehicle_type":"hgv_32t","fuel_type":"diesel","load_tonnes":10},
    {"trip_id":"TRP-010","date":"11-Apr-24","carrier":"GreenFleet India",
     "origin":"Delhi","destination":"Agra","distance_km":204,
     "vehicle_type":"ev_lgv","fuel_type":"electric","load_tonnes":1.2},
]

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "company" not in st.session_state:
    st.session_state.company = ""
if "fy" not in st.session_state:
    st.session_state.fy = "2024-25"

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌿 CarbonLedger")
    st.caption("GLEC v3.0 / ISO 14083 · BRSR Core")
    st.divider()

    st.markdown("### Company Details")
    company = st.text_input("Company Name", placeholder="Acme Industries Ltd.",
                             value=st.session_state.company)
    fy = st.selectbox("Financial Year", ["2024-25","2023-24","2025-26"],
                       index=0)
    st.session_state.company = company
    st.session_state.fy = fy

    st.divider()
    st.markdown("### Data Input")
    input_mode = st.radio("Choose input mode",
                           ["📁 Upload CSV/Excel", "📋 Use Sample Data", "✏️ Manual Entry"])

    st.divider()
    st.markdown("### 📐 Methodology")
    st.markdown("""
    <div class="methodology-box">
    <b>Standard:</b> GLEC v3.0 / ISO 14083<br>
    <b>Boundary:</b> Well-to-Wheel (WTW)<br>
    <b>Factors:</b> MoPNG 2023, IPCC AR6, CEA 2023-24<br>
    <b>Scope:</b> 3 Category 4 & 9<br><br>
    <b>Data tiers:</b><br>
    L3: Actual fuel consumption<br>
    L2: Distance × default factor<br>
    L1: Spend-based (fallback)
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("For BRSR Core compliance per SEBI circular 12 July 2023")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3,1])
with col_h1:
    st.markdown("# 🌿 Scope 3 Transport Emissions")
    st.caption("GLEC v3.0 / ISO 14083 · BRSR Core Compliant · India-specific emission factors")
with col_h2:
    st.markdown("""
    <div class="brsr-box">
    <b>⚠️ SEBI Deadline</b><br>
    BRSR Core Scope 3 reporting is mandatory for top 150 listed companies from FY2024-25.
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_calc, tab_live = st.tabs(["📊 Emissions Calculator", "🔴 Live GPS Feed (BlackBuck)"])

with tab_calc:
    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # INPUT SECTION
    # ─────────────────────────────────────────────────────────────────────────
    trips_to_process = []

    if input_mode == "📁 Upload CSV/Excel":
        st.markdown('<div class="section-header">Upload Your Transport Data</div>', unsafe_allow_html=True)
        st.caption("Any format accepted — invoices, GPS exports, TMS reports, manual logs. No template required.")

        col_up, col_fmt = st.columns([2,1])
        with col_up:
            uploaded = st.file_uploader("Drop your file here", type=["csv","xlsx","xls"])
        with col_fmt:
            st.markdown("""
            **Columns needed (any name):**
            - Distance / km / trip_distance
            - Vehicle type / truck_type / mode
            - Fuel type / energy_type
            - Carrier / vendor / transporter
            - Origin, Destination (optional)
            - Load / weight / tonnes (optional)
            - Fuel consumed / litres (optional, Level 3)
            """)

        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)

                st.success(f"✅ Loaded {len(df)} rows from {uploaded.name}")
                with st.expander("Preview raw data"):
                    st.dataframe(df.head(10), use_container_width=True)

                df = normalise_column_names(df)

                if "distance_km" not in df.columns:
                    st.error("❌ Could not find a distance column. Please ensure your file has a column named 'distance', 'km', or similar.")
                else:
                    trips_to_process = df.to_dict("records")
                    st.info(f"Columns mapped: {list(df.columns)}")

            except Exception as e:
                st.error(f"Error reading file: {e}")

    elif input_mode == "📋 Use Sample Data":
        st.markdown('<div class="section-header">Sample Dataset — 10 Trips</div>', unsafe_allow_html=True)
        st.caption("Realistic India logistics data across 5 carriers, mix of diesel, CNG and EV.")
        df_sample = pd.DataFrame(SAMPLE_TRIPS)
        st.dataframe(df_sample, use_container_width=True, height=280)
        trips_to_process = SAMPLE_TRIPS
        if not company:
            st.session_state.company = "Sample Manufacturing Co. Ltd."

    else:  # Manual Entry
        st.markdown('<div class="section-header">Manual Trip Entry</div>', unsafe_allow_html=True)
        n_trips = st.number_input("Number of trips to enter", min_value=1, max_value=50, value=3)

        manual_trips = []
        veh_options = list(VEHICLE_LABELS.keys())
        veh_labels  = list(VEHICLE_LABELS.values())
        fuel_options = list(FUEL_LABELS.keys())
        fuel_labels  = list(FUEL_LABELS.values())

        for i in range(int(n_trips)):
            with st.expander(f"Trip {i+1}", expanded=(i==0)):
                c1,c2,c3,c4,c5,c6 = st.columns(6)
                tid  = c1.text_input("Trip ID", value=f"TRP-{i+1:03d}", key=f"tid_{i}")
                dist = c2.number_input("Distance (km)", min_value=1.0, value=150.0, key=f"dist_{i}")
                veh_idx = veh_labels.index(
                    c3.selectbox("Vehicle", veh_labels, index=3, key=f"veh_{i}"))
                fuel_idx = fuel_labels.index(
                    c4.selectbox("Fuel", fuel_labels, index=0, key=f"fuel_{i}"))
                load = c5.number_input("Load (tonnes)", min_value=0.0, value=0.0,
                                        help="0 = use default", key=f"load_{i}")
                carrier = c6.text_input("Carrier", value="Vendor", key=f"carrier_{i}")

                manual_trips.append({
                    "trip_id":      tid,
                    "distance_km":  dist,
                    "vehicle_type": veh_options[veh_idx],
                    "fuel_type":    fuel_options[fuel_idx],
                    "load_tonnes":  load if load > 0 else None,
                    "carrier":      carrier,
                })
        trips_to_process = manual_trips

    # ─────────────────────────────────────────────────────────────────────────
    # RUN CALCULATION
    # ─────────────────────────────────────────────────────────────────────────
    st.divider()
    run_col, _ = st.columns([1,3])
    with run_col:
        run_btn = st.button("🔬 Calculate Emissions", type="primary",
                             use_container_width=True,
                             disabled=(not trips_to_process))

    if run_btn and trips_to_process:
        if not st.session_state.company:
            st.session_state.company = "Your Company"
        with st.spinner("Running GLEC v3.0 calculations..."):
            result = calculate_portfolio(trips_to_process)
            st.session_state.result = result
        st.success(f"✅ Processed {result['summary']['total_trips']} trips successfully")
        if result.get("errors"):
            st.warning(f"⚠️ {len(result['errors'])} trips had errors and were skipped")

    # ─────────────────────────────────────────────────────────────────────────
    # RESULTS
    # ─────────────────────────────────────────────────────────────────────────
    if st.session_state.result:
        result  = st.session_state.result
        summ    = result["summary"]
        company = st.session_state.company or "Your Company"
        fy      = st.session_state.fy

        st.divider()
        st.markdown("## 📊 Results")

        k1, k2, k3, k4 = st.columns(4)
        co2t = summ["total_co2e_tonnes"]
        inten = summ["portfolio_intensity_g_tkm"]
        bench = summ["benchmark_g_tkm"]
        vs_b  = summ["vs_benchmark_pct"]
        sign  = "+" if vs_b > 0 else ""
        clr   = "kpi-val-red" if vs_b > 0 else "kpi-val-grn"

        with k1:
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-val-red">{co2t:.4f}</p>
                <p class="kpi-label">Total CO₂e (tonnes)</p>
            </div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-val">{inten:.1f}</p>
                <p class="kpi-label">g CO₂e / tonne-km</p>
            </div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-card">
                <p class="{clr}">{sign}{vs_b}%</p>
                <p class="kpi-label">vs GLEC India benchmark ({bench} g/tkm)</p>
            </div>""", unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-val">{summ['total_trips']}</p>
                <p class="kpi-label">Trips · {summ['total_distance_km']:,.0f} km total</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("")

        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            st.markdown('<div class="section-header">Emissions by Carrier</div>', unsafe_allow_html=True)
            carriers = result.get("by_carrier", {})
            if carriers:
                carrier_rows = []
                for name, data in sorted(carriers.items(),
                                          key=lambda x: x[1]["co2e_kg"], reverse=True):
                    pct   = data["co2e_kg"] / summ["total_co2e_kg"] * 100 if summ["total_co2e_kg"] > 0 else 0
                    inten = data["intensity_g_tkm"]
                    flag  = "🔴" if inten > 90 else ("🟡" if inten > 70 else "🟢")
                    carrier_rows.append({
                        "Carrier":       name,
                        "Trips":         data["trips"],
                        "CO₂e (kg)":     f"{data['co2e_kg']:.2f}",
                        "CO₂e (tonnes)": f"{data['co2e_kg']/1000:.4f}",
                        "g/tkm":         f"{flag} {inten:.1f}",
                        "% Share":       f"{pct:.1f}%",
                    })
                st.dataframe(pd.DataFrame(carrier_rows), use_container_width=True, hide_index=True)
                st.caption("🔴 >90 g/tkm: High emitter  🟡 70-90: Review  🟢 <70: Good")

        with col_right:
            st.markdown('<div class="section-header">BRSR Core Disclosure Preview</div>',
                         unsafe_allow_html=True)
            brsr_items = {
                "Total Scope 3 Transport CO₂e": f"{co2t:.4f} tCO₂e",
                "Tank-to-Wheel (TTW)":          f"{summ['ttw_co2e_tonnes']:.4f} tCO₂e",
                "Well-to-Tank (WTT)":           f"{summ['wtt_co2e_tonnes']:.4f} tCO₂e",
                "Emission Intensity":           f"{inten:.2f} g CO₂e/tkm",
                "Total Distance":               f"{summ['total_distance_km']:,.0f} km",
                "Total Freight Activity":       f"{summ['total_tonne_km']:,.0f} tkm",
                "Data Quality — Level 3":       f"{summ['data_quality_level3_pct']:.1f}%",
                "Data Quality — Level 2":       f"{summ['data_quality_level2_pct']:.1f}%",
                "Standard":                     "GLEC v3.0 / ISO 14083:2023",
            }
            for k, v in brsr_items.items():
                c1, c2 = st.columns([1.6, 1])
                c1.caption(k)
                c2.markdown(f"**{v}**")

        col_v, col_f = st.columns(2)
        with col_v:
            st.markdown('<div class="section-header">Fleet Mix by Vehicle Type</div>',
                         unsafe_allow_html=True)
            bv = result.get("by_vehicle", {})
            if bv:
                vdf = pd.DataFrame([
                    {"Vehicle": k, "Trips": v["trips"],
                     "CO₂e (tonnes)": round(v["co2e_kg"]/1000, 4),
                     "% Share": f"{v['co2e_kg']/summ['total_co2e_kg']*100:.1f}%"}
                    for k, v in sorted(bv.items(), key=lambda x: x[1]["co2e_kg"], reverse=True)
                ])
                st.dataframe(vdf, use_container_width=True, hide_index=True)

        with col_f:
            st.markdown('<div class="section-header">Fleet Mix by Fuel Type</div>',
                         unsafe_allow_html=True)
            bf = result.get("by_fuel", {})
            if bf:
                fdf = pd.DataFrame([
                    {"Fuel": k, "Trips": v["trips"],
                     "CO₂e (tonnes)": round(v["co2e_kg"]/1000, 4),
                     "% Share": f"{v['co2e_kg']/summ['total_co2e_kg']*100:.1f}%"}
                    for k, v in sorted(bf.items(), key=lambda x: x[1]["co2e_kg"], reverse=True)
                ])
                st.dataframe(fdf, use_container_width=True, hide_index=True)

        trips = result.get("trips", [])
        if trips:
            st.markdown('<div class="section-header">Trip-Level Detail</div>', unsafe_allow_html=True)
            trip_df = pd.DataFrame([{
                "Trip ID":     r.get("trip_id",""),
                "Carrier":     r.get("carrier",""),
                "Route":       r.get("route",""),
                "Dist (km)":   r["distance_km"],
                "Vehicle":     r["vehicle_label"],
                "Fuel":        r["fuel_label"],
                "CO₂e (kg)":   r["total_co2e_kg"],
                "g/tkm":       r["intensity_g_tkm"],
                "Method":      "L3" if "Level 3" in r["method"] else "L2",
            } for r in sorted(trips, key=lambda x: x["total_co2e_kg"], reverse=True)])
            st.dataframe(trip_df, use_container_width=True, hide_index=True, height=280)

        st.markdown('<div class="section-header">Methodology Statement (for BRSR filing)</div>',
                     unsafe_allow_html=True)
        meth = result.get("methodology", {})
        st.markdown(f"""
        <div class="methodology-box">
        <b>Framework:</b> {meth.get('framework','GLEC Framework v3.0')}<br>
        <b>Standard:</b> {meth.get('standard','ISO 14083:2023')}<br>
        <b>Emission Factors:</b> {meth.get('emission_factors','MoPNG 2023, IPCC AR6, CEA 2023-24')}<br>
        <b>Boundary:</b> {meth.get('boundary','Well-to-Wheel (WTW) — TTW + WTT')}<br>
        <b>Scope:</b> {meth.get('scope','Scope 3 Category 4 (Upstream Transportation and Distribution)')}<br>
        <b>GHGs:</b> {meth.get('ghg_included','CO₂, CH₄, N₂O expressed as CO₂e using AR6 GWP100 values')}<br>
        <b>India Grid Factor:</b> 0.716 kg CO₂e/kWh (CEA 2023-24 national average)<br>
        <b>Assurance:</b> Full input-output calculation log available for third-party verification.
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown("## 📥 Download")
        dl1, dl2, dl3 = st.columns(3)

        with dl1:
            with st.spinner("Generating PDF..."):
                try:
                    pdf_bytes = generate_report(result, company, fy)
                    st.download_button(
                        label="📄 Download BRSR Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"CarbonLedger_BRSR_Scope3_{company.replace(' ','_')}_FY{fy}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
                except Exception as e:
                    st.error(f"PDF generation error: {e}")

        with dl2:
            if trips:
                csv_df = pd.DataFrame([{
                    "trip_id":       r.get("trip_id"),
                    "carrier":       r.get("carrier"),
                    "route":         r.get("route"),
                    "distance_km":   r["distance_km"],
                    "vehicle_type":  r["vehicle_label"],
                    "fuel_type":     r["fuel_label"],
                    "load_tonnes":   r["load_tonnes"],
                    "fuel_qty":      r["fuel_qty"],
                    "fuel_unit":     r["fuel_unit"],
                    "ttw_co2e_kg":   r["ttw_co2e_kg"],
                    "wtt_co2e_kg":   r["wtt_co2e_kg"],
                    "total_co2e_kg": r["total_co2e_kg"],
                    "intensity_g_tkm": r["intensity_g_tkm"],
                    "method":        r["method"],
                    "standard":      r["standard"],
                } for r in trips])
                st.download_button(
                    label="📊 Download Audit Trail (CSV)",
                    data=csv_df.to_csv(index=False),
                    file_name=f"CarbonLedger_AuditTrail_{company.replace(' ','_')}_FY{fy}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        with dl3:
            st.download_button(
                label="🔢 Download Raw Data (JSON)",
                data=json.dumps({
                    "company": company, "fy": fy,
                    "generated": datetime.now().isoformat(),
                    "summary": summ,
                    "methodology": meth,
                    "by_carrier": result.get("by_carrier",{}),
                }, indent=2),
                file_name=f"CarbonLedger_Data_{company.replace(' ','_')}_FY{fy}.json",
                mime="application/json",
                use_container_width=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# LIVE GPS TAB
# ─────────────────────────────────────────────────────────────────────────────
with tab_live:
    st.markdown("## 🔴 Live GPS Feed")
    st.caption("Real-time vehicle data from BlackBuck telematics — auto-refreshes every 30 seconds")

    SUPA_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
    SUPA_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

    if not SUPA_URL or not SUPA_KEY:
        st.warning("⚠️ Supabase credentials not configured. Add SUPABASE_URL and SUPABASE_KEY to your Streamlit secrets.")
        st.code("""
# In Streamlit Cloud: go to App Settings > Secrets and add:
SUPABASE_URL = "https://grhzlvxnnjbfezkvrpzr.supabase.co"
SUPABASE_KEY = "your-secret-key-here"
        """)
    else:
        try:
            from supabase import create_client as sb_create_client
            supa = sb_create_client(SUPA_URL, SUPA_KEY)
            data = supa.table("gps_pings").select("*").order("created_at", desc=True).limit(200).execute()
            rows = data.data

            if not rows:
                st.info("📡 No GPS pings received yet. Waiting for BlackBuck to send data to the webhook...")
                st.markdown(f"""
                **Webhook URL to give BlackBuck:**
                ```
                https://web-production-6e262c.up.railway.app/gps
                ```
                Method: POST, Format: JSON
                """)
            else:
                total    = len(rows)
                alerts   = sum(1 for r in rows if r.get("is_alert"))
                vehicles = len(set(r["vehicle_number"] for r in rows if r.get("vehicle_number")))
                latest   = rows[0]["timestamp"] if rows else "N/A"

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total Pings", total)
                k2.metric("Unique Vehicles", vehicles)
                k3.metric("Alert Events", alerts)
                k4.metric("Last Ping", str(latest)[:16] if latest else "N/A")

                if alerts:
                    st.markdown("### 🚨 Alert Events")
                    alert_rows = [r for r in rows if r.get("is_alert")]
                    st.dataframe(pd.DataFrame([{
                        "Vehicle":    r.get("vehicle_number", ""),
                        "Alert Type": r.get("alert_type", "Unknown"),
                        "Speed":      r.get("speed", 0),
                        "Time":       str(r.get("timestamp", ""))[:16],
                        "Lat":        r.get("latitude", ""),
                        "Lng":        r.get("longitude", ""),
                    } for r in alert_rows]), use_container_width=True, hide_index=True)

                st.markdown("### 🗺️ Vehicle Locations")
                map_data = pd.DataFrame([{
                    "lat": r["latitude"],
                    "lon": r["longitude"],
                } for r in rows if r.get("latitude") and r.get("longitude")
                    and r["latitude"] != 0 and r["longitude"] != 0])
                if not map_data.empty:
                    st.map(map_data)
                else:
                    st.info("No valid coordinates yet.")

                st.markdown("### 📋 Recent Pings")
                st.dataframe(pd.DataFrame([{
                    "Vehicle":    r.get("vehicle_number", ""),
                    "Lat":        r.get("latitude", ""),
                    "Lng":        r.get("longitude", ""),
                    "Speed":      r.get("speed", ""),
                    "Alert":      "🚨 " + str(r.get("alert_type","")) if r.get("is_alert") else "OK",
                    "Time":       str(r.get("timestamp", ""))[:16],
                } for r in rows[:50]]), use_container_width=True, hide_index=True)

                col_r1, col_r2 = st.columns([1, 4])
                with col_r1:
                    if st.button("🔄 Refresh Now"):
                        st.rerun()
                with col_r2:
                    st.caption("Page auto-refreshes — click Refresh for latest data immediately")

        except Exception as e:
            st.error(f"Could not connect to database: {e}")
            st.caption("Check that SUPABASE_URL and SUPABASE_KEY are set correctly in Streamlit secrets.")

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "CarbonLedger · GLEC v3.0 / ISO 14083:2023 · "
    "India emission factors: MoPNG 2023, IPCC AR6, CEA 2023-24 · "
    "SEBI BRSR Core circular 12 July 2023 · "
    "Not a registered auditor — independent assurance recommended for formal filing."
)
