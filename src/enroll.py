import argparse
from getpass import getpass
from pathlib import Path
import sys

# When this file is run directly (for example `python src/enroll.py`),
# Python's import system may not include the project root. We add it
# to `sys.path` so `import src.*` works. Running as a module
# (`python -m src.enroll`) does not need this hack, but it's harmless.
if __package__ is None:
    proj_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(proj_root))

import src.db as db
import src.crypto as crypto
import src.face as face


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--init-db", action="store_true")
    args = parser.parse_args()
    if args.init_db:
        db.init_db()
        print("DB initialized")
        return
    # Get a simple username and PIN from the person enrolling. We keep the
    # CLI interaction minimal so beginners can follow along.
    name = input("Enter user name: ").strip()
    pin = getpass("Enter numeric PIN: ").strip()
    if not pin:
        print("PIN required")
        return

    # Capture a small dataset of face images and train a simple model.
    dataset_dir = Path.cwd() / "data" / "datasets"
    images_dir = face.capture_images_for_user(name, dataset_dir, count=20)
    model_dir = Path.cwd() / "models"
    model_path = model_dir / f"{name}.yml"
    model_dir.mkdir(parents=True, exist_ok=True)
    face.train_lbph_model(images_dir, model_path)

    # Hash the PIN (never store the raw PIN!) and save user to DB.
    salt, phash = crypto.hash_pin(pin)
    db.init_db()
    db.add_user(name, str(model_path), salt, phash)
    print(f"Enrolled {name} and saved model to {model_path}")


if __name__ == "__main__":
    main()
