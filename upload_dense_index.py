"""
One-time script: uploads the dense retrieval index to HuggingFace Hub.

Run this once from the project root after building the index:
    python upload_dense_index.py

Required env vars (same ones used by HF Spaces):
    HF_MODEL_REPO   e.g. "ritarshi/smart-legal-models"
    HF_TOKEN        HF access token with write permission
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DENSE_DIR     = Path("src/data/models/dense")
HF_MODEL_REPO = os.getenv("HF_MODEL_REPO", "")
HF_TOKEN      = os.getenv("HF_TOKEN") or None

FILES_TO_UPLOAD = [
    DENSE_DIR / "embeddings.npy",
    DENSE_DIR / "corpus_meta.json",
    DENSE_DIR / "index_meta.json",
]


def main():
    if not HF_MODEL_REPO:
        logger.error(
            "HF_MODEL_REPO is not set.\n"
            "Set it with:  set HF_MODEL_REPO=ritarshi/smart-legal-models\n"
            "              set HF_TOKEN=hf_..."
        )
        sys.exit(1)

    # HF_TOKEN is optional — if not set, huggingface-cli login credentials are used
    if not HF_TOKEN:
        logger.info("HF_TOKEN not set — using cached huggingface-cli login credentials.")

    missing = [f for f in FILES_TO_UPLOAD if not f.exists()]
    if missing:
        logger.error(
            f"Missing files: {[str(f) for f in missing]}\n"
            "Run:  python -m src.scripts.build_dense_index  first."
        )
        sys.exit(1)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        logger.error("huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    api = HfApi(token=HF_TOKEN)

    # Create the repo if it doesn't exist yet (private model repo)
    logger.info(f"Ensuring repo exists: {HF_MODEL_REPO}")
    api.create_repo(
        repo_id=HF_MODEL_REPO,
        repo_type="model",
        private=True,
        exist_ok=True,
    )
    logger.info("Repo ready.")

    logger.info(f"Uploading dense index to: {HF_MODEL_REPO}")
    logger.info("Files: embeddings.npy (121 MB) + corpus_meta.json (14 MB) + index_meta.json")
    logger.info("This may take a few minutes depending on your upload speed...")

    for local_path in FILES_TO_UPLOAD:
        # Upload to dense/ subfolder in the HF repo so snapshot_download places
        # them at src/data/models/dense/ (matching the local path structure)
        repo_path = f"dense/{local_path.name}"
        size_mb   = local_path.stat().st_size / 1e6
        logger.info(f"Uploading {local_path.name} ({size_mb:.1f} MB) → {repo_path}")
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=repo_path,
            repo_id=HF_MODEL_REPO,
            repo_type="model",
        )
        logger.info(f"  ✓ {local_path.name} uploaded")

    logger.info("All dense index files uploaded successfully.")
    logger.info(
        "The app will now download them automatically at startup via download_models.py."
    )


if __name__ == "__main__":
    main()
