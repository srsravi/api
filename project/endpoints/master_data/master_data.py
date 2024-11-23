from datetime import datetime, timezone
from sqlalchemy import and_
from datetime import datetime
from ...models.admin_user import AdminUser
from sqlalchemy.orm import  joinedload
from datetime import date
from fastapi.encoders import jsonable_encoder

from . import APIRouter, Utility, SUCCESS, FAIL, EXCEPTION ,INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.master_data import DownloadFile
import re
from ...schemas.master_data import getMasterData,CalculateCurrency,KycDocsListReq,Kycheck,Kycenable,CreateKycSchema,kycDocDetailsReqSchema,EditKycSchema
from ...models.user_model import TenantModel
import os
from ...models.user_model import CustomerModal
from sqlalchemy.sql import select, and_, or_, not_,func
import json
from pathlib import Path
from ...models.master_data_models import  MdCountries,MdLocations,MdStates,MdTaskStatus,MdTenantStatus,MdTimeZone,MdUserRole,MdUserStatus
from sqlalchemy import desc, asc
from ...models.master_data_models import  MdServiceTypes,MdLeadSources,MdProfessionTypes,MdProfessionSubTypes,mdIncomeTypes,MdObligationTypes, MdLoanApplicationStatus,MdSubscriptionPlansModel,ServiceConfigurationModel,MdEnquiryStatusModel

# APIRouter creates path operations for product module
from ...constant.messages import MASTER_DATA_LIST
from ...models.admin_user import AdminUser

from ...models.user_model import NotificationModel
from sqlalchemy import delete
from ...common.mail import Email
from fastapi import FastAPI, File, UploadFile,BackgroundTasks
from ...constant import messages as all_messages
from ...library.mfiles import login_user_for_mfiles,get_currency,save_file_in_mfiles,download_files_from_mfiles_to_desired_folder
from fastapi import WebSocket, WebSocketDisconnect
from ...library.webSocketConnectionManager import manager

router = APIRouter(
    prefix="/masterdata",
    tags=["Master Data"],
    responses={404: {"description": "Not found"}},
)
file_to_model = {
            
            "md_countries.json": MdCountries,
            "md_states.json": MdStates,
            "md_locations.json": MdLocations,
            
            "md_task_status.json": MdTaskStatus,
            "md_tenant_status.json": MdTenantStatus,
            "md_timezone.json": MdTimeZone,
            "md_user_roles.json": MdUserRole,
            "md_user_status.json": MdUserStatus,
           
            "md_tanants.json":TenantModel,
            "md_service_types.json":MdServiceTypes,
            "md_lead_sources.json":MdLeadSources,
            "md_profession_types.json":MdProfessionTypes,
            "md_profession_sub_types.json":MdProfessionSubTypes,
            "md_income_types.json":mdIncomeTypes,
            "md_obligation_types.json": MdObligationTypes,
            "md_loan_application_status.json":MdLoanApplicationStatus,
            "md_subscription_plans.json":MdSubscriptionPlansModel,
            "service_configuration.json":ServiceConfigurationModel,
            "md_enquiry_status.json":MdEnquiryStatusModel
           

        }
related_tables ={
   
   "default_admin.json":AdminUser,
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token:str):
    user_data = AuthHandler().verify_ws_token(token)
    if user_data is None or "id" not in user_data:
        return
    else:
        
        socket_id = Utility.generate_websocket_id(user_data)
        print(socket_id)
        await manager.connect(socket_id, websocket)
        try:
            while True:
                await websocket.receive_text()  # Keep connection open
        except WebSocketDisconnect:           
            manager.disconnect(socket_id)

@router.get("/test", response_description="Test Socket")
async def test_socket(auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    socket_id = Utility.generate_websocket_id(auth_user)
    await manager.send_message(socket_id,{"message":"HI first Message","category":"`REDIRECT` or GET_UPDATED_DATA","path":"SETTINGS"})
    return "Success"

       
 
@router.get("/migrate", response_description="Migrate Master Data")
def get_users(db: Session = Depends(get_database_session)):
       
    
        #return {"status": "FAIL", "message": "Data migrated successfully"}
    def insertBulkData(file_to_model):    
        json_directory = Path(__file__).resolve().parent.parent.parent / "master_data"
        batch_size = 500
        for filename in os.listdir(json_directory):
            
            if filename in file_to_model:
                model = file_to_model[filename]
                file_path = json_directory / filename
                with open(file_path, 'r') as file:
                    data = json.load(file)

                batch = []
                for entry in data:
                    # Filter out any keys not matching the model's attributes
                    filtered_entry = {key: value for key, value in entry.items() if hasattr(model, key)}
                    if(filename=="md_countries.json"):
                                        
                        if "zipcodeLength" in filtered_entry and (filtered_entry.get("zipcodeLength",10)):
                            filtered_entry["zipcodeLength"] = int(filtered_entry["zipcodeLength"])
                        else:
                            filtered_entry["zipcodeLength"] = 10

                    
                    record = model(**filtered_entry)
                    batch.append(record)

                    if len(batch) >= batch_size:
                        db.bulk_save_objects(batch)
                        batch.clear()

                if batch:
                    db.bulk_save_objects(batch)

                db.commit()
    #insert Main data
    insertBulkData(file_to_model)
    insertBulkData(related_tables)
    return {"status": "SUCCESS", "message": "Data migrated successfully"}

    

@router.post("/get-master-data", response_description="Migrate Master Data")
def get_users(request: getMasterData ,db: Session = Depends(get_database_session)):
       
    try:
        categories = request.categories
        country_id = None
        state_id = None
        if request.country_id:
            country_id = request.country_id
        if request.state_id :
            state_id = request.state_id    

        
        output ={}
        
        for category in categories:
            if category+".json" in file_to_model:
                model = file_to_model[category+".json"]
                if category=="md_states" and country_id:
                    query = db.query(model).filter(model.countryId==int(country_id))
                    sort_column = getattr(model, "name", None)
                    if sort_column:
                        query = query.order_by(asc(sort_column))
                    else:
                        query = query.order_by(asc("id"))    
                    records = query.all()  
                    output[category] =  [Utility.model_to_dict(record) for record in records]
                elif category=="md_locations" and state_id:
                    query = db.query(model).filter(model.stateId==int(state_id))
                    sort_column = getattr(model, "name", None)
                    if sort_column:
                        query = query.order_by(asc(sort_column))
                    else:
                        query = query.order_by(asc("id"))    
                    records =  query.all()
                    output[category] =  [Utility.model_to_dict(record) for record in records]
                elif category=="transaction_purpose_model":
                    records = db.query(model).order_by(asc("id")) .all()
                    output[category] =  [Utility.model_to_dict(record) for record in records]
                elif category=="md_service_types":
                    records = db.query(model).order_by(asc("id")) .all()
                    output[category] =  [Utility.model_to_dict(record) for record in records]
                
                else:    
                    query = db.query(model)
                    sort_column = getattr(model, "name", None)
                    if sort_column:
                        query = query.order_by(asc(sort_column))
                    else:
                        query = query.order_by(asc("id"))

                    records  = query.all()    
                    output[category] =  [Utility.model_to_dict(record) for record in records]

        return Utility.json_response(status=SUCCESS, message=MASTER_DATA_LIST, error=[], data=output)
    except Exception as e:
        print(e)        
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data=[])





@router.post("/upload-file", response_description="UploadFIles")
async def upload_file(file: UploadFile = File(...),auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        #data = await login_user_for_mfiles()
        #save_in_mfiles_using_directly_file(data["response"],)
        req ={'request_data':{}}
        req["request_data"]["username"] = "mRemit"
        content = await file.read()
        final_result = {"name":'',"content_type":"","size":0}
        final_result["name"] = file.filename
        final_result["content_type"] = file.content_type
        final_result["size"] = len(content)
        data  =  await save_file_in_mfiles(req, content)
        if data is not None:
            final_result["path"] = data["file_name"]
            return Utility.json_response(status=SUCCESS, message=all_messages.FILE_UPLOAD_SUCCESS, error=[], data=final_result)
        else:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/download-file", response_description="Download File")
async def download_file(request: DownloadFile):
    try:
        #"415b9ebac05e5e8e15a87d88b3e146882e2d9053bb2b72112bb1481823aa212996820b25"
        path = request.path
        final_result = {"file_data":''}
        data  =  await download_files_from_mfiles_to_desired_folder(path)
        if data is not None:
            final_result["file_data"] = data
            return Utility.json_response(status=SUCCESS, message=all_messages.FILE_DOWNLOAD_SUCCESS, error=[], data=final_result)
        else:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/get-currency-reates", response_description="Download File")
async def get_currency_rates(request: CalculateCurrency):
    try:
        
        result = await get_currency(request.from_currency,request.to_currency)
        return Utility.json_response(status=SUCCESS, message="", error=[], data=result)                          
                        
    except Exception as E:
        print(E)        
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data=[])



