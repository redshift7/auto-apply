"""
Lever.co job application handler.
"""
import time
import re
from pathlib import Path
from playwright.sync_api import Page, BrowserContext
from form_filler import fill_text_field, upload_file, find_submit_button
from ai_responder import answer_question, is_ai_question
from cover_letter_gen import generate_cover_letter
from captcha_handler import handle_captcha_if_present
from config import RESUME_PATH, SLOW_MO


def _wait_for_new_tab(context: BrowserContext, current_pages: int, timeout: int = 5) -> Page | None:
    """Wait for a new tab to open and return it."""
    start = time.time()
    while time.time() - start < timeout:
        if len(context.pages) > current_pages:
            return context.pages[-1]
        time.sleep(0.3)
    return None


def apply_to_lever_job(
    page: Page,
    url: str,
    profile: dict,
    job_info: dict = None
) -> dict:
    """
    Apply to a job on Lever.co
    
    Args:
        page: Playwright page object
        url: Lever job URL
        profile: Candidate profile dict
        job_info: Optional job info (title, company, description)
    
    Returns:
        dict with 'success', 'message', and 'job_title'
    """
    result = {"success": False, "message": "", "job_title": "", "url": url}
    context = page.context
    application_page = page
    
    try:
        # Navigate to job page
        page.goto(url, wait_until="networkidle")
        time.sleep(2)
        
        # Check for CAPTCHA
        if not handle_captcha_if_present(page):
            result["message"] = "CAPTCHA timeout"
            return result
        
        # Extract job info if not provided
        if not job_info:
            job_info = _extract_lever_job_info(page)
        
        result["job_title"] = job_info.get("title", "Unknown Position")
        result["company"] = job_info.get("company", "Unknown Company")
        
        print(f"Applying to: {result['job_title']} at {result['company']}")
        
        # Click Apply button to open application form - may open new tab
        apply_btn = page.locator("a.postings-btn, a:has-text('Apply for this job'), a:has-text('Apply')").first
        if apply_btn.is_visible(timeout=3000):
            current_pages = len(context.pages)
            apply_btn.click()
            time.sleep(2)
            
            # Check if a new tab opened
            new_tab = _wait_for_new_tab(context, current_pages)
            if new_tab:
                print("Application form opened in new tab")
                application_page = new_tab
                application_page.wait_for_load_state("networkidle")
                time.sleep(1)
                
                # Check for CAPTCHA in new tab
                if not handle_captcha_if_present(application_page):
                    result["message"] = "CAPTCHA timeout on application page"
                    return result
        
        # Fill basic fields
        _fill_lever_basic_fields(application_page, profile)
        
        # Upload resume
        _upload_lever_resume(application_page)
        
        # Handle additional questions
        _handle_lever_questions(application_page, profile, job_info)
        
        # Generate and add cover letter if field exists
        _add_lever_cover_letter(application_page, profile, job_info)
        
        # Submit application
        submit_btn = application_page.locator("button:has-text('Submit application'), button:has-text('Submit'), button[type='submit']").first
        if submit_btn.is_visible(timeout=3000):
            submit_btn.click()
            time.sleep(3)
            
            # Check for CAPTCHA after submit
            if not handle_captcha_if_present(application_page):
                result["message"] = "CAPTCHA timeout after submit"
                return result
            
            # Check for success
            if _check_lever_success(application_page):
                result["success"] = True
                result["message"] = "Application submitted successfully"
            else:
                result["message"] = "Submitted but could not confirm success"
        else:
            result["message"] = "Could not find submit button"
            
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
    finally:
        # Close the application tab if it was opened separately
        if application_page != page:
            try:
                application_page.close()
            except:
                pass
    
    return result


def _extract_lever_job_info(page: Page) -> dict:
    """Extract job information from Lever job page."""
    info = {"title": "", "company": "", "description": "", "location": ""}
    
    try:
        # Job title
        title_elem = page.locator("h2.posting-headline, h1.posting-headline").first
        if title_elem.is_visible(timeout=1000):
            info["title"] = title_elem.text_content().strip()
        
        # Company name (from URL or page)
        url = page.url
        match = re.search(r'jobs\.lever\.co/([^/]+)', url)
        if match:
            info["company"] = match.group(1).replace("-", " ").title()
        
        # Location
        location_elem = page.locator(".location, .posting-categories .location").first
        if location_elem.is_visible(timeout=1000):
            info["location"] = location_elem.text_content().strip()
        
        # Job description
        desc_elem = page.locator(".section-wrapper.page-full-width, .posting-description").first
        if desc_elem.is_visible(timeout=1000):
            info["description"] = desc_elem.text_content()[:3000]
            
    except Exception as e:
        print(f"Error extracting job info: {e}")
    
    return info


def _fill_lever_basic_fields(page: Page, profile: dict):
    """Fill basic application fields on Lever."""
    field_mappings = [
        ("input[name='name']", f"{profile.get('first_name', '')} {profile.get('last_name', '')}"),
        ("input[name='email']", profile.get("email", "")),
        ("input[name='phone']", profile.get("phone", "")),
        ("input[name='urls[LinkedIn]'], input[placeholder*='LinkedIn' i]", profile.get("linkedin", "")),
        ("input[name='urls[GitHub]'], input[placeholder*='GitHub' i]", profile.get("github", "")),
        ("input[name='urls[Portfolio]'], input[placeholder*='Portfolio' i], input[placeholder*='Website' i]", profile.get("website", "")),
        ("input[name='location'], input[placeholder*='Location' i]", profile.get("location", "")),
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


def _upload_lever_resume(page: Page):
    """Upload resume on Lever."""
    try:
        file_input = page.locator("input[type='file'][name='resume']").first
        if file_input.count() > 0:
            file_input.set_input_files(str(RESUME_PATH))
            print("Resume uploaded")
            time.sleep(1)
    except Exception as e:
        print(f"Resume upload error: {e}")


def _handle_lever_questions(page: Page, profile: dict, job_info: dict):
    """Handle additional questions on Lever application."""
    # Find all question containers
    questions = page.locator(".application-question").all()
    
    for q_container in questions:
        try:
            # Get question text
            label = q_container.locator("label, .field-label").first
            if not label.is_visible(timeout=500):
                continue
                
            question_text = label.text_content().strip()
            
            # Check for textarea (long answer)
            textarea = q_container.locator("textarea").first
            if textarea.is_visible(timeout=500):
                if is_ai_question(question_text):
                    answer = answer_question(question_text, profile, job_info.get("description", ""))
                    textarea.fill(answer)
                    time.sleep(SLOW_MO / 1000)
                continue
            
            # Check for text input
            text_input = q_container.locator("input[type='text']").first
            if text_input.is_visible(timeout=500):
                # Try to answer with profile data or AI
                answer = _get_simple_answer(question_text, profile)
                if answer:
                    text_input.fill(answer)
                    time.sleep(SLOW_MO / 1000)
                continue
            
            # Check for select dropdown
            select = q_container.locator("select").first
            if select.is_visible(timeout=500):
                _handle_lever_select(select, question_text, profile)
                continue
            
            # Check for radio buttons
            radios = q_container.locator("input[type='radio']").all()
            if radios:
                _handle_lever_radio(q_container, question_text, profile)
                
        except Exception as e:
            print(f"Error handling question: {e}")
            continue


def _get_simple_answer(question: str, profile: dict) -> str:
    """Get a simple answer for common questions."""
    q_lower = question.lower()
    
    if "linkedin" in q_lower:
        return profile.get("linkedin", "")
    if "github" in q_lower:
        return profile.get("github", "")
    if "website" in q_lower or "portfolio" in q_lower:
        return profile.get("website", "")
    if "phone" in q_lower:
        return profile.get("phone", "")
    if "email" in q_lower:
        return profile.get("email", "")
    if "location" in q_lower or "city" in q_lower:
        return profile.get("location", "")
    if "years" in q_lower and "experience" in q_lower:
        return str(profile.get("years_experience", ""))
    
    return ""


def _handle_lever_select(select: any, question: str, profile: dict):
    """Handle dropdown selection."""
    q_lower = question.lower()
    
    # Work authorization
    if "authorized" in q_lower or "work" in q_lower and "us" in q_lower:
        try:
            select.select_option(label="Yes")
        except:
            pass
        return
    
    # Sponsorship
    if "sponsor" in q_lower:
        try:
            select.select_option(label="No")
        except:
            pass
        return


def _handle_lever_radio(container: any, question: str, profile: dict):
    """Handle radio button selection."""
    q_lower = question.lower()
    
    # Common yes/no questions
    if "authorized" in q_lower:
        try:
            container.locator("label:has-text('Yes')").first.click()
        except:
            pass
        return
    
    if "sponsor" in q_lower:
        try:
            container.locator("label:has-text('No')").first.click()
        except:
            pass
        return


def _add_lever_cover_letter(page: Page, profile: dict, job_info: dict):
    """Add cover letter if field exists."""
    try:
        # Check for cover letter textarea
        cl_field = page.locator("textarea[name*='cover'], textarea[placeholder*='cover letter' i]").first
        if cl_field.is_visible(timeout=1000):
            cover_letter = generate_cover_letter(
                profile=profile,
                job_title=job_info.get("title", ""),
                company_name=job_info.get("company", ""),
                job_description=job_info.get("description", ""),
                save_to_file=True
            )
            cl_field.fill(cover_letter)
            print("Cover letter added")
    except:
        pass
    
    # Check for cover letter file upload
    try:
        cl_upload = page.locator("input[type='file'][name*='cover']").first
        if cl_upload.is_visible(timeout=1000):
            # TODO: Generate PDF cover letter and upload
            pass
    except:
        pass


def _check_lever_success(page: Page) -> bool:
    """Check if application was submitted successfully."""
    success_indicators = [
        "thank you",
        "application received",
        "successfully submitted",
        "we've received your application"
    ]
    
    page_text = page.content().lower()
    return any(indicator in page_text for indicator in success_indicators)
