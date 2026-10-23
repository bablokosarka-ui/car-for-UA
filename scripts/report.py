"""Щоденний звіт кампанії в Telegram. Запуск: python report.py"""
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_config, load_env, read_tracker, tg_send


def main():
    load_env()
    token = os.environ.get("TG_BOT_TOKEN", "")
    chats = [c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()]
    if not token or not chats:
        print("Немає TG_BOT_TOKEN або TG_CHAT_ID у змінних середовища")
        sys.exit(1)

    cfg = load_config()
    rows = read_tracker()
    today = date.today().isoformat()

    sent = [r for r in rows if r["date_sent"].strip()]
    last24 = [r for r in sent if r["date_sent"] == today]
    answered = [r for r in rows if r["response_date"].strip()]
    follows = [r for r in rows if r["followup_due"].strip() and r["followup_due"] <= today
               and r["date_sent"].strip() and not r["response_date"].strip()]

    lines = [
        f"📋 <b>Звіт кампанії «4-та машина»</b> — {today}",
        f"📤 Відправлено листів: <b>{len(sent)}</b> (сьогодні: {len(last24)})",
        f"📥 Відповідей: <b>{len(answered)}</b>",
        f"💰 Зібрано: <b>{cfg.get('raised_ua', 0)}</b> з {cfg.get('target_ua', 0)} грн",
    ]
    if follows:
        fl = "\n".join(f"  • {r['station_name']} ({r['country']})" for r in follows[:5])
        more = f"\n  … і ще {len(follows) - 5}" if len(follows) > 5 else ""
        lines.append(f"⏰ Фолоу-апи:\n{fl}{more}")
    if not sent:
        lines.append("ℹ️ Трекер порожній — додайте станції у radio-tracker.csv")

    text = "\n".join(lines)
    for chat in chats:
        tg_send(token, chat, text)
        print(f"Звіт -> {chat}")


if __name__ == "__main__":
    main()
