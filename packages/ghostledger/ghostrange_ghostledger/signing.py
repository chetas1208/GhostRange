"""Local Ed25519 signing — development identity only."""

from __future__ import annotations

import base64
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from .canonical import canonical_json_bytes


@dataclass
class DevSigner:
    key_id: str
    private_key: Ed25519PrivateKey

    @classmethod
    def generate(cls, key_id: str = "ghostrange-dev") -> "DevSigner":
        return cls(key_id=key_id, private_key=Ed25519PrivateKey.generate())

    def public_key_pem(self) -> str:
        pub = self.private_key.public_key()
        return pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()

    def sign_payload(self, payload: dict) -> str:
        sig = self.private_key.sign(canonical_json_bytes(payload))
        return base64.b64encode(sig).decode("ascii")

    @staticmethod
    def verify_payload(payload: dict, signature_b64: str, public_key_pem: str) -> bool:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        pub = load_pem_public_key(public_key_pem.encode())
        if not hasattr(pub, "verify"):
            return False
        try:
            pub.verify(base64.b64decode(signature_b64), canonical_json_bytes(payload))
            return True
        except Exception:
            return False


def export_private_pem(signer: DevSigner) -> str:
    return signer.private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    ).decode()


__all__ = ["DevSigner", "export_private_pem"]
