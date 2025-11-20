import os
import logging
import traceback
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
        
        # Check for membership status on dashboard
        logger.info("Verifying dashboard and membership status...")
        membership_elem = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CLASS_NAME, "membership-status")))
        membership_text = membership_elem.text
        logger.info(f"Membership status: {membership_text}")
        
        # Check for expiry warning
        warning_elem = driver.find_element(By.ID, "membership-warning")
        if warning_elem.is_displayed():
            logger.warning("Membership has expired!")
            notify("⚠ Masa aktif membership telah berakhir.")
            return False
        
        logger.info("Login and dashboard verification successful.")
        notify(">> Login Success")
        return True
    except Exception as e:
        logger.error(f"Login failed: {e}")
        debug_capture(driver, "03_login_failed")
        notify(">> Login Failed, Please Check")
        return False

# =============================
# Check Sessions Function
# =============================
def check_sessions(driver):
    logger.info("Checking sessions for tomorrow...")
    
    if DASHBOARD_URL not in driver.current_url:
        driver.get(DASHBOARD_URL)
        WebDriverWait(driver, TIMEOUT).until(EC.url_contains("dashboard.php"))
    
    debug_capture(driver, "04_dashboard_loaded")
    
    notify(">> Checking session availability for today...")

        for session_id in range(1, 7):  # Sessions 1 to 6
            try:
                slot = driver.find_element(By.CSS_SELECTOR, f".session-slot[data-session-id='{session_id}']")
                quota_elem = slot.find_element(By.CLASS_NAME, "session-quota")
                quota_text = quota_elem.text  # e.g., "Kuota: 21/30"
                
                # Check status: If quota is 30/30, mark as Unavailable; else check for Full or Available
                if "30/30" in quota_text:
                    status = "Unavailable"
                else:
                    is_full = "full" in slot.get_attribute("class") or "Penuh" in slot.find_element(By.TAG_NAME, "button").text
                    status = "Full" if is_full else "Available"
                
                logger.info(f"{date.capitalize()} - Session {session_id}: {status} ({quota_text})")
                notify(f">> {date.capitalize()} - Session {session_id}: {status} ({quota_text})")
            except Exception as e:
                logger.warning(f"Could not check {date} session {session_id}: {e}")
                notify(f">> {date.capitalize()} - Session {session_id}: Unable to check")
            
    logger.info("Clicking tomorrow tab...")
    try:
        tomorrow_btn = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".date-btn[data-day='tomorrow']")))
        tomorrow_btn.click()
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".session-slot")))  # Wait for slots to load
        debug_capture(driver, "05_tomorrow_tab_clicked")
    except Exception as e:
        logger.error(f"Could not click tomorrow tab: {e}")
        notify(">> Could not click tomorrow tab")
        return
    notify(">> Checking session availability for tomorrow...")
        for session_id in range(1, 7):  # Sessions 1 to 6
            try:
                slot = driver.find_element(By.CSS_SELECTOR, f".session-slot[data-session-id='{session_id}']")
                quota_elem = slot.find_element(By.CLASS_NAME, "session-quota")
                quota_text = quota_elem.text  # e.g., "Kuota: 21/30"
                
                # Check status: If quota is 30/30, mark as Unavailable; else check for Full or Available
                if "30/30" in quota_text:
                    status = "Unavailable"
                else:
                    is_full = "full" in slot.get_attribute("class") or "Penuh" in slot.find_element(By.TAG_NAME, "button").text
                    status = "Full" if is_full else "Available"
                
                logger.info(f"{date.capitalize()} - Session {session_id}: {status} ({quota_text})")
                notify(f">> {date.capitalize()} - Session {session_id}: {status} ({quota_text})")
            except Exception as e:
                logger.warning(f"Could not check {date} session {session_id}: {e}")
                notify(f">> {date.capitalize()} - Session {session_id}: Unable to check")

            
# =============================
# MAIN
# =============================
def main():
    notify("__**>> Checking Sessions <<**__")
    
    driver = None
    try:
        driver = create_driver()
        if not login(driver):
            logger.error("Login failed, exiting.")
            return
        
        check_sessions(driver)
        notify(">> Session check complete")
    
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
