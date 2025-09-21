# News Aggregator & Auto-Poster (Flask)


## What this does
- Pulls top items from configured RSS feeds
- Fetches article text
- Uses Hugging Face Inference API to combine/rewrite/create summary
- Generates images via a Stable Diffusion HF model
- Uploads images to Google Cloud Storage (public)
- Publishes posts to Blogger using Blogger API


## Requirements
- Python 3.10+
- A Hugging Face API token (set as `HF_TOKEN`)
- Google Cloud project with:
- Blogger API enabled
- OAuth 2.0 credentials.json (OAuth Client ID) for desktop/web flow
- Google Cloud Storage bucket (public or with signed URLs)
- A Blogger blog id (set as `BLOG_ID`)


## Quickstart (local testing)
1. Clone the repo.
2. Create a Python virtualenv and install requirements:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
