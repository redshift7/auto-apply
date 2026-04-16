"""
Auto Apply - Main orchestrator for automated job applications.

Usage:
    python main.py                    # Search and apply to jobs
    python main.py --search-only      # Only search, don't apply
    python main.py --max 10           # Limit to 10 applications
    python main.py --headless         # Run in headless mode
"""
import argparse
import time
import json
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright

from config import (
    PROFILE_PATH, HEADLESS, MAX_APPLICATIONS_PER_RUN,
    REQUEST_DELAY_SECONDS, ANTHROPIC_API_KEY,
    CHROME_PROFILE_DIR
)
from job_searcher import search_jobs_google, search_jobs_combined, categorize_jobs_by_platform
from tracker import (
    is_already_applied, record_application, get_applied_urls,
    print_summary
)
from platforms.lever import apply_to_lever_job
from platforms.greenhouse import apply_to_greenhouse_job
from platforms.ashby import apply_to_ashby_job


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_apply.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_profile() -> dict:
    """Load the candidate profile."""
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Profile not found at {PROFILE_PATH}. "
            "Run 'python resume_parser.py' first."
        )
    
    with open(PROFILE_PATH, 'r') as f:
        return json.load(f)


def apply_to_job(page, job: dict, profile: dict) -> dict:
    """Apply to a single job based on its platform."""
    platform = job["platform"]
    url = job["url"]
    
    if platform == "lever":
        return apply_to_lever_job(page, url, profile)
    elif platform == "greenhouse":
        return apply_to_greenhouse_job(page, url, profile)
    elif platform == "ashby":
        return apply_to_ashby_job(page, url, profile)
    else:
        return {"success": False, "message": f"Unknown platform: {platform}"}


def run_auto_apply(
    max_applications: int = MAX_APPLICATIONS_PER_RUN,
    headless: bool = HEADLESS,
    search_only: bool = False,
    custom_query: str = None
):
    """
    Main function to search and apply to jobs.
    
    Args:
        max_applications: Maximum number of applications to submit
        headless: Whether to run browser in headless mode
        search_only: If True, only search without applying
        custom_query: Optional custom search query
    """
    logger.info("=" * 60)
    logger.info("AUTO APPLY - Starting job application automation")
    logger.info("=" * 60)
    
    # Validate API key
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set. AI features will be limited.")
    
    # Load profile
    try:
        profile = load_profile()
        logger.info(f"Loaded profile for: {profile.get('first_name', '')} {profile.get('last_name', '')}")
    except FileNotFoundError as e:
        logger.error(str(e))
        return
    
    # Search for jobs
    logger.info("Searching for jobs...")
    jobs = search_jobs_combined(query=custom_query, max_results=max_applications * 2)
    logger.info(f"Found {len(jobs)} job listings")
    
    if not jobs:
        logger.warning("No jobs found. Try adjusting your search query.")
        return
    
    # Categorize by platform
    by_platform = categorize_jobs_by_platform(jobs)
    for platform, platform_jobs in by_platform.items():
        logger.info(f"  {platform.capitalize()}: {len(platform_jobs)} jobs")
    
    # Filter out already applied
    applied_urls = get_applied_urls()
    new_jobs = [j for j in jobs if j["url"] not in applied_urls]
    logger.info(f"New jobs to apply: {len(new_jobs)} (filtered {len(jobs) - len(new_jobs)} already applied)")
    
    if search_only:
        logger.info("\n--- SEARCH ONLY MODE ---")
        print("\nJobs found:")
        for i, job in enumerate(new_jobs[:max_applications], 1):
            print(f"{i}. [{job['platform']}] {job['title']}")
            print(f"   {job['url']}\n")
        return
    
    if not new_jobs:
        logger.info("No new jobs to apply to.")
        return
    
    # Apply to jobs
    applications_made = 0
    
    with sync_playwright() as p:
        # Use separate Chrome profile for automation
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_PROFILE_DIR),
            headless=headless,
            slow_mo=100,
        )
        page = browser.new_page()
        
        for job in new_jobs:
            if applications_made >= max_applications:
                logger.info(f"Reached max applications limit ({max_applications})")
                break
            
            url = job["url"]
            
            # Skip if already applied (double check)
            if is_already_applied(url):
                continue
            
            logger.info(f"\n--- Applying to: {job['title']} ---")
            logger.info(f"Platform: {job['platform']}")
            logger.info(f"URL: {url}")
            
            try:
                result = apply_to_job(page, job, profile)
                
                record_application(
                    url=url,
                    job_title=result.get("job_title", job["title"]),
                    company=result.get("company", "Unknown"),
                    platform=job["platform"],
                    success=result["success"],
                    message=result["message"]
                )
                
                applications_made += 1
                
                if result["success"]:
                    logger.info(f"✓ Successfully applied!")
                else:
                    logger.warning(f"✗ Application failed: {result['message']}")
                
            except Exception as e:
                logger.error(f"Error applying to job: {e}")
                record_application(
                    url=url,
                    job_title=job["title"],
                    company="Unknown",
                    platform=job["platform"],
                    success=False,
                    message=f"Error: {str(e)}"
                )
            
            # Delay between applications
            if applications_made < max_applications:
                logger.info(f"Waiting {REQUEST_DELAY_SECONDS}s before next application...")
                time.sleep(REQUEST_DELAY_SECONDS)
        
        browser.close()
    
    # Print summary
    print_summary()


def main():
    parser = argparse.ArgumentParser(
        description="Auto Apply - Automated job application tool"
    )
    parser.add_argument(
        "--max", "-m",
        type=int,
        default=MAX_APPLICATIONS_PER_RUN,
        help=f"Maximum number of applications (default: {MAX_APPLICATIONS_PER_RUN})"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--search-only", "-s",
        action="store_true",
        help="Only search for jobs, don't apply"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Custom search query (overrides default)"
    )
    parser.add_argument(
        "--parse-resume",
        action="store_true",
        help="Re-parse resume before applying"
    )
    
    args = parser.parse_args()
    
    # Optionally re-parse resume
    if args.parse_resume:
        from resume_parser import load_or_parse_resume
        load_or_parse_resume(force_reparse=True)
    
    run_auto_apply(
        max_applications=args.max,
        headless=args.headless,
        search_only=args.search_only,
        custom_query=args.query
    )


if __name__ == "__main__":
    main()
