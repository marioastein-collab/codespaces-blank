from playwright.sync_api import sync_playwright

def extract_open_days(cal):
    """Helper to extract open days from a calendar div."""
    available_days = []
    tds = cal.query_selector_all("td")
    for td in tds:
        link = td.query_selector("a")
        if link:
            day = link.inner_text().strip()
            if day.isdigit():
                available_days.append(int(day))
    return sorted(available_days)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # --- Login ---
    page.goto("https://pk-reserve.haneda-airport.jp/airport/en/entrance/0000.jsf")
    page.click("img[alt='login']")
    page.wait_for_selector("form#form1")
    page.select_option('select[name="form1:_idJsp66"]', "61")   # 品川
    page.fill('input[name="form1:Vehicle_type_code"]', "331")
    page.select_option('select[name="form1:_idJsp68"]', "21")   # ね
    page.fill('input[name="form1:Specified_number"]', "9300")
    page.fill('input[name="form1:パスワード"]', "Chessmama16")
    page.click('#form1\\:loginbutton img[alt="ログイン"]')
    page.wait_for_selector("#welcomarea", timeout=10000)

    # --- Go to reservations ---
    page.click("img[alt='予約']")
    page.wait_for_selector("div#calendar01", timeout=15000)

    # --- September availability ---
    print("===== September Availability =====")
    for idx, cal_id in enumerate(["calendar01", "calendar02", "calendar03"], start=1):
        cal = page.query_selector(f"div#{cal_id}")
        if not cal:
            continue
        days = extract_open_days(cal)
        print(f"✅ ParkingType{idx} (September): {days}")

    # --- October availability ---
    print("\n===== October Availability =====")
    for idx, cal_id in enumerate(["calendar01", "calendar02", "calendar03"], start=1):
        cal = page.query_selector(f"div#{cal_id}")
        if not cal:
            continue
        # click the right arrow inside this calendar
        right_arrow = cal.query_selector("img[src*='arrow_r.gif']")
        if right_arrow:
            right_arrow.click()
            page.wait_for_timeout(2000)  # wait for reload
            # re-query the calendar after reload
            cal = page.query_selector(f"div#{cal_id}")
            days = extract_open_days(cal)
            print(f"✅ ParkingType{idx} (October): {days}")
        else:
            print(f"⚠️ No right arrow found for {cal_id}")

    page.screenshot(path="september_october.png", full_page=True)
    browser.close()
