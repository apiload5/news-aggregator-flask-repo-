# gcs_upload.py
import os
from google.cloud import storage

def upload_file_bytes(bucket_name: str, destination_filename: str, file_bytes: bytes, content_type: str = 'image/png') -> str:
    """Uploads in-memory bytes to GCS and returns a public URL.

    The service account or environment must permit writing. Make bucket public or use signed URLs.
    """
    # If running locally, set GOOGLE_APPLICATION_CREDENTIALS env var to a service account
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_filename)
    blob.upload_from_string(file_bytes, content_type=content_type)
    # Option 1: make the blob public (ensure this is acceptable for your use-case)
    try:
        blob.make_public()
        return blob.public_url
    except Exception:
        # If you prefer signed URL, implement signed URL generation
        return f"gs://{bucket_name}/{destination_filename}"
