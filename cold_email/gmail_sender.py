"""
Gmail Sender - Send emails via Gmail API with attachments.
"""
import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Gmail API scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Paths
CREDENTIALS_PATH = Path(__file__).parent / "credentials.json"
TOKEN_PATH = Path(__file__).parent / "token.json"


def get_gmail_service():
    """Get authenticated Gmail API service."""
    creds = None
    
    # Load existing token
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                print("\n" + "=" * 60)
                print("GMAIL API SETUP REQUIRED")
                print("=" * 60)
                print("""
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a new project (or select existing)
3. Enable Gmail API: APIs & Services > Enable APIs > Gmail API
4. Create OAuth credentials:
   - Create Credentials > OAuth client ID
   - Application type: Desktop app
   - Download JSON
5. Save the JSON file as: credentials.json
   In folder: {0}
                """.format(Path(__file__).parent))
                raise FileNotFoundError("credentials.json not found. Follow setup instructions above.")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save token for future use
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)


def create_message_with_attachment(
    sender: str,
    to: str,
    subject: str,
    body: str,
    attachment_path: str = None
) -> dict:
    """Create email message with optional attachment."""
    
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    
    # Attach body
    message.attach(MIMEText(body, 'plain'))
    
    # Attach file if provided
    if attachment_path and Path(attachment_path).exists():
        attachment = Path(attachment_path)
        
        with open(attachment, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{attachment.name}"'
        )
        message.attach(part)
    
    # Encode message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw}


def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_path: str = None,
    sender: str = "me"
) -> dict:
    """
    Send an email via Gmail API.
    
    Args:
        to: Recipient email
        subject: Email subject
        body: Email body text
        attachment_path: Optional path to attachment (e.g., resume PDF)
        sender: Sender email (default "me" uses authenticated account)
    
    Returns:
        dict with 'success', 'message_id', 'error'
    """
    try:
        service = get_gmail_service()
        
        message = create_message_with_attachment(
            sender=sender,
            to=to,
            subject=subject,
            body=body,
            attachment_path=attachment_path
        )
        
        result = service.users().messages().send(
            userId='me',
            body=message
        ).execute()
        
        return {
            'success': True,
            'message_id': result.get('id'),
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'message_id': None,
            'error': str(e)
        }


def send_test_email(to: str):
    """Send a test email to verify setup."""
    result = send_email(
        to=to,
        subject="Test Email - Cold Email Tool",
        body="This is a test email from your cold email outreach tool.\n\nIf you received this, the setup is working!",
    )
    
    if result['success']:
        print(f"✓ Test email sent successfully! Message ID: {result['message_id']}")
    else:
        print(f"✗ Failed to send: {result['error']}")
    
    return result


# Test
if __name__ == "__main__":
    print("Testing Gmail API connection...")
    
    try:
        service = get_gmail_service()
        print("✓ Successfully connected to Gmail API")
        
        # Get user's email
        profile = service.users().getProfile(userId='me').execute()
        print(f"✓ Authenticated as: {profile.get('emailAddress')}")
        
    except FileNotFoundError as e:
        print(str(e))
    except Exception as e:
        print(f"Error: {e}")
