"""
Greenhouse job application handler.
"""
import time
import re
from pathlib import Path
from playwright.sync_api import Page, BrowserContext, FrameLocator
from form_filler import fill_text_field
from ai_responder import answer_question, is_ai_question
from cover_letter_gen import generate_cover_letter
from puzzle_solver import handle_puzzle_if_present
from config import RESUME_PATH, SLOW_MO


def _get_application_frame(page: Page) -> Page | FrameLocator:
    """
    Get the correct frame for the application form.
    Greenhouse jobs are often embedded in iframes, but sometimes the form
    is on the main page even if an iframe exists.
    """
    # First, check if form fields are on the main page
    # If they are, use the main page regardless of iframes
    main_page_fields = page.locator("#first_name, #email, input[id='first_name']").first
    try:
        if main_page_fields.is_visible(timeout=1000):
            print("Form fields found on main page")
            return page
    except:
        pass
    
    # Check for Greenhouse iframe
    iframe_selectors = [
        "iframe[src*='greenhouse']",
        "iframe[src*='boards.greenhouse.io']",
        "iframe#grnhse_iframe",
        "iframe[id*='greenhouse']",
    ]
    
    for selector in iframe_selectors:
        try:
            iframe = page.frame_locator(selector)
            # Test if iframe has actual form content
            test = iframe.locator("#first_name, #email, input[type='text']")
            if test.count() > 0:
                print(f"Found Greenhouse iframe with form: {selector}")
                return iframe
        except:
            continue
    
    # No iframe with form found, return the page itself
    return page


def apply_to_greenhouse_job(
    page: Page,
    url: str,
    profile: dict,
    job_info: dict = None
) -> dict:
    """
    Apply to a job on Greenhouse (job-boards.greenhouse.io)
    """
    result = {"success": False, "message": "", "job_title": "", "url": url}
    
    try:
        # Navigate to job page
        page.goto(url, wait_until="networkidle")
        time.sleep(3)
        
        # Check if site redirected away from Greenhouse (some companies do this)
        current_url = page.url.lower()
        if "greenhouse" not in current_url:
            # Check if there's a Greenhouse iframe on the redirected page
            frame = _get_application_frame(page)
            if frame == page:  # No iframe found either
                result["message"] = f"Site redirected away from Greenhouse to {page.url} - skipping"
                print(result["message"])
                return result
        
        # Get the correct frame (might be in iframe)
        frame = _get_application_frame(page)
        is_iframe = frame != page
        
        # Extract job info
        if not job_info:
            job_info = _extract_greenhouse_job_info(page, frame)
        
        result["job_title"] = job_info.get("title", "Unknown Position")
        result["company"] = job_info.get("company", "Unknown Company")
        
        print(f"Applying to: {result['job_title']} at {result['company']}")
        if is_iframe:
            print("(Content is in iframe)")
        
        # Step 1: Check for coding puzzles FIRST (some sites show puzzle before form)
        if not handle_puzzle_if_present(page):
            print("Puzzle detected but not solved - waiting for manual input...")
            time.sleep(30)
        time.sleep(2)  # Wait after puzzle for page to update
        
        # Re-get the frame after puzzle (page may have changed)
        frame = _get_application_frame(page)
        
        # Step 2: Look for "Application" tab
        try:
            application_tab = frame.locator("button:has-text('Application'), [role='tab']:has-text('Application')").first
            if application_tab.is_visible(timeout=2000):
                print("Clicking Application tab...")
                application_tab.click()
                time.sleep(2)
        except:
            pass
        
        # Step 3: Click "Apply" button
        try:
            apply_btn = frame.locator("a:has-text('Apply for this job'), a:has-text('Apply now'), button:has-text('Apply'), a:has-text('Apply')").first
            if apply_btn.is_visible(timeout=2000):
                print("Clicking Apply button...")
                apply_btn.click()
                time.sleep(2)
                if not is_iframe:
                    page.wait_for_load_state("networkidle")
        except:
            pass
        
        # Now fill the form
        print("Filling application form...")
        
        # Fill basic fields
        filled = _fill_greenhouse_basic_fields(frame, profile)
        print(f"Filled {filled} basic fields")
        
        # Upload resume
        _upload_greenhouse_resume(page, frame)
        
        # Upload cover letter if field exists
        _handle_greenhouse_cover_letter(frame, profile, job_info)
        
        # Handle custom questions
        _handle_greenhouse_questions(frame, profile, job_info)
        
        # Handle education fields
        _fill_greenhouse_education(frame, profile)
        
        # Handle work authorization
        _handle_greenhouse_authorization(frame, profile)
        
        # Submit
        submit_btn = frame.locator("input[type='submit'], button[type='submit'], button:has-text('Submit application')").first
        if submit_btn.is_visible(timeout=3000):
            print("Clicking Submit...")
            submit_btn.click()
            time.sleep(3)
            
            if _check_greenhouse_success(page, frame):
                result["success"] = True
                result["message"] = "Application submitted successfully"
            else:
                result["message"] = "Submitted but could not confirm success"
        else:
            result["message"] = "Could not find submit button"
            
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
    
    return result


def _extract_greenhouse_job_info(page: Page, frame) -> dict:
    """Extract job information from Greenhouse job page."""
    info = {"title": "", "company": "", "description": "", "location": ""}
    
    try:
        # Job title - try both page and frame
        for target in [frame, page]:
            title_elem = target.locator("h1.app-title, .job-title, h1").first
            try:
                if title_elem.is_visible(timeout=1000):
                    info["title"] = title_elem.text_content().strip()
                    break
            except:
                continue
        
        # Company name from URL
        url = page.url
        match = re.search(r'greenhouse\.io/([^/]+)', url)
        if match:
            info["company"] = match.group(1).replace("_", " ").replace("-", " ").title()
            
    except Exception as e:
        print(f"Error extracting job info: {e}")
    
    return info


def _fill_greenhouse_basic_fields(frame, profile: dict) -> int:
    """Fill basic Greenhouse application fields. Returns count of fields filled."""
    filled = 0
    
    # Try multiple selector patterns for each field
    field_mappings = [
        # First name
        (["#first_name", "input[name='first_name']", "input[name*='first' i][name*='name' i]", 
          "input[placeholder*='First' i]", "input[autocomplete='given-name']"], 
         profile.get("first_name", "")),
        # Last name  
        (["#last_name", "input[name='last_name']", "input[name*='last' i][name*='name' i]",
          "input[placeholder*='Last' i]", "input[autocomplete='family-name']"],
         profile.get("last_name", "")),
        # Email
        (["#email", "input[name='email']", "input[type='email']", 
          "input[placeholder*='Email' i]", "input[autocomplete='email']"],
         profile.get("email", "")),
        # Phone
        (["#phone", "input[name='phone']", "input[type='tel']",
          "input[placeholder*='Phone' i]", "input[autocomplete='tel']"],
         profile.get("phone", "")),
        # LinkedIn
        (["input[name*='linkedin' i]", "input[id*='linkedin' i]", 
          "input[placeholder*='LinkedIn' i]"],
         profile.get("linkedin", "")),
        # Website/Portfolio
        (["input[name*='website' i]", "input[name*='portfolio' i]",
          "input[placeholder*='Website' i]", "input[placeholder*='Portfolio' i]"],
         profile.get("website", "")),
    ]
    
    for selectors, value in field_mappings:
        if not value:
            continue
        for selector in selectors:
            try:
                field = frame.locator(selector).first
                if field.is_visible(timeout=300):
                    field.clear()
                    field.fill(value)
                    filled += 1
                    print(f"  Filled: {selector} = {value[:30]}...")
                    time.sleep(SLOW_MO / 1000)
                    break  # Move to next field
            except:
                continue
    
    return filled


def _upload_greenhouse_resume(page: Page, frame):
    """Upload resume on Greenhouse."""
    try:
        # Try frame first, then page (file inputs can be tricky with iframes)
        for target in [frame, page]:
            try:
                file_input = target.locator("input[type='file'][id*='resume'], input[type='file'][name*='resume']").first
                if file_input.count() > 0:
                    file_input.set_input_files(str(RESUME_PATH))
                    print("Resume uploaded")
                    time.sleep(1)
                    return
            except:
                continue
        
        # Try generic file upload
        for target in [frame, page]:
            try:
                file_input = target.locator("input[type='file']").first
                if file_input.count() > 0:
                    file_input.set_input_files(str(RESUME_PATH))
                    print("Resume uploaded (generic)")
                    time.sleep(1)
                    return
            except:
                continue
            
    except Exception as e:
        print(f"Resume upload error: {e}")


def _handle_greenhouse_cover_letter(frame, profile: dict, job_info: dict):
    """Handle cover letter upload/text on Greenhouse."""
    try:
        # Check for cover letter textarea
        cl_textarea = frame.locator("textarea[id*='cover'], textarea[name*='cover']").first
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
    except:
        pass


def _handle_greenhouse_questions(frame, profile: dict, job_info: dict):
    """Handle custom questions on Greenhouse."""
    try:
        # Find question fields
        questions = frame.locator(".field, .application-field").all()
        
        for q_container in questions:
            try:
                # Get label text
                label = q_container.locator("label").first
                if not label.is_visible(timeout=500):
                    continue
                
                question_text = label.text_content().strip()
                
                # Skip already filled basic fields
                if any(x in question_text.lower() for x in ["first name", "last name", "email", "phone", "resume"]):
                    continue
                
                # Handle textarea
                textarea = q_container.locator("textarea").first
                if textarea.is_visible(timeout=500):
                    if is_ai_question(question_text):
                        answer = answer_question(question_text, profile, job_info.get("description", ""))
                        textarea.fill(answer)
                        time.sleep(SLOW_MO / 1000)
                    continue
                
                # Handle text input
                text_input = q_container.locator("input[type='text']").first
                if text_input.is_visible(timeout=500):
                    answer = _get_greenhouse_simple_answer(question_text, profile)
                    if answer:
                        text_input.fill(answer)
                        time.sleep(SLOW_MO / 1000)
                    continue
                
                # Handle select
                select = q_container.locator("select").first
                if select.is_visible(timeout=500):
                    _handle_greenhouse_select(select, question_text, profile)
                    
            except Exception as e:
                continue
    except:
        pass


def _get_greenhouse_simple_answer(question: str, profile: dict) -> str:
    """Get simple answers for common Greenhouse questions."""
    q_lower = question.lower()
    
    if "linkedin" in q_lower:
        return profile.get("linkedin", "")
    if "github" in q_lower:
        return profile.get("github", "")
    if "website" in q_lower or "portfolio" in q_lower:
        return profile.get("website", "")
    if "years" in q_lower and "experience" in q_lower:
        return str(profile.get("years_experience", ""))
    if "salary" in q_lower:
        return ""  # Skip salary questions
    
    return ""


def _handle_greenhouse_select(select, question: str, profile: dict):
    """Handle Greenhouse dropdown selections."""
    q_lower = question.lower()
    
    try:
        if "authorized" in q_lower or ("work" in q_lower and "legally" in q_lower):
            select.select_option(label="Yes")
        elif "sponsor" in q_lower or "visa" in q_lower:
            select.select_option(label="No")
        elif "gender" in q_lower:
            select.select_option(index=1)  # Usually "Prefer not to say" or first option
        elif "race" in q_lower or "ethnicity" in q_lower:
            select.select_option(index=1)
        elif "veteran" in q_lower:
            select.select_option(index=1)
    except:
        pass


def _fill_greenhouse_education(frame, profile: dict):
    """Fill education fields on Greenhouse."""
    education = profile.get("education", [])
    if not education:
        return
    
    edu = education[0]  # Most recent
    
    try:
        # School name
        school_field = frame.locator("input[id*='school'], input[name*='school']").first
        if school_field.is_visible(timeout=500):
            school_field.fill(edu.get("school", ""))
        
        # Degree
        degree_field = frame.locator("select[id*='degree'], select[name*='degree']").first
        if degree_field.is_visible(timeout=500):
            degree = edu.get("degree", "")
            if "master" in degree.lower():
                degree_field.select_option(label="Master's Degree")
            elif "bachelor" in degree.lower():
                degree_field.select_option(label="Bachelor's Degree")
        
        # Field of study
        major_field = frame.locator("input[id*='discipline'], input[name*='discipline'], input[id*='major']").first
        if major_field.is_visible(timeout=500):
            major_field.fill(edu.get("field", ""))
            
    except Exception as e:
        print(f"Education field error: {e}")


def _handle_greenhouse_authorization(frame, profile: dict):
    """Handle work authorization questions."""
    try:
        # Look for authorization radio buttons
        auth_yes = frame.locator("input[type='radio'][value='Yes']").first
        if auth_yes.is_visible(timeout=500):
            auth_yes.click()
    except:
        pass
    
    try:
        # Sponsorship - select No
        sponsor_no = frame.locator("input[type='radio'][value='No']").first
        if sponsor_no.is_visible(timeout=500):
            sponsor_no.click()
    except:
        pass


def _check_greenhouse_success(page: Page, frame) -> bool:
    """Check if Greenhouse application was successful."""
    success_indicators = [
        "thank you",
        "application received", 
        "successfully submitted",
        "application has been submitted"
    ]
    
    # Check both page and frame
    for target in [frame, page]:
        try:
            content = target.locator("body").text_content().lower()
            if any(indicator in content for indicator in success_indicators):
                return True
        except:
            continue
    
    return False
