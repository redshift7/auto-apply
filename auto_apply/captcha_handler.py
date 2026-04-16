"""
CAPTCHA Handler - Detects CAPTCHAs and waits for manual solving.
"""
import time
from playwright.sync_api import Page


def detect_captcha(page: Page) -> bool:
    """Check if page has a CAPTCHA challenge - only real CAPTCHA elements."""
    try:
        # Only check for actual CAPTCHA iframe/elements, NOT text content
        # Text-based detection causes too many false positives
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
            "iframe[src*='captcha']",
            ".g-recaptcha",
            ".h-captcha",
            "[data-sitekey]",
            "#cf-turnstile",
            ".cf-turnstile",
            # Cloudflare challenge page
            "#challenge-running",
            "#challenge-stage",
        ]
        
        for selector in captcha_selectors:
            try:
                elem = page.locator(selector)
                if elem.count() > 0 and elem.first.is_visible(timeout=500):
                    return True
            except:
                pass
        
        # Check for Cloudflare challenge page specifically
        if "challenges.cloudflare.com" in page.url:
            return True
        
        # Check for challenge text only if it's a dedicated challenge page
        page_title = page.title().lower()
        if "just a moment" in page_title or "security check" in page_title:
            return True
        
        return False
        
    except Exception as e:
        return False


def play_alert_sound():
    """Play a beep to alert the user about CAPTCHA."""
    try:
        import winsound
        winsound.Beep(1000, 500)
        winsound.Beep(1200, 300)
    except:
        print("\a")


def wait_for_captcha_solved(page: Page, timeout_minutes: int = 5) -> bool:
    """
    Wait for user to manually solve CAPTCHA.
    Returns True if CAPTCHA was solved, False if timeout.
    """
    play_alert_sound()
    
    print("\n" + "=" * 50)
    print("⚠️  CAPTCHA DETECTED!")
    print("=" * 50)
    print("Please solve the CAPTCHA in the browser window.")
    print(f"Waiting up to {timeout_minutes} minutes...")
    print("=" * 50 + "\n")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    check_interval = 2
    
    while time.time() - start_time < timeout_seconds:
        time.sleep(check_interval)
        
        if not detect_captcha(page):
            print("✓ CAPTCHA solved! Continuing...")
            time.sleep(1)
            return True
        
        elapsed = int(time.time() - start_time)
        if elapsed % 30 == 0 and elapsed > 0:
            remaining = timeout_seconds - elapsed
            print(f"  Still waiting... ({remaining}s remaining)")
    
    print("✗ CAPTCHA timeout - skipping this job")
    return False


def handle_captcha_if_present(page: Page, timeout_minutes: int = 3) -> bool:
    """
    Check for CAPTCHA and handle it.
    Returns True if no CAPTCHA or CAPTCHA was solved.
    Returns False if CAPTCHA timeout.
    """
    if detect_captcha(page):
        return wait_for_captcha_solved(page, timeout_minutes)
    return True
