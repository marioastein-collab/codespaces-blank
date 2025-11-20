# haneda_dec_oracle_test.py
from playwright.sync_api import sync_playwright
import requests
from datetime import datetime

# === Telegram Bot Config ===
BOT_TOKEN = "8402262632:AAHLXhtlueDYepJd8LUEK6J4mSh1UF2MHxg"
CHAT_ID = [
    "8430243174",
    "8543641889",
]

#CHAT_ID = "8430243174"
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

        # --- Go to December ---
        cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
        results = {}
        for idx in range(len(cal_divs)):
            cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
            cal = cal_divs[idx]

            # Move 1 month forward (Nov → Dec)
            for _ in range(1):
                next_btn = cal.query_selector("img[src*='arrow_r.gif']")
                if next_btn:
                    with page.expect_navigation():
                        next_btn.click()
                    page.wait_for_selector("table.calendar_waku", timeout=20000)
                    cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
                    cal = cal_divs[idx]

            tname = get_type_name(cal)
            open_days = get_open_days(cal)

            # Only keep Public / Private in results (ignore Unknown)
            if tname in ("Public", "Private"):
                results[tname] = open_days

            # Screenshot for verification (still taken for all)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            page.screenshot(path=f"december_{tname.lower()}_{timestamp}.png")
            print(f"📸 Screenshot saved: december_{tname.lower()}_{timestamp}.png")

        browser.close()
        return results


# === Run Once (Test) ===
print("Running December availability test...\n")
results = check_availability()

# Print only Public / Private results
for ttype in results:
    print(f"{ttype} December open days: {results[ttype]}")

# --- Notify via Telegram if any availability is found ---
available_lines = []
for ttype, days in results.items():
    if days:  # only if there is at least one open day
        day_list = ", ".join(str(d) for d in days)
        available_lines.append(f"{ttype}: {day_list}")

if available_lines:
    message = (
        "🚗 Haneda Parking – December availability detected!\n"
        + "\n".join(available_lines)
    )
    send_telegram(message)
    print("\n📩 Telegram notification sent.")
else:
    print("\n❌ No available dates found. No Telegram message sent.")

print("\n✅ Screenshots saved for visual verification.")
