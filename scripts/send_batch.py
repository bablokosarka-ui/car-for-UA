"""Персоналізує і відправляє порцію листів, оновлює трекер.

Приклади:
  python send_batch.py                  # звичайний запуск (DAILY_LIMIT листів, за замовч. 10)
  python send_batch.py --limit 3        # відправити 3
  python send_batch.py --dry-run        # показати, що буде відправлено, нічого не слати
  python send_batch.py --test my@mail   # надіслати ПЕРШИЙ лист зі списку собі на перевірку
"""
import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_config, load_env, read_tracker, write_tracker, brevo_send


def pick_template(lang):
    p = ROOT / "letters" / f"radio_{lang.strip().lower()}.txt"
    if p.exists():
        return p
    return ROOT / "letters" / "media_en.txt"


def build_letter(row, cfg):
    tpl = pick_template(row.get("language", ""))
    text = tpl.read_text(encoding="utf-8")
    subject, _, body = text.partition("\n\n")
    subject = subject.replace("SUBJECT:", "").strip()
    repl = {
        "{{station}}": row.get("station_name") or "your team",
        "{{city}}": row.get("city") or "your city",
        "{{country}}": row.get("country") or "your country",
        "{{jar}}": cfg["jar_url"],
        "{{contact_email}}": os.environ.get("SENDER_EMAIL", ""),
        "{{signature}}": cfg["signature"],
    }
    for k, v in repl.items():
        body = body.replace(k, v)
    subject = subject.replace("{{station}}", repl["{{station}}"])
    return subject, body


def pending(rows):
    for r in rows:
        if (r["contact_email"].strip() and not r["date_sent"].strip()
                and "no" not in r["response"].lower()):
            yield r


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=int(os.environ.get("DAILY_LIMIT", "10")))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", metavar="EMAIL")
    args = ap.parse_args()

    cfg = load_config()
    rows = read_tracker()
    queue = list(pending(rows))

    if args.test:
        if not queue:
            print("Немає заповнених станцій у трекері — додайте рядок у radio-tracker.csv")
            return
        subject, body = build_letter(queue[0], cfg)
        status = brevo_send(os.environ["BREVO_API_KEY"], os.environ["SENDER_EMAIL"],
                            os.environ["SENDER_NAME"], args.test, "[TEST] " + subject, body)
        print(f"Тест-лист надіслано на {args.test}, статус {status}")
        return

    sent, failed = [], []
    for row in queue[: args.limit]:
        subject, body = build_letter(row, cfg)
        if args.dry_run:
            print(f"[DRY] -> {row['contact_email']} | {subject}")
            continue
        try:
            brevo_send(os.environ["BREVO_API_KEY"], os.environ["SENDER_EMAIL"],
                       os.environ["SENDER_NAME"], row["contact_email"], subject, body)
            row["date_sent"] = date.today().isoformat()
            row["followup_due"] = (date.today() + timedelta(days=4)).isoformat()
            row["letter_template_sent"] = pick_template(row.get("language", "")).stem
            sent.append(row)
            print(f"OK -> {row['contact_email']}")
        except Exception as e:  # noqa: BLE001 — логуємо і продовжуємо порцію
            failed.append((row["contact_email"], str(e)))
            print(f"FAIL -> {row['contact_email']}: {e}")

    if not args.dry_run:
        write_tracker(rows)
    print(f"Підсумок: надіслано {len(sent)}, помилок {len(failed)}")
    if failed and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
