import os
import time
from selenium.webdriver import Remote
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
    """Gunakan Selenium Remote WebDriver (Chrome Container Github Actions)."""
    log("Menghubungkan ke Selenium Remote Chrome...")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = Remote(
        command_executor="http://localhost:4444/wd/hub",
        options=options
    )
    return driver


def wait_css(driver, selector, timeout=25):
    for _ in range(timeout * 2):
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            return el
        except:
            time.sleep(0.5)
    return None


def ensure_tomorrow_active(driver):
    """Klik tombol besok hingga class = active muncul."""
    for _ in range(6):
        btn = wait_css(driver, ".date-btn[data-day='tomorrow']", timeout=5)
        if not btn:
            time.sleep(1)
            continue

        btn.click()
        time.sleep(1.2)

        kelas = btn.get_attribute("class")
        if "active" in kelas:
            log("Tombol 'Besok' aktif.")
            return True

    log("Gagal mengaktifkan tombol besok.")
    return False


def wait_session_grid(driver):
    """Pastikan grid sesi muncul sebelum melanjutkan."""
    for _ in range(20):
        grid = driver.find_elements(By.CSS_SELECTOR, ".session-slot")
        if grid:
            return True
        time.sleep(1)
    log("Grid sesi tidak muncul.")
    return False


def login(driver):
    log("Membuka halaman login...")
    driver.get(URL)
    time.sleep(2)

    kode = wait_css(driver, "#kode")
    nama = wait_css(driver, "#nama")
    if not kode or not nama:
        log("Form login tidak ditemukan.")
        return False

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


def get_available_sessions(driver):
    """Ambil semua sesi dengan class available."""
    sessions = driver.find_elements(By.CSS_SELECTOR, ".session-slot.available")
    return sessions


def try_booking(driver, session_id):
    try:
        sel = driver.find_element(By.CSS_SELECTOR,
            f".session-slot.available[data-session-id='{session_id}']")

        btn = sel.find_element(By.TAG_NAME, "button")

        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.4)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)

        kelas_baru = sel.get_attribute("class")
        if "reserved-by-user" in kelas_baru or "unavailable-booked" in kelas_baru:
            log(f"=== BOOKING BERHASIL SESI {session_id} ===")
            return True

        log(f"Klik pada sesi {session_id} tidak mengubah status.")
        return False

    except Exception as e:
        log(f"Error sesi {session_id}: {e}")
        return False


def main():
    start = time.time()
    retry = 0

    log("=== BOT BOOKING DIMULAI ===")

    driver = create_driver()

    if not login(driver):
        driver.quit()
        return

    ensure_tomorrow_active(driver)
    wait_session_grid(driver)

    log("Mengambil sesi yang tersedia...")

    while True:
        if time.time() - start > MAX_RUNTIME:
            log("Runtime melebihi batas, stop.")
            driver.quit()
            return

        sessions = get_available_sessions(driver)

        if sessions:
            log(f"Ditemukan {len(sessions)} sesi available.")
        else:
            log("Tidak ada sesi available.")

        for sid in PREFERRED_SESSIONS:
            log(f"Mencoba booking sesi {sid}...")
            if try_booking(driver, sid):
                driver.quit()
                return

        retry += 1
        if retry >= MAX_RETRY_LOOP:
            log("Gagal booking, retry habis.")
            driver.quit()
            return

        log(f"Retry {retry}/{MAX_RETRY_LOOP}, refresh halaman...")
        time.sleep(SLEEP_RETRY)

        driver.refresh()
        time.sleep(2)
        ensure_tomorrow_active(driver)
        wait_session_grid(driver)


if __name__ == "__main__":
    main()
