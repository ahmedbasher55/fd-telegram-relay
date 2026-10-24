"""Telegram -> Claude (cloud) relay, run by GitHub Actions every few minutes.

1. Reads new Telegram messages for the owner's chat (getUpdates, short poll).
2. For each one, runs Claude Code (subscription token) inside a checkout of the private project repo.
3. Sends Claude's answer back to Telegram, appends both to control/tg_history.md, commits and pushes.

PRIVACY: this repo is public and so are its Action logs. Never print message text, answers or secrets.
If the PC bot is long-polling at the same time, Telegram returns 409 and we simply exit (the PC answers).
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOKEN = os.environ["TG_TOKEN"]
CHAT = int(os.environ["TG_CHAT_ID"])
WORK = Path(os.environ.get("WORK_DIR", "work"))
HISTORY = WORK / "control" / "tg_history.md"
SYSTEM = (
    "You are Claude running in the CLOUD (GitHub Actions) for Ahmed's 'First Dollar online ISA' project. He talks to "
    "you from Telegram while away from his PC. Read CLAUDE.md and 01_وصلنا_لفين.md for context; the recent Telegram "
    "conversation is in the <history> block. Act on his request directly and reply in short Egyptian Arabic suited to "
    "a phone screen. You CANNOT send from his Hotmail or LinkedIn here (that only runs on his PC); queue such work in "
    "the repo for the PC runner and say so. Commit nothing yourself: the relay commits and pushes your file changes "
    "to main after you finish. Follow every guardrail in CLAUDE.md.")


def tg(method, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=data)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error_code": e.code}


def send(text):
    for i in range(0, max(len(text), 1), 3900):
        tg("sendMessage", chat_id=CHAT, text=text[i:i + 3900] or "(empty)", disable_web_page_preview="true")


def poll():
    upd = tg("getUpdates", timeout=0)
    if not upd.get("ok"):
        print("telegram busy (PC bot is polling) or error:", upd.get("error_code"))
        return [], None
    msgs, last = [], None
    for u in upd.get("result", []):
        last = u["update_id"]
        m = u.get("message") or {}
        if (m.get("chat") or {}).get("id") == CHAT and (m.get("text") or "").strip():
            msgs.append(m["text"].strip())
    return msgs, last


def ask(text):
    hist = HISTORY.read_text(encoding="utf-8")[-6000:] if HISTORY.exists() else ""
    prompt = f"<history>\n{hist}\n</history>\n\nAhmed (Telegram): {text}"
    r = subprocess.run(["claude", "-p", prompt, "--output-format", "json", "--permission-mode", "bypassPermissions",
                        "--model", "sonnet", "--append-system-prompt", SYSTEM], cwd=WORK, capture_output=True, text=True, timeout=3000)
    try:
        return (json.loads(r.stdout).get("result") or "").strip() or "(مافيش رد)"
    except ValueError:
        return f"⚠️ Claude (cloud) error, exit {r.returncode}"


def main():
    msgs, last = poll()
    if last is None:
        Path("has_messages").write_text("0")
        return
    if not msgs:
        tg("getUpdates", offset=last + 1, timeout=0)  # confirm non-owner/empty updates
        Path("has_messages").write_text("0")
        return
    if sys.argv[1:] == ["--check"]:
        Path("has_messages").write_text("1")  # leave them unconfirmed for the answering step
        return
    print(f"{len(msgs)} message(s) to answer")
    for text in msgs:
        send("☁️ Claude (السحابة) شغال على طلبك…")
        answer = ask(text)
        send(answer)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as f:
            f.write(f"\n### {stamp}\n**Ahmed:** {text}\n\n**Claude (cloud):** {answer}\n")
    tg("getUpdates", offset=last + 1, timeout=0)  # mark as handled only after answering
    print("answered")


if __name__ == "__main__":
    main()
