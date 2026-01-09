# Dual-Biometric Secure Access System

This project provides a secure access control system using dual biometric verification: face recognition (OpenCV LBPH) and PIN verification (PBKDF2). Access decisions use a simple fuzzy-logic combiner.

Quick setup

1. Create a virtual env and install requirements:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Initialize the database (first run will auto-create DB):

```bash
python src/enroll.py --init-db
```

Enrollment

- Run `python src/enroll.py` and follow prompts to enter a username and PIN. The script captures face images from your webcam, trains a per-user LBPH model and saves user record to the DB.

Authentication

- Run `python src/recognize.py` and follow prompts. The script captures a face, matches against stored models, asks for PIN, uses fuzzy logic to decide access and logs the attempt.

Files added

- `src/db.py` — SQLite DB helpers
- `src/crypto.py` — secure PIN hashing + verification
- `src/face.py` — face capture/train/predict utilities
- `src/fuzzy_access.py` — fuzzy decision logic
- `src/enroll.py` — enrollment CLI
- `src/recognize.py` — authentication CLI

Notes

- This implementation uses per-user LBPH models saved under `models/` and dataset images under `data/datasets/`.
- On Windows, ensure your webcam is available to the scripts.
