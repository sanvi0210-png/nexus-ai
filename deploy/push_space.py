"""Usage: python deploy/push_space.py YOUR_HF_USERNAME/nexus-ai-api   (needs HF_TOKEN env var, write access)"""
import os
import sys

from huggingface_hub import HfApi

repo = sys.argv[1]
api = HfApi(token=os.environ["HF_TOKEN"])
api.create_repo(repo_id=repo, repo_type="space", space_sdk="docker", exist_ok=True)
api.upload_folder(folder_path="hf-space", repo_id=repo, repo_type="space")
print("Uploaded. Build logs: https://huggingface.co/spaces/" + repo)
