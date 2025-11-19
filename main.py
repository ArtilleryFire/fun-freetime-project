import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

URL = "https://performancelab.my.id"

# Ambil Secret dari GitHub Actions
GYM_CODE = os.getenv("GYM_CODE")
GYM_NAME = os.getenv("GYM_NAME")

# Urutan sesi yang kamu inginkan (paling kanan = paling awal)
PREFERRED_SESSIONS = [6, 5, 4, 3, 2, 1]


def log(msg):
    print(f"[BOT] {msg}")


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = webdriver.Remote(
        command_executor="http://localhost:4444/wd/hub",
        options=options
    )
    return driver


def login(driver):
    log("Membuka halaman login...")
    driver.get(URL)
    time.sleep(2)

    log("Mengisi kode dan nama...")
    driver.find_element(By.ID, "kode").send_keys(GYM_CODE)
    driver.find_element(By.ID, "nama").send_keys(GYM_NAME)

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)

    log("Login selesai.")


def select_tomorrow(driver):
    log("Memilih hari BESOK...")
    btn = driver.find_element(By.CSS_SELECTOR, ".date-btn[data-day='tomorrow']")
    btn.click()
    time.sleep(2)


def get_sessions(driver, max_retries=20):
    for attempt in range(max_retries):
        try:
            # Deteksi halaman error
            if "500" in driver.page_source.lower() or "error" in driver.title.lower():
                log(f"[ERROR] Server 500. Retry {attempt+1}/{max_retries}...")
                time.sleep(2)
                driver.refresh()
                continue

            sessions = driver.find_elements(By.CSS_SELECTOR, ".session-slot")

            if len(sessions) == 0:
                log(f"[WARNING] Sesi kosong. Retry {attempt+1}/{max_retries}...")
                time.sleep(2)
                driver.refresh()
                continue

            log(f"Berhasil menemukan {len(sessions)} sesi.")
            return sessions

        except Exception as e:
            log(f"[EXCEPTION] {e} | Retry {attempt+1}/{max_retries}")
            time.sleep(2)
            driver.refresh()

    log("[FATAL] Tidak bisa mengambil sesi.")
    return None


def try_booking(driver, session_id):
    try:
        slot = driver.find_element(
            By.CSS_SELECTOR, 
            f".session-slot[data-session-id='{session_id}']"
        )

        # ========== CEK STATUS PENUH ==========  
        classes = slot.get_attribute("class")

        if "full" in classes:
            log(f"Sesi {session_id} PENUH (detected by class). Skip.")
            return False

        # tombol
        btn = slot.find_element(By.TAG_NAME, "button")

        if not btn.is_enabled():
            log(f"Sesi {session_id} TIDAK BISA DIPILIH (button disabled). Skip.")
            return False
        
        text = btn.text.strip().lower()
        if "penuh" in text or "full" in text:
            log(f"Sesi {session_id} PENUH (detected by button text). Skip.")
            return False

        # ========== JIKA AVAILABLE ==========  
        btn.click()
        time.sleep(2)

        log(f"=== BOOKING BERHASIL: SESI {session_id} ===")
        return True

    except Exception as e:
        log(f"Sesi {session_id} tidak ditemukan / error: {e}")
        return False


def main():
    driver = create_driver()

    login(driver)

    select_tomorrow(driver)

    log("Mengambil sesi...")
    sessions = get_sessions(driver)

    if sessions is None:
        log("Gagal mengambil sesi. Stop.")
        driver.quit()
        return

    log("Mulai mencoba booking...")

    while True:
        for session_id in PREFERRED_SESSIONS:
            log(f"Mencoba sesi {session_id}...")
            if try_booking(driver, session_id):
                driver.quit()
                return
        
        log("Belum dapat sesi, retry 3 detik...")
        time.sleep(3)
        driver.refresh()
        select_tomorrow(driver)


if __name__ == "__main__":
    main()
