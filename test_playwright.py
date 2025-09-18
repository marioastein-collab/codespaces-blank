from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=False if you want to see the browser
        page = browser.new_page()
        page.goto("https://example.com")
        print("Page title:", page.title())
        browser.close()

if __name__ == "__main__":
    run()
