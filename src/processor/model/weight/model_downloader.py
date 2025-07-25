from huggingface_hub import hf_hub_download, snapshot_download
from huggingface_hub import login

# Embedding model
repo_id = "BAAI/bge-base-en-v1.5"
local_dir = "bge-base"
snapshot_download(repo_id, local_dir=local_dir, resume_download=True)

# LLM
repo_id = "Qwen/Qwen3-8B"
local_dir = "qwen3-8b"
snapshot_download(repo_id, local_dir=local_dir, resume_download=True)

# OLD MODEL:
# repo_id = "Qwen/Qwen2.5-7B-Instruct"
# local_dir = "qwen25-7b"
# snapshot_download(repo_id, local_dir=local_dir, resume_download=True)
