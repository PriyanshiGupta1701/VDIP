"""Quick SMTP check using the settings in backend/.env. Run: python test_smtp.py
Prints progress only; it never prints your password or encoded credentials."""
import os, smtplib
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("EMAIL_SMTP_SERVER", "")
port = int(os.getenv("EMAIL_SMTP_PORT", 587))
user = os.getenv("EMAIL_SENDER", "")
pwd = os.getenv("EMAIL_PASSWORD", "")
print(f"Server: {host}:{port} | Sender: {user} | Password length: {len(pwd)}")

try:
    server = smtplib.SMTP_SSL(host, port, timeout=30) if port == 465 else smtplib.SMTP(host, port, timeout=30)
    print("1. Connected to server")
    if port != 465:
        server.starttls()
        print("2. TLS started")
    server.login(user, pwd)
    print("3. ✅ Login OK - SMTP settings are working")
    server.quit()
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Login rejected ({e.smtp_code}): {e.smtp_error.decode(errors='ignore')[:200]}")
except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")