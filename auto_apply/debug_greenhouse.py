"""Debug script to see what's on the Greenhouse page."""
from playwright.sync_api import sync_playwright
from config import CHROME_PROFILE_DIR
import time

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=str(CHROME_PROFILE_DIR),
        headless=False,
    )
    page = browser.new_page()
    
    # Use the Lithic job that was just tested
    url = 'http://job-boards.greenhouse.io/lithic/jobs/5833301004'
    print(f'Loading: {url}')
    page.goto(url, wait_until='networkidle')
    print(f'Landed on: {page.url}')
    time.sleep(3)
    
    # First, dismiss any cookie popups
    print('\nLooking for cookie/consent popups to dismiss...')
    dismiss_selectors = [
        "button:has-text('Accept')",
        "button:has-text('Accept all')",
        "button:has-text('Agree')",
        "button:has-text('OK')",
        "button:has-text('Got it')",
        "[aria-label='Close']",
        ".close-button",
    ]
    for selector in dismiss_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=500):
                print(f'  Clicking: {selector}')
                btn.click()
                time.sleep(1)
        except:
            pass
    
    # Check for puzzle - look on MAIN PAGE first
    print('\n--- Checking for puzzle on MAIN PAGE ---')
    from puzzle_solver import detect_puzzle, solve_puzzle
    
    puzzle = detect_puzzle(page)
    if puzzle:
        print('PUZZLE FOUND!')
        answer = solve_puzzle(puzzle)
        print(f'Answer: {answer}')
        
        # Look for puzzle input on MAIN page (not iframe)
        print('\nLooking for puzzle input fields on main page...')
        inputs = page.locator('input:visible').all()
        print(f'Found {len(inputs)} visible inputs on main page:')
        for i, inp in enumerate(inputs):
            try:
                inp_type = inp.get_attribute('type') or 'text'
                name = inp.get_attribute('name') or ''
                inp_id = inp.get_attribute('id') or ''
                placeholder = inp.get_attribute('placeholder') or ''
                print(f'  {i}: type={inp_type} id="{inp_id}" name="{name}" placeholder="{placeholder}"')
            except:
                pass
        
        # Try to enter the answer
        if answer and inputs:
            print(f'\nEntering answer: {answer}')
            for inp in inputs:
                try:
                    if inp.is_visible():
                        inp.fill(answer)
                        print('Filled input!')
                        break
                except:
                    pass
            
            # Click submit
            print('Looking for submit button...')
            submit_selectors = [
                "button:has-text('Submit')",
                "button:has-text('Continue')",
                "button[type='submit']",
                "input[type='submit']",
            ]
            for sel in submit_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=1000):
                        print(f'Clicking: {sel}')
                        btn.click()
                        time.sleep(3)
                        break
                except:
                    pass
    else:
        print('No puzzle detected')
    
    # Now check iframe for form
    print('\n--- After puzzle, checking iframe ---')
    time.sleep(2)
    
    iframe_selectors = [
        "iframe[src*='greenhouse']",
        "iframe#grnhse_iframe",
    ]
    frame = None
    for sel in iframe_selectors:
        try:
            f = page.frame_locator(sel)
            test = f.locator("body")
            if test.count() > 0:
                print(f'Found iframe: {sel}')
                frame = f
                break
        except:
            pass
    
    if frame:
        inputs = frame.locator('input').all()
        print(f'Found {len(inputs)} inputs in iframe')
        for i, inp in enumerate(inputs[:15]):
            try:
                inp_type = inp.get_attribute('type') or 'text'
                name = inp.get_attribute('name') or ''
                inp_id = inp.get_attribute('id') or ''
                visible = 'visible' if inp.is_visible() else 'hidden'
                print(f'  {i}: type={inp_type} id="{inp_id}" name="{name}" [{visible}]')
            except Exception as e:
                pass
    
    print('\n>>> Browser stays open 60 seconds <<<')
    time.sleep(60)
    browser.close()
