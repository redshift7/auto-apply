"""
Configuration and constants for the auto-apply tool.
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
RESUME_PATH = Path(r"[PATH_TO_YOUR_RESUME]")
PROFILE_PATH = BASE_DIR / "profile.json"
APPLIED_JOBS_PATH = BASE_DIR / "applied_jobs.json"
COVER_LETTERS_DIR = BASE_DIR / "cover_letters"

# Chrome Profile - Separate profile for automation (to avoid conflicts)
CHROME_PROFILE_DIR = Path(__file__).parent / "chrome_profile"

# API Keys
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Search Configuration
SEARCH_QUERY = '(site:jobs.lever.co OR site:job-boards.greenhouse.io OR site:jobs.ashbyhq.com) intitle:"data engineer" OR "analytics engineer" OR "data engineer intern" -senior -staff -lead -II -III -principal'

# Platform URL patterns
PLATFORM_PATTERNS = {
    "lever": "jobs.lever.co",
    "greenhouse": "job-boards.greenhouse.io",
    "ashby": "jobs.ashbyhq.com"
}

# Browser settings
HEADLESS = False  # Set to True for background operation
SLOW_MO = 100  # Milliseconds between actions (helps avoid detection)

# Application limits
MAX_APPLICATIONS_PER_RUN = 50
REQUEST_DELAY_SECONDS = 2  # Delay between applications

# Field mappings for common form fields
COMMON_FIELD_MAPPINGS = {
    "first_name": ["first name", "firstname", "first_name", "given name"],
    "last_name": ["last name", "lastname", "last_name", "surname", "family name"],
    "email": ["email", "e-mail", "email address"],
    "phone": ["phone", "telephone", "phone number", "mobile", "cell"],
    "linkedin": ["linkedin", "linkedin url", "linkedin profile"],
    "github": ["github", "github url", "github profile"],
    "website": ["website", "portfolio", "personal website", "url"],
    "location": ["location", "city", "address", "current location"],
    "resume": ["resume", "cv", "curriculum vitae"],
    "cover_letter": ["cover letter", "cover_letter", "coverletter"],
}

# Questions that should use AI (partial matches)
AI_QUESTION_KEYWORDS = [
    "why do you want",
    "tell us about",
    "describe",
    "what interests you",
    "why are you",
    "what makes you",
    "how would you",
    "what experience",
    "elaborate",
    "explain",
    "additional information",
    "anything else",
    "cover letter",
]
