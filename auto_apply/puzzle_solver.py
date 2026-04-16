"""
Puzzle Solver - Detects and solves coding puzzles in job applications.
Some companies add coding challenges to filter out bots and test candidates.
"""
import base64
import re
from playwright.sync_api import Page


def detect_puzzle(page: Page) -> dict | None:
    """
    Detect if page has a coding puzzle challenge.
    Returns puzzle info dict or None if no puzzle found.
    """
    try:
        page_text = page.content()
        
        # Look for base64 encoded content (common puzzle format)
        # Base64 strings are typically long alphanumeric with = padding
        base64_pattern = r'[A-Za-z0-9+/]{50,}={0,2}'
        matches = re.findall(base64_pattern, page_text)
        
        for match in matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8')
                # Check if it looks like Python code
                if 'def ' in decoded or 'import ' in decoded or 'print(' in decoded:
                    return {
                        "type": "base64_python",
                        "encoded": match,
                        "decoded": decoded
                    }
            except:
                continue
        
        # Look for puzzle indicators in text
        puzzle_indicators = [
            "crack the code",
            "hidden code",
            "solve the puzzle",
            "decode",
            "decrypt",
            "enter the code below",
        ]
        
        page_lower = page_text.lower()
        for indicator in puzzle_indicators:
            if indicator in page_lower:
                # Found puzzle text, look harder for the code
                for match in matches:
                    try:
                        decoded = base64.b64decode(match).decode('utf-8')
                        if len(decoded) > 20:  # Has some content
                            return {
                                "type": "base64_unknown",
                                "encoded": match,
                                "decoded": decoded
                            }
                    except:
                        continue
        
        return None
        
    except Exception as e:
        print(f"Error detecting puzzle: {e}")
        return None


def solve_puzzle(puzzle: dict) -> str | None:
    """
    Attempt to solve a detected puzzle.
    Returns the answer string or None if can't solve.
    """
    if not puzzle:
        return None
    
    try:
        decoded = puzzle["decoded"]
        
        # Try to execute Python code and capture output
        if puzzle["type"] == "base64_python" or "def " in decoded:
            return _solve_python_puzzle(decoded)
        
        # Check if decoded content is just the answer
        if len(decoded) < 50 and decoded.strip().isalnum():
            return decoded.strip()
        
        return None
        
    except Exception as e:
        print(f"Error solving puzzle: {e}")
        return None


def _solve_python_puzzle(code: str) -> str | None:
    """Execute Python puzzle code and extract the answer."""
    try:
        # Common patterns in puzzle code
        
        # Pattern 1: XOR decryption (like the Abacus puzzle)
        # Look for password and key variables
        password_match = re.search(r'password\s*=\s*b["\'](.+?)["\']', code)
        key_match = re.search(r'_?key\s*=\s*b["\'](.+?)["\']', code)
        
        if password_match and key_match:
            # Extract byte strings and XOR them
            password_str = password_match.group(1)
            key_str = key_match.group(1)
            
            # Parse escape sequences
            password_bytes = password_str.encode().decode('unicode_escape').encode('latin-1')
            key_bytes = key_str.encode().decode('unicode_escape').encode('latin-1')
            
            result = bytes(a ^ b for a, b in zip(password_bytes, key_bytes))
            return result.decode('utf-8')
        
        # Pattern 2: Look for assert statement with expected answer
        assert_match = re.search(r'assert\s+result\s*==\s*["\'](.+?)["\']', code)
        if assert_match:
            return assert_match.group(1)
        
        # Pattern 3: Execute in sandbox and capture print output
        answer = _execute_sandbox(code)
        if answer:
            return answer
        
        return None
        
    except Exception as e:
        print(f"Error solving Python puzzle: {e}")
        return None


def _execute_sandbox(code: str) -> str | None:
    """Execute code in a restricted sandbox and capture output."""
    import io
    import sys
    
    try:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()
        
        # Create restricted globals
        safe_globals = {
            '__builtins__': {
                'print': print,
                'bytes': bytes,
                'zip': zip,
                'range': range,
                'len': len,
                'str': str,
                'int': int,
            }
        }
        
        # Execute
        exec(code, safe_globals)
        
        # Get output
        output = captured.getvalue()
        sys.stdout = old_stdout
        
        # Extract answer from output
        # Look for patterns like "answer: X" or "password: X" or "result: X"
        for pattern in [r':\s*(\S+)\s*$', r'is\s*(\S+)\s*$', r'=\s*(\S+)\s*$']:
            match = re.search(pattern, output.strip(), re.MULTILINE)
            if match:
                return match.group(1).strip('"\'')
        
        # Just return last line if short
        lines = output.strip().split('\n')
        if lines and len(lines[-1]) < 50:
            return lines[-1].strip()
        
        return None
        
    except Exception as e:
        sys.stdout = old_stdout
        print(f"Sandbox execution error: {e}")
        return None


def handle_puzzle_if_present(page: Page) -> bool:
    """
    Detect and solve puzzle, enter answer if found.
    Returns True if puzzle was solved or no puzzle present.
    Returns False if puzzle found but couldn't solve.
    """
    puzzle = detect_puzzle(page)
    
    if not puzzle:
        return True  # No puzzle, continue normally
    
    print("\n" + "=" * 50)
    print("CODING PUZZLE DETECTED!")
    print("=" * 50)
    
    answer = solve_puzzle(puzzle)
    
    if answer:
        print(f"Solved! Answer: {answer}")
        
        # Find input field specifically for puzzle answer
        # Must NOT be a standard form field (first_name, email, etc.)
        puzzle_input_selectors = [
            "input[name*='code' i]",
            "input[name*='answer' i]",
            "input[name*='puzzle' i]",
            "input[placeholder*='code' i]",
            "input[placeholder*='answer' i]",
            "input[placeholder*='puzzle' i]",
            "input[id*='code' i]",
            "input[id*='answer' i]",
        ]
        
        # Selectors to AVOID (standard form fields)
        avoid_ids = ['first_name', 'last_name', 'email', 'phone', 'resume', 
                     'cover_letter', 'linkedin', 'website', 'gender', 
                     'country', 'veteran', 'disability', 'ethnicity']
        
        for selector in puzzle_input_selectors:
            try:
                field = page.locator(selector).first
                if field.is_visible(timeout=1000):
                    field_id = field.get_attribute('id') or ''
                    # Make sure it's not a standard form field
                    if not any(avoid in field_id.lower() for avoid in avoid_ids):
                        field.fill(answer)
                        print(f"Entered answer in field: {selector}")
                        
                        # Look for submit/continue button
                        submit_btn = page.locator("button:has-text('Submit'), button:has-text('Continue'), button[type='submit']").first
                        if submit_btn.is_visible(timeout=1000):
                            submit_btn.click()
                            print("Clicked submit")
                            import time
                            time.sleep(2)
                        
                        return True
            except:
                continue
        
        # No dedicated puzzle input found - puzzle might be informational only
        print("Note: Puzzle detected but no dedicated input field found")
        print("      (This may be decorative - proceeding with application)")
        return True  # Continue anyway
    else:
        print("Could not solve puzzle automatically")
        print("  Please solve manually in the browser")
        return False


# Test
if __name__ == "__main__":
    # Test with the Abacus puzzle
    test_code = '''#!/usr/bin/env python3
"""The answer to life, the universe, and everything — encrypted."""

password = b"\\xed\\xc1"
_key = b"\\xd9\\xf3\\xed\\xfb\\x80\\xc4~\\xa7\\n\\xb8\\xfb<\\xfbO^\\xfb"

def decrypt_password() -> str:
    return bytes(a ^ b for a, b in zip(password, _key)).decode()

if __name__ == "__main__":
    result = decrypt_password()
    print(f"Decrypted password: {result}")
    assert result == "42", "Don't panic — but decryption failed!"
'''
    
    puzzle = {"type": "base64_python", "decoded": test_code}
    answer = solve_puzzle(puzzle)
    print(f"Test answer: {answer}")
