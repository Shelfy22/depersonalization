"""Create a local configuration with a random API secret. Never overwrite an existing .env."""

import argparse
import re
import secrets
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", action="store_true", help="Use the Docker model-cache path")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    content = (root / ".env.example").read_text(encoding="utf-8")
    values = {
        "ANON_API_KEY": secrets.token_urlsafe(32),
        "HF_HOME": "/models" if args.docker else (root / "models").as_posix(),
    }
    for key, value in values.items():
        content = re.sub(rf"(?m)^{key}=.*$", lambda _, replacement=f"{key}={value}": replacement, content)
    destination = root / ".env"
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as output:
            output.write(content)
    except FileExistsError:
        parser.exit(1, ".env already exists; existing secrets and settings were preserved.\n")
    print("Created .env with a random API key. Read it locally; do not commit or share the key.")


if __name__ == "__main__":
    main()
