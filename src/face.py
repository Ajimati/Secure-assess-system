import cv2
import cv2.face
from pathlib import Path
import numpy as np
import os
import inspect


# Name of the Haar cascade file we need.
_DEFAULT_CASCADE = "haarcascade_frontalface_default.xml"


def _find_haarcascade():
    """Locate the Haar cascade xml file robustly across environments.

    Tries several strategies and returns a string path. Raises RuntimeError
    if the file cannot be found.
    """
    # 1) Typical OpenCV installation exposes the directory at `cv2.data.haarcascades`
    try:
        base = getattr(cv2, "data", None)
        if base is not None:
            base_path = getattr(base, "haarcascades", None)
            if base_path:
                candidate = os.path.join(base_path, _DEFAULT_CASCADE)
                if os.path.exists(candidate):
                    return candidate
    except Exception:
        pass

    # 2) Try to locate near the cv2 module installation (some builds package data differently)
    try:
        cv2_file = inspect.getsourcefile(cv2)
        if cv2_file:
            candidate = os.path.join(os.path.dirname(cv2_file), "data", _DEFAULT_CASCADE)
            if os.path.exists(candidate):
                return candidate
    except Exception:
        pass

    # 3) Try a path relative to this repository (in case the project ships cascades)
    candidate = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", _DEFAULT_CASCADE))
    if os.path.exists(candidate):
        return candidate

    # 4) Last resort: if cv2.data.haarcascades exists return that string (may still fail later)
    try:
        data_module = getattr(cv2, "data", None)
        if data_module is not None:
            haarcascades_path = getattr(data_module, "haarcascades", None)
            if haarcascades_path:
                return str(haarcascades_path + _DEFAULT_CASCADE)
    except Exception:
        pass

    raise RuntimeError("Could not locate Haar cascade xml. Ensure OpenCV data files are installed.")


# Resolved cascade path (string)
CASCADE = _find_haarcascade()


def ensure_dir(p: Path):
    # Ensure the parent directory exists so we can write files there.
    p.parent.mkdir(parents=True, exist_ok=True)


def capture_images_for_user(name: str, out_dir: str | Path, count: int = 20):
    """Capture `count` face images from the webcam and save them.

    - `name` is used to create a folder under `out_dir`.
    - The function shows a small camera window; press 'q' to stop early.
    - Returns the path to the folder where images were saved.
    """
    out_dir = Path(out_dir) / name
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(0)
    detector = cv2.CascadeClassifier(CASCADE)
    captured = 0
    print("Starting capture - press 'q' to quit early")
    while captured < count:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        for (x, y, w, h) in faces:
            # Crop the face region and resize to 200x200 for consistency
            face = gray[y : y + h, x : x + w]
            face_resized = cv2.resize(face, (200, 200))
            fn = out_dir / f"{captured}.png"
            cv2.imwrite(str(fn), face_resized)
            captured += 1
            # Draw a rectangle so the user knows a face was detected
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            break
        cv2.imshow("capture", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
    print(f"Captured {captured} images to {out_dir}")
    return str(out_dir)


def _create_lbph_recognizer() -> cv2.face.LBPHFaceRecognizer:
    """Create and return an LBPH recognizer, trying multiple OpenCV APIs.

    Raises RuntimeError with an action hint if no recognizer is available.
    """
    face_mod = getattr(cv2, "face", None)

    # candidate constructor names to try (module-level and top-level)
    candidates = [
        ("face", "LBPHFaceRecognizer_create"),
        ("face", "createLBPHFaceRecognizer"),
        ("top", "createLBPHFaceRecognizer"),
        ("top", "LBPHFaceRecognizer_create"),
    ]

    for where, name in candidates:
        ctor = None
        if where == "face" and face_mod is not None:
            ctor = getattr(face_mod, name, None)
        if ctor is None:
            ctor = getattr(cv2, name, None)
        if callable(ctor):
            try:
                return ctor()  # type: ignore
            except TypeError:
                # If ctor is a factory requiring different args, just try calling without args
                try:
                    return ctor()  # type: ignore
                except Exception:
                    continue

    raise RuntimeError(
        "LBPHFaceRecognizer is not available in this OpenCV build. "
        "Install the contrib package (e.g. `pip install opencv-contrib-python`) "
        "and ensure the installed version matches your cv2 package."
    )


def train_lbph_model(images_dir: str | Path, model_path: str | Path):
    """Train a simple LBPH face recognizer on images in `images_dir`.

    We train a per-user model: all images in the folder are treated as a
    single class. The trained model is written to `model_path`.
    """
    images_dir = Path(images_dir)
    model_path = Path(model_path)
    imgs = []
    labels = []
    for i, img_path in enumerate(sorted(images_dir.glob("*.png"))):
        im = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        imgs.append(im)
        labels.append(0)  # single label for per-user model
    if not imgs:
        raise RuntimeError("No images to train on")
    recognizer = _create_lbph_recognizer()
    recognizer.train(imgs, np.array(labels))
    ensure_dir(Path(model_path))
    recognizer.write(str(model_path))
    return str(model_path)


def predict_with_model(model_path: str | Path, gray_face_image: np.ndarray):
    """Load a saved model and predict the confidence for `gray_face_image`.

    Returns (label, confidence). For LBPH confidence is lower for better
    matches, so callers may need to convert it to a more intuitive score.
    """
    recognizer = _create_lbph_recognizer()
    recognizer.read(str(model_path))  # type: ignore
    label, confidence = recognizer.predict(gray_face_image)
    return label, confidence


def detect_largest_face(gray_frame: np.ndarray):
    """Detect faces and return the largest one resized to 200x200.

    Returns None if no face is found.
    """
    detector = cv2.CascadeClassifier(CASCADE)
    faces = detector.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        return None
    # pick largest face by area
    faces = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)
    x, y, w, h = faces[0]
    face = gray_frame[y : y + h, x : x + w]
    face_resized = cv2.resize(face, (200, 200))
    return face_resized
