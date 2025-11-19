import os
import time
from selenium.webdriver import Remote
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from notify import send_log as send_message

# ==============================
# UTIL LOGGING
# ==============================
def log(msg):
    print(f"[BOT] {msg}")
    try:
        send_message(msg)
    except:
        pass

# ==============================
# SCREENSHOT DEBUG
# ==============================
def ss(driver, name):
    path = f"debug-{name}.png"
    try:
        driver.save_screenshot(path)
        log(f"Screenshot disimpan: {path}")
    except:
        log("Gagal screenshot")

# ==============================
# DRIVER CREATION
# ==============================
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    log("Menghubungkan ke Selenium Remote Chrome...")
    driver = Remote(
        command_executor="http://localhost:4444/wd/hub",
        options=chrome_options
    )
    log("Driver OK!")
    return driver

# ==============================
# WAIT CLICK
# ==============================
def wait_click(driver, selector, timeout=20):
    log(f"Menunggu elemen: {selector}")
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )

# ==============================
# LOGIN
# ==============================
def login(driver):
    log("Mulai login...")
    driver.get("https://website-booking.com/login")
    time.sleep(3)
    ss(driver, "login-page")

    # DEBUG: print snippet
    log("HTML Login Snippet:\n" + driver.page_source[:500])

    # isi username password
    driver.find_element(By.ID, "username").send_keys("USERNAME_KAMU")
    driver.find_element(By.ID, "password").send_keys("PASSWORD_KAMU")

    wait_click(driver, "button.login-btn").click()
    time.sleep(3)
    ss(driver, "after-login")

# ==============================
# GET SESSIONS
# ==============================
def get_sessions(driver):
    log("Membuka halaman sesi...")
    driver.get("https://website-booking.com/schedule")
    time.sleep(4)
    ss(driver, "schedule-page")

    log("HTML SCHEDULE Snippet:\n" + driver.page_source[:500])

    # klik tanggal besok
    try:
        wait_click(driver, "[data-day='tomorrow']").click()
        log("Klik tanggal besok OK")
    except:
        log("GAGAL klik tanggal besok — cek selector!")
        ss(driver, "tomorrow-fail")
        return []

    time.sleep(3)
    ss(driver, "after-select-date")

    # ambil slot sesi
    slots = driver.find_elements(By.CSS_SELECTOR, ".session-slot")
    log(f"Jumlah slot ditemukan: {len(slots)}")

    for s in slots:
        html = s.get_attribute("outerHTML")
        log(f"Slot HTML: {html[:200]}")

    return slots

# ==============================
# BOOK SESSION
# ==============================
def try_booking(slots):
    for slot in slots:
        cls = slot.get_attribute("class")
        if "available" in cls:
            log("Menemukan slot AVAILABLE! Mencoba booking...")
            try:
                slot.click()
                time.sleep(2)
                log("BOOKING BERHASIL (kemungkinan besar)")
                return True
            except Exception as e:
                log(f"Gagal klik slot: {e}")
                continue
    log("Tidak ada slot available.")
    return False

# ==============================
# MAIN LOOP
# ==============================
def main():
    log("=== BOT BOOKING DEBUG MODE DIMULAI ===")
    driver = create_driver()

    try:
        login(driver)

        for i in range(5):
            log(f"Cek sesi ke-{i+1}...")
            slots = get_sessions(driver)
            if try_booking(slots):
                log("FINISHED!")
                break
            time.sleep(5)

    except Exception as e:
        log(f"ERROR FATAL: {e}")
        ss(driver, "fatal-error")

    finally:
        log("Menutup driver...")
        driver.quit()


if __name__ == "__main__":
    main()
