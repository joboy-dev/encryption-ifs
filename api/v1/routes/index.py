import hashlib
import json
import libipld
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import ipfshttpclient
from sqlalchemy.orm import Session
from api.core.dependencies.context import add_template_context
from api.db.database import get_db, get_db_with_ctx_manager
from api.utils.loggers import create_logger, log_error
from api.v1.models.user import User
from api.v1.services.nimc import NIMCService
from check_ipfs import check_ipfs


index_router = APIRouter(tags=["External"])
logger = create_logger(__name__)

client = check_ipfs()

@index_router.get("/")
@add_template_context('pages/index.html')
async def index(request: Request) -> dict:
    """Landing page - showcases the platform"""
    return {}


@index_router.get("/app")
@add_template_context('pages/app.html')
async def app(request: Request) -> dict:
    """Main application page - encryption and verification interface"""
    return {}

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

        encrypted_bytes = json.dumps(encrypted, sort_keys=True).encode()
        data_hash = hashlib.sha256(encrypted_bytes).hexdigest()

        # Upload to IPFS
        # client = ipfshttpclient.connect()
        res = client.add_json(encrypted)
        cid = res
        print(cid)
    
        # MongoDB
        user = User.create(
            db=db,
            email=payload.get('email'),
            cid=cid,
            hash=data_hash,
        )
        
        # Blockchain
        blockchain_res = NIMCService.record_on_blockchain(
            user_id=user.id, 
            data_hash=data_hash, 
            cid=cid,
            email=payload.get('email'),
        )
        
        if blockchain_res and blockchain_res.get("status") == "success":
            pass
        else:
            db.rollback()  # Undo the user creation since blockchain recording failed
            logger.warning(f"Blockchain recording failed for user {user.id}")
            raise HTTPException(400, "Failed to record on blockchain")
            
        print({
            "cid": cid,
            "hash": data_hash
        })

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Encryption complete", "cid": cid}
        )
    
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "message": e.detail}
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
        # client = ipfshttpclient.connect()
        encrypted = client.get_json(payload.get('cid'))
        print('encrypted', encrypted)

        recalculated_hash = hashlib.sha256(
            json.dumps(encrypted, sort_keys=True).encode()
        ).hexdigest()
        
        print('recalculated_hash', recalculated_hash)
        
        user = User.fetch_one_by_field(
            db=db, error_message="Record with this cid does not exist",
            cid=payload.get('cid')
        )

        chain_data = NIMCService.get_blockchain_record(user.id)
        
        if not chain_data:
            raise HTTPException(400, "No blockchain record found for this user")

        if recalculated_hash != chain_data.get("Color"):
            raise HTTPException(400, "Data integrity compromised")

        decrypted = NIMCService.decrypt(encrypted)
        print('decrypted', decrypted)
        
        decrypted_data = decrypted.get('_dict')  # stores email, full_name, id_number

        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "message": "Verification complete",
                "decrypted_data": decrypted_data
            }
        )
    
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "message": e.detail}
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
    
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "message": e.detail}
        )
          
    except Exception as e:
        log_error(logger, e, "An error occurred during fetch")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Fetching failed"}
        )
    