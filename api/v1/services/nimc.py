from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import ipfshttpclient
import hashlib
import os
import json
import requests
from base64 import b64encode, b64decode

from sqlalchemy.orm import Session

app = FastAPI(title="Blockchain Identity PoC")

# -------------------------
# ECC KEY PAIR (PoC ONLY)
# -------------------------
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()


class NIMCService:
    
    @classmethod
    def encrypt(cls, data: dict):
        shared_key = private_key.exchange(ec.ECDH(), public_key)

        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'identity-demo',
            backend=default_backend()
        ).derive(shared_key)

        iv = os.urandom(12)
        encryptor = Cipher(
            algorithms.AES(derived_key),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()

        plaintext = json.dumps(data).encode()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return {
            "ciphertext": b64encode(ciphertext).decode(),
            "iv": b64encode(iv).decode(),
            "tag": b64encode(encryptor.tag).decode()
        }
        
    
    @classmethod
    def decrypt(cls, enc: dict):
        shared_key = private_key.exchange(ec.ECDH(), public_key)

        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'identity-demo',
            backend=default_backend()
        ).derive(shared_key)

        decryptor = Cipher(
            algorithms.AES(derived_key),
            modes.GCM(
                b64decode(enc["iv"]),
                b64decode(enc["tag"])
            ),
            backend=default_backend()
        ).decryptor()

        plaintext = decryptor.update(b64decode(enc["ciphertext"])) + decryptor.finalize()
        return json.loads(plaintext)
    

    @classmethod
    def verify(cls):
        pass