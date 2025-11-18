import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# === Ambil data login dari GitHub Secret ===
GYM_CODE = os.getenv("GYM_CODE")
GYM_NAME = os.getenv("GYM_NAME")

# === Konfigurasi Selenium ===
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

URL = "https://performancelab.my.id"

# urutan sesi yang kamu inginkan
PREFERRED_SESSIONS = [6, 5, 4, 3, 2, 1]

def log(msg):
    print(f"[BOT] {msg}")

def login():
    log("Membuka halaman login...")
    driver.get(URL)
    time.sleep(2)

    log("Mengisi kode dan nama...")
    driver.find_element(By.ID, "kode").send_keys(GYM_CODE)
    driver.find_element(By.ID, "nama").send_keys(GYM_NAME)

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)
    log("Login selesai.")

def select_tomorrow():
    log("Memilih hari BESOK...")
    btn = driver.find_element(By.CSS_SELECTOR, ".date-btn[data-day='tomorrow']")
    btn.click()
    time.sleep(2)

def try_booking(session_id):
    try:
        slot = driver.find_element(By.CSS_SELECTOR, f".session-slot[data-session-id='{session_id}']")
        btn = slot.find_element(By.TAG_NAME, "button")

        if not btn.is_enabled():
            log(f"Sesi {session_id} tidak tersedia.")
            return False

        btn.click()
        time.sleep(2)
        log(f"BERHASIL pilih sesi {session_id}!")
        return True
    except:
        log(f"Sesi {session_id} tidak ditemukan.")
        return False

def main():
    login()
    select_tomorrow()

    log("Mulai mencoba booking...")
    
    while True:
        for session_id in PREFERRED_SESSIONS:
            log(f"Mencoba sesi {session_id}...")
            success = try_booking(session_id)
            if success:
                log(f"=== RESERVASI SUKSES: SESI {session_id} ===")
                driver.quit()
                return
        
        log("Belum dapat sesi. Retry 3 detik...")
        time.sleep(3)
        driver.refresh()
        select_tomorrow()

if __name__ == "__main__":
    main()
