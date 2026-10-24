"""Daily digest to Telegram (runs in GitHub Actions, PC can be off):
- today's outreach numbers from the project repo logs
- new PART-TIME / contract remote IT jobs from public job APIs (Remotive, RemoteOK), never repeated
Public logs: prints only counts, never content.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOKEN, CHAT = os.environ["TG_TOKEN"], int(os.environ["TG_CHAT_ID"])
WORK = Path(os.environ.get("WORK_DIR", "work"))
SEEN = WORK / "jobs" / "alerts_seen.txt"
CAIRO = timezone(timedelta(hours=3))
UA = {"User-Agent": "Mozilla/5.0 (personal job alerts)"}
ROLE = re.compile(r"support|help ?desk|service desk|it\b|technical|implementation|onboarding|crm|salesforce|qa|"
                  r"automation|accessibility|wcag|data entry|virtual assistant|operations", re.I)
SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|head|director|manager|vp)\b", re.I)
OPEN = re.compile(r"worldwide|anywhere|global|emea|europe|africa|middle east|mena|egypt|international", re.I)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def send(text):
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": text[:3900], "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=40)


def count(rel, day, needle=""):
    p = WORK / rel
    if not p.exists():
        return 0
    return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.startswith(day) and needle in l)


def jobs():
    found = []
    try:
        for j in get("https://remotive.com/api/remote-jobs?limit=300")["jobs"]:
            if j.get("job_type") in ("part_time", "contract", "freelance"):
                found.append((j["url"], j["title"], j["company_name"], j.get("candidate_required_location", ""),
                              j.get("job_type")))
    except Exception:
        pass
    try:
        for j in get("https://remoteok.com/api")[1:]:
            tags = " ".join(j.get("tags", [])).lower()
            if "part time" in tags or "part-time" in tags or "contract" in tags:
                found.append((j.get("url", ""), j.get("position", ""), j.get("company", ""),
                              j.get("location", "") or "Worldwide", "part-time/contract"))
    except Exception:
        pass
    seen = set(SEEN.read_text(encoding="utf-8").splitlines()) if SEEN.exists() else set()
    new = [f for f in found if f[0] and f[0] not in seen and ROLE.search(f[1]) and not SENIOR.search(f[1])
           and (not f[3] or OPEN.search(f[3]))]
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    with SEEN.open("a", encoding="utf-8") as fh:
        for f in new:
            fh.write(f[0] + "\n")
    return new[:8]


def main():
    day = datetime.now(CAIRO).date().isoformat()
    lines = [f"🌙 ملخص اليوم {day}",
             f"✉️ إيميلات فرنسا: {count('automation/sent_log.csv', day, 'marque blanche')}",
             f"✉️ إيميلات إنجليزي: {count('automation/sent_log.csv', day, 'White-label')}",
             f"🤝 طلبات LinkedIn: {count('automation/li_log.csv', day)}",
             f"💬 رسايل متابعة: {count('automation/li_messages_log.csv', day)}",
             f"💼 تقديمات وظايف: {count('jobs/applications.csv', day)}",
             "(الأرقام دي من آخر مزامنة للكمبيوتر)"]
    new = jobs()
    if new:
        lines += ["", f"🔎 وظايف Part-time / Contract جديدة ({len(new)}):"]
        lines += [f"• {t} – {c} ({k})\n{u}" for u, t, c, _, k in new]
    else:
        lines += ["", "🔎 مافيش وظايف Part-time جديدة مناسبة النهارده."]
    send("\n".join(lines))
    print(f"digest sent, {len(new)} new jobs")


if __name__ == "__main__":
    main()
