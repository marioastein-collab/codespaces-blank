# haneda_oct_alert.py
from playwright.sync_api import sync_playwright
import requests
import re

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
        print(f"⚠️ Failed to send Telegram message: {r.text}")

# === Haneda Reservation Scraper ===
LOGIN_URL = "https://pk-reserve.haneda-airport.jp/airport/en/entrance/0000.jsf"
TARGET_DAYS = {16, 17, 18, 19}   # Days you want to be notified about
TARGET_MONTH = 10         # October

# --- Helpers ---
def get_type_name(cal_div):
    img = cal_div.query_selector("table.calendar_btm img")
    if not img:
        return "Unknown"
    src = (img.get_attribute("src") or "").lower()
    if "public_month" in src:  return "Public"
    if "private_month" in src: return "Private"
    if "handicap_month" in src:return "Handicap"
    return "Unknown"

def find_calendar(page, wanted_type):
    for cal in page.query_selector_all("div#calendar01, div#calendar02"):
        if get_type_name(cal) == wanted_type:
            return cal
    return None

def read_month_number(cal_div, wanted_type):
    header_cls = {"Public":"publ", "Private":"priv", "Handicap":"hand"}[wanted_type]
    td = cal_div.query_selector(f"table.calendar_btm td.{header_cls}")
    if not td:
        return None
    txt = (td.inner_text() or "").strip()
    m = re.search(r"\b(\d{1,2})\b", txt)
    return int(m.group(1)) if m else None

def goto_month(page, wanted_type, target_month=10, max_clicks=3):
    for _ in range(max_clicks):
        cal = find_calendar(page, wanted_type)
        if not cal:
            raise RuntimeError(f"{wanted_type} calendar not found")
        current = read_month_number(cal, wanted_type)
        if current == target_month:
            return
        arrow = cal.query_selector("a img[src*='arrow_r.gif']")
        if not arrow:
            break
        arrow.click()
        page.wait_for_load_state("networkidle")
    cal = find_calendar(page, wanted_type)
    if read_month_number(cal, wanted_type) != target_month:
        raise RuntimeError(f"Couldn't switch {wanted_type} calendar to month {target_month}")

def get_open_days(cal_div):
    days = []
    cells = cal_div.query_selector_all("table.calendar_waku td.empty, table.calendar_waku td.congestion")
    for td in cells:
        a = td.query_selector("a")
        if not a:
            continue
        txt = (a.inner_text() or "").strip()
        if txt.isdigit():
            days.append(int(txt))
    return sorted(set(days))

# --- Main ---
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

    # --- Move both calendars to October and scrape ---
    results = {}
    for tname in ["Public", "Private"]:
        goto_month(page, tname, TARGET_MONTH)
        cal = find_calendar(page, tname)
        if cal:
            results[tname] = get_open_days(cal)
        else:
            results[tname] = []

    # --- Check target days ---
    alerts = []
    for tname, days in results.items():
        print(f"{tname} October open days: {days}")
        wanted = sorted(TARGET_DAYS.intersection(days))
        if wanted:
            alerts.append(f"{tname}: {wanted}")

    # --- Send Telegram if matches ---
    if alerts:
        msg = "🚨 Haneda Parking Alert!\n" + "\n".join(alerts)
        send_telegram(msg)
    else:
        print("No target dates available.")

    browser.close()
