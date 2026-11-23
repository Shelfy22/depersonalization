"""Explicit online provisioning step. Run before starting the offline inference service."""

import os

# These must be set before importing huggingface_hub / transformers.
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"

from huggingface_hub import snapshot_download  # noqa: E402

from app.config import Settings  # noqa: E402


def main():
    settings = Settings()
    if settings.enable_rubert:
        snapshot_download(
            settings.rubert_model,
            revision=settings.rubert_revision,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
        )
    if settings.enable_gliner:
        from gliner import GLiNER

        # Also provisions the backbone tokenizer required by this GLiNER generation.
        GLiNER.from_pretrained(
            settings.gliner_model,
            revision=settings.gliner_revision,
            local_files_only=False,
        )
    print("Model provisioning complete. Start the service with HF_HUB_OFFLINE=1.")


if __name__ == "__main__":
    main()
