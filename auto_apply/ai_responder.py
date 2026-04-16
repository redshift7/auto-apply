"""
AI Responder - Uses Claude to answer custom application questions.
"""
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, AI_QUESTION_KEYWORDS


client = None


def get_client() -> Anthropic:
    """Get or create Anthropic client."""
    global client
    if client is None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return client


def is_ai_question(question: str) -> bool:
    """Determine if a question should be answered by AI."""
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in AI_QUESTION_KEYWORDS)


def answer_question(question: str, profile: dict, job_description: str = "", max_chars: int = None) -> str:
    """
    Use Claude to generate an answer to an application question.
    
    Args:
        question: The question to answer
        profile: Candidate profile dict
        job_description: Optional job description for context
        max_chars: Optional character limit for the answer
    
    Returns:
        Generated answer string
    """
    client = get_client()
    
    char_limit_instruction = ""
    if max_chars:
        char_limit_instruction = f"\n\nIMPORTANT: Keep your response under {max_chars} characters."
    
    prompt = f"""You are helping a job candidate answer an application question. 
Write a compelling, authentic response in first person that highlights relevant experience.
Be specific and concise. Don't be generic or use filler phrases.

Candidate Profile:
{_format_profile_for_prompt(profile)}

{"Job Description:" + chr(10) + job_description if job_description else ""}

Question: {question}
{char_limit_instruction}

Write the answer directly without any preamble:"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text.strip()


def _format_profile_for_prompt(profile: dict) -> str:
    """Format profile dict into readable text for the prompt."""
    parts = []
    
    name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
    if name:
        parts.append(f"Name: {name}")
    
    if profile.get('current_title'):
        parts.append(f"Current Title: {profile['current_title']}")
    
    if profile.get('summary'):
        parts.append(f"Summary: {profile['summary']}")
    
    if profile.get('years_experience'):
        parts.append(f"Years of Experience: {profile['years_experience']}")
    
    # Education
    if profile.get('education'):
        edu_lines = ["Education:"]
        for edu in profile['education']:
            edu_lines.append(f"  - {edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('school', '')} ({edu.get('graduation_date', '')})")
        parts.append("\n".join(edu_lines))
    
    # Work Experience
    if profile.get('work_experience'):
        exp_lines = ["Work Experience:"]
        for exp in profile['work_experience'][:3]:  # Limit to recent 3
            exp_lines.append(f"  - {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('start_date', '')} - {exp.get('end_date', '')})")
            for highlight in exp.get('highlights', [])[:2]:  # Limit highlights
                exp_lines.append(f"    • {highlight}")
        parts.append("\n".join(exp_lines))
    
    # Skills
    if profile.get('skills'):
        skills = profile['skills']
        skill_items = []
        for category, items in skills.items():
            if items:
                skill_items.extend(items if isinstance(items, list) else [items])
        if skill_items:
            parts.append(f"Skills: {', '.join(skill_items[:15])}")  # Limit skills
    
    # Projects
    if profile.get('projects'):
        proj_lines = ["Projects:"]
        for proj in profile['projects'][:2]:
            proj_lines.append(f"  - {proj.get('name', '')}: {proj.get('description', '')}")
        parts.append("\n".join(proj_lines))
    
    return "\n\n".join(parts)


def generate_short_answer(question: str, profile: dict, job_description: str = "") -> str:
    """Generate a short answer (1-2 sentences) for simpler questions."""
    return answer_question(question, profile, job_description, max_chars=200)


def generate_long_answer(question: str, profile: dict, job_description: str = "") -> str:
    """Generate a longer answer (2-3 paragraphs) for essay-style questions."""
    return answer_question(question, profile, job_description, max_chars=1500)


if __name__ == "__main__":
    # Test with sample question
    import json
    from config import PROFILE_PATH
    
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            profile = json.load(f)
        
        test_question = "Why are you interested in this data engineering position?"
        answer = answer_question(test_question, profile)
        print(f"Q: {test_question}\n\nA: {answer}")
    else:
        print("Profile not found. Run resume_parser.py first.")
