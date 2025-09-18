# haneda_oct_alert.py
from playwright.sync_api import sync_playwright
from zoneinfo import ZoneInfo
import argparse, json, os, requests
from datetime import datetime

LOGIN_URL = "https://pk-reserve.haneda-airport.jp/airport/en/entrance/0000.jsf"

# --- Telegram ---
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8402262632:AAHLXhtlueDYepJd8LUEK6J4mSh1UF2MHxg")
CHAT_ID   = os.getenv("TG_CHAT_ID",  "8430243174")
TG_URL    = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram(text: str):
    r = requests.post(TG_URL, data={"chat_id": CHAT_ID, "text": text})
    print("Telegram status:", r.status_code, r.text)

# --- Helpers for scraping ---
def get_type_name(cal_div):
    img = cal_div.query_selector("table.calendar_btm img")
    if not img:
        return "Unknown"
    src = (img.get_attribute("src") or "").lower()
    if "public_month" in src:  return "Public"
    if "private_month" in src: return "Private"
    if "handicap_month" in src: return "Handicap"
    return "Unknown"

def get_open_days(cal_div):
    days = []
    # Available = td.empty or td.congestion (FULL/UNAVAILABLE are not)
    cells = cal_div.query_selector_all(
        "table.calendar_waku td.empty, table.calendar_waku td.congestion"
    )
    for td in cells:
        a = td.query_selector("a")
        if not a:
            continue
        txt = (a.inner_text() or "").strip()
        if txt.isdigit():
            days.append(int(txt))
    return sorted(set(days))

def within_allowed_window(tz_str="Asia/Tokyo"):
    now = datetime.now(ZoneInfo(tz_str))
    minutes = now.hour * 60 + now.minute
    # allowed: 06:30 <= time < 24:00
    return (minutes >= 6*60 + 30) and (minutes < 24*60)

def load_state(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_args():
    ap = argparse.ArgumentParser(description="Check Haneda October availability and alert via Telegram")
    ap.add_argument("--types", default="Public,Private",
                    help="Comma list of parking types to alert on (Public,Private,Handicap). Default: Public,Private")
    ap.add_argument("--days",  default="1,2,3",
                    help="Comma list of specific October days to watch, e.g. '1,2,3'. Default: 1,2,3")
    ap.add_argument("--state-file", default="alert_state_oct.json",
                    help="Path to file for deduping alerts. Default: alert_state_oct.json")
    ap.add_argument("--tz", default="Asia/Tokyo", help="Timezone for quiet hours. Default: Asia/Tokyo")
    ap.add_argument("--force-send", action="store_true",
                    help="Send alerts regardless of time window (ignore quiet hours).")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    target_types = {t.strip() for t in args.types.split(",") if t.strip()}
    target_days  = {int(x.strip()) for x in args.days.split(",") if x.strip().isdigit()}

    if not args.force_send and not within_allowed_window(args.tz):
        print("⏰ Outside send window (06:30–24:00). Skipping Telegram send.")
        send_ok = False
    else:
        send_ok = True

    state = load_state(args.state_file)  # { "Public":[1,3], "Private":[1,2,3] ... }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # --- Login ---
        page.goto(LOGIN_URL)
        page.click("img[alt='login']")
        page.wait_for_selector("form#form1", timeout=20000)
        page.select_option('select[name="form1:_idJsp66"]', "61")   # 品川
        page.fill('input[name="form1:Vehicle_type_code"]', "331")
        page.select_option('select[name="form1:_idJsp68"]', "21")   # ね
        page.fill('input[name="form1:Specified_number"]', "9300")
        page.fill('input[name="form1:パスワード"]', "Chessmama16")
        page.click('#form1\\:loginbutton img[alt="ログイン"]')
        page.wait_for_selector("#welcomarea", timeout=20000)

        # --- Go to reservations ---
        if page.query_selector("#sidebar\\:_idJsp0\\:_idJsp18"):
            with page.expect_navigation():
                page.click("#sidebar\\:_idJsp0\\:_idJsp18")
        else:
            with page.expect_navigation():
                page.click("img[alt='予約']")
        page.wait_for_selector("table.calendar_waku", timeout=20000)

        # --- Find the 3 calendar blocks (2 x calendar01, 1 x calendar02) ---
        cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
        if not cal_divs:
            print("⚠️ No calendar blocks found.")
            browser.close()
            exit(1)

        results = {}
        # Advance EACH calendar block to October individually via its right arrow
        for idx in range(len(cal_divs)):
            cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
            cal = cal_divs[idx]
            # Click this block's right arrow
            next_btn = cal.query_selector("img[src*='arrow_r.gif']")
            if next_btn:
                with page.expect_navigation():
                    next_btn.click()
                page.wait_for_selector("table.calendar_waku", timeout=20000)
                # Re-grab the same index after reload
                cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
                cal = cal_divs[idx]

            tname = get_type_name(cal)
            open_days = get_open_days(cal)
            results[tname] = open_days

        # --- Report + filter to target types/days ---
        for t in ["Public", "Private", "Handicap"]:
            if t in results:
                print(f"{t} October open days:", results[t])

        matches = {}
        for t, days in results.items():
            if t in target_types:
                hit = sorted(set(days) & target_days)
                if hit:
                    matches[t] = hit

        # --- Deduplicate: send only new matches since last time ---
        newly_found_lines = []
        for t, hit in matches.items():
            prev = set(state.get(t, []))
            new  = sorted(set(hit) - prev)
            if new:
                newly_found_lines.append(f"{t}: {new}")
            # update state to remember we've seen these hits
            state[t] = sorted(prev | set(hit))

        if newly_found_lines:
            msg = "🚨 Haneda Parking Alert (October)\n" + "\n".join(newly_found_lines)
            if send_ok:
                send_telegram(msg)
            else:
                print("🔕 In quiet hours; not sending Telegram. Would have sent:\n" + msg)
            save_state(args.state_file, state)
        else:
            print("No NEW target-day openings to alert.")

        browser.close()
