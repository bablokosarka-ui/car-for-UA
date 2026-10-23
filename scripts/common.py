"""Спільні утиліти агент-конвеєра збору. Тільки стандартна бібліотека Python."""
import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "radio-tracker.csv"
FIELDS = ["date_added", "country", "city", "station_name", "genre", "contact_email",
          "contact_form_url", "language", "letter_template_sent", "date_sent",
          "followup_due", "response", "response_date", "notes"]


def load_env():
    """Підтягує .env з кореня репо (для локальних запусків). В Actions не потрібен."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        return json.load(f)


def read_tracker():
    with open(TRACKER, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in FIELDS:
            r.setdefault(k, "")
    return rows


def write_tracker(rows):
    with open(TRACKER, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def brevo_send(api_key, sender_email, sender_name, to_email, subject, body_text):
    payload = json.dumps({
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body_text,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email", data=payload, method="POST",
        headers={"api-key": api_key, "content-type": "application/json",
                 "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def tg_send(token, chat, text):
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "parse_mode": "HTML",
        "disable_web_page_preview": "true"}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status
