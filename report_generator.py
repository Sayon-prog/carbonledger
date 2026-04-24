"""
CarbonLedger — BRSR Core Scope 3 Transport Emissions Report Generator
Produces a PDF that satisfies SEBI BRSR Core verification requirements.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                  TableStyle, HRFlowable, PageBreak, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from io import BytesIO
from datetime import datetime

# ── PALETTE ──────────────────────────────────────────────────────────────────
INK       = colors.HexColor("#0D1B2A")
RED       = colors.HexColor("#C0392B")
GREEN     = colors.HexColor("#1A6B3C")
AMBER     = colors.HexColor("#B8620A")
SLATE     = colors.HexColor("#1E293B")
MIST      = colors.HexColor("#F8FAFC")
RULE      = colors.HexColor("#E2E8F0")
WHITE     = colors.white
LIGHT_RED = colors.HexColor("#FEF2F2")
LIGHT_GRN = colors.HexColor("#F0FDF4")

def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle("title",
        fontName="Helvetica-Bold", fontSize=22, textColor=WHITE,
        leading=28, spaceAfter=4)

    styles["subtitle"] = ParagraphStyle("subtitle",
        fontName="Helvetica", fontSize=11, textColor=colors.HexColor("#94A3B8"),
        leading=16, spaceAfter=2)

    styles["h1"] = ParagraphStyle("h1",
        fontName="Helvetica-Bold", fontSize=14, textColor=INK,
        leading=20, spaceBefore=16, spaceAfter=6)

    styles["h2"] = ParagraphStyle("h2",
        fontName="Helvetica-Bold", fontSize=11, textColor=SLATE,
        leading=16, spaceBefore=10, spaceAfter=4)

    styles["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9.5, textColor=INK,
        leading=14, spaceAfter=4, alignment=TA_JUSTIFY)

    styles["body_sm"] = ParagraphStyle("body_sm",
        fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#475569"),
        leading=12, spaceAfter=2)

    styles["mono"] = ParagraphStyle("mono",
        fontName="Courier", fontSize=8, textColor=INK, leading=12)

    styles["label"] = ParagraphStyle("label",
        fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#64748B"),
        leading=10, spaceAfter=1)

    styles["kpi_val"] = ParagraphStyle("kpi_val",
        fontName="Helvetica-Bold", fontSize=22, textColor=INK,
        leading=26, spaceAfter=2, alignment=TA_CENTER)

    styles["kpi_label"] = ParagraphStyle("kpi_label",
        fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#64748B"),
        leading=10, spaceAfter=0, alignment=TA_CENTER)

    styles["red_val"] = ParagraphStyle("red_val",
        fontName="Helvetica-Bold", fontSize=22, textColor=RED,
        leading=26, spaceAfter=2, alignment=TA_CENTER)

    styles["green_val"] = ParagraphStyle("green_val",
        fontName="Helvetica-Bold", fontSize=22, textColor=GREEN,
        leading=26, spaceAfter=2, alignment=TA_CENTER)

    styles["tbl_hdr"] = ParagraphStyle("tbl_hdr",
        fontName="Helvetica-Bold", fontSize=8, textColor=WHITE,
        leading=10, alignment=TA_CENTER)

    styles["tbl_cell"] = ParagraphStyle("tbl_cell",
        fontName="Helvetica", fontSize=8, textColor=INK,
        leading=10, alignment=TA_CENTER)

    styles["tbl_cell_l"] = ParagraphStyle("tbl_cell_l",
        fontName="Helvetica", fontSize=8, textColor=INK,
        leading=10, alignment=TA_LEFT)

    styles["disclaimer"] = ParagraphStyle("disclaimer",
        fontName="Helvetica-Oblique", fontSize=7.5,
        textColor=colors.HexColor("#94A3B8"), leading=11, alignment=TA_JUSTIFY)

    return styles


def tbl_style(header_bg=None):
    hbg = header_bg or SLATE
    return TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  hbg),
        ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("ALIGN",       (0,1), (0,-1),  "LEFT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[MIST, WHITE]),
        ("GRID",        (0,0), (-1,-1), 0.4, RULE),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0),(-1,-1),  6),
    ])


def generate_report(portfolio_result: dict, company_name: str,
                    fy: str = "2024-25") -> bytes:
    """Generate BRSR Core compliant Scope 3 transport emissions PDF report."""

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=2*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm
    )

    s      = make_styles()
    W      = A4[0] - 3.6*cm   # usable width
    story  = []
    summ   = portfolio_result["summary"]
    now    = datetime.now().strftime("%d %B %Y")
    method = portfolio_result.get("methodology", {})

    # ─────────────────────────────────────────────────────────────────────────
    # COVER HEADER
    # ─────────────────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"<b>SCOPE 3 TRANSPORT EMISSIONS REPORT</b>", s["title"]),
    ]]
    header_tbl = Table(header_data, colWidths=[W])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,0), SLATE),
        ("TOPPADDING",    (0,0),(0,0), 18),
        ("BOTTOMPADDING", (0,0),(0,0), 14),
        ("LEFTPADDING",   (0,0),(0,0), 16),
        ("RIGHTPADDING",  (0,0),(0,0), 16),
    ]))
    story.append(header_tbl)

    meta_data = [[
        Paragraph(f"<b>Company:</b> {company_name}", s["body"]),
        Paragraph(f"<b>Financial Year:</b> FY {fy}", s["body"]),
        Paragraph(f"<b>Standard:</b> GLEC v3.0 / ISO 14083:2023", s["body"]),
        Paragraph(f"<b>Generated:</b> {now}", s["body"]),
    ]]
    meta_tbl = Table(meta_data, colWidths=[W*0.3, W*0.25, W*0.27, W*0.18])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F1F5F9")),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("GRID",          (0,0),(-1,-1), 0.3, RULE),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────────
    # EXECUTIVE SUMMARY KPI CARDS
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("1. EXECUTIVE SUMMARY", s["h1"]))
    story.append(HRFlowable(width=W, thickness=1, color=RED, spaceAfter=8))

    co2_tonnes = summ["total_co2e_tonnes"]
    intensity  = summ["portfolio_intensity_g_tkm"]
    vs_bench   = summ["vs_benchmark_pct"]
    bench_clr  = GREEN if vs_bench <= 0 else RED
    bench_sign = "+" if vs_bench > 0 else ""
    bench_label = "above benchmark" if vs_bench > 0 else "below benchmark"

    kpi_data = [[
        [Paragraph(f"{co2_tonnes:.2f}", s["red_val"]),
         Paragraph("Total Scope 3 Transport CO₂e (tonnes)", s["kpi_label"])],

        [Paragraph(f"{intensity:.1f}", s["kpi_val"]),
         Paragraph("Emission Intensity (g CO₂e/tonne-km)", s["kpi_label"])],

        [Paragraph(f"{summ['total_trips']}", s["kpi_val"]),
         Paragraph("Total Trips Analysed", s["kpi_label"])],

        [Paragraph(f"{bench_sign}{vs_bench}%", s["green_val"] if vs_bench <= 0 else s["red_val"]),
         Paragraph(f"vs GLEC India Benchmark ({bench_label})", s["kpi_label"])],
    ]]

    kpi_inner = []
    for cell in kpi_data[0]:
        inner = Table([[cell[0]], [cell[1]]], colWidths=[W*0.22])
        inner.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), WHITE),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("RIGHTPADDING",  (0,0),(-1,-1), 4),
            ("BOX",           (0,0),(-1,-1), 0.5, RULE),
        ]))
        kpi_inner.append(inner)

    kpi_row = Table([kpi_inner], colWidths=[W*0.25]*4)
    kpi_row.setStyle(TableStyle([
        ("ALIGN",   (0,0),(-1,-1), "CENTER"),
        ("VALIGN",  (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LEFTPADDING", (0,0),(-1,-1), 2),
        ("RIGHTPADDING",(0,0),(-1,-1), 2),
    ]))
    story.append(kpi_row)
    story.append(Spacer(1, 12))

    # TTW vs WTT breakdown
    ttw = summ["ttw_co2e_tonnes"]
    wtt = summ["wtt_co2e_tonnes"]
    dq3 = summ["data_quality_level3_pct"]
    dq2 = summ["data_quality_level2_pct"]

    breakdown_data = [
        [Paragraph("Emission Boundary", s["tbl_hdr"]),
         Paragraph("CO₂e (tonnes)", s["tbl_hdr"]),
         Paragraph("% of Total", s["tbl_hdr"]),
         Paragraph("GLEC Boundary", s["tbl_hdr"])],
        ["Tank-to-Wheel (TTW)", f"{ttw:.4f}",
         f"{ttw/co2_tonnes*100:.1f}%" if co2_tonnes > 0 else "—",
         "Required"],
        ["Well-to-Tank (WTT)", f"{wtt:.4f}",
         f"{wtt/co2_tonnes*100:.1f}%" if co2_tonnes > 0 else "—",
         "Required"],
        [Paragraph("<b>TOTAL (Well-to-Wheel)</b>", s["body"]),
         Paragraph(f"<b>{co2_tonnes:.4f}</b>", s["body"]),
         "100%",
         Paragraph("<b>Reported</b>", s["body"])],
    ]
    breakdown_tbl = Table(breakdown_data, colWidths=[W*0.35, W*0.2, W*0.2, W*0.25])
    breakdown_tbl.setStyle(tbl_style())
    breakdown_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("BACKGROUND",    (0,-1),(-1,-1), colors.HexColor("#F1F5F9")),
        ("FONTNAME",      (0,-1),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("ALIGN",         (0,1), (0,-1),  "LEFT"),
        ("GRID",          (0,0), (-1,-1), 0.4, RULE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(breakdown_tbl)
    story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────────
    # BRSR CORE DISCLOSURE FORMAT
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("2. BRSR CORE DISCLOSURE — SCOPE 3 TRANSPORT (SEBI FORMAT)", s["h1"]))
    story.append(HRFlowable(width=W, thickness=1, color=RED, spaceAfter=8))
    story.append(Paragraph(
        "The following disclosure is prepared in accordance with SEBI's Business Responsibility and "
        "Sustainability Reporting (BRSR) Core framework (Circular No. SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 "
        "dated 12 July 2023) for Scope 3 Category 4 (Upstream Transportation and Distribution) and "
        "Category 9 (Downstream Transportation and Distribution).",
        s["body"]))
    story.append(Spacer(1, 8))

    brsr_data = [
        [Paragraph("BRSR Parameter", s["tbl_hdr"]),
         Paragraph("Unit", s["tbl_hdr"]),
         Paragraph("FY " + fy + " (Current Year)", s["tbl_hdr"]),
         Paragraph("Methodology", s["tbl_hdr"])],
        ["Total GHG emissions from transport (Scope 3)",
         "Metric tonnes CO₂e",
         f"{co2_tonnes:.4f}",
         "GLEC v3.0 / ISO 14083"],
        ["Tank-to-Wheel (TTW) emissions",
         "Metric tonnes CO₂e",
         f"{ttw:.4f}",
         "Actual/Default factors"],
        ["Well-to-Tank (WTT) emissions",
         "Metric tonnes CO₂e",
         f"{wtt:.4f}",
         "GLEC WTT uplift factors"],
        ["Emission intensity — transport",
         "g CO₂e per tonne-km",
         f"{intensity:.2f}",
         "Activity-based calculation"],
        ["Total transport distance",
         "Kilometres",
         f"{summ['total_distance_km']:,.0f}",
         "GPS/Invoice verified"],
        ["Total freight activity",
         "Tonne-kilometres",
         f"{summ['total_tonne_km']:,.0f}",
         "Distance × payload"],
        ["Number of trips analysed",
         "Count",
         f"{summ['total_trips']}",
         "Trip-level data"],
        ["Data coverage — Level 3 (actual fuel)",
         "% of trips",
         f"{dq3:.1f}%",
         "Measured data"],
        ["Data coverage — Level 2 (distance-based)",
         "% of trips",
         f"{dq2:.1f}%",
         "Default GLEC factors"],
    ]

    brsr_tbl = Table(brsr_data, colWidths=[W*0.38, W*0.18, W*0.22, W*0.22])
    brsr_tbl.setStyle(tbl_style())
    story.append(brsr_tbl)
    story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────────
    # CARRIER BREAKDOWN
    # ─────────────────────────────────────────────────────────────────────────
    carriers = portfolio_result.get("by_carrier", {})
    if carriers:
        story.append(Paragraph("3. EMISSIONS BY CARRIER / LOGISTICS PARTNER", s["h1"]))
        story.append(HRFlowable(width=W, thickness=1, color=RED, spaceAfter=8))

        carrier_rows = [
            [Paragraph("Carrier / Vendor", s["tbl_hdr"]),
             Paragraph("Trips", s["tbl_hdr"]),
             Paragraph("Distance (km)", s["tbl_hdr"]),
             Paragraph("CO₂e (kg)", s["tbl_hdr"]),
             Paragraph("CO₂e (tonnes)", s["tbl_hdr"]),
             Paragraph("Intensity (g/tkm)", s["tbl_hdr"]),
             Paragraph("% of Total", s["tbl_hdr"])],
        ]
        sorted_carriers = sorted(carriers.items(), key=lambda x: x[1]["co2e_kg"], reverse=True)
        for name, data in sorted_carriers:
            pct = data["co2e_kg"] / summ["total_co2e_kg"] * 100 if summ["total_co2e_kg"] > 0 else 0
            inten = data["intensity_g_tkm"]
            inten_clr = "red" if inten > 90 else ("orange" if inten > 70 else "green")
            carrier_rows.append([
                name,
                str(data["trips"]),
                f"{data['distance_km']:,.0f}",
                f"{data['co2e_kg']:,.2f}",
                f"{data['co2e_kg']/1000:.4f}",
                Paragraph(f"<font color='{inten_clr}'><b>{inten:.1f}</b></font>", s["tbl_cell"]),
                f"{pct:.1f}%",
            ])

        # Total row
        carrier_rows.append([
            Paragraph("<b>TOTAL</b>", s["tbl_cell_l"]),
            Paragraph(f"<b>{summ['total_trips']}</b>", s["tbl_cell"]),
            Paragraph(f"<b>{summ['total_distance_km']:,.0f}</b>", s["tbl_cell"]),
            Paragraph(f"<b>{summ['total_co2e_kg']:,.2f}</b>", s["tbl_cell"]),
            Paragraph(f"<b>{co2_tonnes:.4f}</b>", s["tbl_cell"]),
            Paragraph(f"<b>{intensity:.1f}</b>", s["tbl_cell"]),
            Paragraph("<b>100%</b>", s["tbl_cell"]),
        ])

        c_tbl = Table(carrier_rows,
                      colWidths=[W*0.22, W*0.07, W*0.14, W*0.14, W*0.13, W*0.15, W*0.10],
                      repeatRows=1)
        c_tbl.setStyle(tbl_style())
        c_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,-1),(-1,-1), colors.HexColor("#F1F5F9")),
            ("FONTNAME",   (0,-1),(-1,-1), "Helvetica-Bold"),
        ]))
        story.append(c_tbl)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "Note: Emission intensity above 90 g CO₂e/tonne-km is highlighted in red (above GLEC India benchmark). "
            "Carriers in red should be prioritised for decarbonisation initiatives.",
            s["body_sm"]))
        story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────────
    # BY VEHICLE AND FUEL
    # ─────────────────────────────────────────────────────────────────────────
    by_vehicle = portfolio_result.get("by_vehicle", {})
    by_fuel    = portfolio_result.get("by_fuel", {})

    if by_vehicle or by_fuel:
        story.append(Paragraph("4. FLEET MIX ANALYSIS", s["h1"]))
        story.append(HRFlowable(width=W, thickness=1, color=RED, spaceAfter=8))

        col1_rows = [
            [Paragraph("Vehicle Type", s["tbl_hdr"]),
             Paragraph("Trips", s["tbl_hdr"]),
             Paragraph("CO₂e (tonnes)", s["tbl_hdr"]),
             Paragraph("Share", s["tbl_hdr"])],
        ]
        for vname, vdata in sorted(by_vehicle.items(), key=lambda x: x[1]["co2e_kg"], reverse=True):
            pct = vdata["co2e_kg"] / summ["total_co2e_kg"] * 100 if summ["total_co2e_kg"] > 0 else 0
            col1_rows.append([vname, str(vdata["trips"]),
                               f"{vdata['co2e_kg']/1000:.4f}", f"{pct:.1f}%"])

        col2_rows = [
            [Paragraph("Fuel Type", s["tbl_hdr"]),
             Paragraph("Trips", s["tbl_hdr"]),
             Paragraph("CO₂e (tonnes)", s["tbl_hdr"]),
             Paragraph("Share", s["tbl_hdr"])],
        ]
        for fname, fdata in sorted(by_fuel.items(), key=lambda x: x[1]["co2e_kg"], reverse=True):
            pct = fdata["co2e_kg"] / summ["total_co2e_kg"] * 100 if summ["total_co2e_kg"] > 0 else 0
            col2_rows.append([fname, str(fdata["trips"]),
                               f"{fdata['co2e_kg']/1000:.4f}", f"{pct:.1f}%"])

        t1 = Table(col1_rows, colWidths=[W*0.24, W*0.07, W*0.13, W*0.07])
        t2 = Table(col2_rows, colWidths=[W*0.18, W*0.07, W*0.13, W*0.07])
        for t in [t1, t2]:
            t.setStyle(tbl_style())

        mix_tbl = Table([[t1, Spacer(0.02*W, 1), t2]],
                         colWidths=[W*0.51+4, 0.02*W, W*0.45+4])
        mix_tbl.setStyle(TableStyle([
            ("VALIGN", (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        story.append(mix_tbl)
        story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────────
    # TRIP DETAIL TABLE (top 20 by emissions)
    # ─────────────────────────────────────────────────────────────────────────
    trips = portfolio_result.get("trips", [])
    if trips:
        story.append(PageBreak())
        story.append(Paragraph("5. TRIP-LEVEL AUDIT DETAIL (Top 20 by Emissions)", s["h1"]))
        story.append(HRFlowable(width=W, thickness=1, color=RED, spaceAfter=8))

        top_trips = sorted(trips, key=lambda x: x["total_co2e_kg"], reverse=True)[:20]

        trip_rows = [
            [Paragraph("Trip ID", s["tbl_hdr"]),
             Paragraph("Route", s["tbl_hdr"]),
             Paragraph("Carrier", s["tbl_hdr"]),
             Paragraph("Dist (km)", s["tbl_hdr"]),
             Paragraph("Vehicle", s["tbl_hdr"]),
             Paragraph("Fuel", s["tbl_hdr"]),
             Paragraph("CO₂e (kg)", s["tbl_hdr"]),
             Paragraph("g/tkm", s["tbl_hdr"]),
             Paragraph("Method", s["tbl_hdr"])],
        ]
        for r in top_trips:
            method_short = "L3" if "Level 3" in r["method"] else "L2"
            inten = r["intensity_g_tkm"]
            inten_str = f"{inten:.0f}"
            trip_rows.append([
                r.get("trip_id","")[:12],
                (r.get("route","") or "")[:20],
                (r.get("carrier","") or "")[:16],
                f"{r['distance_km']:.0f}",
                r["vehicle_label"][:14],
                r["fuel_label"][:8],
                f"{r['total_co2e_kg']:.3f}",
                inten_str,
                method_short,
            ])

        trip_tbl = Table(trip_rows,
                         colWidths=[W*0.10, W*0.16, W*0.13, W*0.08,
                                    W*0.13, W*0.08, W*0.09, W*0.07, W*0.07],
                         repeatRows=1)
        trip_tbl.setStyle(tbl_style())
        story.append(trip_tbl)
        story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────────
    # REDUCTION OPPORTUNITIES
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("6. REDUCTION OPPORTUNITIES", s["h1"]))
    story.append(HRFlowable(width=W, thickness=1, color=RED, spaceAfter=8))

    opps = []
    # High-intensity carriers
    for name, data in (carriers or {}).items():
        if data["intensity_g_tkm"] > 90:
            saving = (data["intensity_g_tkm"] - 75) * data["tonne_km"] / 1e6
            opps.append({
                "opportunity": f"Optimise {name} (intensity {data['intensity_g_tkm']:.0f} g/tkm)",
                "action": "Route optimisation or vehicle upgrade",
                "potential_saving_tco2": round(saving, 3),
                "priority": "High",
            })
    # Diesel to EV for LCVs
    diesel_lcv = sum(1 for t in trips
                     if t.get("vehicle_type","") in ["lgv_van","lgv_pickup","car_diesel"]
                     and t.get("fuel_type","") == "diesel")
    if diesel_lcv > 0:
        potential = diesel_lcv * 0.05   # rough estimate
        opps.append({
            "opportunity": f"Electrify {diesel_lcv} diesel LCV/car trips",
            "action": "Transition to EV alternatives",
            "potential_saving_tco2": round(potential, 3),
            "priority": "Medium",
        })

    if not opps:
        story.append(Paragraph(
            "Fleet emission intensity is within GLEC benchmarks. Continue monitoring and "
            "implement SBTi-aligned targets for further reduction.",
            s["body"]))
    else:
        opp_rows = [
            [Paragraph("Opportunity", s["tbl_hdr"]),
             Paragraph("Recommended Action", s["tbl_hdr"]),
             Paragraph("Est. Saving (tCO₂e)", s["tbl_hdr"]),
             Paragraph("Priority", s["tbl_hdr"])],
        ]
        for o in opps:
            p_clr = "red" if o["priority"] == "High" else "orange"
            opp_rows.append([
                o["opportunity"],
                o["action"],
                f"{o['potential_saving_tco2']:.3f}",
                Paragraph(f"<font color='{p_clr}'><b>{o['priority']}</b></font>", s["tbl_cell"]),
            ])
        opp_tbl = Table(opp_rows, colWidths=[W*0.35, W*0.32, W*0.18, W*0.15])
        opp_tbl.setStyle(tbl_style())
        story.append(opp_tbl)

    story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────────────────
    # METHODOLOGY STATEMENT
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("7. METHODOLOGY AND DATA SOURCES", s["h1"]))
    story.append(HRFlowable(width=W, thickness=1, color=RED, spaceAfter=8))

    meth_rows = [
        ["Framework",        method.get("framework", "GLEC Framework v3.0")],
        ["Standard",         method.get("standard", "ISO 14083:2023")],
        ["Emission Factors", method.get("emission_factors", "MoPNG 2023, IPCC AR6, CEA 2023-24")],
        ["Boundary",         method.get("boundary", "Well-to-Wheel (WTW) — TTW + WTT")],
        ["Scope",            method.get("scope", "Scope 3 Category 4 (Upstream Transport)")],
        ["GHGs Included",    method.get("ghg_included", "CO₂, CH₄, N₂O (expressed as CO₂e, AR6 GWPs)")],
        ["Fuel Factors",     "Diesel: 2.68 kg CO₂e/L (TTW) · Petrol: 2.31 · CNG: 2.13/kg · LPG: 1.61"],
        ["Grid Factor",      "National average 0.716 kg CO₂e/kWh (CEA 2023-24)"],
        ["Vehicle Defaults", "ARAI India vehicle efficiency data, GLEC v3.0 Table 4"],
        ["Data Quality",     f"Level 3 (actual fuel): {dq3:.1f}% of trips | Level 2 (default): {dq2:.1f}%"],
        ["Assurance Ready",  "Input log, formula chain, and emission factor citations included in audit package"],
    ]

    meth_tbl = Table(meth_rows, colWidths=[W*0.28, W*0.72])
    meth_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS",  (0,0),(-1,-1), [colors.HexColor("#F8FAFC"), WHITE]),
        ("GRID",            (0,0),(-1,-1), 0.3, RULE),
        ("FONTNAME",        (0,0),(0,-1),  "Helvetica-Bold"),
        ("FONTSIZE",        (0,0),(-1,-1), 8.5),
        ("TOPPADDING",      (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",   (0,0),(-1,-1), 5),
        ("LEFTPADDING",     (0,0),(-1,-1), 8),
        ("VALIGN",          (0,0),(-1,-1), "TOP"),
    ]))
    story.append(meth_tbl)
    story.append(Spacer(1, 16))

    # ─────────────────────────────────────────────────────────────────────────
    # FOOTER DISCLAIMER
    # ─────────────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=RULE, spaceAfter=6))
    story.append(Paragraph(
        f"This report was generated by CarbonLedger on {now} using the GLEC Framework v3.0 / ISO 14083:2023. "
        "Calculations are deterministic and auditable. Emission factors are sourced from MoPNG (2023), "
        "IPCC AR6, and CEA (2023-24). This report is prepared for BRSR Core disclosure purposes in "
        "accordance with SEBI circular dated 12 July 2023. All calculations are available for third-party "
        "verification. CarbonLedger is not a registered auditor; independent assurance by a SEBI-recognised "
        "third party is recommended for formal BRSR filing.",
        s["disclaimer"]))

    doc.build(story)
    return buf.getvalue()
