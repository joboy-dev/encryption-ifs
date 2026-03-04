from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import json, subprocess
from base64 import b64encode, b64decode
from decouple import config

# -------------------------
# ECC KEY PAIR (PoC ONLY)
# -------------------------
# private_key = ec.generate_private_key(ec.SECP256R1())
# public_key = private_key.public_key()

KEY_FILE = "ecc_private.pem"

# Configuration for your test-network
FABRIC_SAMPLES_PATH = config("FABRIC_PATH", default="/path/to/fabric-samples/test-network")  # Update this path
FABRIC_PATH = f"{FABRIC_SAMPLES_PATH}/test-network"  # Path to your test-network directory


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
    
    @classmethod
    def _get_fabric_env(cls):
        """Helper to set up the environment variables for Peer CLI"""
        env = os.environ.copy()
        # 1. Path to core.yaml
        env["FABRIC_CFG_PATH"] = f"{FABRIC_SAMPLES_PATH}/config/"
        
        # 2. Identity - Pointing to Org1's admin certificates
        org1_msp = f"{FABRIC_PATH}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
        env["CORE_PEER_MSPCONFIGPATH"] = org1_msp
        env["CORE_PEER_LOCALMSPID"] = "Org1MSP"
        
        # 3. Connection Details
        env["CORE_PEER_ADDRESS"] = "localhost:7051"
        env["CORE_PEER_TLS_ENABLED"] = "true"
        env["CORE_PEER_TLS_ROOTCERT_FILE"] = f"{FABRIC_PATH}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
        env["ORDERER_CA"] = f"{FABRIC_PATH}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
        return env
    
    # @classmethod
    # def record_on_blockchain(cls, user_id: str, hash: str, cid: str):
    #     """
    #     Invokes the chaincode to store the record.
    #     Using peer CLI for the test-network is often the most reliable 
    #     way to bypass deprecated Python SDK issues.
    #     Returns the blockchain transaction ID.
    #     """
    #     try:
    #         command = [
    #             f"{FABRIC_PATH}/bin/peer", "chaincode", "invoke",
    #             "-C", "mychannel", "-n", "basic",
    #             "-c", json.dumps({"Args": ["CreateAsset", user_id, hash, cid]})
    #         ]
    #         result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    #         if result.returncode == 0:
    #             return {"status": "success", "message": "Record stored on blockchain"}
    #         else:
    #             print(f"Blockchain Error: {result.stderr}")
    #             return None
    #     except Exception as e:
    #         print(f"Blockchain Error: {e}")
    #         return None
    
    @classmethod
    def record_on_blockchain(cls, user_id: str, data_hash: str, cid: str):
        try:
            orderer_ca = f"{FABRIC_PATH}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
            
            command = [
                f"{FABRIC_SAMPLES_PATH}/bin/peer", "chaincode", "invoke",
                "-o", "localhost:7050",
                "--tls",
                "--cafile", orderer_ca,
                "-C", config("CHANNEL_NAME"), "-n", "basic",
                "--peerAddresses", "localhost:7051",
                "--tlsRootCertFiles", f"{FABRIC_PATH}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt",
                "-c", json.dumps({"Args": ["CreateAsset", str(user_id), data_hash, cid]})
            ]
            
            result = subprocess.run(
                command, 
                env=cls._get_fabric_env(),
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                print(result.stdout)
                return {"status": "success", "tx_id": "captured_from_stdout"}
            else:
                print(f"Blockchain Error: {result.stderr}")
                return None
        except Exception as e:
            print(f"Exception: {e}")
            return None

    
    @classmethod
    def get_blockchain_record(cls, user_id: str):
        """
        Queries the ledger to get the original hash for comparison.
        """
        try:
            command = [
                f"{FABRIC_SAMPLES_PATH}/bin/peer", "chaincode", "query",
                "-C", config("CHANNEL_NAME"), "-n", "basic",
                "-c", json.dumps({"Args": ["GetAsset", str(user_id)]})
            ]
            result = subprocess.run(
                command,
                env=cls._get_fabric_env(),
                capture_output=True, 
                text=True, 
                timeout=30
            )
            if result.returncode == 0:
                output = json.loads(result.stdout)
                print(output)
                return output
            else:
                print(f"Query Error: {result.stderr}")
                return None
        except Exception as e:
            print(f"Query Error: {e}")
            return None
