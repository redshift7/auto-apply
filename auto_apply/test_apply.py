"""
Quick test - Apply directly to a specific job URL.
Usage: python test_apply.py <job_url>
"""
import sys
import json
from playwright.sync_api import sync_playwright
from config import PROFILE_PATH, CHROME_PROFILE_DIR, ANTHROPIC_API_KEY
import os

os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY or ""

from platforms.lever import apply_to_lever_job
from platforms.greenhouse import apply_to_greenhouse_job
from platforms.ashby import apply_to_ashby_job


def detect_platform(url: str) -> str:
    if "lever.co" in url:
        return "lever"
    elif "greenhouse.io" in url:
        return "greenhouse"
    elif "ashbyhq.com" in url:
        return "ashby"
    return None


def test_apply(url: str):
    """Test applying to a single job."""
    # Load profile
    with open(PROFILE_PATH) as f:
        profile = json.load(f)
    
    print(f"Testing application to: {url}")
    print(f"Candidate: {profile.get('first_name')} {profile.get('last_name')}")
    print("-" * 50)
    
    platform = detect_platform(url)
    if not platform:
        print("Error: Unknown platform. URL must be from Lever, Greenhouse, or Ashby.")
        return
    
    print(f"Platform: {platform}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_PROFILE_DIR),
            headless=False,
            slow_mo=150,
        )
        page = browser.new_page()
        
        try:
            if platform == "lever":
                result = apply_to_lever_job(page, url, profile)
            elif platform == "greenhouse":
                result = apply_to_greenhouse_job(page, url, profile)
            elif platform == "ashby":
                result = apply_to_ashby_job(page, url, profile)
            
            print("\n" + "=" * 50)
            print("RESULT:")
            print(f"  Success: {result['success']}")
            print(f"  Job: {result.get('job_title', 'N/A')}")
            print(f"  Company: {result.get('company', 'N/A')}")
            print(f"  Message: {result['message']}")
            print("=" * 50)
            
            # Keep browser open for review
            input("\nPress Enter to close browser...")
            
        finally:
            browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_apply.py <job_url>")
        print("\nExample URLs:")
        print("  https://jobs.lever.co/openai/...")
        print("  https://job-boards.greenhouse.io/discord/...")
        print("  https://jobs.ashbyhq.com/notion/...")
        sys.exit(1)
    
    test_apply(sys.argv[1])
