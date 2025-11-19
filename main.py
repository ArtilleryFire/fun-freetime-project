import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from notify import send_log


URL = "https://performancelab.my.id"
DASHBOARD_URL = "https://performancelab.my.id/dashboard.php"

# Secrets
GYM_CODE = os.getenv("GYM_CODE")
GYM_NAME = os.getenv("GYM_NAME")

# Booking preferences
PREFERRED_SESSIONS = [6, 5, 4, 3, 2, 1]

MAX_RUNTIME = 240      # 4 menit
MAX_RETRY_LOOP = 5
SLEEP_RETRY = 3


def log(msg):
    print(f"[BOT] {msg}", flush=True)
    try:
        send_log(f"[BOT] {msg}")
    except:
        pass


def create_driver():
    """Create Chrome headless driver (NOT Selenium Grid)."""
    log("Menjalankan Chrome Headless lokal...")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        ChromeDriverManager().install(),
        options=options
    )
    return driver


def wait_css(driver, selector, timeout=20):
    """Wait until CSS selector exists."""
    for _ in range(timeout * 2):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector)
        except:
            time.sleep(0.5)
    return None


def login(driver):
    log("Membuka halaman login...")
    driver.get(URL)
    time.sleep(1)

    kode = wait_css(driver, "#kode")
    nama = wait_css(driver, "#nama")

    if not kode or not nama:
        log("ERROR: Form login tidak ditemukan.")
        return False

    kode.send_keys(GYM_CODE)
    nama.send_keys(GYM_NAME)

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Tunggu masuk dashboard
    for _ in range(20):
        if DASHBOARD_URL in driver.current_url:
            log("Login berhasil.")
            return True
        time.sleep(1)

    log("Login gagal, tidak masuk ke dashboard.")
    return False


def select_tomorrow(driver):
    btn = wait_css(driver, ".date-btn[data-day='tomorrow']", timeout=10)
    if not btn:
        log("Tombol 'Besok' tidak ditemukan.")
        return False

    btn.click()
    time.sleep(1)
    log("Tanggal besok dipilih.")
    return True


def get_sessions(driver, max_retries=20):
    """Load available session slots."""
    for attempt in range(max_retries):
        slots = driver.find_elements(By.CSS_SELECTOR, ".session-slot.available")

        if slots:
            log(f"Menemukan {len(slots)} sesi tersedia.")
            return slots

        log(f"Sesi belum muncul (retry {attempt+1}/{max_retries})...")
        time.sleep(1)

        driver.refresh()
        select_tomorrow(driver)

    return None


def try_booking(driver, session_id):
    """Attempt booking specific session ID."""
    try:
        slot = driver.find_element(
            By.CSS_SELECTOR,
            f".session-slot.available[data-session-id='{session_id}']"
        )
        btn = slot.find_element(By.TAG_NAME, "button")

        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)

        log(f"=== BOOKING BERHASIL UNTUK SESI {session_id} ===")
        return True

    except Exception as e:
        log(f"Gagal booking sesi {session_id}: {e}")
        return False


def main():
    log("=== BOT BOOKING DIMULAI (HEADLESS MODE) ===")

    start = time.time()
    retry_count = 0

    driver = create_driver()
    time.sleep(1)

    if not login(driver):
        driver.quit()
        return

    select_tomorrow(driver)

    sessions = get_sessions(driver)
    if not sessions:
        log("Tidak ada sesi muncul. STOP.")
        driver.quit()
        return

    log("Mulai mencoba booking...")

    while True:
        if time.time() - start > MAX_RUNTIME:
            log("Runtime melebihi batas, stop.")
            driver.quit()
            return

        for session_id in PREFERRED_SESSIONS:
            log(f"Mencoba booking sesi {session_id}...")
            if try_booking(driver, session_id):
                driver.quit()
                return

        retry_count += 1
        if retry_count >= MAX_RETRY_LOOP:
            log("Gagal booking setelah banyak percobaan. Stop.")
            driver.quit()
            return

        log(f"Retry booking... ({retry_count}/{MAX_RETRY_LOOP})")
        time.sleep(SLEEP_RETRY)
        driver.refresh()
        select_tomorrow(driver)


if __name__ == "__main__":
    main()
