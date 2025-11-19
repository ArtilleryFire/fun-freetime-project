import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from notify import send_log

URL = "https://performancelab.my.id"
DASHBOARD_URL = "https://performancelab.my.id/dashboard.php"

GYM_CODE = os.getenv("GYM_CODE")
GYM_NAME = os.getenv("GYM_NAME")

PREFERRED_SESSIONS = [6, 5, 4, 3, 2, 1]
MAX_RUNTIME = 300
MAX_RETRY_LOOP = 5
SLEEP_RETRY = 3

def log(msg):
    full = f"[BOT] {msg}"
    print(full, flush=True)
    try:
        send_log(full)
    except:
        pass

def create_driver():
    log("Menjalankan Chrome headless lokal…")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

def wait_css(driver, selector, timeout=30):
    for _ in range(timeout * 2):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector)
        except:
            time.sleep(0.5)
    return None

def login(driver):
    log("Membuka halaman login…")
    driver.get(URL)
    time.sleep(2)

    kode = wait_css(driver, "#kode")
    nama = wait_css(driver, "#nama")
    kode.send_keys(GYM_CODE)
    nama.send_keys(GYM_NAME)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    for _ in range(20):
        if DASHBOARD_URL in driver.current_url:
            log("Login berhasil.")
            return True
        time.sleep(1)

    log("Login gagal.")
    return False

def select_tomorrow(driver):
    btn = wait_css(driver, ".date-btn[data-day='tomorrow']", timeout=10)
    if btn:
        btn.click()
        time.sleep(1.5)
        return True
    return False

def get_sessions(driver, max_retries=25):
    for attempt in range(max_retries):
        sessions = driver.find_elements(By.CSS_SELECTOR, ".session-slot.available")
        if sessions:
            log(f"Menemukan {len(sessions)} sesi tersedia.")
            return sessions

        log(f"Sesi belum muncul (retry {attempt+1}/{max_retries})")
        time.sleep(2)
        driver.refresh()
        select_tomorrow(driver)
    return None

def try_booking(driver, session_id):
    try:
        slot = driver.find_element(By.CSS_SELECTOR,
            f".session-slot.available[data-session-id='{session_id}']")
        btn = slot.find_element(By.TAG_NAME, "button")
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", btn)
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
    if not login(driver):
        driver.quit()
        return

    time.sleep(1)
    select_tomorrow(driver)

    sessions = get_sessions(driver)
    if not sessions:
        log("Gagal mengambil sesi.")
        driver.quit()
        return

    log("Mulai proses booking…")

    while True:
        if time.time() - start > MAX_RUNTIME:
            log("Stop: runtime > 5 menit.")
            driver.quit()
            return

        for session_id in PREFERRED_SESSIONS:
            log(f"Mencoba sesi {session_id}…")
            if try_booking(driver, session_id):
                driver.quit()
                return

        retry_count += 1
        if retry_count >= MAX_RETRY_LOOP:
            log(f"Gagal booking setelah {retry_count} retry.")
            driver.quit()
            return

        log(f"Belum dapat sesi, retry {retry_count}/{MAX_RETRY_LOOP}… (tunggu {SLEEP_RETRY}s)")
        time.sleep(SLEEP_RETRY)
        driver.refresh()
        select_tomorrow(driver)

if __name__ == "__main__":
    main()
