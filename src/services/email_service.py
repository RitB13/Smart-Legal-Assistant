"""
Email Service — sends OTP emails via Brevo API (HTTP) or Gmail SMTP fallback.

Production (HF Spaces): uses Brevo HTTP API (port 443, always open).
Local development: falls back to Gmail SMTP if BREVO_API_KEY is not set.

Environment variables:
  BREVO_API_KEY     — Brevo transactional API key (production)
  SMTP_EMAIL        — Gmail address (local fallback)
  SMTP_APP_PASSWORD — Gmail App Password (local fallback)
"""

import smtplib
import random
import logging
import os
import requests as _requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

BREVO_API_KEY   = os.getenv("BREVO_API_KEY", "")
SMTP_EMAIL      = os.getenv("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
SMTP_FROM_NAME  = os.getenv("SMTP_FROM_NAME", "Smart Legal Assistant")
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587

BREVO_API_URL   = "https://api.brevo.com/v3/smtp/email"


def generate_otp(length: int = 6) -> str:
    return "".join([str(random.SystemRandom().randint(0, 9)) for _ in range(length)])


def _build_otp_email_html(otp: str, purpose: str, user_name: str) -> str:
    action_labels = {
        "verification": ("Verify Your Email", "to complete your registration"),
        "password_reset": ("Reset Your Password", "to reset your password"),
    }
    title, subtitle = action_labels.get(purpose, ("Your OTP Code", "to proceed"))

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }}
    .container {{ max-width: 480px; margin: 40px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .header {{ background: #1e40af; padding: 24px; text-align: center; }}
    .header h1 {{ color: #ffffff; margin: 0; font-size: 22px; }}
    .body {{ padding: 32px; }}
    .otp-box {{ background: #f0f4ff; border: 2px dashed #1e40af; border-radius: 8px; text-align: center; padding: 20px; margin: 24px 0; }}
    .otp-code {{ font-size: 42px; font-weight: bold; letter-spacing: 10px; color: #1e40af; }}
    .expiry {{ color: #6b7280; font-size: 13px; margin-top: 8px; }}
    .footer {{ background: #f9fafb; padding: 16px; text-align: center; color: #9ca3af; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header"><h1>⚖️ Smart Legal Assistant</h1></div>
    <div class="body">
      <h2>{title}</h2>
      <p>Hi {user_name},</p>
      <p>Use the code below {subtitle}. This code expires in <strong>10 minutes</strong>.</p>
      <div class="otp-box">
        <div class="otp-code">{otp}</div>
        <div class="expiry">Valid for 10 minutes only</div>
      </div>
      <p>If you did not request this, please ignore this email. Your account remains secure.</p>
    </div>
    <div class="footer">
      Smart Legal Assistant &mdash; AI-powered legal guidance<br>
      Do not share this code with anyone.
    </div>
  </div>
</body>
</html>
"""


def _send_via_brevo(to_email: str, otp: str, user_name: str, purpose: str) -> bool:
    subject_map = {
        "verification": "Your Smart Legal Assistant verification code",
        "password_reset": "Reset your Smart Legal Assistant password",
    }
    subject = subject_map.get(purpose, "Your OTP code")

    payload = {
        "sender": {"name": SMTP_FROM_NAME, "email": SMTP_EMAIL or "noreply@smartlegalassistant.com"},
        "to": [{"email": to_email, "name": user_name}],
        "subject": subject,
        "htmlContent": _build_otp_email_html(otp, purpose, user_name),
        "textContent": (
            f"Hi {user_name},\n\n"
            f"Your OTP code is: {otp}\n\n"
            f"This code expires in 10 minutes.\n\n"
            f"— Smart Legal Assistant"
        ),
    }

    try:
        resp = _requests.post(
            BREVO_API_URL,
            headers={
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info(f"[EMAIL] Brevo: OTP sent to {to_email} (purpose: {purpose})")
            return True
        else:
            logger.error(f"[EMAIL] Brevo error {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"[EMAIL] Brevo request failed: {e}")
        return False


def _send_via_smtp(to_email: str, otp: str, user_name: str, purpose: str) -> bool:
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        logger.error("[EMAIL] SMTP credentials not configured")
        return False

    subject_map = {
        "verification": "Your Smart Legal Assistant verification code",
        "password_reset": "Reset your Smart Legal Assistant password",
    }
    subject = subject_map.get(purpose, "Your OTP code")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(
        f"Hi {user_name},\n\nYour OTP code is: {otp}\n\nExpires in 10 minutes.\n\n— Smart Legal Assistant",
        "plain"
    ))
    msg.attach(MIMEText(_build_otp_email_html(otp, purpose, user_name), "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        logger.info(f"[EMAIL] SMTP: OTP sent to {to_email} (purpose: {purpose})")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("[EMAIL] Gmail authentication failed")
        return False
    except Exception as e:
        logger.error(f"[EMAIL] SMTP error: {e}")
        return False


def send_otp_email(
    to_email: str,
    otp: str,
    user_name: str = "User",
    purpose: str = "verification",
) -> bool:
    if BREVO_API_KEY:
        return _send_via_brevo(to_email, otp, user_name, purpose)
    return _send_via_smtp(to_email, otp, user_name, purpose)
