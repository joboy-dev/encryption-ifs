import hashlib
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
import ipfshttpclient
from sqlalchemy.orm import Session
from api.core.dependencies.context import add_template_context
from api.db.database import get_db, get_db_with_ctx_manager
from api.utils.loggers import create_logger, log_error
from api.v1.models.user import User
from api.v1.services.nimc import NIMCService
from api.core.dependencies.flash_messages import MessageCategory, flash


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
            flash(request, "Record with this email already exists", MessageCategory.ERROR)
            return RedirectResponse(url="/", status_code=303)
        
        encrypted = NIMCService.encrypt(payload.__dict__)

        encrypted_bytes = json.dumps(encrypted).encode()
        data_hash = hashlib.sha256(encrypted_bytes).hexdigest()

        # Upload to IPFS
        client = ipfshttpclient.connect()
        res = client.add_json(encrypted)
        cid = res
        print(cid)
        
        
        # Commented out ipfsapi code due to errors:
        # client = ipfsapi.connect(
        #     host='127.0.0.1',
        #     port=5001
        # )
        # res = client.add_json(encrypted)
        # cid = res

        # import requests

        # # Test connection to IPFS HTTP API using requests (GET method, but can POST if required)
        # ipfs_api_url = "http://localhost:5001/api/v0/version?stream-channels=true"

        # try:
        #     response = requests.post(ipfs_api_url)
        #     print("IPFS POST /api/v0/version?stream-channels=true response:", response.text)
        # except Exception as e:
        #     print("Failed to reach IPFS API:", str(e))

        # TODO: Storing encrypted data to IPFS via HTTP API,
        # see: https://docs.ipfs.tech/reference/kubo/api/#apiv0add for details.
        # You'd typically need to use the `/api/v0/add` endpoint
        # and send the file contents as form data (multipart/form-data).

        # Example (sketched; see docs for real implementation):
        # files = {'file': json.dumps(encrypted).encode()}
        # add_url = "http://localhost:5001/api/v0/add"
        # add_resp = requests.post(add_url, files=files)
        # print("IPFS add response:", add_resp.text)
        # ipfs_response = add_resp.json() # or parse add_resp.text for 'Hash'/CID
        # cid = ipfs_response.get('Hash', None)
        # cid = None  # Placeholder until real implementation
        # print(cid)
    
        # Blockchain
        # blockchain_tx = record_on_blockchain(user.id_number, data_hash, cid)
        blockchain_tx = None

        # MongoDB
        # User.create(
        #     db=db,
        #     email=payload.get('email'),
        #     cid=cid,
        #     hash=data_hash,
        #     blockchain_tx=blockchain_tx
        # )

        # print({
        #     "cid": cid,
        #     "hash": data_hash
        # })
        
        # request.state['cid'] = cid
        
        flash(request, 'Encryption complete', MessageCategory.SUCCESS)    
    
    except Exception as e:
        log_error(logger, e, "An error occurred during encryption")
        flash(request, 'Encryption failed', MessageCategory.ERROR)    
                
    return RedirectResponse(url="/", status_code=303)
    

@index_router.post("/verify")
async def verify(
    request: Request,
    db: Session=Depends(get_db)
):
    payload = await request.form()
    
    try:
        client = ipfshttpclient.connect()
        encrypted = client.get_json(payload.get('cid'))

        recalculated_hash = hashlib.sha256(
            json.dumps(encrypted).encode()
        ).hexdigest()

        # chain_data = get_blockchain_record(data.user_id)

        # if recalculated_hash != chain_data["hash"]:
        #     raise HTTPException(400, "Data integrity compromised")

        decrypted = NIMCService.decrypt(encrypted)
        print(decrypted)

        flash(request, 'Verification complete', MessageCategory.SUCCESS)    
               
    except Exception as e:
        log_error(logger, e, "An error occurred during encryption")
        flash(request, 'Verification failed', MessageCategory.ERROR)  
    
    return RedirectResponse(url="/", status_code=303)


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
        
        flash(request, 'Fetch complete', MessageCategory.SUCCESS)   
        
        request.state['cid'] = user.cid 
          
    except Exception as e:
        log_error(logger, e, "An error occurred during encryption")
        flash(request, 'Fetching failed', MessageCategory.ERROR)  
    
    return RedirectResponse(url="/", status_code=303)
    