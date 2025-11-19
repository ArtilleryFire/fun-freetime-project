import os
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from notify import send_log   # <<< DISCORD NOTIF

URL = "https://performancelab.my.id"

GYM_CODE = os.getenv("GYM_CODE")
GYM_NAME = os.getenv("GYM_NAME")

# Urutan sesi yang akan dicoba
PREFERRED_SESSIONS = [6, 5, 4, 3, 2, 1]

MAX_RUNTIME = 300          # 5 menit batas aman runner GA
MAX_RETRY_LOOP = 5         # <<<<<< BATAS RETRY 5x
SLEEP_RETRY = 3            # jeda antara loop retry


def log(msg):
    """Print + kirim ke Discord"""
    full = f"[BOT] {msg}"
    print(full)
    try:
        send_log(full)
    except:
        pass  # biar tidak ganggu eksekusi utama


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = webdriver.Remote(
        command_executor=os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub"),
        options=options
    )
    return driver


def wait_css(driver, selector, timeout=30):
    for i in range(timeout * 2):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector)
        except:
            time.sleep(0.5)
    return None


def login(driver):
    log("Membuka halaman login...")
    driver.get(URL)
    time.sleep(2)

    kode = wait_css(driver, "#kode")
    nama = wait_css(driver, "#nama")

    kode.send_keys(GYM_CODE)
    nama.send_keys(GYM_NAME)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    time.sleep(2)
    log("Login selesai.")


def select_tomorrow(driver):
    btn = wait_css(driver, ".date-btn[data-day='tomorrow']", timeout=15)
    if btn:
        btn.click()
        time.sleep(2)
        return True
    return False


def get_sessions(driver, max_retries=25):
    for attempt in range(max_retries):
        sessions = driver.find_elements(By.CSS_SELECTOR, ".session-slot")
        if len(sessions) > 0:
            log(f"Menemukan {len(sessions)} sesi.")
            return sessions

        log(f"Sesi belum muncul (retry {attempt+1}/{max_retries})")
        time.sleep(2)
        driver.refresh()
        select_tomorrow(driver)

    return None


def try_booking(driver, session_id):
    try:
        slot = driver.find_element(
            By.CSS_SELECTOR,
            f".session-slot[data-session-id='{session_id}']"
        )

        classes = slot.get_attribute("class")

        if "full" in classes:
            log(f"Sesi {session_id} PENUH (class). Skip.")
            return False

        btn = slot.find_element(By.TAG_NAME, "button")

        if not btn.is_enabled():
            log(f"Sesi {session_id} disabled. Skip.")
            return False

        text = btn.text.strip().lower()
        if "penuh" in text or "full" in text:
            log(f"Sesi {session_id} PENUH (text). Skip.")
            return False

        # booking available
        btn.click()
        time.sleep(2)
        log(f"=== BOOKING BERHASIL SESI {session_id} ===")
        return True

    except Exception as e:
        log(f"Error sesi {session_id}: {e}")
        return False


def main():
    start = time.time()
    retry_count = 0

    log("=== BOT BOOKING DIMULAI ===")

    driver = create_driver()

    login(driver)
    time.sleep(1)
    select_tomorrow(driver)

    sessions = get_sessions(driver)
    if sessions is None:
        log("Gagal mengambil sesi (timeout).")
        driver.quit()
        return

    log("Mulai proses booking...")

    while True:
        # stop jika runtime > 5 menit
        if time.time() - start > MAX_RUNTIME:
            log("Stop karena runtime > 5 menit.")
            driver.quit()
            return

        for session_id in PREFERRED_SESSIONS:
            log(f"Mencoba sesi {session_id}...")
            if try_booking(driver, session_id):
                driver.quit()
                return

        retry_count += 1
        if retry_count >= MAX_RETRY_LOOP:
            log(f"Gagal booking setelah {retry_count} kali retry.")
            driver.quit()
            return

        log(f"Belum dapat sesi, retry {retry_count}/{MAX_RETRY_LOOP} (jeda {SLEEP_RETRY}s)...")
        time.sleep(SLEEP_RETRY)
        driver.refresh()
        select_tomorrow(driver)


if __name__ == "__main__":
    main()
