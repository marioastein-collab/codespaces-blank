from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # set False if you want to watch
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

    # --- Helper function to extract availability ---
    def get_availability(calendars, month_label):
        results = {}
        for idx, cal in enumerate(calendars, start=1):
            available_days = []
            tds = cal.query_selector_all("td")
            for td in tds:
                link = td.query_selector("a")
                if link:
                    day_text = link.inner_text().strip()
                    onclick = link.get_attribute("onclick") or ""
                    # Only count clickable days with oamSubmitForm
                    if day_text.isdigit() and "oamSubmitForm" in onclick:
                        available_days.append(int(day_text))
            results[f"ParkingType{idx}"] = sorted(available_days)

        print(f"\n===== {month_label} Availability =====")
        for ptype, days in results.items():
            print(f"✅ {ptype} ({month_label}): {days}")

    # --- September ---
    calendars = page.query_selector_all("div#calendar01, div#calendar02, div#calendar03")
    get_availability(calendars, "September")

    # --- Switch to October ---
    next_button = page.query_selector("img[src*='arrow_r.gif']")
    if next_button:
        next_button.click()
        page.wait_for_selector("div#calendar01", timeout=15000)
        calendars = page.query_selector_all("div#calendar01, div#calendar02, div#calendar03")
        get_availability(calendars, "October")

    # --- Screenshot for confirmation ---
    page.screenshot(path="september_october.png", full_page=True)

    browser.close()
