"""Script to create a clean ZIP package of The SilentZone Sentinel source code
and generate a comprehensive Step-by-Step PDF Deployment Guide for GitHub & Render.com.
"""
import os
import shutil
import sys
import zipfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT_DIR = Path(r"D:\Juniad baghdadi\khamoshi-radar")
OUTPUT_ZIP = Path(r"D:\Juniad baghdadi\The_SilentZone_Sentinel_SourceCode.zip")
OUTPUT_ZIP_LOCAL = ROOT_DIR / "The_SilentZone_Sentinel_SourceCode.zip"
OUTPUT_PDF = Path(r"D:\Juniad baghdadi\Deployment_Guide_SilentZone_Sentinel.pdf")
OUTPUT_PDF_LOCAL = ROOT_DIR / "Deployment_Guide_SilentZone_Sentinel.pdf"

def make_zip():
    print(f"[*] Creating ZIP archive...")
    ignore_dirs = {".venv", "__pycache__", ".git", ".idea", ".vscode", "dist", "build"}
    ignore_extensions = {".pyc", ".pyo", ".pyd"}

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ignore_extensions:
                    continue
                if file.endswith(".zip") or file.endswith(".tar.gz"):
                    continue
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR)
                zipf.write(full_path, rel_path)
                
    shutil.copy2(OUTPUT_ZIP, OUTPUT_ZIP_LOCAL)
    print(f"[+] ZIP created successfully at:\n    - {OUTPUT_ZIP}\n    - {OUTPUT_ZIP_LOCAL}")


def make_pdf():
    print(f"[*] Generating Step-by-Step PDF Deployment Guide...")
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e3d59"),
        alignment=1, # Center
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#17b978"),
        alignment=1, # Center
    )
    h1_style = ParagraphStyle(
        "H1Style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e3d59"),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "H2Style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0f4c81"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#2d3748"),
    )
    code_style = ParagraphStyle(
        "CodeStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1a202c"),
        backColor=colors.HexColor("#edf2f7"),
        borderColor=colors.HexColor("#cbd5e0"),
        borderWidth=1,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6,
    )
    note_box_style = ParagraphStyle(
        "NoteBox",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#15803d"),
        backColor=colors.HexColor("#f0fdf4"),
        borderColor=colors.HexColor("#bbf7d0"),
        borderWidth=1,
        borderPadding=8,
        spaceBefore=6,
        spaceAfter=6,
    )

    story = []

    # Title & Header
    story.append(Paragraph("🛡️ The SilentZone Sentinel — Deployment Guide", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Step-by-Step Guide for Private GitHub Setup & Cloud Hosting on Render.com", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Prepared by: <b>Malik Junaid Ahmad</b> & <b>Saira Khan</b>", ParagraphStyle("Auth", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13, alignment=1, textColor=colors.HexColor("#4a5568"))))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3d59"), spaceAfter=12))

    # Introduction Box
    intro_text = (
        "<b>Important Security Notice:</b> By hosting via a <b>Private GitHub Repository</b>, "
        "your raw source code remains 100% confidential and safe. Users will only interact with the live "
        "web dashboard in their browsers and cannot view or download your proprietary code."
    )
    story.append(Paragraph(intro_text, note_box_style))
    story.append(Spacer(1, 10))

    # Phase 1
    story.append(Paragraph("Phase 1: Extract & Prepare Source Code on New Computer", h1_style))
    story.append(Paragraph("1. Copy <b>The_SilentZone_Sentinel_SourceCode.zip</b> to the new computer and unzip/extract it into a folder.", body_style))
    story.append(Paragraph("2. Verify that the project contains the following essential files in the root folder:", body_style))
    story.append(Paragraph("• <code>backend/</code> (FastAPI API & LangGraph Agents)<br/>"
                           "• <code>frontend/</code> (Streamlit Command Dashboard & PDF Generator)<br/>"
                           "• <code>Dockerfile</code> (Docker container build recipe)<br/>"
                           "• <code>requirements.txt</code> (Python dependencies list)<br/>"
                           "• <code>run_server.py</code> (Production launcher script)<br/>"
                           "• <code>.env</code> (Environment configuration)", code_style))
    story.append(Spacer(1, 10))

    # Phase 2
    story.append(Paragraph("Phase 2: Push Project to a PRIVATE GitHub Repository", h1_style))
    story.append(Paragraph("1. Open your browser and go to <b>https://github.com</b>.", body_style))
    story.append(Paragraph("2. Log in and click the <b>'New'</b> button (or '+' at top-right) to create a new repository.", body_style))
    story.append(Paragraph("3. <b>Repository Name:</b> Enter <code>silentzone-sentinel</code> (or any name you prefer).", body_style))
    story.append(Paragraph("4. <b>Visibility (CRITICAL):</b> Select <b>🔒 Private</b> (this ensures only YOU have access to source code).", body_style))
    story.append(Paragraph("5. Leave other options unchecked and click <b>'Create repository'</b>.", body_style))
    story.append(Paragraph("6. Open Command Prompt (CMD) or PowerShell in your extracted project folder and run:", body_style))
    
    git_cmds = (
        "git init<br/>"
        "git add .<br/>"
        'git commit -m "Initial commit - The SilentZone Sentinel"<br/>'
        "git branch -M main<br/>"
        "git remote add origin YOUR_PRIVATE_GITHUB_REPO_URL<br/>"
        "git push -u origin main"
    )
    story.append(Paragraph(git_cmds, code_style))
    story.append(Spacer(1, 10))

    # Phase 3
    story.append(Paragraph("Phase 3: Deploy Live Web Service on Render.com (100% Free)", h1_style))
    story.append(Paragraph("1. Open <b>https://render.com</b> and create a free account (Sign up with GitHub for 1-click connect).", body_style))
    story.append(Paragraph("2. On your Render dashboard, click <b>'New +'</b> at the top and select <b>'Web Service'</b>.", body_style))
    story.append(Paragraph("3. Select <b>'Build and deploy from a Git repository'</b> and connect your GitHub account.", body_style))
    story.append(Paragraph("4. Find and choose your Private repository <b><code>silentzone-sentinel</code></b>.", body_style))
    story.append(Paragraph("5. Configure the deployment parameters exactly as follows:", body_style))

    # Table of settings
    table_data = [
        ["Setting Field", "Value to Enter / Select"],
        ["Name", "silentzone-sentinel"],
        ["Region", "Singapore / Frankfurt (closest to your users)"],
        ["Branch", "main"],
        ["Language / Runtime", "Docker (Render automatically detects Dockerfile)"],
        ["Instance Type", "Free (0.1 CPU, 512 MB RAM)"],
    ]
    t = Table(table_data, colWidths=[180, 330])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3d59")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("6. Click the <b>'Deploy Web Service'</b> button at the bottom.", body_style))
    story.append(Paragraph("7. Wait 2–3 minutes while Render builds the Docker image. Once complete, Render will give you a live URL, for example: <b><code>https://silentzone-sentinel.onrender.com</code></b>.", body_style))
    story.append(Spacer(1, 10))

    # Local Run alternative
    story.append(Paragraph("Alternative: Running Locally on Any New Computer", h1_style))
    story.append(Paragraph("If you want to run the project locally on any Windows/Mac/Linux machine without cloud deployment:", body_style))
    local_cmds = (
        "1. Open terminal inside the extracted project folder.<br/>"
        "2. Create virtual environment: <b>python -m venv .venv</b><br/>"
        "3. Activate: <b>.venv\\Scripts\\activate</b> (or <b>source .venv/bin/activate</b> on Linux/Mac)<br/>"
        "4. Install dependencies: <b>pip install -r requirements.txt</b><br/>"
        "5. Launch all services: <b>python run_server.py</b><br/>"
        "6. Open browser: <b>http://localhost:8501</b>"
    )
    story.append(Paragraph(local_cmds, code_style))
    story.append(Spacer(1, 15))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e0"), spaceAfter=8))
    story.append(Paragraph("Project Developed by <b>Malik Junaid Ahmad</b> & <b>Saira Khan</b> — The SilentZone Sentinel © 2026", ParagraphStyle("Footer", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, alignment=1, textColor=colors.HexColor("#718096"))))

    doc.build(story)
    shutil.copy2(OUTPUT_PDF, OUTPUT_PDF_LOCAL)
    print(f"[+] PDF Guide created successfully at:\n    - {OUTPUT_PDF}\n    - {OUTPUT_PDF_LOCAL}")

if __name__ == "__main__":
    make_zip()
    make_pdf()
