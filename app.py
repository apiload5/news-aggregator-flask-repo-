# app.py
import os
from flask import Flask, jsonify
from dotenv import load_dotenv
import time
import requests
from utils import collect_feed_items, fetch_full_article
from gcs_upload import upload_file_bytes

load_dotenv()

app = Flask(__name__)

HF_TOKEN = os.environ.get('HF_TOKEN')
HF_TEXT_MODEL = os.environ.get('HF_TEXT_MODEL', 'meta-llama/Llama-3-7B-Instruct')
HF_IMG_MODEL = os.environ.get('HF_IMG_MODEL', 'stabilityai/stable-diffusion-2-1')
BLOG_ID = os.environ.get('BLOG_ID')
GCS_BUCKET = os.environ.get('GCS_BUCKET')


HEADERS = {'Authorization': f'Bearer {HF_TOKEN}'}


def hf_text_generation(prompt, max_new_tokens=512):
    url = f'https://api-inference.huggingface.co/models/{HF_TEXT_MODEL}'
    payload = {'inputs': prompt, 'parameters': {'max_new_tokens': max_new_tokens}}
    r = requests.post(url, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    out = r.json()
    # Many HF text models return a list with generated_text
    if isinstance(out, list) and 'generated_text' in out[0]:
        return out[0]['generated_text']
    # Some return dict with 'error'
    if isinstance(out, dict) and 'error' in out:
        raise Exception(out['error'])
    # fallback — try to stringify
    try:
        return out[0].get('generated_text', str(out))
    except Exception:
        return str(out)


def hf_image_generation(prompt):
    # HF image inference can return bytes; depending on model endpoint
    url = f'https://api-inference.huggingface.co/models/{HF_IMG_MODEL}'
    payload = {'inputs': prompt}
    r = requests.post(url, headers=HEADERS, json=payload, timeout=120)
    r.raise_for_status()
    return r.content


# Blogger publishing helper
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']


def get_blogger_service():
    # credentials.json must be present for first-time OAuth flow
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as f:
            f.write(creds.to_json())
    service = build('blogger', 'v3', credentials=creds)
    return service


@app.route('/run', methods=['GET'])
def run_pipeline():
    # 1) collect candidates
    items = collect_feed_items()
    if not items:
        return jsonify({'error': 'no feed items'}), 400

    # 2) pick first (you can improve selection logic)
    chosen = items[0]
    try:
        title, text = fetch_full_article(chosen['link'])
    except Exception:
        title = chosen.get('title', 'Untitled')
        text = chosen.get('summary', '')

    # 3) build prompt for LLM
    prompt = f"""
You are an expert news editor. Combine and rewrite the following article into a neutral, clear news piece.
Output must include:
- Title (single line)
- 2-line summary
- Full article (approx 300-500 words)

Content:
{ text }
"""
    try:
        llm_out = hf_text_generation(prompt, max_new_tokens=700)
    except Exception as e:
        return jsonify({'error': 'LLM text generation failed', 'detail': str(e)}), 500

    # very naive parse: first line title, next paragraph summary
    parts = llm_out.strip().split('\n\n')
    final_title = parts[0].strip() if parts else title
    final_summary = parts[1].strip() if len(parts) > 1 else ''
    final_article = '\n\n'.join(parts[2:]) if len(parts) > 2 else llm_out

    # 4) generate image
    img_prompt = f"Photojournalistic editorial image for: {final_title}. realistic, high-res"
    try:
        img_bytes = hf_image_generation(img_prompt)
    except Exception as e:
        img_bytes = None

    image_url = None
    if img_bytes and GCS_BUCKET:
        dest_name = f"auto_images/{int(time.time())}.png"
        try:
            image_url = upload_file_bytes(GCS_BUCKET, dest_name, img_bytes, content_type='image/png')
        except Exception as e:
            image_url = None

    # 5) create HTML and post to Blogger
    body_html = ''
    if final_summary:
        body_html += f"<p><em>{final_summary}</em></p>"
    if image_url:
        body_html += f"<p><img src=\"{image_url}\" alt=\"{final_title}\"/></p>"
    body_html += '<p>' + final_article.replace('\n', '<br/>') + '</p>'

    try:
        service = get_blogger_service()
        post_body = {
            'kind': 'blogger#post',
            'blog': {'id': BLOG_ID},
            'title': final_title,
            'content': body_html,
            'labels': ['AI-Generated','News']
        }
        post = service.posts().insert(blogId=BLOG_ID, body=post_body, isDraft=False).execute()
    except Exception as e:
        return jsonify({'error': 'Blogger publish failed', 'detail': str(e)}), 500

    return jsonify({'status': 'posted', 'id': post.get('id'), 'url': post.get('url')})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
