import httpx

from app import config

RESEND_API_URL = "https://api.resend.com/emails"


async def send_otp_email(to_email: str, code: str, purpose: str) -> bool:
    """Send an OTP code via Resend. Returns True if actually sent.

    If RESEND_API_KEY isn't configured, or the send fails, this degrades
    gracefully -- it prints the code to the server log instead of raising,
    so local dev/demo works without a Resend account. The code is still
    valid and verifiable either way; only the delivery channel differs.
    """
    subject = {
        "login": "Your AyuSetu login code",
        "register": "Verify your AyuSetu account",
    }.get(purpose, "Your AyuSetu verification code")

    if not config.RESEND_API_KEY:
        print(f"⚠️  RESEND_API_KEY not set -- OTP for {to_email} ({purpose}): {code}")
        return False

    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>{subject}</h2>
      <p>Your one-time code is:</p>
      <p style="font-size: 32px; font-weight: bold; letter-spacing: 4px;">{code}</p>
      <p style="color: #666;">This code expires in 5 minutes. If you didn't request this, you can ignore this email.</p>
    </div>
    """

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
                json={
                    "from": config.RESEND_FROM_EMAIL,
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                },
            )
            resp.raise_for_status()
        print(f"✅ OTP email sent to {to_email} ({purpose})")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP email to {to_email}: {e} -- code was: {code}")
        return False
