"""
Job Searcher - Finds job listings from Lever, Greenhouse, and Ashby.
Now includes direct job board search to avoid Google CAPTCHAs.
"""
import time
import random
import re
from urllib.parse import quote_plus, urlparse
from playwright.sync_api import sync_playwright, Page, Browser
from config import SEARCH_QUERY, PLATFORM_PATTERNS, REQUEST_DELAY_SECONDS, CHROME_PROFILE_DIR
from captcha_handler import handle_captcha_if_present


# Known companies with data engineering roles - direct links
DIRECT_JOB_BOARDS = [
    # Lever companies
    "https://jobs.lever.co/twitch",
    "https://jobs.lever.co/stripe",
    "https://jobs.lever.co/netflix",
    "https://jobs.lever.co/reddit",
    "https://jobs.lever.co/robinhood",
    "https://jobs.lever.co/coinbase",
    "https://jobs.lever.co/square",
    "https://jobs.lever.co/lyft",
    "https://jobs.lever.co/instacart",
    "https://jobs.lever.co/dropbox",
    "https://jobs.lever.co/plaid",
    "https://jobs.lever.co/databricks",
    "https://jobs.lever.co/openai",
    "https://jobs.lever.co/anthropic",
    "https://jobs.lever.co/figma",
    # Greenhouse companies  
    "https://job-boards.greenhouse.io/doordash",
    "https://job-boards.greenhouse.io/airbnb",
    "https://job-boards.greenhouse.io/discord",
    "https://job-boards.greenhouse.io/pinterest",
    "https://job-boards.greenhouse.io/duolingo",
    "https://job-boards.greenhouse.io/spotify",
    "https://job-boards.greenhouse.io/nerdwallet",
    # Ashby companies
    "https://jobs.ashbyhq.com/notion",
    "https://jobs.ashbyhq.com/ramp",
    "https://jobs.ashbyhq.com/vercel",
    "https://jobs.ashbyhq.com/linear",
]

# Keywords to match data engineering roles
DATA_KEYWORDS = ["data engineer", "analytics engineer", "data", "engineer", "etl", "pipeline", "warehouse"]
EXCLUDE_KEYWORDS = ["senior", "staff", "lead", "principal", "manager", "director", "ii", "iii", "iv"]


def search_direct_job_boards(max_results: int = 50) -> list[dict]:
    """
    Search job boards directly without Google.
    Goes to each company's career page and finds matching roles.
    """
    jobs = []
    
    with sync_playwright() as p:
        # Use automation Chrome profile
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_PROFILE_DIR),
            headless=False,
        )
        page = browser.new_page()
        
        for board_url in DIRECT_JOB_BOARDS:
            if len(jobs) >= max_results:
                break
                
            try:
                print(f"Checking: {board_url}")
                page.goto(board_url, wait_until="networkidle", timeout=15000)
                time.sleep(1)
                
                # Handle CAPTCHA if present
                handle_captcha_if_present(page)
                
                platform = _detect_platform(board_url)
                
                # Find all job links on the page
                if platform == "lever":
                    new_jobs = _extract_lever_jobs(page, board_url)
                elif platform == "greenhouse":
                    new_jobs = _extract_greenhouse_jobs(page, board_url)
                elif platform == "ashby":
                    new_jobs = _extract_ashby_jobs(page, board_url)
                else:
                    new_jobs = []
                
                # Filter for data engineering roles
                filtered = _filter_data_roles(new_jobs)
                jobs.extend(filtered)
                print(f"  Found {len(filtered)} matching jobs")
                
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        browser.close()
    
    return jobs[:max_results]


def _extract_lever_jobs(page: Page, base_url: str) -> list[dict]:
    """Extract jobs from a Lever career page."""
    jobs = []
    
    # Lever job listings are in posting-title links
    links = page.locator("a.posting-title, a[data-qa='posting-name']").all()
    
    for link in links:
        try:
            href = link.get_attribute("href")
            title = link.text_content().strip()
            
            if href and title:
                # Make absolute URL if needed
                if not href.startswith("http"):
                    href = f"https://jobs.lever.co{href}"
                
                jobs.append({
                    "url": href,
                    "title": title,
                    "platform": "lever"
                })
        except:
            continue
    
    return jobs


def _extract_greenhouse_jobs(page: Page, base_url: str) -> list[dict]:
    """Extract jobs from a Greenhouse career page."""
    jobs = []
    
    # Greenhouse job listings
    links = page.locator("a[data-mapped='true'], .opening a, .job-post a").all()
    
    for link in links:
        try:
            href = link.get_attribute("href")
            title = link.text_content().strip()
            
            if href and title and len(title) > 3:
                if not href.startswith("http"):
                    href = f"https://job-boards.greenhouse.io{href}"
                
                jobs.append({
                    "url": href,
                    "title": title,
                    "platform": "greenhouse"
                })
        except:
            continue
    
    return jobs


def _extract_ashby_jobs(page: Page, base_url: str) -> list[dict]:
    """Extract jobs from an Ashby career page."""
    jobs = []
    
    # Ashby job listings
    links = page.locator("a[href*='/jobs/']").all()
    
    for link in links:
        try:
            href = link.get_attribute("href")
            title = link.text_content().strip()
            
            if href and title and len(title) > 3:
                if not href.startswith("http"):
                    href = f"https://jobs.ashbyhq.com{href}"
                
                jobs.append({
                    "url": href,
                    "title": title,
                    "platform": "ashby"
                })
        except:
            continue
    
    return jobs


def _filter_data_roles(jobs: list[dict]) -> list[dict]:
    """Filter jobs to only include data engineering related roles."""
    filtered = []
    
    for job in jobs:
        title_lower = job["title"].lower()
        
        # Must contain at least one data keyword
        has_keyword = any(kw in title_lower for kw in DATA_KEYWORDS)
        
        # Must not contain exclusion keywords (senior, lead, etc)
        has_exclusion = any(kw in title_lower for kw in EXCLUDE_KEYWORDS)
        
        if has_keyword and not has_exclusion:
            filtered.append(job)
    
    return filtered


def search_jobs_google(query: str = None, max_results: int = 50) -> list[dict]:
    """
    Search Google for job listings matching the query.
    
    Returns:
        List of dicts with 'url', 'title', 'platform' keys
    """
    if query is None:
        query = SEARCH_QUERY
    
    jobs = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Go to Google
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=100"
            page.goto(search_url, wait_until="networkidle")
            time.sleep(3)
            
            # Handle consent if needed (multiple variations)
            for selector in ["button:has-text('Accept all')", "button:has-text('I agree')", "button:has-text('Accept')", "#L2AGLb"]:
                try:
                    accept_btn = page.locator(selector)
                    if accept_btn.is_visible(timeout=1000):
                        accept_btn.click()
                        time.sleep(2)
                        break
                except:
                    pass
            
            # Extract search results
            page_num = 0
            while len(jobs) < max_results and page_num < 5:
                new_jobs = _extract_jobs_from_page(page)
                jobs.extend(new_jobs)
                print(f"Found {len(new_jobs)} jobs on page {page_num + 1}")
                
                # If no jobs found on first page, try alternative extraction
                if page_num == 0 and len(new_jobs) == 0:
                    new_jobs = _extract_jobs_alternative(page)
                    jobs.extend(new_jobs)
                    print(f"Found {len(new_jobs)} jobs (alternative method)")
                
                # Try to go to next page
                try:
                    next_btn = page.locator("a#pnnext")
                    if next_btn.is_visible(timeout=2000):
                        next_btn.click()
                        time.sleep(REQUEST_DELAY_SECONDS + random.uniform(1, 3))
                        page_num += 1
                    else:
                        break
                except:
                    break
            
        finally:
            browser.close()
    
    # Deduplicate by URL
    seen = set()
    unique_jobs = []
    for job in jobs:
        if job['url'] not in seen:
            seen.add(job['url'])
            unique_jobs.append(job)
    
    return unique_jobs[:max_results]


def _extract_jobs_alternative(page: Page) -> list[dict]:
    """Alternative extraction method using all links on page."""
    jobs = []
    
    # Get all links on the page
    all_links = page.locator("a[href]").all()
    
    for link in all_links:
        try:
            href = link.get_attribute("href")
            if not href:
                continue
            
            platform = _detect_platform(href)
            if platform:
                title = link.text_content() or "Unknown Position"
                title = title.strip()[:100]  # Limit title length
                if title and len(title) > 3:
                    jobs.append({
                        "url": href,
                        "title": title,
                        "platform": platform
                    })
        except:
            continue
    
    return jobs


def _extract_jobs_from_page(page: Page) -> list[dict]:
    """Extract job listings from a Google search results page."""
    jobs = []
    
    # Get all search result links
    links = page.locator("div.g a[href]").all()
    
    for link in links:
        try:
            href = link.get_attribute("href")
            if not href:
                continue
            
            # Check if it's a job board URL
            platform = _detect_platform(href)
            if platform:
                title_elem = link.locator("h3").first
                title = title_elem.text_content() if title_elem.is_visible() else "Unknown Position"
                
                jobs.append({
                    "url": href,
                    "title": title.strip() if title else "Unknown Position",
                    "platform": platform
                })
        except Exception as e:
            continue
    
    return jobs


def _detect_platform(url: str) -> str | None:
    """Detect which job platform a URL belongs to."""
    url_lower = url.lower()
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern in url_lower:
            return platform
    return None


def is_valid_job_url(url: str) -> bool:
    """Validate that a URL is a proper job posting URL."""
    if not url or not url.startswith("http"):
        return False
    
    # Must contain one of our known platforms
    if not _detect_platform(url):
        return False
    
    # Must not be a search result or relative URL
    invalid_patterns = ["/?q=", "search?", "/search", "google.com", "duckduckgo.com"]
    for pattern in invalid_patterns:
        if pattern in url.lower():
            return False
    
    return True


def search_jobs_duckduckgo(query: str = None, max_results: int = 50) -> list[dict]:
    """
    Alternative search using DuckDuckGo (less likely to be blocked).
    """
    if query is None:
        query = SEARCH_QUERY
    
    jobs = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
            page.goto(search_url, wait_until="networkidle")
            time.sleep(3)
            
            # Scroll to load more results
            for _ in range(5):
                page.keyboard.press("End")
                time.sleep(1)
            
            # Get all links and filter for job platforms
            all_links = page.locator("a[href]").all()
            
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Skip relative URLs and internal DDG links
                    if not href.startswith("http"):
                        continue
                    if "duckduckgo.com" in href:
                        continue
                    
                    platform = _detect_platform(href)
                    if platform:
                        title = link.text_content() or "Unknown Position"
                        title = title.strip()[:100]
                        if title and len(title) > 2:
                            jobs.append({
                                "url": href,
                                "title": title,
                                "platform": platform
                            })
                except:
                    continue
                    
        finally:
            browser.close()
    
    # Deduplicate
    seen = set()
    unique = []
    for job in jobs:
        if job['url'] not in seen:
            seen.add(job['url'])
            unique.append(job)
    
    return unique[:max_results]


def search_jobs_combined(query: str = None, max_results: int = 50) -> list[dict]:
    """Search using Google with Chrome profile (has your cookies)."""
    if query is None:
        query = SEARCH_QUERY
    
    jobs = []
    
    with sync_playwright() as p:
        # Use automation Chrome profile
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_PROFILE_DIR),
            headless=False,
        )
        page = browser.new_page()
        
        try:
            # Search Google
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=50"
            print(f"Searching: {search_url[:80]}...")
            page.goto(search_url, wait_until="networkidle")
            time.sleep(2)
            
            # Handle CAPTCHA if present (user solves manually)
            handle_captcha_if_present(page, timeout_minutes=3)
            
            # Extract job URLs from search results
            all_links = page.locator("a[href]").all()
            
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    if not href or not href.startswith("http"):
                        continue
                    
                    # Clean the URL (remove Google redirect)
                    if "/url?q=" in href:
                        href = href.split("/url?q=")[1].split("&")[0]
                    
                    # Validate the URL before adding
                    if not is_valid_job_url(href):
                        continue
                    
                    platform = _detect_platform(href)
                    if platform:
                        title = link.text_content() or "Unknown Position"
                        title = title.strip()[:100]
                        
                        if title and len(title) > 3:
                            jobs.append({
                                "url": href,
                                "title": title,
                                "platform": platform
                            })
                except:
                    continue
            
            print(f"Found {len(jobs)} jobs from Google search")
            
            # If no jobs from Google, try direct boards
            if len(jobs) < 5:
                print("Trying direct job boards...")
                for board_url in DIRECT_JOB_BOARDS[:10]:
                    if len(jobs) >= max_results:
                        break
                    try:
                        page.goto(board_url, wait_until="networkidle", timeout=10000)
                        time.sleep(1)
                        handle_captcha_if_present(page)
                        
                        platform = _detect_platform(board_url)
                        if platform == "lever":
                            new_jobs = _extract_lever_jobs(page, board_url)
                        elif platform == "greenhouse":
                            new_jobs = _extract_greenhouse_jobs(page, board_url)
                        elif platform == "ashby":
                            new_jobs = _extract_ashby_jobs(page, board_url)
                        else:
                            new_jobs = []
                        
                        filtered = _filter_data_roles(new_jobs)
                        jobs.extend(filtered)
                    except:
                        continue
                        
        finally:
            browser.close()
    
    # Deduplicate
    seen = set()
    unique = []
    for job in jobs:
        if job['url'] not in seen:
            seen.add(job['url'])
            unique.append(job)
    
    return unique[:max_results]


def categorize_jobs_by_platform(jobs: list[dict]) -> dict[str, list[dict]]:
    """Group jobs by their platform."""
    categorized = {"lever": [], "greenhouse": [], "ashby": []}
    
    for job in jobs:
        platform = job.get("platform")
        if platform in categorized:
            categorized[platform].append(job)
    
    return categorized


def filter_applied_jobs(jobs: list[dict], applied_urls: set[str]) -> list[dict]:
    """Filter out jobs that have already been applied to."""
    return [job for job in jobs if job["url"] not in applied_urls]


if __name__ == "__main__":
    print("Searching for jobs...")
    jobs = search_jobs_google(max_results=20)
    
    print(f"\nFound {len(jobs)} jobs:")
    for i, job in enumerate(jobs, 1):
        print(f"{i}. [{job['platform']}] {job['title']}")
        print(f"   {job['url']}\n")
    
    categorized = categorize_jobs_by_platform(jobs)
    print("\nBy platform:")
    for platform, platform_jobs in categorized.items():
        print(f"  {platform}: {len(platform_jobs)} jobs")
