"""
Email Service — sends OTP emails via Gmail SMTP.

Uses Python's built-in smtplib so no extra dependencies needed.
Reads credentials from SMTP_EMAIL and SMTP_APP_PASSWORD env vars.
"""

import smtplib
import random
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Smart Legal Assistant")


def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically random numeric OTP."""
    return "".join([str(random.SystemRandom().randint(0, 9)) for _ in range(length)])


def _build_otp_email_html(otp: str, purpose: str, user_name: str) -> str:
    """Build a clean HTML email body for OTP delivery."""
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


def send_otp_email(
    to_email: str,
    otp: str,
    user_name: str = "User",
    purpose: str = "verification"
) -> bool:
    """
    Send an OTP email via Gmail SMTP.

    Args:
        to_email: Recipient email address
        otp: The 6-digit OTP string
        user_name: Recipient's name for personalization
        purpose: 'verification' or 'password_reset'

    Returns:
        True if sent successfully, False otherwise
    """
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        logger.error("[EMAIL] SMTP_EMAIL or SMTP_APP_PASSWORD not configured in .env")
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

    plain_text = (
        f"Hi {user_name},\n\n"
        f"Your OTP code is: {otp}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you did not request this, ignore this email.\n\n"
        f"— Smart Legal Assistant"
    )
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(_build_otp_email_html(otp, purpose, user_name), "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        logger.info(f"[EMAIL] OTP email sent to {to_email} (purpose: {purpose})")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[EMAIL] Gmail authentication failed. Check SMTP_APP_PASSWORD in .env")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"[EMAIL] SMTP error sending to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"[EMAIL] Unexpected error sending email to {to_email}: {e}")
        return False
