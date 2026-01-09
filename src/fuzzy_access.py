
def decide(face_score: float, pin_score: float) -> tuple[str, float, str]:
    # Convert raw scores into simple membership values (0.0..1.0)
    # - face_high ~ how much the face score looks 'high'
    # - face_med ~ how much the face score looks 'medium'
    face_high = max(0.0, min(1.0, (face_score - 70) / 30))
    face_med = max(0.0, min(1.0, (face_score - 40) / 30))
    # For PIN we use a crisp threshold: 90+ is considered correct
    pin_ok = 1.0 if pin_score >= 90 else 0.0

    # Rules are intentionally simple and easy to follow:
    # 1) Strong grant when face is high and PIN ok
    r1 = min(face_high, pin_ok)
    # 2) Weaker grant when face is medium but PIN ok
    r2 = min(face_med, pin_ok) * 0.7
    # 3) Minimal grant if PIN ok even when face is low
    r3 = pin_ok * 0.3 if face_score < 40 else 0.0

    # Aggregate the rules by taking the maximum supporting rule and
    # scale to 0..100 for an intuitive overall score.
    score = max(r1, r2, r3) * 100

    # Map numeric score into simple decision categories
    if score >= 60:
        return "GRANTED", score, "High confidence"
    if score >= 35:
        return "GRANTED_MARGINAL", score, "Marginal confidence"
    return "DENIED", score, "Insufficient evidence"
