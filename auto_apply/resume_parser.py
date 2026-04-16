"""
Resume parser - Extracts structured data from PDF resume using PyMuPDF and Claude.
"""
import fitz
import json
import re
from pathlib import Path
from anthropic import Anthropic
from config import RESUME_PATH, PROFILE_PATH, ANTHROPIC_API_KEY


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def parse_resume_with_ai(resume_text: str) -> dict:
    """Use Claude to parse resume text into structured JSON."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Parse the following resume and extract structured information. Return ONLY valid JSON with no additional text.

Resume:
{resume_text}

Return JSON with this exact structure:
{{
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "phone": "string",
    "linkedin": "string or null",
    "github": "string or null",
    "website": "string or null",
    "location": "string",
    "summary": "1-2 sentence professional summary",
    "current_title": "string",
    "years_experience": number,
    "education": [
        {{
            "degree": "string",
            "field": "string",
            "school": "string",
            "location": "string",
            "graduation_date": "string",
            "gpa": "string or null"
        }}
    ],
    "work_experience": [
        {{
            "title": "string",
            "company": "string",
            "location": "string",
            "start_date": "string",
            "end_date": "string or Present",
            "highlights": ["string"]
        }}
    ],
    "skills": {{
        "programming_languages": ["string"],
        "frameworks": ["string"],
        "databases": ["string"],
        "cloud_platforms": ["string"],
        "tools": ["string"]
    }},
    "projects": [
        {{
            "name": "string",
            "technologies": ["string"],
            "description": "string",
            "date": "string"
        }}
    ],
    "certifications": ["string"],
    "work_authorization": "string or null",
    "requires_sponsorship": null
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Extract JSON from response
    response_text = response.content[0].text.strip()
    
    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
        response_text = re.sub(r'\n?```$', '', response_text)
    
    return json.loads(response_text)


def parse_resume_basic(resume_text: str) -> dict:
    """Basic regex-based parsing as fallback if AI is unavailable."""
    profile = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "linkedin": None,
        "github": None,
        "website": None,
        "location": "",
        "summary": "",
        "skills": {},
    }
    
    # Extract email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
    if email_match:
        profile["email"] = email_match.group()
    
    # Extract phone
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text)
    if phone_match:
        profile["phone"] = phone_match.group()
    
    # Extract LinkedIn
    linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', resume_text, re.I)
    if linkedin_match:
        profile["linkedin"] = "https://www." + linkedin_match.group()
    
    # Extract GitHub
    github_match = re.search(r'github\.com/[\w-]+', resume_text, re.I)
    if github_match:
        profile["github"] = "https://" + github_match.group()
    
    # Extract name (usually first line)
    lines = resume_text.strip().split('\n')
    if lines:
        name_parts = lines[0].strip().split()
        if len(name_parts) >= 2:
            profile["first_name"] = name_parts[0]
            profile["last_name"] = " ".join(name_parts[1:])
    
    return profile


def load_or_parse_resume(force_reparse: bool = False) -> dict:
    """Load profile from cache or parse resume if needed."""
    if PROFILE_PATH.exists() and not force_reparse:
        with open(PROFILE_PATH, 'r') as f:
            return json.load(f)
    
    print(f"Parsing resume from {RESUME_PATH}...")
    resume_text = extract_text_from_pdf(RESUME_PATH)
    
    if ANTHROPIC_API_KEY:
        try:
            profile = parse_resume_with_ai(resume_text)
            print("Successfully parsed resume with AI")
        except Exception as e:
            print(f"AI parsing failed: {e}, falling back to basic parsing")
            profile = parse_resume_basic(resume_text)
    else:
        print("No API key found, using basic parsing")
        profile = parse_resume_basic(resume_text)
    
    # Save to cache
    with open(PROFILE_PATH, 'w') as f:
        json.dump(profile, f, indent=2)
    
    print(f"Profile saved to {PROFILE_PATH}")
    return profile


if __name__ == "__main__":
    profile = load_or_parse_resume(force_reparse=True)
    print(json.dumps(profile, indent=2))
