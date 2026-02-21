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

RESEND_API_KEY     = os.getenv("RESEND_API_KEY", "")
GMAIL_SMTP_SERVER  = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
GMAIL_SMTP_PORT    = int(os.getenv("GMAIL_SMTP_PORT", "587"))
GMAIL_EMAIL        = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", GMAIL_EMAIL or "svidron.robert@gmail.com")
FROM_EMAIL  = os.getenv("FROM_EMAIL", GMAIL_EMAIL or "noreply@svidnet.com")
FROM_NAME   = "Svidhaus Arena"

BASE_URL = os.getenv("BASE_URL", "https://svidhaus.up.railway.app")

# ── Shared email wrapper ───────────────────────────────────────────────────────

_BASE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f1a;padding:40px 16px;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

      <!-- Header -->
      <tr>
        <td style="background:linear-gradient(135deg,#1a0a0a 0%,#2d1515 100%);
                   border-radius:16px 16px 0 0;padding:36px 40px;text-align:center;
                   border-bottom:3px solid #e53e3e;">
          <div style="font-size:28px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
            <span style="color:#e53e3e;">SVID</span>HAUS
          </div>
          <div style="color:#999;font-size:12px;letter-spacing:3px;margin-top:4px;text-transform:uppercase;">
            Arena
          </div>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="background:#1a1a2e;padding:40px;">
          {body}
        </td>
      </tr>

      <!-- Feature cards -->
      <tr>
        <td style="background:#16162a;padding:28px 40px;">
          <p style="color:#888;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 16px;">
            Explore Svidhaus Arena
          </p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="33%" style="padding:0 4px 0 0;">
                <a href="{base_url}/trivia" style="text-decoration:none;display:block;
                   background:#1e1e35;border:1px solid #2a2a45;border-radius:10px;
                   padding:16px 12px;text-align:center;">
                  <div style="font-size:22px;margin-bottom:6px;">🧠</div>
                  <div style="color:#fff;font-size:12px;font-weight:600;">Trivia</div>
                  <div style="color:#666;font-size:10px;margin-top:2px;">Test your knowledge</div>
                </a>
              </td>
              <td width="33%" style="padding:0 2px;">
                <a href="{base_url}/wrestling" style="text-decoration:none;display:block;
                   background:#1e1e35;border:1px solid #2a2a45;border-radius:10px;
                   padding:16px 12px;text-align:center;">
                  <div style="font-size:22px;margin-bottom:6px;">&#129340;</div>
                  <div style="color:#fff;font-size:12px;font-weight:600;">Wrestling</div>
                  <div style="color:#666;font-size:10px;margin-top:2px;">Make predictions</div>
                </a>
              </td>
              <td width="33%" style="padding:0 0 0 4px;">
                <a href="{base_url}/wordle" style="text-decoration:none;display:block;
                   background:#1e1e35;border:1px solid #2a2a45;border-radius:10px;
                   padding:16px 12px;text-align:center;">
                  <div style="font-size:22px;margin-bottom:6px;">🟩</div>
                  <div style="color:#fff;font-size:12px;font-weight:600;">Wordle</div>
                  <div style="color:#666;font-size:10px;margin-top:2px;">Daily word game</div>
                </a>
              </td>
            </tr>
            <tr><td colspan="3" style="height:8px;"></td></tr>
            <tr>
              <td width="33%" style="padding:0 4px 0 0;">
                <a href="{base_url}/sportsbook" style="text-decoration:none;display:block;
                   background:#1e1e35;border:1px solid #2a2a45;border-radius:10px;
                   padding:16px 12px;text-align:center;">
                  <div style="font-size:22px;margin-bottom:6px;">🏆</div>
                  <div style="color:#fff;font-size:12px;font-weight:600;">Sportsbook</div>
                  <div style="color:#666;font-size:10px;margin-top:2px;">Place your bets</div>
                </a>
              </td>
              <td width="33%" style="padding:0 2px;">
                <a href="{base_url}/movies" style="text-decoration:none;display:block;
                   background:#1e1e35;border:1px solid #2a2a45;border-radius:10px;
                   padding:16px 12px;text-align:center;">
                  <div style="font-size:22px;margin-bottom:6px;">🎬</div>
                  <div style="color:#fff;font-size:12px;font-weight:600;">Movies</div>
                  <div style="color:#666;font-size:10px;margin-top:2px;">Rate &amp; review</div>
                </a>
              </td>
              <td width="33%" style="padding:0 0 0 4px;">
                <a href="{base_url}/links" style="text-decoration:none;display:block;
                   background:#1e1e35;border:1px solid #2a2a45;border-radius:10px;
                   padding:16px 12px;text-align:center;">
                  <div style="font-size:22px;margin-bottom:6px;">🔗</div>
                  <div style="color:#fff;font-size:12px;font-weight:600;">Links</div>
                  <div style="color:#666;font-size:10px;margin-top:2px;">Community hub</div>
                </a>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="background:#111120;border-radius:0 0 16px 16px;padding:24px 40px;text-align:center;
                   border-top:1px solid #1e1e35;">
          <p style="color:#444;font-size:11px;margin:0 0 8px;">
            You're receiving this because you have an account at
            <a href="{base_url}" style="color:#e53e3e;text-decoration:none;">Svidhaus Arena</a>.
          </p>
          <p style="color:#333;font-size:10px;margin:0;">
            &copy; 2025 Svidhaus Arena &nbsp;&middot;&nbsp; svidnet.com
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""


def _wrap(subject: str, body_html: str) -> str:
    """Wrap body content in the shared email shell."""
    return _BASE_HTML.format(subject=subject, body=body_html, base_url=BASE_URL)


# ── Transport ──────────────────────────────────────────────────────────────────

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


# ── Email templates ────────────────────────────────────────────────────────────

def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Send email-verification link to a newly registered user."""
    verify_url = f"{BASE_URL}/api/auth/verify-email?token={token}"
    subject = "Verify your Svidhaus Arena email"
    body = f"""\
      <h2 style="color:#ffffff;font-size:22px;font-weight:700;margin:0 0 8px;">
        Welcome, {username}! &#127881;
      </h2>
      <p style="color:#aaa;font-size:15px;line-height:1.6;margin:0 0 28px;">
        You're one step away from full access to Svidhaus Arena.
        Click the button below to verify your email address.
      </p>

      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
        <tr>
          <td align="center">
            <a href="{verify_url}"
               style="display:inline-block;background:#e53e3e;color:#ffffff;
                      font-size:15px;font-weight:700;padding:14px 36px;
                      border-radius:8px;text-decoration:none;letter-spacing:0.3px;">
              &#10003;&nbsp; Verify My Email
            </a>
          </td>
        </tr>
      </table>

      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#111120;border:1px solid #1e1e35;border-radius:10px;
                    padding:16px 20px;margin-bottom:24px;">
        <tr>
          <td style="color:#666;font-size:11px;text-transform:uppercase;
                     letter-spacing:1.5px;padding-bottom:8px;">
            What you unlock
          </td>
        </tr>
        <tr>
          <td>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:#ccc;font-size:13px;padding:4px 0;">
                  &#129518;&nbsp; <strong style="color:#fff;">Wrestling Predictions</strong>
                  &nbsp;—&nbsp; Pick winners before every event
                </td>
              </tr>
              <tr>
                <td style="color:#ccc;font-size:13px;padding:4px 0;">
                  &#129504;&nbsp; <strong style="color:#fff;">Trivia Battles</strong>
                  &nbsp;—&nbsp; Compete on the leaderboard
                </td>
              </tr>
              <tr>
                <td style="color:#ccc;font-size:13px;padding:4px 0;">
                  &#127361;&nbsp; <strong style="color:#fff;">Daily Wordle</strong>
                  &nbsp;—&nbsp; Streak tracking &amp; stats
                </td>
              </tr>
              <tr>
                <td style="color:#ccc;font-size:13px;padding:4px 0;">
                  &#127942;&nbsp; <strong style="color:#fff;">Sportsbook</strong>
                  &nbsp;—&nbsp; Place bets &amp; climb the board
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>

      <p style="color:#555;font-size:12px;line-height:1.6;margin:0;">
        This link expires in <strong style="color:#777;">24 hours</strong>.
        If you didn't create this account, you can safely ignore this email.
      </p>
    """
    return _send(to_email, subject, _wrap(subject, body))


def send_admin_new_user_notification(admin_email: str, username: str, user_email: str) -> bool:
    """Notify admin that a user just verified their email."""
    subject = f"New verified user: {username}"
    body = f"""\
      <h2 style="color:#ffffff;font-size:20px;font-weight:700;margin:0 0 20px;">
        &#128075; New verified user
      </h2>

      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#111120;border:1px solid #1e1e35;border-radius:10px;
                    margin-bottom:24px;">
        <tr>
          <td style="padding:20px;">
            <table width="100%" cellpadding="0" cellspacing="4">
              <tr>
                <td style="color:#666;font-size:12px;width:100px;padding:6px 0;">Username</td>
                <td style="color:#fff;font-size:14px;font-weight:600;padding:6px 0;">
                  {username}
                </td>
              </tr>
              <tr>
                <td style="color:#666;font-size:12px;padding:6px 0;">Email</td>
                <td style="color:#fff;font-size:14px;padding:6px 0;">{user_email}</td>
              </tr>
              <tr>
                <td style="color:#666;font-size:12px;padding:6px 0;">Role</td>
                <td style="padding:6px 0;">
                  <span style="background:rgba(34,197,94,0.15);color:#22c55e;
                               font-size:11px;font-weight:700;padding:3px 10px;
                               border-radius:20px;letter-spacing:0.5px;">
                    USER
                  </span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>

      <p style="color:#666;font-size:13px;margin:0;">
        Their account has been automatically upgraded from
        <span style="color:#888;">basic</span> to
        <strong style="color:#22c55e;">user</strong>.
        You can manage roles from the
        <a href="{BASE_URL}/admin" style="color:#e53e3e;text-decoration:none;">
          admin panel
        </a>.
      </p>
    """
    return _send(admin_email, subject, _wrap(subject, body))


def send_wrestling_event_notification(recipients: list[str], event_title: str, event_description: str = "") -> bool:
    """Notify users about a new wrestling event."""
    if not recipients:
        print("⚠ No recipients for wrestling event notification")
        return False

    wrestling_url = f"{BASE_URL}/wrestling"
    subject = f"New Event: {event_title} — Make Your Predictions!"
    desc_block = (
        f'<p style="color:#aaa;font-size:14px;line-height:1.6;margin:0 0 24px;">'
        f'{event_description}</p>'
    ) if event_description else ""

    body = f"""\
      <div style="text-align:center;margin-bottom:28px;">
        <div style="display:inline-block;background:rgba(229,62,62,0.1);
                    border:1px solid rgba(229,62,62,0.3);border-radius:8px;
                    padding:6px 16px;margin-bottom:16px;">
          <span style="color:#e53e3e;font-size:11px;font-weight:700;
                       letter-spacing:2px;text-transform:uppercase;">
            &#129340;&nbsp; New Event Live
          </span>
        </div>
        <h2 style="color:#ffffff;font-size:24px;font-weight:800;margin:0 0 12px;
                   line-height:1.2;">
          {event_title}
        </h2>
        {desc_block}
        <a href="{wrestling_url}"
           style="display:inline-block;background:#e53e3e;color:#ffffff;
                  font-size:15px;font-weight:700;padding:14px 40px;
                  border-radius:8px;text-decoration:none;letter-spacing:0.3px;">
          &#127919;&nbsp; Submit My Predictions
        </a>
      </div>

      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#111120;border:1px solid #1e1e35;
                    border-radius:10px;margin-bottom:8px;">
        <tr>
          <td style="padding:16px 20px;border-bottom:1px solid #1e1e35;">
            <span style="color:#666;font-size:11px;text-transform:uppercase;
                         letter-spacing:1.5px;">How it works</span>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 20px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:#ccc;font-size:13px;padding:5px 0;">
                  <span style="color:#e53e3e;font-weight:700;">1.</span>
                  &nbsp;Head to the Wrestling page and open this event
                </td>
              </tr>
              <tr>
                <td style="color:#ccc;font-size:13px;padding:5px 0;">
                  <span style="color:#e53e3e;font-weight:700;">2.</span>
                  &nbsp;Submit your predictions before it locks
                </td>
              </tr>
              <tr>
                <td style="color:#ccc;font-size:13px;padding:5px 0;">
                  <span style="color:#e53e3e;font-weight:700;">3.</span>
                  &nbsp;After the event, results are graded automatically
                </td>
              </tr>
              <tr>
                <td style="color:#ccc;font-size:13px;padding:5px 0;">
                  <span style="color:#e53e3e;font-weight:700;">4.</span>
                  &nbsp;Climb the leaderboard &amp; trash-talk in the comments
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    """
    return _send(recipients, subject, _wrap(subject, body))
