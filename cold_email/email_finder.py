"""
Email Finder - Discovers email addresses using pattern guessing and verification.
"""
import re
import socket
import smtplib
import dns.resolver
from typing import Optional


# Common email patterns (in order of likelihood)
EMAIL_PATTERNS = [
    "{first}.{last}",      # john.smith
    "{first}{last}",       # johnsmith  
    "{first}_{last}",      # john_smith
    "{f}{last}",           # jsmith
    "{first}{l}",          # johns
    "{first}",             # john
    "{last}.{first}",      # smith.john
    "{f}.{last}",          # j.smith
    "{first}-{last}",      # john-smith
]


def normalize_name(name: str) -> tuple[str, str]:
    """Split full name into first and last, normalized."""
    parts = name.strip().lower().split()
    if len(parts) >= 2:
        return parts[0], parts[-1]
    elif len(parts) == 1:
        return parts[0], ""
    return "", ""


def generate_email_variants(name: str, domain: str) -> list[str]:
    """Generate possible email addresses for a person at a company."""
    first, last = normalize_name(name)
    
    if not first:
        return []
    
    # Clean domain
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    if domain.startswith("http"):
        domain = domain.split("//")[-1].split("/")[0]
    
    emails = []
    for pattern in EMAIL_PATTERNS:
        try:
            local = pattern.format(
                first=first,
                last=last,
                f=first[0] if first else "",
                l=last[0] if last else ""
            )
            # Skip patterns that need last name if we don't have one
            if "{last}" in pattern and not last:
                continue
            if local:
                emails.append(f"{local}@{domain}")
        except (IndexError, KeyError):
            continue
    
    return emails


def get_mx_record(domain: str) -> Optional[str]:
    """Get the MX record for a domain."""
    try:
        records = dns.resolver.resolve(domain, 'MX')
        # Return the highest priority MX record
        mx_record = sorted(records, key=lambda x: x.preference)[0]
        return str(mx_record.exchange).rstrip('.')
    except Exception:
        return None


def verify_email_smtp(email: str, timeout: int = 10) -> bool:
    """
    Verify if an email address exists using SMTP.
    Note: Many servers block this or return false positives.
    """
    try:
        domain = email.split('@')[1]
        mx_host = get_mx_record(domain)
        
        if not mx_host:
            return False
        
        # Connect to mail server
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_host)
        smtp.helo('verify.com')
        smtp.mail('verify@verify.com')
        code, _ = smtp.rcpt(email)
        smtp.quit()
        
        # 250 = valid, 550 = invalid
        return code == 250
        
    except Exception:
        return False


def find_email(name: str, domain: str, verify: bool = False) -> dict:
    """
    Find the most likely email for a person at a company.
    
    Returns:
        dict with 'email', 'confidence', 'verified'
    """
    variants = generate_email_variants(name, domain)
    
    if not variants:
        return {"email": None, "confidence": 0, "verified": False}
    
    if verify:
        # Try to verify each variant
        for email in variants:
            if verify_email_smtp(email):
                return {"email": email, "confidence": 0.9, "verified": True}
    
    # Return most likely pattern without verification
    return {
        "email": variants[0],  # first.last@domain is most common
        "confidence": 0.7,
        "verified": False
    }


def bulk_find_emails(contacts: list[dict], verify: bool = False) -> list[dict]:
    """
    Find emails for a list of contacts.
    
    Args:
        contacts: List of dicts with 'name' and 'domain' keys
        verify: Whether to verify emails via SMTP
    
    Returns:
        List of contacts with 'email' added
    """
    results = []
    
    for contact in contacts:
        name = contact.get('name', '')
        domain = contact.get('domain', contact.get('company', ''))
        
        result = find_email(name, domain, verify=verify)
        
        results.append({
            **contact,
            'email': result['email'],
            'email_confidence': result['confidence'],
            'email_verified': result['verified']
        })
    
    return results


# Test
if __name__ == "__main__":
    # Test email generation
    test_cases = [
        ("John Smith", "google.com"),
        ("Jane Doe", "meta.com"),
        ("[YOUR_NAME]", "example.com"),
    ]
    
    for name, domain in test_cases:
        variants = generate_email_variants(name, domain)
        print(f"\n{name} @ {domain}:")
        for v in variants[:5]:
            print(f"  {v}")
