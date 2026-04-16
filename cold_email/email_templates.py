"""
Email Templates - Personalized cold email templates for job outreach.
"""

TEMPLATES = {
    "recruiter": {
        "subject": "Data Engineer interested in {company} opportunities",
        "body": """Hi {first_name},

I came across your profile while researching {company}'s talent acquisition team, and I wanted to reach out directly.

I'm a Data Engineer with experience in building data pipelines, ETL processes, and working with cloud platforms (AWS, GCP). I'm particularly interested in {company} because of your work in {industry_or_product}.

I've attached my resume for your review. I'd love to have a quick conversation about any Data Engineering opportunities at {company}.

Would you have 15 minutes this week for a brief call?

Best regards,
{sender_name}

{linkedin_url}
"""
    },
    
    "hiring_manager": {
        "subject": "Data Engineer ready to contribute at {company}",
        "body": """Hi {first_name},

I'm reaching out because I'm very interested in Data Engineering roles at {company}.

A bit about me:
• Built and maintained data pipelines processing millions of records daily
• Experience with Python, SQL, Spark, and cloud data platforms
• Strong focus on data quality and pipeline reliability

I've attached my resume with more details on my projects and experience.

I'd love to learn more about your team's data challenges and how I might contribute. Would you be open to a brief conversation?

Best regards,
{sender_name}

{linkedin_url}
"""
    },
    
    "hr_general": {
        "subject": "Application for Data Engineering roles at {company}",
        "body": """Hi {first_name},

I hope this email finds you well. I'm writing to express my interest in Data Engineering opportunities at {company}.

I'm a Data Engineer with hands-on experience in:
• Building scalable ETL pipelines
• Working with SQL, Python, and cloud platforms
• Data modeling and warehouse design

I've attached my resume for your consideration. I would be grateful for the opportunity to discuss how my skills could benefit {company}.

Thank you for your time.

Best regards,
{sender_name}

{linkedin_url}
"""
    },
    
    "data_team_lead": {
        "subject": "Data Engineer interested in joining your team at {company}",
        "body": """Hi {first_name},

I noticed you lead the Data Engineering/Analytics team at {company}, and I wanted to reach out directly.

I'm passionate about building robust data infrastructure and have experience with:
• Designing and implementing data pipelines at scale
• Python, SQL, Spark, Airflow
• AWS/GCP data services

I'm particularly drawn to {company} because of {reason_interested}.

I'd love to hear about the challenges your team is tackling and explore if there's a fit. I've attached my resume for reference.

Would you be open to a brief chat?

Best,
{sender_name}

{linkedin_url}
"""
    }
}


def get_template(role: str) -> dict:
    """Get the appropriate template based on the recipient's role."""
    role_lower = role.lower()
    
    if any(word in role_lower for word in ['recruiter', 'talent', 'acquisition', 'sourcer']):
        return TEMPLATES['recruiter']
    elif any(word in role_lower for word in ['hr', 'human resources', 'people']):
        return TEMPLATES['hr_general']
    elif any(word in role_lower for word in ['manager', 'lead', 'director', 'head', 'vp']):
        if any(word in role_lower for word in ['data', 'engineering', 'analytics']):
            return TEMPLATES['data_team_lead']
        return TEMPLATES['hiring_manager']
    else:
        return TEMPLATES['hr_general']


def personalize_email(
    template: dict,
    recipient_name: str,
    company: str,
    sender_name: str,
    linkedin_url: str = "",
    industry_or_product: str = "",
    reason_interested: str = ""
) -> dict:
    """
    Fill in template with personalized values.
    
    Returns:
        dict with 'subject' and 'body'
    """
    # Get first name
    first_name = recipient_name.split()[0] if recipient_name else "there"
    
    # Default values
    if not industry_or_product:
        industry_or_product = "the tech industry"
    if not reason_interested:
        reason_interested = "your innovative approach to data"
    
    # Format template
    subject = template['subject'].format(
        company=company,
        first_name=first_name
    )
    
    body = template['body'].format(
        first_name=first_name,
        company=company,
        sender_name=sender_name,
        linkedin_url=linkedin_url if linkedin_url else "",
        industry_or_product=industry_or_product,
        reason_interested=reason_interested
    )
    
    return {"subject": subject, "body": body.strip()}


def generate_email(
    recipient_name: str,
    recipient_role: str,
    company: str,
    sender_name: str,
    linkedin_url: str = "",
    **kwargs
) -> dict:
    """
    Generate a personalized email for a recipient.
    
    Returns:
        dict with 'subject' and 'body'
    """
    template = get_template(recipient_role)
    return personalize_email(
        template=template,
        recipient_name=recipient_name,
        company=company,
        sender_name=sender_name,
        linkedin_url=linkedin_url,
        **kwargs
    )


# Test
if __name__ == "__main__":
    email = generate_email(
        recipient_name="John Smith",
        recipient_role="Technical Recruiter",
        company="Google",
        sender_name="Sathvik Kasoju",
        linkedin_url="https://linkedin.com/in/sathvik"
    )
    
    print("Subject:", email['subject'])
    print("\nBody:")
    print(email['body'])
