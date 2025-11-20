# haneda_parking_watcher.py
from playwright.sync_api import sync_playwright
import requests
import time
from datetime import datetime

# === Telegram Bot Config ===
BOT_TOKEN = "8402262632:AAHLXhtlueDYepJd8LUEK6J4mSh1UF2MHxg"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Multiple chat IDs (your two accounts)
CHAT_IDS = [
    "8430243174",   # Your first account
    "8543641889",   # Your new phone's Telegram
]


def send_telegram(msg: str):
    """Send Telegram message to all configured chat IDs."""
    for chat_id in CHAT_IDS:
        payload = {"chat_id": chat_id, "text": msg}
        r = requests.post(TELEGRAM_URL, data=payload)
        if r.status_code == 200:
            print(f"📩 Sent Telegram message to {chat_id}")
        else:
            print(f"⚠️ Failed to send Telegram message to {chat_id}: {r.text}")


def get_type_name(cal_div):
    """Determine if the calendar is Public or Private."""
    img = cal_div.query_selector("table.calendar_btm img")
    if not img:
        return "Unknown"
    src = (img.get_attribute("src") or "").lower()
    if "public_month" in src:
        return "Public"
    if "private_month" in src:
        return "Private"
    return "Unknown"


def get_open_days(cal_div):
    """Collect available days (empty or congestion)."""
    days = []
    cells = cal_div.query_selector_all(
        "table.calendar_waku td.empty, table.calendar_waku td.congestion"
    )
    for td in cells:
        a = td.query_selector("a")
        if a:
            txt = (a.inner_text() or "").strip()
            if txt.isdigit():
                days.append(int(txt))
    return sorted(set(days))


def check_availability():
    """Logs into Haneda and returns availability for Public and Private only."""
    LOGIN_URL = "https://pk-reserve.haneda-airport.jp/airport/en/entrance/0000.jsf"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # --- Login ---
        page.goto(LOGIN_URL)
        page.click("img[alt='login']")
        page.wait_for_selector("form#form1", timeout=20000)

        page.select_option('select[name="form1:_idJsp66"]', "61")     # 品川
        page.fill('input[name="form1:Vehicle_type_code"]', "331")
        page.select_option('select[name="form1:_idJsp68"]', "21")     # ね
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

        # --- Go to December ---
        results = {}
        cal_divs = page.query_selector_all("div#calendar01, div#calendar02")

        for idx in range(len(cal_divs)):
            cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
            cal = cal_divs[idx]

            # Move 1 month forward (Nov → Dec)
            next_btn = cal.query_selector("img[src*='arrow_r.gif']")
            if next_btn:
                with page.expect_navigation():
                    next_btn.click()
                page.wait_for_selector("table.calendar_waku", timeout=20000)
                cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
                cal = cal_divs[idx]

            tname = get_type_name(cal)
            open_days = get_open_days(cal)

            # Save only Public and Private
            if tname in ("Public", "Private"):
                results[tname] = open_days

            # Save screenshot
            #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            #fname = f"december_{tname.lower()}_{timestamp}.png"
            #page.screenshot(path=fname)
            #print(f"📸 Screenshot saved: {fname}")

        browser.close()
        return results


def run_once():
    """Run one availability check + Telegram notification."""
    print(f"\n=== Checking Haneda availability at {datetime.now()} ===")

    try:
        results = check_availability()
    except Exception as e:
        err = f"⚠️ Haneda script error: {e}"
        print(err)
        send_telegram(err)
        return

    # Print local output
    for ttype, days in results.items():
        print(f"{ttype} December open days: {days}")

    # Notify if availability found
    msgs = []
    for ttype, days in results.items():
        if days:
            msgs.append(f"{ttype}: {', '.join(str(d) for d in days)}")

    if msgs:
        full_msg = "🚗 Haneda Parking – December availability detected!\n" + "\n".join(msgs)
        send_telegram(full_msg)
        print("📩 Telegram notification sent.")
    else:
        print("❌ No available dates found.")


if __name__ == "__main__":
    print("🚀 Haneda Parking Watcher started — checking every 5 minutes.\nPress CTRL+C to stop.\n")
    while True:
        run_once()
        print("⏱ Waiting 30 seconds...\n")
        time.sleep(30) #adjusted to 30 sec - change to 300 for 5 min
