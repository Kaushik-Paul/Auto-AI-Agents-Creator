import base64
import json
import os
import shutil
from datetime import datetime, timezone, timedelta

from google.cloud import storage
from google.oauth2 import service_account

def upload_to_gcp(self):
    project_id = os.getenv("GCP_PROJECT_ID")
    bucket_name = os.getenv("GCP_BUCKET_NAME")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    bucket_file_name = f"ai-agentic-coder-{timestamp}"
    gcp_service_key = os.getenv("GCP_SERVICE_KEY")
    local_file_name = bucket_file_name + ".zip"
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../output"))

    # Create a zip file of the output directory
    shutil.make_archive(bucket_file_name, format="zip", root_dir=output_dir)

    service_key = json.loads(base64.b64decode(gcp_service_key).decode('utf-8'))
    creds = service_account.Credentials.from_service_account_info(service_key)

    # Initialize the GCP client
    client = storage.Client(project=project_id, credentials=creds)
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(bucket_file_name)
    blob.upload_from_filename(local_file_name)

    # Delete the temporary zip file after uploading
    os.remove(local_file_name)

    # Get the signed URL for the uploaded file
    signed_url = blob.generate_signed_url(
        version="v4",
        method="GET",
        expiration=timedelta(minutes=10)
    )

    return signed_url