import base64
import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class UnsupportedSigningKeyError(ValueError):
    pass


def _base64url_uint(value: int) -> str:
    if value < 0:
        raise ValueError("unsigned integer cannot be negative")

    size = max(1, (value.bit_length() + 7) // 8)
    raw = value.to_bytes(size, byteorder="big", signed=False)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def load_rsa_public_key(public_key_pem: str) -> rsa.RSAPublicKey:
    try:
        key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
    except (TypeError, ValueError) as exc:
        raise UnsupportedSigningKeyError("invalid PEM public key") from exc

    if not isinstance(key, rsa.RSAPublicKey):
        raise UnsupportedSigningKeyError("only RSA public keys are supported for RS256")
    return key


def rsa_public_key_to_jwk(public_key_pem: str, *, algorithm: str) -> dict[str, Any]:
    if algorithm != "RS256":
        raise UnsupportedSigningKeyError(f"unsupported signing algorithm: {algorithm}")

    key = load_rsa_public_key(public_key_pem)
    numbers = key.public_numbers()

    thumbprint_document = {
        "e": _base64url_uint(numbers.e),
        "kty": "RSA",
        "n": _base64url_uint(numbers.n),
    }
    canonical = json.dumps(
        thumbprint_document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    kid = base64.urlsafe_b64encode(hashlib.sha256(canonical).digest()).rstrip(b"=").decode("ascii")

    return {
        **thumbprint_document,
        "use": "sig",
        "alg": algorithm,
        "kid": kid,
    }
