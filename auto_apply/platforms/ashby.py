"""
Ashby job application handler.
"""
import time
import re
from pathlib import Path
from playwright.sync_api import Page, BrowserContext
from form_filler import fill_text_field
from ai_responder import answer_question, is_ai_question
from cover_letter_gen import generate_cover_letter
from config import RESUME_PATH, SLOW_MO


def apply_to_ashby_job(
    page: Page,
    url: str,
    profile: dict,
    job_info: dict = None
) -> dict:
    """
    Apply to a job on Ashby (jobs.ashbyhq.com)
    """
    result = {"success": False, "message": "", "job_title": "", "url": url}
    
    try:
        # Navigate to job page
        page.goto(url, wait_until="networkidle")
        time.sleep(2)
        
        # Extract job info
        if not job_info:
            job_info = _extract_ashby_job_info(page)
        
        result["job_title"] = job_info.get("title", "Unknown Position")
        result["company"] = job_info.get("company", "Unknown Company")
        
        print(f"Applying to: {result['job_title']} at {result['company']}")
        
        # Step 1: Click on "Application" tab if it exists
        application_tab = page.locator("button:has-text('Application'), [role='tab']:has-text('Application')").first
        if application_tab.is_visible(timeout=3000):
            print("Clicking Application tab...")
            application_tab.click()
            time.sleep(2)
        
        # Step 2: Click "Apply" button if present (starts the actual form)
        apply_btn = page.locator("button:has-text('Apply'), a:has-text('Apply')").first
        if apply_btn.is_visible(timeout=2000):
            print("Clicking Apply button...")
            apply_btn.click()
            time.sleep(2)
            page.wait_for_load_state("networkidle")
        
        # Now we should be on the application form
        # Debug: print what's on the page
        print("Looking for form fields...")
        
        # Fill basic fields
        _fill_ashby_basic_fields(page, profile)
        
        # Upload resume
        _upload_ashby_resume(page)
        
        # Handle cover letter
        _handle_ashby_cover_letter(page, profile, job_info)
        
        # Handle custom questions
        _handle_ashby_questions(page, profile, job_info)
        
        # Submit
        submit_btn = page.locator("button[type='submit'], button:has-text('Submit application'), button:has-text('Submit')").first
        if submit_btn.is_visible(timeout=3000):
            print("Clicking Submit...")
            submit_btn.click()
            time.sleep(3)
            
            if _check_ashby_success(page):
                result["success"] = True
                result["message"] = "Application submitted successfully"
            else:
                result["message"] = "Submitted but could not confirm success"
        else:
            result["message"] = "Could not find submit button"
            
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
    
    return result


def _extract_ashby_job_info(page: Page) -> dict:
    """Extract job information from Ashby job page."""
    info = {"title": "", "company": "", "description": "", "location": ""}
    
    try:
        # Job title - Ashby uses various selectors
        title_elem = page.locator("h1, [data-testid='job-title']").first
        if title_elem.is_visible(timeout=1000):
            info["title"] = title_elem.text_content().strip()
        
        # Company from URL
        url = page.url
        match = re.search(r'ashbyhq\.com/([^/]+)', url)
        if match:
            info["company"] = match.group(1).replace("-", " ").replace("_", " ").title()
        
        # Location
        location_elem = page.locator("[data-testid='job-location'], .job-location").first
        if location_elem.is_visible(timeout=1000):
            info["location"] = location_elem.text_content().strip()
        
        # Description
        desc_elem = page.locator("[data-testid='job-description'], .job-description, .prose").first
        if desc_elem.is_visible(timeout=1000):
            info["description"] = desc_elem.text_content()[:3000]
            
    except Exception as e:
        print(f"Error extracting job info: {e}")
    
    return info


def _fill_ashby_basic_fields(page: Page, profile: dict):
    """Fill basic Ashby application fields."""
    # Ashby forms can vary, try multiple selectors
    field_mappings = [
        # Name fields
        ("input[name*='name' i][name*='first' i], input[placeholder*='First name' i]", profile.get("first_name", "")),
        ("input[name*='name' i][name*='last' i], input[placeholder*='Last name' i]", profile.get("last_name", "")),
        # Sometimes just one name field
        ("input[name='name'], input[placeholder='Full name' i]", f"{profile.get('first_name', '')} {profile.get('last_name', '')}"),
        # Email
        ("input[type='email'], input[name*='email' i]", profile.get("email", "")),
        # Phone
        ("input[type='tel'], input[name*='phone' i]", profile.get("phone", "")),
        # LinkedIn
        ("input[name*='linkedin' i], input[placeholder*='LinkedIn' i]", profile.get("linkedin", "")),
        # GitHub
        ("input[name*='github' i], input[placeholder*='GitHub' i]", profile.get("github", "")),
        # Location
        ("input[name*='location' i], input[placeholder*='Location' i]", profile.get("location", "")),
    ]
    
    for selector, value in field_mappings:
        if value:
            try:
                field = page.locator(selector).first
                if field.is_visible(timeout=500):
                    field.clear()
                    field.fill(value)
                    time.sleep(SLOW_MO / 1000)
            except:
                pass


def _upload_ashby_resume(page: Page):
    """Upload resume on Ashby."""
    try:
        # Ashby often has a drop zone or file input
        file_input = page.locator("input[type='file']").first
        if file_input.count() > 0:
            file_input.set_input_files(str(RESUME_PATH))
            print("Resume uploaded")
            time.sleep(1)
    except Exception as e:
        print(f"Resume upload error: {e}")


def _handle_ashby_cover_letter(page: Page, profile: dict, job_info: dict):
    """Handle cover letter on Ashby."""
    try:
        # Check for cover letter textarea
        cl_textarea = page.locator("textarea[name*='cover' i], textarea[placeholder*='cover letter' i]").first
        if cl_textarea.is_visible(timeout=1000):
            cover_letter = generate_cover_letter(
                profile=profile,
                job_title=job_info.get("title", ""),
                company_name=job_info.get("company", ""),
                job_description=job_info.get("description", ""),
                save_to_file=True
            )
            cl_textarea.fill(cover_letter)
            print("Cover letter added")
            return
    except:
        pass
    
    try:
        # Check for cover letter file upload
        cl_upload = page.locator("input[type='file'][name*='cover' i]").first
        if cl_upload.count() > 0:
            # Would need to save cover letter to file first
            pass
    except:
        pass


def _handle_ashby_questions(page: Page, profile: dict, job_info: dict):
    """Handle custom questions on Ashby application."""
    # Find all form groups / questions
    form_groups = page.locator("[data-testid='custom-question'], .form-group, .field").all()
    
    for group in form_groups:
        try:
            # Get label
            label = group.locator("label").first
            if not label.is_visible(timeout=500):
                continue
            
            question_text = label.text_content().strip()
            
            # Skip basic fields already handled
            basic_fields = ["name", "email", "phone", "resume", "first", "last"]
            if any(x in question_text.lower() for x in basic_fields):
                continue
            
            # Handle textarea (long answer)
            textarea = group.locator("textarea").first
            if textarea.is_visible(timeout=500):
                if is_ai_question(question_text):
                    answer = answer_question(question_text, profile, job_info.get("description", ""))
                    textarea.fill(answer)
                    time.sleep(SLOW_MO / 1000)
                continue
            
            # Handle text input
            text_input = group.locator("input[type='text']").first
            if text_input.is_visible(timeout=500):
                answer = _get_ashby_simple_answer(question_text, profile)
                if answer:
                    text_input.fill(answer)
                    time.sleep(SLOW_MO / 1000)
                elif is_ai_question(question_text):
                    answer = answer_question(question_text, profile, job_info.get("description", ""), max_chars=200)
                    text_input.fill(answer)
                continue
            
            # Handle select dropdown
            select = group.locator("select").first
            if select.is_visible(timeout=500):
                _handle_ashby_select(select, question_text, profile)
                continue
            
            # Handle radio buttons
            radios = group.locator("input[type='radio']").all()
            if radios:
                _handle_ashby_radio(group, question_text, profile)
                
        except Exception as e:
            continue


def _get_ashby_simple_answer(question: str, profile: dict) -> str:
    """Get simple answers for common Ashby questions."""
    q_lower = question.lower()
    
    if "linkedin" in q_lower:
        return profile.get("linkedin", "")
    if "github" in q_lower:
        return profile.get("github", "")
    if "website" in q_lower or "portfolio" in q_lower:
        return profile.get("website", "")
    if "years" in q_lower and "experience" in q_lower:
        return str(profile.get("years_experience", ""))
    if "current" in q_lower and ("company" in q_lower or "employer" in q_lower):
        experience = profile.get("work_experience", [])
        if experience:
            return experience[0].get("company", "")
    if "current" in q_lower and "title" in q_lower:
        return profile.get("current_title", "")
    
    return ""


def _handle_ashby_select(select, question: str, profile: dict):
    """Handle Ashby dropdown selections."""
    q_lower = question.lower()
    
    try:
        if "authorized" in q_lower or "legally" in q_lower:
            select.select_option(label="Yes")
        elif "sponsor" in q_lower or "visa" in q_lower:
            select.select_option(label="No")
        elif "hear" in q_lower:  # How did you hear about us
            try:
                select.select_option(label="Job Board")
            except:
                select.select_option(index=1)
    except:
        pass


def _handle_ashby_radio(group, question: str, profile: dict):
    """Handle Ashby radio button selections."""
    q_lower = question.lower()
    
    try:
        if "authorized" in q_lower:
            group.locator("label:has-text('Yes')").first.click()
        elif "sponsor" in q_lower:
            group.locator("label:has-text('No')").first.click()
        elif "18" in q_lower or "age" in q_lower:
            group.locator("label:has-text('Yes')").first.click()
    except:
        pass


def _check_ashby_success(page: Page) -> bool:
    """Check if Ashby application was successful."""
    success_indicators = [
        "thank you",
        "application received",
        "successfully submitted",
        "application submitted",
        "we've received"
    ]
    
    page_text = page.content().lower()
    return any(indicator in page_text for indicator in success_indicators)
