# haneda_oct_oracle.py
from playwright.sync_api import sync_playwright
import requests
import time
import sys

# === Telegram Bot Config ===
BOT_TOKEN = "8402262632:AAHLXhtlueDYepJd8LUEK6J4mSh1UF2MHxg"
CHAT_ID = "8430243174"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram(msg: str):
    payload = {"chat_id": CHAT_ID, "text": msg}
    r = requests.post(TELEGRAM_URL, data=payload)
    if r.status_code == 200:
        print("📩 Sent Telegram message")
    else:
        print(f"⚠️ Telegram failed: {r.text}")

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

        # --- Go to October ---
        cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
        results = {}
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

# === Prompt user for targets ===
print("Enter the target dates for October (comma-separated, e.g. 1,2,3):")
dates_input = input("Target dates: ").strip()
TARGET_DATES = set(int(x) for x in dates_input.split(",") if x.strip().isdigit())

print("Do you want Public, Private, or Both?")
lot_choice = input("Type choice: ").strip().lower()
if lot_choice == "public":
    TARGET_TYPES = {"Public"}
elif lot_choice == "private":
    TARGET_TYPES = {"Private"}
else:
    TARGET_TYPES = {"Public", "Private"}

print(f"✅ Watching for {TARGET_TYPES} dates: {TARGET_DATES}")

# === Loop until target found ===
while True:
    results = check_availability()

    for ttype in results:
        # Always print what’s found
        print(f"🔎 {ttype} October open days: {results[ttype]}")

    # Only alert if target lot(s) and date(s) intersect
    for ttype in TARGET_TYPES:
        if ttype in results:
            hit = TARGET_DATES.intersection(results[ttype])
            if hit:
                msg = f"🚨 Haneda Parking Alert!\n{ttype}: {sorted(hit)} available in October!"
                print(msg)
                send_telegram(msg)
                sys.exit(0)

    # Sleep 30s before trying again
    time.sleep(30)
