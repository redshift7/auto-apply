"""
Form Filler - Generic form detection and filling utilities.
"""
import re
import time
from typing import Optional
from playwright.sync_api import Page, Locator, ElementHandle
from config import COMMON_FIELD_MAPPINGS, SLOW_MO


def find_field_by_label(page: Page, label_keywords: list[str]) -> Optional[Locator]:
    """Find an input field by its label text."""
    for keyword in label_keywords:
        # Try label element
        try:
            label = page.locator(f"label:has-text('{keyword}')").first
            if label.is_visible(timeout=500):
                for_attr = label.get_attribute("for")
                if for_attr:
                    field = page.locator(f"#{for_attr}")
                    if field.is_visible(timeout=500):
                        return field
                # Try sibling/child input
                field = label.locator("xpath=following::input[1]").first
                if field.is_visible(timeout=500):
                    return field
        except:
            pass
        
        # Try placeholder
        try:
            field = page.locator(f"input[placeholder*='{keyword}' i]").first
            if field.is_visible(timeout=500):
                return field
        except:
            pass
        
        # Try name attribute
        try:
            field = page.locator(f"input[name*='{keyword}' i]").first
            if field.is_visible(timeout=500):
                return field
        except:
            pass
    
    return None


def fill_text_field(field: Locator, value: str):
    """Fill a text field with value."""
    try:
        field.clear()
        field.fill(value)
        time.sleep(SLOW_MO / 1000)
    except Exception as e:
        print(f"Error filling field: {e}")


def fill_common_fields(page: Page, profile: dict):
    """Fill common application fields from profile data."""
    field_values = {
        "first_name": profile.get("first_name", ""),
        "last_name": profile.get("last_name", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "linkedin": profile.get("linkedin", ""),
        "github": profile.get("github", ""),
        "website": profile.get("website", ""),
        "location": profile.get("location", ""),
    }
    
    filled = []
    for field_name, keywords in COMMON_FIELD_MAPPINGS.items():
        if field_name in field_values and field_values[field_name]:
            field = find_field_by_label(page, keywords)
            if field:
                fill_text_field(field, field_values[field_name])
                filled.append(field_name)
    
    return filled


def upload_file(page: Page, field_keywords: list[str], file_path: str) -> bool:
    """Upload a file to a file input field."""
    for keyword in field_keywords:
        try:
            # Find file input
            file_input = page.locator(f"input[type='file'][name*='{keyword}' i]").first
            if file_input.count() > 0:
                file_input.set_input_files(file_path)
                return True
        except:
            pass
        
        try:
            # Try by label
            label = page.locator(f"label:has-text('{keyword}')").first
            if label.is_visible(timeout=500):
                file_input = page.locator("input[type='file']").first
                if file_input.count() > 0:
                    file_input.set_input_files(file_path)
                    return True
        except:
            pass
    
    return False


def select_dropdown(page: Page, field_keywords: list[str], value: str) -> bool:
    """Select a value from a dropdown."""
    for keyword in field_keywords:
        try:
            select = page.locator(f"select[name*='{keyword}' i]").first
            if select.is_visible(timeout=500):
                select.select_option(label=value)
                return True
        except:
            pass
    return False


def click_radio_or_checkbox(page: Page, label_text: str) -> bool:
    """Click a radio button or checkbox by its label."""
    try:
        label = page.locator(f"label:has-text('{label_text}')").first
        if label.is_visible(timeout=500):
            label.click()
            return True
    except:
        pass
    
    try:
        input_elem = page.locator(f"input[value*='{label_text}' i]").first
        if input_elem.is_visible(timeout=500):
            input_elem.click()
            return True
    except:
        pass
    
    return False


def get_visible_form_fields(page: Page) -> list[dict]:
    """Get all visible form fields with their labels."""
    fields = []
    
    # Get all inputs, textareas, selects
    for selector in ["input:visible", "textarea:visible", "select:visible"]:
        try:
            elements = page.locator(selector).all()
            for elem in elements:
                field_info = {
                    "type": elem.get_attribute("type") or "text",
                    "name": elem.get_attribute("name") or "",
                    "placeholder": elem.get_attribute("placeholder") or "",
                    "required": elem.get_attribute("required") is not None,
                }
                
                # Try to find label
                field_id = elem.get_attribute("id")
                if field_id:
                    try:
                        label = page.locator(f"label[for='{field_id}']").first
                        field_info["label"] = label.text_content().strip()
                    except:
                        field_info["label"] = ""
                else:
                    field_info["label"] = ""
                
                fields.append(field_info)
        except:
            continue
    
    return fields


def find_submit_button(page: Page) -> Optional[Locator]:
    """Find the submit button on the page."""
    submit_texts = ["submit", "apply", "send application", "submit application"]
    
    for text in submit_texts:
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if btn.is_visible(timeout=500):
                return btn
        except:
            pass
        
        try:
            btn = page.locator(f"input[type='submit'][value*='{text}' i]").first
            if btn.is_visible(timeout=500):
                return btn
        except:
            pass
    
    # Try generic submit button
    try:
        btn = page.locator("button[type='submit']").first
        if btn.is_visible(timeout=500):
            return btn
    except:
        pass
    
    return None


def extract_question_text(element: Locator) -> str:
    """Extract the question text from a form field's container."""
    try:
        # Try to get parent container text
        parent = element.locator("xpath=ancestor::div[contains(@class, 'question')]").first
        if parent.is_visible(timeout=500):
            return parent.text_content().strip()
    except:
        pass
    
    # Try label
    try:
        field_id = element.get_attribute("id")
        if field_id:
            label = element.page.locator(f"label[for='{field_id}']")
            if label.is_visible(timeout=500):
                return label.text_content().strip()
    except:
        pass
    
    return element.get_attribute("placeholder") or element.get_attribute("name") or ""
