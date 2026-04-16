# Auto-Apply Setup & Configuration Guide

A Python automation tool for applying to job listings on Lever, Greenhouse, and Ashby platforms with AI-powered cover letter generation and form filling.

## Features

- **Automatic Job Search**: Finds job listings on supported platforms
- **Smart Form Filling**: Automatically fills application forms with your information
- **AI Cover Letters**: Generates customized cover letters using Claude AI
- **CAPTCHA Handling**: Attempts to solve CAPTCHAs automatically
- **Cold Email Module**: Discover and email hiring managers
- **Application Tracking**: Keeps detailed records of all applications

## Prerequisites

- **Python 3.8+**
- **Playwright** (for browser automation)
- **Anthropic API Key** (for Claude AI integration)
- **Gmail API Credentials** (optional, for cold email module)

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/redshift7/auto-apply.git
cd auto-apply
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers
```bash
playwright install
```

### 4. Configure Environment Variables

Copy the example environment file and add your credentials:
```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

**To get your Anthropic API Key:**
1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste into `.env`

### 5. Configure Resume & Profile

Edit `auto_apply/config.py` and set your resume path:
```python
RESUME_PATH = Path(r"C:\Users\YourName\Documents\Your_Resume.pdf")  # Windows
RESUME_PATH = Path(r"/Users/YourName/Documents/Your_Resume.pdf")    # macOS/Linux
```

Update your profile information in `profile.json`:
```json
{
  "first_name": "Your First Name",
  "last_name": "Your Last Name",
  "email": "your.email@example.com",
  "phone": "+1-XXX-XXX-XXXX",
  "location": "City, State",
  "work_experience": [...]
}
```

## Running the Tool

### Run Auto-Apply
```bash
# Run from repository root
python -m auto_apply.main [options]

# Available options:
# --search-only       : Only search for jobs, don't apply
# --apply-only        : Only apply to discovered jobs
# --keyword "python"  : Search for specific keyword
```

### Cold Email Module
```bash
# Note: Requires Gmail API setup first
python -m cold_email.gmail_sender
```

## Gmail API Setup (For Cold Email)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 Desktop Application credentials
5. Download credentials.json and place in `auto-apply/` directory
6. First run will prompt for authentication

## Configuration Files

### `config.py`
Main configuration file containing:
- Resume path
- API keys and credentials
- Platform-specific settings
- Search filters

### `profile.json`
User profile template with:
- Personal information
- Work experience
- Education
- Skills

### `applied_jobs.json`
Application history (auto-maintained). Shows:
- Job ID and title
- Company name
- Application status
- Application date

## Troubleshooting

### Import Errors
**Error**: `ModuleNotFoundError: No module named 'config'`

**Solution**: Always run with the full module path:
```bash
python -m auto_apply.main
```

### API Key Not Found
**Error**: `ANTHROPIC_API_KEY not found`

**Solution**: 
1. Ensure `.env` file exists in repository root
2. Add your API key: `ANTHROPIC_API_KEY=your-key-here`
3. Verify it's readable: `cat .env`

### Playwright Browser Errors
**Error**: `Failed to launch browser`

**Solution**:
```bash
# Reinstall Playwright
playwright install

# On Linux, may need system dependencies
sudo apt-get install -y libglib2.0-0 libdbus-1-3
```

### Resume Parsing Errors
**Error**: `Failed to parse resume PDF`

**Solution**:
- Verify resume path in `config.py` is correct
- Ensure PDF is readable and not encrypted
- Try converting PDF to text: `pdftotext resume.pdf resume.txt`

### Application Not Submitting
**Error**: Form validation errors

**Solution**:
- Check `profile.json` has all required fields
- Verify phone number format matches platform requirements
- Check for CAPTCHA - may need manual interaction

## Performance Optimization

### Reduce Search Time
```python
# In config.py
SEARCH_DELAY = 2  # seconds between searches (default: 5)
FORM_FILL_TIMEOUT = 10  # seconds (default: 30)
```

### Parallel Applications
```bash
# Run multiple instances (not recommended - platform blocks)
python -m auto_apply.main --apply-only &
python -m auto_apply.main --apply-only &
```

## Platform Support

| Platform | Status | Features |
|----------|--------|----------|
| Lever.co | ✅ Full | Search, apply, cover letter |
| Greenhouse | ✅ Full | Search, apply, cover letter |
| Ashby | ✅ Full | Search, apply, cover letter |
| Custom Forms | ⚠️ Limited | Basic field filling |

## Security & Privacy

### Important Notes
- **Never commit credentials** to the repository
- Use `.env` for API keys (already in `.gitignore`)
- Keep `token.json` and `credentials.json` in `.gitignore`
- Don't share your `profile.json` with sensitive personal info

### Data Stored Locally
- `applied_jobs.json` - keeps track of applications
- `profile.json` - your information
- `cover_letters/` - generated letters (consider privacy)
- Browser profile in `chrome_profile/` (auto-managed)

## Log Files

Application logs are stored in:
- `auto_apply.log` - main application log

Check logs for debugging:
```bash
tail -f auto_apply.log  # Linux/macOS
Get-Content -Tail 50 auto_apply.log  # PowerShell
```

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| No jobs found | Filter too strict | Broaden keywords, reduce filters |
| Forms not filling | Unsupported form layout | Manual intervention, report issue |
| API rate limited | Too many requests | Increase delays in config.py |
| Gmail auth fails | Token expired | Delete `token.json` and re-authenticate |
| Proxy/VPN issues | Geographic restriction | Disable VPN or use residential proxy |

## Development

### Running Tests
```bash
python -m pytest tests/

# With coverage
pytest --cov=auto_apply tests/
```

### Code Structure
```
auto_apply/
├── main.py              # Entry point
├── config.py            # Configuration
├── resume_parser.py     # PDF parsing
├── job_searcher.py      # Job discovery
├── form_filler.py       # Form automation
├── ai_responder.py      # Claude integration
├── cover_letter_gen.py  # Letter generation
├── platforms/           # Platform handlers
│   ├── lever.py
│   ├── greenhouse.py
│   └── ashby.py
└── utils/               # Utility functions
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes (no hardcoded credentials!)
4. Test thoroughly
5. Submit a pull request

## License

[Add your license]

## Support & Contact

For issues, questions, or feature requests:
- GitHub Issues: [Project Repository]
- Email: [your-contact@example.com]

## Additional Resources

- [Anthropic API Documentation](https://docs.anthropic.com)
- [Playwright Documentation](https://playwright.dev/python/)
- [Gmail API Guide](https://developers.google.com/gmail/api)

---

Last Updated: 2026-04-16
Maintainer: [YOUR_NAME]
