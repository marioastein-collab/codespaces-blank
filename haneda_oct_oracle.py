import time
import sys
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
import requests

# === Telegram Bot Config ===
BOT_TOKEN = "8402262632:AAHLXhtlueDYepJd8LUEK6J4mSh1UF2MHxg"
CHAT_ID = "8430243174"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram(msg: str):
    payload = {"chat_id": CHAT_ID, "text": msg}
    r = requests.post(TELEGRAM_URL, data=payload)
    print(f"Telegram status: {r.status_code} {r.text}")

def get_type_name(cal_div):
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
    LOGIN_URL = "https://pk-reserve.haneda-airport.jp/airport/en/entrance/0000.jsf"
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Login
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

        # Go to reservations
        if page.query_selector("#sidebar\\:_idJsp0\\:_idJsp18"):
            with page.expect_navigation():
                page.click("#sidebar\\:_idJsp0\\:_idJsp18")
        else:
            with page.expect_navigation():
                page.click("img[alt='予約']")

        page.wait_for_selector("table.calendar_waku", timeout=20000)

        # Go to October
        cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
        for idx in range(len(cal_divs)):
            cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
            cal = cal_divs[idx]

            next_btn = cal.query_selector("img[src*='arrow_r.gif']")
            if next_btn:
                with page.expect_navigation():
                    next_btn.click()
                page.wait_for_selector("table.calendar_waku", timeout=20000)
                cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
                cal = cal_divs[idx]

            tname = get_type_name(cal)
            open_days = get_open_days(cal)
            results[tname] = open_days

        browser.close()
    return results

# === Target setup ===
TARGET_DATES = {16, 17, 18, 19}
TARGET_TYPES = {"Public"}

print(f"✅ Watching for {TARGET_TYPES} on dates {TARGET_DATES}")

# === Timer ===
start_time = datetime.now()
end_time = start_time + timedelta(hours=24)

while datetime.now() < end_time:
    results = check_availability()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ttype in results:
        print(f"[{timestamp}] 🔎 {ttype} October open days: {results[ttype]}")

    for ttype in TARGET_TYPES:
        if ttype in results:
            hit = TARGET_DATES.intersection(results[ttype])
            if hit:
                msg = f"🚨 Haneda Parking Alert!\n{ttype}: {sorted(hit)} available in October!"
                print(msg)
                send_telegram(msg)
                sys.exit(0)

    time.sleep(30)

print("⏹️ 24 hours passed, stopping script.")
