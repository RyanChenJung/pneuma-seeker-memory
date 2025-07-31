from huggingface_hub import snapshot_download


# Embedding model
repo_id = "BAAI/bge-base-en-v1.5"
local_dir = "bge-base"
snapshot_download(repo_id, local_dir=local_dir, resume_download=True)

# LLM for Pneuma & Processor
repo_id = "Qwen/Qwen3-8B"
local_dir = "qwen3-8b"
snapshot_download(repo_id, local_dir=local_dir, resume_download=True)

# LLM for RAG
repo_id = "mistralai/Mistral-7B-Instruct-v0.3"
local_dir = "mistral-7b"
snapshot_download(repo_id, local_dir=local_dir, resume_download=True)

# LLM for SQL generator
repo_id = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
local_dir = "qwen25coder-1_5b"
snapshot_download(repo_id, local_dir=local_dir, resume_download=True)
