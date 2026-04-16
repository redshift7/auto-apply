# Auto Apply Tool

Automated job application tool that searches and applies to Data Engineer positions on Lever, Greenhouse, and Ashby job boards.

## Features

- 🔍 **Job Search**: Automatically searches Google for matching jobs on Lever, Greenhouse, and Ashby
- 📄 **Resume Parsing**: Extracts your information from PDF resume using AI
- ✍️ **Cover Letter Generation**: Creates personalized cover letters for each application
- 🤖 **AI Responses**: Uses Claude to answer custom application questions
- 📊 **Duplicate Tracking**: Prevents applying to the same job twice
- 📝 **Logging**: Tracks all applications with success/failure status

## Setup

1. **Set your Anthropic API key:**
   ```powershell
   $env:ANTHROPIC_API_KEY = "your-api-key-here"
   ```

2. **Your resume** is configured at:
   `C:\Users\sathv\Desktop\UNH\Sathvik-Resume.pdf`

3. **Parse your resume** (already done, but to re-parse):
   ```bash
   python resume_parser.py
   ```

## Usage

### Basic Usage
```bash
# Search and apply to jobs (default: up to 50 applications)
python main.py

# Limit applications
python main.py --max 10

# Search only (don't apply)
python main.py --search-only

# Run in headless mode (no browser window)
python main.py --headless

# Custom search query
python main.py --query "data analyst intern"

# Re-parse resume before applying
python main.py --parse-resume
```

### Test Individual Components

```bash
# Test resume parsing
python resume_parser.py

# Test job search
python job_searcher.py

# Test cover letter generation
python cover_letter_gen.py

# Test AI responses
python ai_responder.py

# View application stats
python tracker.py
```

## Configuration

Edit `config.py` to customize:

- `SEARCH_QUERY`: Default job search query
- `MAX_APPLICATIONS_PER_RUN`: Max applications per session
- `HEADLESS`: Run browser without window
- `SLOW_MO`: Delay between actions (helps avoid detection)
- `AI_QUESTION_KEYWORDS`: Keywords that trigger AI responses

## File Structure

```
auto_apply/
├── main.py              # Entry point
├── config.py            # Configuration
├── resume_parser.py     # PDF resume parsing
├── job_searcher.py      # Google job search
├── form_filler.py       # Generic form utilities
├── ai_responder.py      # Claude AI integration
├── cover_letter_gen.py  # Cover letter generation
├── tracker.py           # Application tracking
├── platforms/
│   ├── lever.py         # Lever.co handler
│   ├── greenhouse.py    # Greenhouse handler
│   └── ashby.py         # Ashby handler
├── profile.json         # Your parsed resume data
├── applied_jobs.json    # Tracking database
├── cover_letters/       # Generated cover letters
└── auto_apply.log       # Application log
```

## Tips

1. **Start with `--search-only`** to preview jobs before applying
2. **Watch the first few applications** to ensure forms are filled correctly
3. **Review `profile.json`** to ensure your data was extracted correctly
4. **Check `applied_jobs.json`** for application history

## Troubleshooting

- **"No API key found"**: Set `ANTHROPIC_API_KEY` environment variable
- **Google CAPTCHA**: Try using `--headless` mode less frequently
- **Form filling issues**: Some forms may need custom handling

## Customization

To modify the search query, edit `SEARCH_QUERY` in `config.py`:

```python
SEARCH_QUERY = '(site:jobs.lever.co OR site:job-boards.greenhouse.io) intitle:"data engineer"'
```
