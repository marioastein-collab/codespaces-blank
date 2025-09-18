# haneda_sept_v3.py
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://pk-reserve.haneda-airport.jp/airport/en/entrance/0000.jsf"

def get_type_name(cal_div):
    # Identify calendar type by the header image (public/private/handicap)
    img = cal_div.query_selector("table.calendar_btm img")
    if not img:
        return "Unknown"
    src = (img.get_attribute("src") or "").lower()
    if "public_month" in src:
        return "Public"
    if "private_month" in src:
        return "Private"
    if "handicap_month" in src:
        return "Handicap"
    return "Unknown"

def get_open_days(cal_div):
    days = []
    # "empty" and "congestion" are available; "full" and "unavailable" are not
    cells = cal_div.query_selector_all("table.calendar_waku td.empty, table.calendar_waku td.congestion")
    for td in cells:
        a = td.query_selector("a")
        if not a:
            continue
        txt = (a.inner_text() or "").strip()
        if txt.isdigit():
            days.append(int(txt))
    return sorted(set(days))

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

    # --- Go to reservations (予約) ---
    # Click the anchor if we can (more reliable than the image); else fallback to the image
    if page.query_selector("#sidebar\\:_idJsp0\\:_idJsp18"):
        with page.expect_navigation():
            page.click("#sidebar\\:_idJsp0\\:_idJsp18")
    else:
        with page.expect_navigation():
            page.click("img[alt='予約']")

    # Wait specifically for the calendar tables (not the wrapper divs)
    page.wait_for_selector("table.calendar_waku", timeout=20000)

    # Save snapshot for sanity
    page.screenshot(path="reservation_sept.png", full_page=True)
    with open("reservation_sept.html", "w", encoding="utf-8") as f:
        f.write(page.content())

    # --- Extract availability grouped by parking type ---
    results = {}
    # There are two calendar01 blocks (Public, Private) and one calendar02 (Handicap)
    cal_divs = page.query_selector_all("div#calendar01, div#calendar02")
    if not cal_divs:
        print("⚠️ No calendar blocks found.")
    else:
        for cal in cal_divs:
            tname = get_type_name(cal)
            open_days = get_open_days(cal)
            results[tname] = open_days

    # Print grouped results
    order = ["Public", "Private", "Handicap"]
    printed = set()
    for key in order:
        if key in results:
            print(f"✅ {key} open days in September: {results[key]}")
            printed.add(key)
    # Any unexpected/unknown types
    for key, val in results.items():
        if key not in printed:
            print(f"✅ {key} open days in September: {val}")

    print("📸 Saved reservation_sept.png + reservation_sept.html")

    browser.close()
