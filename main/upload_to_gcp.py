import base64
import json
import os
import shutil
from datetime import datetime, timezone, timedelta

import glob
import zipfile

from google.cloud import storage
from google.oauth2 import service_account


def upload_to_gcp():
    """

    """

    # Shared timestamp for both archives (UTC for determinism)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    # Env and credentials
    project_id = os.getenv("GCP_PROJECT_ID")
    bucket_name = os.getenv("GCP_BUCKET_NAME")
    gcp_service_key = os.getenv("GCP_SERVICE_KEY")

    service_key = json.loads(base64.b64decode(gcp_service_key).decode("utf-8"))
    creds = service_account.Credentials.from_service_account_info(service_key)

    # Initialize the GCP client
    client = storage.Client(project=project_id, credentials=creds)
    bucket = client.get_bucket(bucket_name)

    def _create_zip(zip_basename, files):
        zip_path = f"{zip_basename}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in files:
                if os.path.isfile(fp):
                    zf.write(fp, arcname=os.path.basename(fp))
        return zip_path

    ideas_signed_url = None
    agents_signed_url = None

    # 1) Ideas: idea*.md from ../ideas -> bucket prefix ideas/
    files_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ideas"))
    idea_files = sorted(glob.glob(os.path.join(files_dir, "idea*.md"))) if os.path.isdir(files_dir) else []

    if idea_files:
        ideas_zip_basename = f"ideas-{timestamp}"
        ideas_zip_path = _create_zip(ideas_zip_basename, idea_files)
        ideas_blob_name = f"ideas/{os.path.basename(ideas_zip_path)}"
        ideas_blob = bucket.blob(ideas_blob_name)
        ideas_blob.upload_from_filename(ideas_zip_path)
        # Remove local zip
        os.remove(ideas_zip_path)
        # Delete the original .md files
        for fp in idea_files:
            try:
                os.remove(fp)
            except OSError:
                pass
        # Signed URL
        ideas_signed_url = ideas_blob.generate_signed_url(
            version="v4",
            method="GET",
            expiration=timedelta(minutes=10),
        )

    # 2) Agents: agent*.py (excluding agent.py) from current folder -> bucket prefix agents/
    main_dir = os.path.abspath(os.path.dirname(__file__))
    agent_files = sorted(glob.glob(os.path.join(main_dir, "agent*.py")))
    agent_files = [fp for fp in agent_files if os.path.basename(fp) != "agent.py"]

    if agent_files:
        agents_zip_basename = f"auto-agents-{timestamp}"
        agents_zip_path = _create_zip(agents_zip_basename, agent_files)
        agents_blob_name = f"auto-agents/{os.path.basename(agents_zip_path)}"
        agents_blob = bucket.blob(agents_blob_name)
        agents_blob.upload_from_filename(agents_zip_path)
        # Remove local zip
        os.remove(agents_zip_path)
        # Delete the original agent files
        for fp in agent_files:
            try:
                os.remove(fp)
            except OSError:
                pass
        # Signed URL
        agents_signed_url = agents_blob.generate_signed_url(
            version="v4",
            method="GET",
            expiration=timedelta(minutes=10),
        )

    return {
        "ideas_signed_url": ideas_signed_url,
        "agents_signed_url": agents_signed_url,
    }