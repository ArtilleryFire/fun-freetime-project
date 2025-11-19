import os
import logging
import traceback
import time  # Added this import to fix the 'time' not defined error
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Constants
WEB_URL = "https://performancelab.my.id/"
DASHBOARD_URL = "https://performancelab.my.id/dashboard.php"
TIMEOUT = 10  # Seconds for WebDriverWait

# Environment variables
GYM_CODE = os.getenv("GYM_CODE", "")
GYM_NAME = os.getenv("GYM_NAME", "")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================
# Discord Notification
# =============================
def notify(msg):
    logger.info(f"[NOTIFY] {msg}")
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")

# =============================
# Screenshot + HTML Dump
# =============================
def debug_capture(driver, name):
    os.makedirs("debug", exist_ok=True)
    try:
        driver.save_screenshot(f"debug/{name}.png")
        with open(f"debug/{name}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info(f"Debug capture saved: {name}")
    except Exception as e:
        logger.error(f"Failed to capture debug: {e}")

# =============================
# Create Driver
# =============================
def create_driver():
    logger.info("Starting Chrome driver...")
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1366,768")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--disable-extensions")
    chrome_opts.add_argument("--disable-images")  # Speed up loading
    chrome_opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # For GitHub Actions compatibility
    chrome_opts.binary_location = "/usr/bin/google-chrome-stable"
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts
    )
    logger.info("Chrome driver started successfully.")
    return driver

# =============================
# Login Function
# =============================
def login(driver):
    logger.info("Navigating to login page...")
    driver.get(WEB_URL)
    
    try:
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.NAME, "kode")))
        debug_capture(driver, "01_login_page_loaded")
        
        logger.info("Filling login form...")
        driver.find_element(By.NAME, "kode").send_keys(GYM_CODE)
        driver.find_element(By.NAME, "nama").send_keys(GYM_NAME)
        debug_capture(driver, "02_login_form_filled")
        
        logger.info("Submitting login...")
        submit_btn = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        submit_btn.click()
        
        WebDriverWait(driver, TIMEOUT).until(lambda d: "dashboard.php" in d.current_url)
        debug_capture(driver, "03_after_login_attempt")
        
        # New: Check for membership status on dashboard
        logger.info("Verifying dashboard and membership status...")
        membership_elem = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CLASS_NAME, "membership-status")))
        membership_text = membership_elem.text
        logger.info(f"Membership status: {membership_text}")
        notify(f"ℹ Status Membership: {membership_text}")
        
        # Check for expiry warning
        warning_elem = driver.find_element(By.ID, "membership-warning")
        if warning_elem.is_displayed():
            logger.warning("Membership has expired!")
            notify("⚠ Masa aktif membership telah berakhir. Tidak bisa booking.")
            return False
        
        logger.info("Login and dashboard verification successful.")
        notify("✅ Login berhasil.")
        return True
    except Exception as e:
        logger.error(f"Login failed: {e}")
        debug_capture(driver, "03_login_failed")
        notify("❌ Login gagal. Periksa kode atau nama.")
        return False

# =============================
# Booking Function
# =============================
def perform_booking(driver):
    logger.info("Checking dashboard...")
    
    if DASHBOARD_URL not in driver.current_url:
        driver.get(DASHBOARD_URL)
        WebDriverWait(driver, TIMEOUT).until(EC.url_contains("dashboard.php"))
    
    debug_capture(driver, "04_dashboard_loaded")
    
    # Check if already reserved (look for "reserved-by-user" class or similar)
    reserved_slots = driver.find_elements(By.CSS_SELECTOR, ".session-slot.reserved-by-user")
    if reserved_slots:
        logger.info("Slot already reserved for tomorrow.")
        notify("ℹ Slot sudah dipesan untuk besok.")
        return True  # Consider this a success to avoid re-booking
    
    logger.info("Clicking tomorrow tab...")
    try:
        tomorrow_btn = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".date-btn[data-day='tomorrow']")))
        tomorrow_btn.click()
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".session-slot")))  # Wait for slots to load
        debug_capture(driver, "05_tomorrow_tab_clicked")
    except Exception as e:
        logger.error(f"Could not click tomorrow tab: {e}")
        notify("❌ Tidak bisa klik tab Besok.")
        return False
    
    logger.info("Scanning available sessions...")
    try:
        # Wait for available slots to appear (in case they're loaded dynamically)
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".session-slot")))
        slots = driver.find_elements(By.CSS_SELECTOR, ".session-slot.available")
        if not slots:
            logger.warning("No available sessions found.")
            notify("⚠ Tidak ada sesi available untuk besok.")
            return False
        
        # Collect available sessions with their IDs
        available_sessions = []
        for slot in slots:
            session_id = int(slot.get_attribute("data-session-id"))
            available_sessions.append((session_id, slot))
        
        # Sort by session_id descending (6, 5, 4, 3, 2, 1)
        available_sessions.sort(key=lambda x: x[0], reverse=True)
        
        # Pick the highest priority (first in sorted list)
        chosen_session_id, chosen_slot = available_sessions[0]
        logger.info(f"Selected session ID {chosen_session_id} for booking.")
        
        debug_capture(driver, "06_found_available_slots")
        
        logger.info("Clicking selected session...")
        btn = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable(chosen_slot.find_element(By.TAG_NAME, "button")))
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        btn.click()
        
        # Handle the confirmation alert
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            logger.info(f"Accepting confirmation alert: {alert.text}")
            alert.accept()  # Click "OK" to confirm
        except Exception as e:
            logger.warning(f"No alert found or failed to handle: {e}")
        
        # Wait for potential confirmation (e.g., modal or page update)
        time.sleep(2)  # Short wait; adjust if needed
        debug_capture(driver, "07_after_click_session")
        
        # Check for success (e.g., look for a success message or updated class)
        # Based on HTML, you might need to inspect for a specific element after booking
        success_indicators = driver.find_elements(By.CSS_SELECTOR, ".success-message")  # Placeholder; replace with actual selector
        if success_indicators or "reserved" in driver.page_source.lower():
            logger.info("Booking successful.")
            notify(f"🎉 Berhasil booking sesi gym! (Session {chosen_session_id})")
            return True
        else:
            logger.warning("Booking may have failed; no success indicator found.")
            notify("⚠ Booking mungkin gagal; periksa manual.")
            return False
    except Exception as e:
        logger.error(f"Unable to book session: {e}")
        notify("❌ Gagal booking sesi.")
        return False

# =============================
# MAIN
# =============================
def main():
    notify("🔵 Auto Booking dijalankan.")
    
    driver = None
    try:
        driver = create_driver()
        if not login(driver):
            logger.error("Login failed, exiting.")
            return
        
        if perform_booking(driver):
            notify("✅ Booking selesai.")
        else:
            notify("⚠ Booking tidak berhasil.")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
        notify(f"🔥 Script error: {e}")
    
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Driver closed.")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

if __name__ == "__main__":
    main()
