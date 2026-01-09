import cv2
from getpass import getpass
from pathlib import Path
import sys

# If this file is run directly, make sure project root is on sys.path so
if __package__ is None:
    proj_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(proj_root))

import src.db as db
import src.crypto as crypto
import src.face as face
import src.fuzzy_access as fuzzy


def normalize_confidence(confidence: float) -> float:
    # LBPH produces lower confidence for better matches; map to 0..100 (higher better)
    score = max(0.0, 100.0 - confidence)
    return min(100.0, score)


def main():
    # Load users and make sure the DB exists
    db.init_db()
    users = db.get_all_users()
    if not users:
        print("No users enrolled. Run src.enroll.py first.")
        return

    # Take a single snapshot from the camera and detect the largest face
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        print("Camera unavailable")
        cap.release()
        return
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_img = face.detect_largest_face(gray)
    cap.release()
    if face_img is None:
        print("No face detected")
        return

    # Compare the captured face against all stored per-user models and
    # pick the model with the highest (best) normalized score.
    best = None
    for uid, name, model_path, pin_salt, pin_hash in users:
        if not model_path:
            continue
        try:
            label, conf = face.predict_with_model(model_path, face_img)
        except Exception:
            # If a model is missing or corrupted, skip it.
            continue
        score = normalize_confidence(conf)
        if best is None or score > best[2]:
            best = (uid, name, score, pin_salt, pin_hash)

    if best is None:
        print("No matching models found")
        return

    # Below code statement for PIN and verify. PIN verification yields 0 or 100 score
    # here which the fuzzy combiner expects.
    uid, name, face_score, pin_salt, pin_hash = best
    print(f"Best face match: {name} (score={face_score:.1f})")
    pin = getpass("Enter PIN: ").strip()
    pin_ok = crypto.verify_pin(pin, pin_salt, pin_hash)
    pin_score = 100.0 if pin_ok else 0.0

    # Apply the fuzzy decision rules and save the attempt to the DB.
    decision, overall, reason = fuzzy.decide(face_score, pin_score)
    print(f"Decision: {decision} (score={overall:.1f}) - {reason}")

    db.save_log(uid, name, face_score, pin_score, decision, reason)

 
if __name__ == "__main__":
    main()
