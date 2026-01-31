import hashlib
import json
import libipld
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
import ipfshttpclient
from sqlalchemy.orm import Session
from api.core.dependencies.context import add_template_context
from api.db.database import get_db, get_db_with_ctx_manager
from api.utils.loggers import create_logger, log_error
from api.v1.models.user import User
from api.v1.services.nimc import NIMCService


index_router = APIRouter(tags=["External"])
logger = create_logger(__name__)

@index_router.get("/")
@add_template_context('pages/index.html')
async def index(request: Request) -> dict:
    benefits = [
        {
            "icon": "lock",
            "icon_color": "primary",
            "title": "ECC Encryption",
            "description": "Your data is encrypted using Elliptic Curve Cryptography for maximum security.",
        },
        {
            "icon": "circle-check",
            "icon_color": "amber-600",
            "title": "IPFS Storage",
            "description": "Encrypted files are stored on IPFS with immutable Content Identifiers (CID).",
        },
        {
            "icon": "lock",
            "icon_color": "emerald-600",
            "title": "Blockchain Verified",
            "description": "Data hash and CID are recorded on Hyperledger Fabric for tamper detection.",
        }
    ]
    
    return {
        "benefits": benefits
    }

@index_router.post("/encrypt")
async def encrypt(
    request: Request, 
    db: Session=Depends(get_db)
):
    payload = await request.form()
    
    try:
        record = User.fetch_one_by_field(
            db=db, throw_error=False,
            email=payload.get('email')
        )
        
        if record:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Record with this email already exists"}
            )
        
        encrypted = NIMCService.encrypt(payload.__dict__)

        encrypted_bytes = json.dumps(encrypted).encode()
        data_hash = hashlib.sha256(encrypted_bytes).hexdigest()

        # Upload to IPFS
        client = ipfshttpclient.connect()
        res = client.add_json(encrypted)
        cid = res
        print(cid)
    
        # Blockchain
        # blockchain_tx = record_on_blockchain(user.id_number, data_hash, cid)
        blockchain_tx = None

        # MongoDB
        User.create(
            db=db,
            email=payload.get('email'),
            cid=cid,
            hash=data_hash,
            blockchain_tx=blockchain_tx
        )

        print({
            "cid": cid,
            "hash": data_hash
        })

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Encryption complete", "cid": cid}
        )
    
    except Exception as e:
        log_error(logger, e, "An error occurred during encryption")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Encryption failed"}
        )
    

@index_router.post("/verify")
async def verify(
    request: Request,
    db: Session=Depends(get_db)
):
    payload = await request.form()
    
    try:
        client = ipfshttpclient.connect()
        encrypted = client.get_json(payload.get('cid'))
        print('encrypted', encrypted)

        recalculated_hash = hashlib.sha256(
            json.dumps(encrypted).encode()
        ).hexdigest()

        # chain_data = get_blockchain_record(data.user_id)

        # if recalculated_hash != chain_data["hash"]:
        #     raise HTTPException(400, "Data integrity compromised")

        decrypted = NIMCService.decrypt(encrypted)
        print('decrypted', decrypted)

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Verification complete"}
        )
               
    except Exception as e:
        log_error(logger, e, "An error occurred during verification")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Verification failed"}
        )


@index_router.post("/get-cid")
async def fetch_cid(
    request: Request,
    db: Session=Depends(get_db)
):
    payload = await request.form()
    
    try:
        user = User.fetch_one_by_field(
            db=db, error_message="Record with this email does not exist",
            email=payload.get('email')
        )

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Fetch complete", "cid": user.cid}
        )
          
    except Exception as e:
        log_error(logger, e, "An error occurred during fetch")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Fetching failed"}
        )
    