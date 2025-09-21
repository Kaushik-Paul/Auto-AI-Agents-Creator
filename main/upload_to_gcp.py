import os
import glob
import json
import base64
import zipfile
from datetime import datetime, timezone, timedelta
from google.cloud import storage
from google.oauth2 import service_account

def _get_gcp_credentials():
    """Get GCP credentials from environment variables."""

    project_id = os.getenv("GCP_PROJECT_ID")
    bucket_name = os.getenv("GCP_BUCKET_NAME")
    gcp_service_key = os.getenv("GCP_SERVICE_KEY")

    if not all([project_id, bucket_name, gcp_service_key]):
        raise RuntimeError(
            "Missing one or more GCP environment variables: "
            "GCP_PROJECT_ID, GCP_BUCKET_NAME, GCP_SERVICE_KEY"
        )
    
    service_key = json.loads(base64.b64decode(gcp_service_key).decode("utf-8"))
    return project_id, bucket_name, service_account.Credentials.from_service_account_info(service_key)

def _get_storage_client(project_id, credentials):
    """Initialize and return a GCP Storage client."""

    return storage.Client(project=project_id, credentials=credentials)

def _create_zip(zip_basename, files):
    """Create a zip file from a list of files.
    """

    zip_path = f"{zip_basename}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in files:
            if os.path.isfile(fp):
                zf.write(fp, arcname=os.path.basename(fp))
    return zip_path

def _upload_and_cleanup(bucket, file_paths, blob_prefix, zip_basename, timestamp):
    """
    Upload files to GCP bucket and clean up local files.
    """

    if not file_paths:
        return None
        
    # Create zip
    zip_path = _create_zip(f"{zip_basename}-{timestamp}", file_paths)
    
    try:
        # Upload to GCS
        blob_name = f"{blob_prefix}/{os.path.basename(zip_path)}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(zip_path)
        
        # Generate signed URL
        signed_url = blob.generate_signed_url(
            version="v4",
            method="GET",
            expiration=timedelta(minutes=10),
        )
        return signed_url
    finally:
        # Clean up local files
        _cleanup_files([zip_path] + file_paths)

def _cleanup_files(file_paths):
    """Safely remove a list of files."""
    for file_path in file_paths:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except OSError:
            pass

def upload_to_gcp():
    """
    Main function to upload ideas and agents to GCP Storage.
    """

    # Shared timestamp for both archives (UTC for determinism)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    
    # Initialize GCP client
    project_id, bucket_name, credentials = _get_gcp_credentials()
    client = _get_storage_client(project_id, credentials)
    bucket = client.get_bucket(bucket_name)
    
    # Process ideas
    ideas_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ideas"))
    idea_files = sorted(glob.glob(os.path.join(ideas_dir, "idea*.md"))) \
        if os.path.isdir(ideas_dir) else []
    
    ideas_signed_url = _upload_and_cleanup(
        bucket=bucket,
        file_paths=idea_files,
        blob_prefix="ideas",
        zip_basename="ideas",
        timestamp=timestamp
    )
    
    # Process agents
    main_dir = os.path.abspath(os.path.dirname(__file__))
    agent_files = [
        fp for fp in glob.glob(os.path.join(main_dir, "agent*.py"))
        if os.path.basename(fp) != "agent.py"
    ]
    
    agents_signed_url = _upload_and_cleanup(
        bucket=bucket,
        file_paths=agent_files,
        blob_prefix="auto-agents",
        zip_basename="auto-agents",
        timestamp=timestamp
    )
    
    return {
        "ideas_signed_url": ideas_signed_url,
        "agents_signed_url": agents_signed_url,
    }
