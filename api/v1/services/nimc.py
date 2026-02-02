from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import json
from base64 import b64encode, b64decode

# -------------------------
# ECC KEY PAIR (PoC ONLY)
# -------------------------
# private_key = ec.generate_private_key(ec.SECP256R1())
# public_key = private_key.public_key()

KEY_FILE = "ecc_private.pem"


class NIMCService:
    
    @staticmethod
    def _get_key():
        if os.path.exists(KEY_FILE):
            return serialization.load_pem_private_key(
                open(KEY_FILE, "rb").read(),
                password=None
            )

        key = ec.generate_private_key(ec.SECP256R1())
        with open(KEY_FILE, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            )
        return key
    
    
    @classmethod
    def _derive_aes_key(cls) -> bytes:
        """
        Derive a stable 32-byte AES key from the ECC private key.
        """
        private_key = cls._get_key()
        public_key = private_key.public_key()

        shared_key = private_key.exchange(
            ec.ECDH(),
            public_key
        )

        aes_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,                # 256-bit AES key
            salt=b"nimc-static-salt", # MUST stay constant
            info=b"nimc-identity-demo",
            backend=default_backend()
        ).derive(shared_key)

        return aes_key


    @classmethod
    def encrypt(cls, data: dict):
        key = cls._derive_aes_key()
        iv = os.urandom(12)

        encryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()

        plaintext = json.dumps(data, sort_keys=True).encode()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return {
            "ciphertext": b64encode(ciphertext).decode(),
            "iv": b64encode(iv).decode(),
            "tag": b64encode(encryptor.tag).decode()
        }
        

    @classmethod
    def decrypt(cls, enc: dict):
        key = cls._derive_aes_key()

        decryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(
                b64decode(enc["iv"]),
                b64decode(enc["tag"])
            ),
            backend=default_backend()
        ).decryptor()

        plaintext = decryptor.update(
            b64decode(enc["ciphertext"])
        ) + decryptor.finalize()
        
        return json.loads(plaintext)
