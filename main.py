import os
import time
import traceback
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


WEB_URL = "https://performancelab.my.id/"
DASHBOARD_URL = "https://performancelab.my.id/dashboard.php"

GYM_CODE = os.getenv("GYM_CODE", "")
GYM_NAME = os.getenv("GYM_NAME", "")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")


# =============================
# Discord Notification
# =============================
def notify(msg):
    print(f"[NOTIFY] {msg}")
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg})
    except:
        pass


# =============================
# Screenshot + HTML Dump
# =============================
def debug_capture(driver, name):
    os.makedirs("debug", exist_ok=True)
    try:
        driver.save_screenshot(f"debug/{name}.png")
        with open(f"debug/{name}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except:
        pass


# =============================
# Create Driver
# =============================
def create_driver():
    print("[DEBUG] Starting Chrome driver...")

    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1366,768")
    chrome_opts.binary_location = "/usr/bin/chromium-browser"

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts
    )

    print("[DEBUG] Chrome driver started.")
    return driver


# =============================
# Login Function
# =============================
def login(driver):
    print("[DEBUG] Navigating to login page...")
    driver.get(WEB_URL)
    time.sleep(3)
    debug_capture(driver, "01_login_page_loaded")

    print("[DEBUG] Filling login form...")
    driver.find_element(By.NAME, "kode").send_keys(GYM_CODE)
    driver.find_element(By.NAME, "nama").send_keys(GYM_NAME)

    debug_capture(driver, "02_login_form_filled")

    print("[DEBUG] Submitting login...")
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    time.sleep(4)
    debug_capture(driver, "03_after_login_attempt")

    if "dashboard.php" not in driver.current_url:
        print("[ERROR] Login failed or redirect incorrect.")
        notify("❌ Login gagal. Periksa kode atau nama.")
        return False

    print("[DEBUG] Login success.")
    notify("✅ Login berhasil.")
    return True


# =============================
# Booking Function
# =============================
def perform_booking(driver):
    print("[DEBUG] Checking dashboard...")

    if DASHBOARD_URL not in driver.current_url:
        driver.get(DASHBOARD_URL)
        time.sleep(3)

    debug_capture(driver, "04_dashboard_loaded")

    print("[DEBUG] Clicking tomorrow tab...")
    try:
        tomorrow_btn = driver.find_element(By.CSS_SELECTOR, ".date-btn[data-day='tomorrow']")
        tomorrow_btn.click()
        time.sleep(2)
        debug_capture(driver, "05_tomorrow_tab_clicked")
    except Exception as e:
        print("[ERROR] Could not click tomorrow tab:", e)
        notify("❌ Tidak bisa klik tab Besok.")
        return False

    print("[DEBUG] Scanning available sessions...")

    slots = driver.find_elements(By.CSS_SELECTOR, ".session-slot.available")
    if not slots:
        print("[ERROR] No available sessions found.")
        notify("⚠ Tidak ada sesi available untuk besok.")
        return False

    first_slot = slots[0]
    debug_capture(driver, "06_found_available_slots")

    print("[DEBUG] Clicking first available session...")
    try:
        btn = first_slot.find_element(By.TAG_NAME, "button")
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(1)
        btn.click()
        time.sleep(3)
        debug_capture(driver, "07_after_click_session")
        notify("🎉 Berhasil booking sesi gym!")
        return True
    except Exception as e:
        print("[ERROR] Unable to click session button:", e)
        notify("❌ Gagal klik tombol 'Pilih Sesi'.")
        return False


# =============================
# MAIN
# =============================
def main():
    notify("🔵 Auto Booking dijalankan.")

    try:
        driver = create_driver()
        success = login(driver)

        if not success:
            print("[ERROR] Login failed, exiting.")
            driver.quit()
            return

        booking_result = perform_booking(driver)

        if booking_result:
            notify("✅ Booking selesai.")
        else:
            notify("⚠ Booking tidak berhasil.")

    except Exception as e:
        print("[FATAL ERROR]", e)
        traceback.print_exc()
        notify(f"🔥 Script error: {e}")

    finally:
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    main()
