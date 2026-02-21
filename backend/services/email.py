"""
Email service using Resend API (HTTPS, works on Railway)
Fallback: raw Gmail SMTP for local dev where SMTP is not blocked.

Set RESEND_API_KEY in Railway environment variables.
Get a free key at https://resend.com (3,000 emails/month free).
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

RESEND_API_KEY    = os.getenv("RESEND_API_KEY", "")
GMAIL_SMTP_SERVER = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
GMAIL_SMTP_PORT   = int(os.getenv("GMAIL_SMTP_PORT", "587"))
GMAIL_EMAIL       = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", GMAIL_EMAIL or "svidron.robert@gmail.com")
FROM_EMAIL  = os.getenv("FROM_EMAIL", GMAIL_EMAIL or "noreply@svidhaus.app")
FROM_NAME   = "Svidhaus Arena"

# Base URL used in links sent via email
BASE_URL = os.getenv("BASE_URL", "https://svidhaus.up.railway.app")


def _send_via_resend(to: list[str], subject: str, html_body: str) -> bool:
    """Send via Resend REST API over HTTPS using httpx (works on Railway)."""
    try:
        import httpx
    except ImportError:
        print("⚠ httpx not installed — cannot use Resend API")
        return False

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": to,
                "subject": subject,
                "html": html_body,
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            print(f"✓ Email sent via Resend to {to}: {subject}")
            return True
        else:
            print(f"⚠ Resend API error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"⚠ Resend request failed: {e}")
        return False


def _send_via_smtp(to: list[str], subject: str, html_body: str) -> bool:
    """Fallback: send via Gmail SMTP (may be blocked on Railway)."""
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        print("⚠ Gmail SMTP not configured")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{GMAIL_EMAIL}>"
        msg["To"]      = ", ".join(to)
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_EMAIL, to, msg.as_string())

        print(f"✓ Email sent via SMTP to {to}: {subject}")
        return True
    except Exception as e:
        print(f"⚠ SMTP send failed: {e}")
        return False


def _send(to: str | list[str], subject: str, html_body: str) -> bool:
    """Send an HTML email. Tries Resend first, falls back to SMTP."""
    recipients = [to] if isinstance(to, str) else to

    if RESEND_API_KEY:
        return _send_via_resend(recipients, subject, html_body)

    if GMAIL_EMAIL and GMAIL_APP_PASSWORD:
        return _send_via_smtp(recipients, subject, html_body)

    print("⚠ No email provider configured (set RESEND_API_KEY or GMAIL_EMAIL+GMAIL_APP_PASSWORD)")
    return False


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Send email-verification link to a newly registered user."""
    verify_url = f"{BASE_URL}/api/auth/verify-email?token={token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#e53e3e;">Svidhaus Arena</h2>
      <p>Hey <strong>{username}</strong>!</p>
      <p>Thanks for registering. Click the button below to verify your email and unlock full access.</p>
      <p style="text-align:center;margin:30px 0;">
        <a href="{verify_url}"
           style="background:#e53e3e;color:#fff;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:bold;display:inline-block;">
          Verify Email
        </a>
      </p>
      <p style="color:#666;font-size:0.9em;">
        This link expires in <strong>24 hours</strong>.<br>
        If you did not create an account, you can safely ignore this email.
      </p>
    </div>
    """
    return _send(to_email, "Verify your Svidhaus Arena email", html)


def send_admin_new_user_notification(admin_email: str, username: str, user_email: str) -> bool:
    """Notify admin that a user just verified their email."""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#e53e3e;">New verified user — Svidhaus Arena</h2>
      <p>A new user just verified their email address:</p>
      <ul>
        <li><strong>Username:</strong> {username}</li>
        <li><strong>Email:</strong> {user_email}</li>
      </ul>
      <p>Their role has been automatically upgraded to <em>user</em>.</p>
    </div>
    """
    return _send(admin_email, f"New verified user: {username}", html)


def send_wrestling_event_notification(recipients: list[str], event_title: str, event_description: str = "") -> bool:
    """Notify users about a new wrestling event."""
    wrestling_url = f"{BASE_URL}/wrestling"
    desc_html = f"<p>{event_description}</p>" if event_description else ""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#e53e3e;">&#129340; New Wrestling Event — Svidhaus Arena</h2>
      <h3>{event_title}</h3>
      {desc_html}
      <p>Head over to make your predictions before the event locks!</p>
      <p style="text-align:center;margin:30px 0;">
        <a href="{wrestling_url}"
           style="background:#e53e3e;color:#fff;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:bold;display:inline-block;">
          Submit My Predictions
        </a>
      </p>
    </div>
    """
    if not recipients:
        print("⚠ No recipients for wrestling event notification")
        return False
    return _send(recipients, f"New Event: {event_title} — Make Your Predictions!", html)
