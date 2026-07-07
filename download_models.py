"""
Downloads large ML models from HF Hub at container startup.

Classical models (src/data/models/classical/) are small (<5 MB) and committed
directly to git. Large models — InLegalBERT safetensors and the precedent index
— are stored in a private HF Hub model repo and pulled here on first boot.

Required env vars (set in HF Spaces → Settings → Secrets):
  HF_MODEL_REPO  e.g. "ritarshi/smart-legal-models"
  HF_TOKEN       HF access token with read permission
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

MODELS_BASE = Path("src/data/models")
HF_MODEL_REPO = os.getenv("HF_MODEL_REPO", "")
HF_TOKEN = os.getenv("HF_TOKEN") or None

# These files must exist for the app to serve InLegalBERT, precedent, and dense
# retrieval features. Classical models are in git so we don't check for them here.
KEY_FILES = [
    MODELS_BASE / "inlegalbert/fairness/model.safetensors",
    MODELS_BASE / "inlegalbert/outcome/model.safetensors",
    MODELS_BASE / "precedent/precedent_index.pkl",
    MODELS_BASE / "dense/embeddings.npy",
    MODELS_BASE / "dense/corpus_meta.json",
]


def already_present() -> bool:
    missing = [f for f in KEY_FILES if not f.exists()]
    if missing:
        logger.info(f"Missing large model files: {[str(f) for f in missing]}")
    return len(missing) == 0


def download():
    if not HF_MODEL_REPO:
        logger.warning(
            "HF_MODEL_REPO is not set. "
            "InLegalBERT and precedent features will be unavailable. "
            "Set HF_MODEL_REPO and HF_TOKEN in HF Spaces secrets to enable them."
        )
        return

    if already_present():
        logger.info("Large models already present — skipping download.")
        return

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        logger.error("huggingface_hub not installed — cannot download models.")
        sys.exit(1)

    MODELS_BASE.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading large models from HF Hub repo: {HF_MODEL_REPO}")
    logger.info("This will take a few minutes on first boot (~1 GB total)...")

    try:
        snapshot_download(
            repo_id=HF_MODEL_REPO,
            repo_type="model",
            local_dir=str(MODELS_BASE),
            token=HF_TOKEN,
            ignore_patterns=["*.gitattributes", ".gitattributes", "README.md", ".git/*"],
        )
        logger.info("Download complete.")
    except Exception as e:
        logger.error(f"Failed to download models from HF Hub: {e}")
        logger.error(
            "The app will start but InLegalBERT and precedent features won't work. "
            "Check HF_MODEL_REPO and HF_TOKEN are correct in your Spaces secrets."
        )
        # Don't sys.exit — let the app start anyway so other features work
        return

    # Verify key files arrived
    missing = [f for f in KEY_FILES if not f.exists()]
    if missing:
        logger.warning(
            f"Download finished but some files are still missing: {[str(f) for f in missing]}"
        )
    else:
        logger.info("All large models verified successfully.")


if __name__ == "__main__":
    download()
