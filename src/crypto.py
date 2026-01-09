

import hashlib
import secrets


def hash_pin(pin: str, iterations: int = 200_000) -> tuple[str, str]:
    """Hash a PIN and return (salt_hex, hash_hex).

    - `pin` is the string the user typed.
    - We generate a random 16-byte salt.
    - `iterations` controls how slow the hash is (higher is safer).
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
    # Return hex strings which are easy to store in SQLite.
    return salt.hex(), dk.hex()


def verify_pin(pin: str, salt_hex: str, hash_hex: str, iterations: int = 200_000) -> bool:
    """Verify `pin` matches the stored `salt_hex` and `hash_hex`.

    Returns True when the PIN is correct. Uses `compare_digest` to avoid
    leaking timing information.
    """
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(dk, expected)


if __name__ == "__main__":
    # Quick demo for beginners to run and see how this module works.
    s, h = hash_pin("1234")
    print("salt", s)
    print("hash", h)
    print("verify", verify_pin("1234", s, h))
