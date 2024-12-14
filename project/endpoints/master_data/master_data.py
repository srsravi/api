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
from ...schemas.master_data import getMasterData,CalculateCurrency,ConfigurationAddSchema,ConfigurationEditSchema,ConfigurationListSchema,GetIfscCodeSchema,Kycheck,Kycenable,CreateKycSchema,kycDocDetailsReqSchema,EditKycSchema
from ...models.user_model import TenantModel
import os
from ...models.user_model import CustomerModal
from sqlalchemy.sql import select, and_, or_, not_,func
import json
from pathlib import Path
from ...models.master_data_models import  MdCountries,MdLocations,MdStates,MdTaskStatus,MdTenantStatus,MdTimeZone,MdUserRole,MdUserStatus
from sqlalchemy import desc, asc
from ...models.master_data_models import  MdServiceTypes,MdLeadSources,MdProfessionTypes,MdProfessionSubTypes,mdIncomeTypes,MdOtherIncomeTypes,MdObligationTypes, MdLoanApplicationStatus,MdSubscriptionPlansModel,ServiceConfigurationModel,MdEnquiryStatusModel,MdIfscCodes
from ...models.master_data_models import MdIfscCodes
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
from fastapi import  Request, HTTPException
import razorpay

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
            "md_other_income_types.json":MdOtherIncomeTypes,
            "md_obligation_types.json": MdObligationTypes,
            "md_loan_application_status.json":MdLoanApplicationStatus,
            "md_subscription_plans.json":MdSubscriptionPlansModel,
           
            "md_enquiry_status.json":MdEnquiryStatusModel,
            "md_ifsc_codes.json":MdIfscCodes
           

        }
related_tables ={
   
   "default_admin.json":AdminUser,
    }
third_lavel_related_tables ={
   
    "service_configuration.json":ServiceConfigurationModel,
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
    insertBulkData(third_lavel_related_tables)
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

#GetIfscCodeSchema
@router.post("/get-ifsccodes-data", response_description="Migrate Master Data")
def get_users(filter_data: GetIfscCodeSchema ,db: Session = Depends(get_database_session)):
       
    try:
        query = db.query(MdIfscCodes)
        if filter_data.search_string:
            search = f"%{filter_data.search_string}%"
            query = query.filter(
                or_(
                    MdIfscCodes.BANK.ilike(search),
                    MdIfscCodes.IFSC.ilike(search),
                    MdIfscCodes.BRANCH.ilike(search),
                    MdIfscCodes.CITY1.ilike(search),
                    MdIfscCodes.CITY2.ilike(search),
                    
                )
            )
        total_count = query.count()
        sort_column = getattr(MdIfscCodes, filter_data.sort_by, None)
        if sort_column:
            
            if filter_data.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc("IFSC"))

        # Apply pagination
        offset = (filter_data.page - 1) * filter_data.per_page
        paginated_query = query.offset(offset).limit(filter_data.per_page).all()
        # Create a paginated response
        users_list =[]
        for item in paginated_query:
            temp_item = Utility.model_to_dict(item)
            users_list.append(temp_item)
        response_data = {
            "total_count":total_count,
            "list":users_list,
            "page":filter_data.page,
            "per_page":filter_data.per_page
        }
        return Utility.json_response(status=SUCCESS, message="Successfully retrieved", error=[], data=response_data,code="")    
        
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

#ServiceConfigurationModel

@router.post("/add-service-configuration", response_description="add service configuration")
async def add_service_configuration(request:ConfigurationAddSchema,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        tenant_id =1
        if auth_user["role_id"] ==1:
            tenant_id = request.teanat_id
        elif "tenant_id" in auth_user:
            tenant_id = auth_user["tenant_id"]

        query =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.tenant_id==tenant_id,
                                                            ServiceConfigurationModel.service_type_id==request.service_type_id,
                                                            ServiceConfigurationModel.user_id==request.user_id
                                                            )
        if query.count()>0:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.CONFORMATION_EXISTS, error=[], data=[])
        else:

            new_config = ServiceConfigurationModel(
                service_type_id =request.service_type_id,
                user_id =request.user_id,
                tenant_id = tenant_id
            )
            db.add(new_config)
            db.commit()
            if new_config.id:
                return Utility.json_response(status=SUCCESS, message=all_messages.CONFORMATION_ADDED, error=[], data=[])
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data=[])
    except Exception as E:
        print(E)        
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data=[])

@router.post("/edit-service-configuration", response_description="Edit service configuration")
async def add_service_configuration(request:ConfigurationEditSchema,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        tenant_id =1
        if auth_user["role_id"] ==1:
            tenant_id = request.teanat_id
        elif "tenant_id" in auth_user:
            tenant_id = auth_user["tenant_id"]

        result =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.tenant_id==tenant_id,
                                                            ServiceConfigurationModel.id==request.configuration_id
                                                            
                                                            ).one()
        if result is None :
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Configuration Not Found!", error=[], data=[])
        else:
            result.service_type_id =request.service_type_id
            result.user_id =request.user_id
            db.commit()
            return Utility.json_response(status=SUCCESS, message="Configuration successfully updated", error=[], data={},code="")


        
    except Exception as E:
        print(E)        
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data=[])

@router.post("/get-service-configuration", response_description="UploadFIles")
async def upload_file(request:ConfigurationListSchema,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        tenant_id =1
        if auth_user["role_id"] ==1:
            tenant_id = request.teanat_id
        elif "tenant_id" in auth_user:
            tenant_id = auth_user["tenant_id"]

        query =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.tenant_id==tenant_id)
        if request.user_id and auth_user["role_id"] in [1,2]:
            query = query.filter(ServiceConfigurationModel.user_id==request.user_id)
        elif auth_user["role_id"] !=1 and auth_user["role_id"] !=2:
            query = query.filter(ServiceConfigurationModel.user_id==auth_user["id"])

        query = query.all()
        users_list =[]
        for item in query:
            temp_item = Utility.model_to_dict(item)
            if "tenant_id" in temp_item and temp_item["tenant_id"] is not None:
                temp_item["tenant_details"] = Utility.model_to_dict(item.conf_tenant_details)
           
            if "user_id" in temp_item and temp_item["user_id"] is not None:
                user_details =  Utility.model_to_dict(item.user_details)
                temp_item["user_details"] = {}
                temp_item["user_details"]["id"] =user_details["id"]
                temp_item["user_details"]["tfs_id"] =user_details["tfs_id"]
                temp_item["user_details"]["first_name"] =user_details["first_name"]
                temp_item["user_details"]["last_name"] =user_details["last_name"]
                temp_item["user_details"]["name"] =user_details["name"]
                temp_item["user_details"]["email"] =user_details["email"]
                temp_item["user_details"]["mobile_no"] =user_details["mobile_no"]
                


            if "service_type_id" in temp_item and temp_item["service_type_id"] is not None:
                temp_item["service_details"] = Utility.model_to_dict(item.service_details)
                
            users_list.append(temp_item)    
            
            response_data = {
            "total_count":len(users_list),
            "list":users_list,
            "page":1,
            "per_page":len(users_list)
            }
            return Utility.json_response(status=SUCCESS, message="Configuration List successfully retrieved", error=[], data=response_data,code="")


    except Exception as E:
        print(E)        
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data=[])

razorpay_client = razorpay.Client(auth=("your_key_id", "your_key_secret"))
@router.post("/payment-webhook")
async def payment_webhook(request: Request):
    webhook_data = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    # Verify the webhook signature
    try:
        razorpay_client.utility.verify_webhook_signature(webhook_data, signature, "your_webhook_secret")
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Parse the event data
    data = json.loads(webhook_data)
    event = data['event']
    payload = data['payload']['payment']
    print(payload)
    if event == "payment.captured":
        # Handle success case (successful payment)
        payment_id = payload['id']
        order_id = payload['order_id']
        # Redirect user or update your database
        print(f"Payment Success! Payment ID: {payment_id}, Order ID: {order_id}")
        return {"message": "Payment Success", "payment_id": payment_id, "order_id": order_id}
    
    elif event == "payment.failed":
        # Handle failure case (failed payment)
        payment_id = payload['id']
        order_id = payload['order_id']
        # Handle failure
        print(f"Payment Failed! Payment ID: {payment_id}, Order ID: {order_id}")
        return {"message": "Payment Failed", "payment_id": payment_id, "order_id": order_id}

    return {"message": "OK"}




