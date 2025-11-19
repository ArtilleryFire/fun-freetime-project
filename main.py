import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from notify import send_log  # Discord notification

URL_LOGIN = "https://performancelab.my.id/"
URL_DASHBOARD = "https://performancelab.my.id/dashboard.php"

GYM_CODE = os.getenv("GYM_CODE")
GYM_NAME = os.getenv("GYM_NAME")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Prioritas sesi: dari sore ke pagi
PREFERRED_SESSIONS = [6, 5, 4, 3, 2, 1]

MAX_RUNTIME = 300       # stop setelah 5 menit
MAX_RETRY_LOOP = 5      # retry booking maksimal
SLEEP_RETRY = 3         # jeda antar retry


def log(msg):
    """Print ke console + kirim ke Discord"""
    full = f"[BOT] {msg}"
    print(full, flush=True)  # flush=True agar muncul langsung di console
    try:
        send_log(full)
    except:
        pass


def create_driver():
    """Buat driver Chrome headless"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def wait_css(driver, selector, timeout=30):
    """Menunggu elemen muncul"""
    for _ in range(timeout * 2):
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            if el.is_displayed():
                return el
        except:
            pass
        time.sleep(0.5)
    return None


def login(driver):
    log("Membuka halaman login...")
    driver.get(URL_LOGIN)
    time.sleep(2)

    kode = wait_css(driver, "#kode")
    nama = wait_css(driver, "#nama")
    submit = wait_css(driver, "button[type='submit']")

    if not kode or not nama or not submit:
        log("Gagal menemukan elemen login!")
        return False

    kode.clear()
    kode.send_keys(GYM_CODE)
    nama.clear()
    nama.send_keys(GYM_NAME)
    submit.click()

    # tunggu redirect ke dashboard
    for _ in range(10):
        if driver.current_url.startswith(URL_DASHBOARD):
            log("Login berhasil, dashboard terbuka.")
            return True
        time.sleep(1)

    log("Login gagal atau dashboard tidak terbuka.")
    return False


def select_tomorrow(driver):
    btn = wait_css(driver, ".date-btn[data-day='tomorrow']", timeout=15)
    if btn:
        btn.click()
        time.sleep(1)
        return True
    return False


def get_sessions(driver, max_retries=25):
    """Ambil semua slot sesi"""
    for attempt in range(max_retries):
        sessions = driver.find_elements(By.CSS_SELECTOR, ".session-slot.available")
        if sessions:
            log(f"Menemukan {len(sessions)} sesi tersedia.")
            return sessions
        log(f"Sesi belum muncul (retry {attempt+1}/{max_retries})")
        time.sleep(2)
        driver.refresh()
        select_tomorrow(driver)
    return []


def try_booking(driver, session_id):
    """Coba booking satu sesi"""
    try:
        slot = driver.find_element(
            By.CSS_SELECTOR, f".session-slot[data-session-id='{session_id}'].available"
        )
        btn = slot.find_element(By.TAG_NAME, "button")
        if btn.is_enabled():
            btn.click()
            time.sleep(1)
            log(f"=== BOOKING BERHASIL SESI {session_id} ===")
            return True
        else:
            log(f"Sesi {session_id} disabled. Skip.")
    except:
        log(f"Sesi {session_id} tidak tersedia. Skip.")
    return False


def main():
    start = time.time()
    retry_count = 0

    log("=== BOT BOOKING DIMULAI ===")

    driver = create_driver()

    if not login(driver):
        driver.quit()
        return

    select_tomorrow(driver)

    while True:
        if time.time() - start > MAX_RUNTIME:
            log("Stop: runtime > 5 menit")
            driver.quit()
            return

        sessions = get_sessions(driver)
        if not sessions:
            log("Tidak ada sesi tersedia.")
        else:
            for session_id in PREFERRED_SESSIONS:
                log(f"Mencoba sesi {session_id}...")
                if try_booking(driver, session_id):
                    driver.quit()
                    return

        retry_count += 1
        if retry_count >= MAX_RETRY_LOOP:
            log(f"Gagal booking setelah {retry_count} retry")
            driver.quit()
            return

        log(f"Belum dapat sesi, retry {retry_count}/{MAX_RETRY_LOOP} (jeda {SLEEP_RETRY}s)...")
        time.sleep(SLEEP_RETRY)
        driver.refresh()
        select_tomorrow(driver)


if __name__ == "__main__":
    main()
