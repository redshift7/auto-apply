"""
Cover Letter Generator - Creates personalized cover letters using Claude.
"""
import json
import re
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, COVER_LETTERS_DIR


def get_client() -> Anthropic:
    """Get Anthropic client."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_cover_letter(
    profile: dict,
    job_title: str,
    company_name: str,
    job_description: str,
    save_to_file: bool = True
) -> str:
    """
    Generate a personalized cover letter for a specific job.
    
    Args:
        profile: Candidate profile dict
        job_title: The job title
        company_name: Name of the company
        job_description: Full job description text
        save_to_file: Whether to save the cover letter to a file
    
    Returns:
        Generated cover letter text
    """
    client = get_client()
    
    prompt = f"""Write a professional cover letter for the following job application.
The cover letter should:
- Be concise (3-4 paragraphs, under 400 words)
- Highlight relevant experience that matches the job requirements
- Show enthusiasm for the specific role and company
- Include specific accomplishments with metrics when possible
- Sound authentic, not generic or template-like
- NOT start with "I am writing to apply for..." (be more creative)

Candidate Information:
Name: {profile.get('first_name', '')} {profile.get('last_name', '')}
Email: {profile.get('email', '')}
Phone: {profile.get('phone', '')}

Current/Recent Role: {profile.get('current_title', 'N/A')}
Years of Experience: {profile.get('years_experience', 'N/A')}

Summary: {profile.get('summary', 'N/A')}

Key Skills: {_extract_skills(profile)}

Recent Experience:
{_format_experience(profile)}

Target Job:
Title: {job_title}
Company: {company_name}
Description:
{job_description[:3000]}

Write the cover letter below (body only, no header/signature - just the paragraphs):"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    cover_letter = response.content[0].text.strip()
    
    if save_to_file:
        save_cover_letter(cover_letter, company_name, job_title)
    
    return cover_letter


def _extract_skills(profile: dict) -> str:
    """Extract skills as a comma-separated string."""
    skills = profile.get('skills', {})
    all_skills = []
    
    if isinstance(skills, dict):
        for category, items in skills.items():
            if isinstance(items, list):
                all_skills.extend(items)
            elif items:
                all_skills.append(str(items))
    elif isinstance(skills, list):
        all_skills = skills
    
    return ", ".join(all_skills[:20])


def _format_experience(profile: dict) -> str:
    """Format work experience for the prompt."""
    experience = profile.get('work_experience', [])
    if not experience:
        return "N/A"
    
    lines = []
    for exp in experience[:2]:  # Only include recent 2
        title = exp.get('title', 'N/A')
        company = exp.get('company', 'N/A')
        dates = f"{exp.get('start_date', '')} - {exp.get('end_date', '')}"
        highlights = exp.get('highlights', [])
        
        lines.append(f"• {title} at {company} ({dates})")
        for h in highlights[:3]:
            lines.append(f"  - {h}")
    
    return "\n".join(lines)


def save_cover_letter(cover_letter: str, company_name: str, job_title: str) -> Path:
    """Save cover letter to a file."""
    # Create directory if needed
    COVER_LETTERS_DIR.mkdir(exist_ok=True)
    
    # Sanitize filename
    safe_company = re.sub(r'[^\w\s-]', '', company_name)[:30].strip()
    safe_title = re.sub(r'[^\w\s-]', '', job_title)[:30].strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"{safe_company}_{safe_title}_{timestamp}.txt"
    filepath = COVER_LETTERS_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"Cover Letter for {job_title} at {company_name}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(cover_letter)
    
    print(f"Cover letter saved to: {filepath}")
    return filepath


def load_cover_letter(filepath: Path) -> str:
    """Load a previously generated cover letter."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip the header lines
    lines = content.split('\n')
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("="):
            body_start = i + 2
            break
    
    return '\n'.join(lines[body_start:]).strip()


if __name__ == "__main__":
    # Test with sample data
    from config import PROFILE_PATH
    
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            profile = json.load(f)
        
        # Test cover letter generation
        sample_job = """
        Data Engineer at TechCorp
        
        We're looking for a Data Engineer to build and maintain our data infrastructure.
        
        Requirements:
        - 3+ years experience with Python and SQL
        - Experience with Apache Spark, Kafka, or similar big data tools
        - Cloud experience (AWS or Azure)
        - Bachelor's degree in Computer Science or related field
        
        Nice to have:
        - Experience with real-time data processing
        - Knowledge of data warehousing concepts
        """
        
        cover_letter = generate_cover_letter(
            profile=profile,
            job_title="Data Engineer",
            company_name="TechCorp",
            job_description=sample_job
        )
        
        print("\nGenerated Cover Letter:")
        print("-" * 50)
        print(cover_letter)
    else:
        print("Profile not found. Run resume_parser.py first.")
