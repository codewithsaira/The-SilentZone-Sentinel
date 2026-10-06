"""Email Dispatch Service for The SilentZone Sentinel using Python's built-in smtplib."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")


def send_real_gmail_otp(to_email: str, recipient_name: str, otp_code: str) -> tuple[bool, str]:
    """Sends a real, styled HTML verification email with the 6-digit OTP code."""
    # Check if SMTP credentials exist in environment
    sender_email = os.getenv("SMTP_EMAIL", SMTP_EMAIL).strip()
    sender_password = os.getenv("SMTP_APP_PASSWORD", SMTP_APP_PASSWORD).strip()

    if not sender_email or not sender_password:
        return False, "SMTP credentials not configured in .env yet. Displaying verification code on screen."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔐 {otp_code} is your The SilentZone Sentinel Verification Code"
        msg["From"] = f"The SilentZone Sentinel <{sender_email}>"
        msg["To"] = to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }}
            .container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #1e3d59 0%, #17b978 100%); padding: 25px 20px; text-align: center; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
            .header p {{ margin: 5px 0 0 0; font-size: 13px; opacity: 0.9; }}
            .content {{ padding: 30px 25px; color: #333333; }}
            .greeting {{ font-size: 16px; font-weight: 600; margin-bottom: 15px; color: #1e3d59; }}
            .otp-container {{ text-align: center; margin: 25px 0; background: #f0fdf4; border: 2px dashed #17b978; border-radius: 10px; padding: 18px; }}
            .otp-code {{ font-size: 32px; font-weight: 800; color: #1e3d59; letter-spacing: 8px; font-family: 'Courier New', Courier, monospace; }}
            .instructions {{ font-size: 13px; color: #666666; line-height: 1.6; margin-top: 20px; }}
            .footer {{ background: #f8fafc; padding: 15px; text-align: center; font-size: 11px; color: #888888; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>🛡️ The SilentZone Sentinel</h1>
              <p>Autonomous AI Flood Response & Silent Zone Detection</p>
            </div>
            <div class="content">
              <div class="greeting">Salaam, {recipient_name}!</div>
              <p style="font-size: 14px; line-height: 1.5; color: #444;">
                Thank you for registering on <b>The SilentZone Sentinel</b> platform. Use the 6-digit verification code below to confirm your Gmail address:
              </p>
              <div class="otp-container">
                <div style="font-size: 12px; color: #17b978; font-weight: bold; text-transform: uppercase; margin-bottom: 6px;">Your One-Time Security Code</div>
                <div class="otp-code">{otp_code}</div>
              </div>
              <p class="instructions">
                • This code is valid for <b>10 minutes</b>.<br/>
                • Do not share this code with anyone.<br/>
                • If you did not request this code, please ignore this email.
              </p>
            </div>
            <div class="footer">
              <b>Prepared by:</b> Malik Junaid Ahmad & Saira Khan<br/>
              The SilentZone Sentinel Flood Management System
            </div>
          </div>
        </body>
        </html>
        """

        text_content = f"Salaam {recipient_name},\n\nYour The SilentZone Sentinel verification code is: {otp_code}\n\nThis code expires in 10 minutes.\n\nPrepared by: Malik Junaid Ahmad & Saira Khan"

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        return True, f"Verification code successfully sent to {to_email}!"
    except Exception as e:
        return False, f"Failed to send email: {type(e).__name__}: {str(e)}"
