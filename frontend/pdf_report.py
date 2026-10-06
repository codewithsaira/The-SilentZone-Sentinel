"""PDF Report Generator for The SilentZone Sentinel Area Flood & Silent Zone Assessment."""
import io
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_area_flood_pdf(
    area_name: str,
    lat: float,
    lon: float,
    radius_km: float,
    summary: dict,
    silent_zones: list[dict],
    flooded_sos: list[dict],
    safe_zones: list[dict],
    weather_info: dict | None = None,
    operator_name: str = "Active Operator",
) -> bytes:
    """Generates a professional PDF report and returns PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#1e3d59")
    c_secondary = colors.HexColor("#17b978")
    c_danger = colors.HexColor("#d32f2f")
    c_warning = colors.HexColor("#f57c00")
    c_safe = colors.HexColor("#2e7d32")
    c_gray_bg = colors.HexColor("#f8f9fa")
    c_card_border = colors.HexColor("#e0e0e0")

    # Typography Styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_primary,
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#555555"),
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=c_primary,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#222222"),
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#666666"),
    )

    story = []

    # 1. Header & Branding Banner
    banner_data = [
        [
            Paragraph("<b>🛡️ THE SILENTZONE SENTINEL</b><br/><font size='8.5'>Autonomous Multi-Agent Flood Response & Silent Zone Detection System</font>", ParagraphStyle("BannerL", parent=title_style, textColor=colors.white, fontSize=14, leading=18)),
            Paragraph(f"<b>FLOOD ASSESSMENT REPORT</b><br/><font size='8.5'>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</font>", ParagraphStyle("BannerR", parent=subtitle_style, textColor=colors.white, alignment=2, fontSize=9, leading=13))
        ]
    ]
    banner_table = Table(banner_data, colWidths=[360, 180])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_primary),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    # 2. Project Attribution Box (Malik Junaid Ahmad & Saira Khan)
    attrib_data = [
        [
            Paragraph("<b>🎓 Project Prepared By:</b> Malik Junaid Ahmad &nbsp;&nbsp;|&nbsp;&nbsp; Saira Khan", ParagraphStyle("Attrib", parent=body_style, textColor=colors.HexColor("#1b5e20"), fontName="Helvetica-Bold", fontSize=9.5)),
            Paragraph(f"<b>Operator:</b> {operator_name}", ParagraphStyle("Op", parent=meta_style, alignment=2))
        ]
    ]
    attrib_table = Table(attrib_data, colWidths=[380, 160])
    attrib_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e8f5e9")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#a5d6a7")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(attrib_table)
    story.append(Spacer(1, 12))

    # 3. Target Scope & Parameters
    scope_data = [
        [
            Paragraph(f"<b>Target Center:</b> {area_name}", body_style),
            Paragraph(f"<b>Coordinates:</b> {lat:.4f}° N, {lon:.4f}° E", body_style),
            Paragraph(f"<b>Scan Radius:</b> {radius_km:.1f} KM", body_style),
        ]
    ]
    scope_table = Table(scope_data, colWidths=[200, 200, 140])
    scope_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_gray_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, c_card_border),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(scope_table)
    story.append(Spacer(1, 10))

    # 4. Executive Summary Metrics
    story.append(Paragraph("1. Executive Summary & Impact Overview", h2_style))
    
    total_pop_affected = summary.get("total_pop_affected", 0)
    silent_pop = summary.get("silent_pop", 0)
    total_villages = summary.get("total_villages", 0)
    flooded_count = len(silent_zones) + len(flooded_sos)
    silent_count = len(silent_zones)
    safe_count = len(safe_zones)

    metrics_data = [
        [
            Paragraph(f"<b>{total_villages}</b><br/><font size='8' color='#666'>Total Settlements in Radius</font>", ParagraphStyle("M1", parent=body_style, alignment=1, fontSize=12, leading=15)),
            Paragraph(f"<font color='#d32f2f'><b>{flooded_count}</b></font><br/><font size='8' color='#666'>Flooded Settlements</font>", ParagraphStyle("M2", parent=body_style, alignment=1, fontSize=12, leading=15)),
            Paragraph(f"<font color='#c62828'><b>{silent_count}</b></font><br/><font size='8' color='#666'>SILENT ZONES (0 SOS)</font>", ParagraphStyle("M3", parent=body_style, alignment=1, fontSize=12, leading=15)),
            Paragraph(f"<b>{total_pop_affected:,}</b><br/><font size='8' color='#666'>Population Affected</font>", ParagraphStyle("M4", parent=body_style, alignment=1, fontSize=12, leading=15)),
            Paragraph(f"<font color='#2e7d32'><b>{safe_count}</b></font><br/><font size='8' color='#666'>Dry / Safe Buffer</font>", ParagraphStyle("M5", parent=body_style, alignment=1, fontSize=12, leading=15)),
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[108, 108, 108, 108, 108])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#b0bec5")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8dc")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 10))

    # Weather & Severity Note if present
    if weather_info:
        w_text = (
            f"<b>Hydrometeorological Conditions:</b> Rain in past 3 days: <b>{weather_info.get('rain_past_3d_mm', 0)} mm</b> | "
            f"Forecast rain: <b>{weather_info.get('rain_forecast_mm', 0)} mm</b> | "
            f"Soil saturation: <b>{int(weather_info.get('soil_saturation', 0) * 100)}%</b> | "
            f"Severity Rating: <b>{weather_info.get('level', 'MODERATE')}</b>"
        )
        w_data = [[Paragraph(w_text, body_style)]]
        w_table = Table(w_data, colWidths=[540])
        w_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e1f5fe")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#81d4fa")),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(w_table)
        story.append(Spacer(1, 10))

    # 5. Silent Zones Table (Critical Priority)
    story.append(Paragraph("2. Critical Silent Zones (Flooded + Zero SOS Received)", h2_style))
    story.append(Paragraph("<i>These communities are inundated and have stopped communicating. Silence is treated as a high-probability distress indicator.</i>", meta_style))
    story.append(Spacer(1, 4))

    if silent_zones:
        s_headers = [
            Paragraph("<b>Zone ID / Name</b>", body_bold),
            Paragraph("<b>Distance</b>", body_bold),
            Paragraph("<b>Population</b>", body_bold),
            Paragraph("<b>Water Depth</b>", body_bold),
            Paragraph("<b>SOS Count</b>", body_bold),
            Paragraph("<b>Priority Level</b>", body_bold),
        ]
        s_rows = [s_headers]
        for z in silent_zones:
            s_rows.append([
                Paragraph(f"<b>{z.get('id', 'Z')}</b> - {z.get('name', 'Unknown')}", body_style),
                Paragraph(f"{z.get('distance_km', 0):.1f} km", body_style),
                Paragraph(f"{z.get('population', 0):,}", body_style),
                Paragraph(f"{z.get('flood_depth_m', 1.0):.1f} m", body_style),
                Paragraph("<font color='#d32f2f'><b>0 (SILENT)</b></font>", body_style),
                Paragraph("<font color='#c62828'><b>CRITICAL</b></font>", body_style),
            ])
        s_table = Table(s_rows, colWidths=[150, 70, 75, 75, 85, 85])
        s_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ffebee")),
            ('TEXTCOLOR', (0, 0), (-1, 0), c_danger),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#ffcdd2")),
            ('BOX', (0, 0), (-1, -1), 1, c_danger),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(s_table)
    else:
        story.append(Paragraph("✅ <i>No silent flooded zones detected in the selected radius.</i>", body_style))
    story.append(Spacer(1, 12))

    # 6. Flooded Villages with SOS Table
    story.append(Paragraph("3. Inundated Settlements with Active SOS Signals", h2_style))
    if flooded_sos:
        f_headers = [
            Paragraph("<b>Settlement Name</b>", body_bold),
            Paragraph("<b>Distance</b>", body_bold),
            Paragraph("<b>Population</b>", body_bold),
            Paragraph("<b>Flood Depth</b>", body_bold),
            Paragraph("<b>SOS Signals</b>", body_bold),
            Paragraph("<b>Status</b>", body_bold),
        ]
        f_rows = [f_headers]
        for v in flooded_sos:
            f_rows.append([
                Paragraph(f"{v.get('name', 'Unknown')}", body_style),
                Paragraph(f"{v.get('distance_km', 0):.1f} km", body_style),
                Paragraph(f"{v.get('population', 0):,}", body_style),
                Paragraph(f"{v.get('flood_depth_m', 1.0):.1f} m", body_style),
                Paragraph(f"<b>{v.get('sos_count', 1)} Active</b>", body_style),
                Paragraph("<font color='#e65100'>In Distress</font>", body_style),
            ])
        f_table = Table(f_rows, colWidths=[150, 70, 75, 75, 85, 85])
        f_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fff3e0")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#ffe0b2")),
            ('BOX', (0, 0), (-1, -1), 1, c_warning),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(f_table)
    else:
        story.append(Paragraph("<i>No flooded settlements with active SOS signals in this radius.</i>", body_style))
    story.append(Spacer(1, 12))

    # 7. Dry & Safe Buffer Settlements
    story.append(Paragraph("4. Dry / Safe Buffer Settlements (Staging & Verification Nodes)", h2_style))
    if safe_zones:
        safe_sample = safe_zones[:8]
        safe_headers = [
            Paragraph("<b>Settlement Name</b>", body_bold),
            Paragraph("<b>Distance</b>", body_bold),
            Paragraph("<b>Population</b>", body_bold),
            Paragraph("<b>Representative Contact</b>", body_bold),
            Paragraph("<b>Status</b>", body_bold),
        ]
        safe_rows = [safe_headers]
        for s in safe_sample:
            safe_rows.append([
                Paragraph(f"{s.get('name', 'Unknown')}", body_style),
                Paragraph(f"{s.get('distance_km', 0):.1f} km", body_style),
                Paragraph(f"{s.get('population', 0):,}", body_style),
                Paragraph(f"{s.get('rep', 'Village Rep')}", body_style),
                Paragraph("<font color='#2e7d32'><b>DRY / ACCESSIBLE</b></font>", body_style),
            ])
        safe_table = Table(safe_rows, colWidths=[160, 75, 85, 130, 90])
        safe_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e8f5e9")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#c8e6c9")),
            ('BOX', (0, 0), (-1, -1), 1, c_safe),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(safe_table)
        if len(safe_zones) > len(safe_sample):
            story.append(Paragraph(f"<i>...and {len(safe_zones) - len(safe_sample)} more dry settlements in this radius.</i>", meta_style))
    else:
        story.append(Paragraph("<i>No dry settlements found in the selected radius.</i>", body_style))
    story.append(Spacer(1, 14))

    # 8. Operational Recommendations
    recomms = [
        [
            Paragraph(
                "<b>Operational Recommendation for Incident Commander:</b><br/>"
                "1. Immediately deploy neighbor verification to confirm cutoff status for all Silent Zones.<br/>"
                "2. Pre-stage motorized rescue boats from Rescue 1122 and Al-Khidmat at the nearest dry buffer settlement.<br/>"
                "3. Coordinate with Edhi Foundation for emergency food distribution in high-density flooded sectors.<br/>"
                "4. All field actions remain subject to explicit human coordinator approval.",
                body_style
            )
        ]
    ]
    rec_table = Table(recomms, colWidths=[540])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
        ('BOX', (0, 0), (-1, -1), 1, c_primary),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether(rec_table))
    story.append(Spacer(1, 12))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceBefore=10, spaceAfter=8))
    story.append(Paragraph("The SilentZone Sentinel Emergency Assessment Prototype · Prepared by Malik Junaid Ahmad & Saira Khan", meta_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
