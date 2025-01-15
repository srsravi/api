from datetime import datetime, timezone
from sqlalchemy import and_
from datetime import datetime
from ...models.admin_user import AdminUser
from ...models.master_data_models import MdUserRole,MdUserStatus

from . import APIRouter,Utility, SUCCESS, FAIL, EXCEPTION ,INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.register import addSalesUserSchema, TenantSchema,TenantInvitationSchema,AdminRegister,InvitationSchema,TenantUserSchema,resetPassword,UpdateAdminStatus,SetPasswordSchema,UpdateAdminPassword,ForgotPassword
import re
from ...schemas.register import addSalesUserSchema,addAgentUserSchema
from ...schemas.login import Login
from fastapi import BackgroundTasks
from ...common.mail import Email
from ...constant.status_constant import WEB_URL
import os
import json
from pathlib import Path
from ...models.user_model import TenantModel
from ...models.user_model import CustomerModal
from...models.admin_configuration_model import tokensModel

from ...schemas.transaction import CreateCharges,EditCharges, ChargesListReqSchema,UpdateStatusSchema
from ...constant import messages as all_messages
from sqlalchemy.orm import  joinedload
from sqlalchemy import desc, asc
from sqlalchemy.sql import select, and_, or_, not_,func
from datetime import date, datetime,timezone,timedelta
from ...schemas.user_schema import UserDetailsRequest,UserFilterRequest,GetBranchListRequestSchema,PaginatedAdminUserResponse,BranchListResponseSchema,GetUserDetailsReq,UserListResponse, UpdateKycDetails,UpdateProfile,BeneficiaryRequest,BeneficiaryEdit, GetBeneficiaryDetails, ActivateBeneficiary,UpdateBeneficiaryStatus, ResendBeneficiaryOtp,BeneficiaryResponse
from ...aploger import AppLogger

# APIRouter creates path operations for product module
router = APIRouter(
    prefix="/admin",
    tags=["Admin Authentication"],
    responses={404: {"description": "Not found"}},
)

#@router.post("/admin-register", response_description="Admin User Registration")
async def register(request: AdminRegister, db: Session = Depends(get_database_session)):
    try:
        user_name = request.user_name
        contact = request.mobile_no
        email = request.email
        password = request.password
        if user_name == '' or contact == '' or email == '' or password == '':
            return Utility.json_response(status=FAIL, message="Provide valid detail's", error=[], data={})
        if user_name is None or contact is None or email is None or password is None:
            return Utility.json_response(status=FAIL, message="Provide valid detail's", error=[], data={})
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, email):
            return Utility.json_response(status=FAIL, message="Provide valid email", error=[], data={})
        # contact_digits = math.floor(math.log10(contact)) + 1
        if len(str(contact)) < 7 or len(str(contact)) > 15:
            return Utility.json_response(status=FAIL, message="Mobile number not valid. Length must be 7-13.",
                                         error=[], data={})
        user_with_email = db.query(AdminUser).filter(AdminUser.email == email).all()
        if len(user_with_email) != 0:
            return Utility.json_response(status=FAIL, message="Email already exists", error=[], data={})

        user_data = AdminUser(role_id =1,status_id=3, email=email,user_name=user_name, mobile_no=contact,password=AuthHandler().get_password_hash(str(password)))
        db.add(user_data)
        db.flush()
        db.commit()
        
        if user_data.id:
            return Utility.json_response(status=SUCCESS, message="Admin Registered Successfully", error=[],
                                         data={"user_id": user_data.id})
        else:
            return Utility.json_response(status=FAIL, message="Something went wrong", error=[], data={})
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=FAIL, message="Something went wrong", error=[], data={})

@router.post("/add-user", response_description="add user")
async def add_user(request:addSalesUserSchema,background_tasks: BackgroundTasks,login_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        if login_user["role_id"] not in [1,2,3,4]:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={})
       
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, request.email):
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_EMAIL, error=[], data={})
       
        user_id=login_user["id"]
        if login_user["role_id"] ==1:
            tenant_id=request.tenant_id
        else:
            tenant_id=login_user["tenant_id"]
        email = request.email
        first_name =  request.first_name
        last_name  =  request.last_name
        mobile_no  =  request.mobile_no
        experience =  request.experience
        role_id    =  request.role_id
        gender =  None
        country_id = None
        state_id = None
        location_id =  None
        pincode = None
        date_of_birth =None
        
        if request.gender:
            gender = request.gender
        
        
        otp=str(Utility.generate_otp())
        #profile_image =  request.first_name
        exist_user=db.query(AdminUser).filter(AdminUser.email==request.email).first()
        if exist_user:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Email already exists", error=[], data={})
        password=AuthHandler().get_password_hash(otp)
        name = first_name
        if first_name and last_name:
            name = first_name+" "+last_name
        user_data={"experience":experience,"tenant_id":tenant_id,"first_name":first_name,"last_name":last_name, "name":name,"password":password,"email":email,"mobile_no":mobile_no,"role_id":role_id,"status_id":2}
        
        user_data["created_by"] = login_user["id"]
        user_data["created_by_role"] =  login_user["role_id"]
        new_user = AdminUser(**user_data)
        db.add(new_user)
        db.commit()
        if new_user.id:
            if experience:
                new_user.experience = experience
            category="ADD_USER"
            user_dict={"user_id":new_user.id,"catrgory":category,"otp":otp}
            token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":role_id,"email":request.email,"name":name})
            user_dict["token"]=token
            user_dict["ref_id"]=new_user.id
            db.add(tokensModel(**user_dict))
            
            link = f'''{WEB_URL}set-password?token={token}&user_id={new_user.id}'''
            background_tasks.add_task(Email.send_mail, recipient_email=[email], subject="Welcome to TFS", template='add_user.html',data={"name":name,"link":link})
            tfs_id = Utility.generate_tfs_code(role_id)
            new_user.tfs_id = f"{tfs_id}{new_user.id}"
            db.commit()
            return Utility.json_response(status=SUCCESS, message=all_messages.REGISTER_SUCCESS, error=[], data={})
        else:
            db.rollback()
            return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})


    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})

#addAgentUserSchema
@router.post("/add-agent", response_description="add user")
async def add_user(request:addAgentUserSchema,background_tasks: BackgroundTasks,login_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        if login_user["role_id"] not in [1,2,3,4]:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={})
       
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, request.email):
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_EMAIL, error=[], data={})
       
        user_id=login_user["id"]
        
        if login_user["role_id"] ==1:
            tenant_id=request.tenant_id
        else:
            tenant_id=login_user["tenant_id"]
        email = request.email
        first_name =  request.first_name
        last_name  =  request.last_name
        mobile_no  =  request.mobile_no
        experience =  request.experience
        role_id    =  request.role_id
        gender =  None
        country_id = None
        state_id = None
        location_id =  None
        pincode = None
        date_of_birth =None
        if request.country_id:
            country_id = request.country_id
        if request.state_id:
            state_id = request.state_id
        if request.location_id:
            location_id = request.location_id
        if request.pincode:
            pincode = request.pincode
        if request.gender:
            gender = request.gender
        if request.date_of_birth:
            date_of_birth = request.date_of_birth
            
        
        
        otp=str(Utility.generate_otp())
        #profile_image =  request.first_name
        exist_user=db.query(AdminUser).filter(AdminUser.email==request.email).first()
        if exist_user:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Email already exists", error=[], data={})
        password=AuthHandler().get_password_hash(otp)
        name = first_name
        if first_name and last_name:
            name = first_name+" "+last_name
        user_data={"experience":experience,"tenant_id":tenant_id,"first_name":first_name,"last_name":last_name, "name":name,"password":password,"email":email,"mobile_no":mobile_no,"role_id":role_id,"status_id":2}
        
        if request.role_id ==4:
            
            user_data["alternate_mobile_no"] = request.aternate_mobile_no
            user_data["passport"] = request.passport#.encode("utf-8")
            user_data["aadhaar_card"] = request.aadhaar_card#.encode("utf-8")
            user_data["selfie"] = request.selfie#.encode("utf-8")
            user_data["present_address"] = request.present_address
            user_data["present_occupation"] = request.present_occupation
            user_data["employer_name"] = request.employer_name
            user_data["qualification"] = request.qualification
            user_data["account_holder_name"] = request.account_holder_name
            user_data["bank_name"] = request.bank_name
            user_data["bank_account_number"] = request.bank_account_number
            user_data["ifsc_code"] = request. ifsc_code
            user_data["upload_check"] = request.upload_check#.encode("utf-8")
            user_data["referrals"] = request.referrals
            user_data["country_id"] = country_id
            user_data["state_id"] = state_id
            user_data["location_id"] = location_id
            user_data["pincode"] = pincode
            user_data["gender"] = gender
            user_data["date_of_birth"] = date_of_birth
            user_data["created_by"] = login_user["id"]
            user_data["created_by_role"] =  login_user["role_id"]
            
           

        new_user = AdminUser(**user_data)

        db.add(new_user)
        db.commit()
        if new_user.id:
            if experience:
                new_user.experience = experience
            category="ADD_USER"
            user_dict={"user_id":new_user.id,"catrgory":category,"otp":otp}
            token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":role_id,"email":request.email,"name":name})
            user_dict["token"]=token
            user_dict["ref_id"]=new_user.id
            db.add(tokensModel(**user_dict))
            
            link = f'''{WEB_URL}set-password?token={token}&user_id={new_user.id}'''
            background_tasks.add_task(Email.send_mail, recipient_email=[email], subject="Welcome to TFS", template='add_user.html',data={"name":name,"link":link})
            tfs_id = Utility.generate_tfs_code(role_id)
            new_user.tfs_id = f"{tfs_id}{new_user.id}"
            db.commit()
            return Utility.json_response(status=SUCCESS, message=all_messages.REGISTER_SUCCESS, error=[], data={})
        else:
            db.rollback()
            return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})


    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message=str(E), error=[], data={})

@router.post("/set-password", response_description="Forgot Password")
async def reset_password(request: resetPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        token = str(request.token)
        password =  request.password
        category ="ADMIN_FORGOT_PASSWORD"
        customer =0
        if request.customer:
            customer = request.customer
        
        query = db.query(AdminUser).filter(AdminUser.id == user_id)
        if customer>=1:
            category ="CUSTOMER_FORGOT_PASSWORD"
            query = db.query(CustomerModal).filter(CustomerModal.id == user_id)

        user_obj = query.first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            if user_obj.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={},code="LOGOUT_ACCOUNT")
            elif user_obj.status_id == 5:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={},code="LOGOUT_ACCOUNT")
            
            token_data = db.query(tokensModel).filter(tokensModel.token == token, tokensModel.user_id==user_id, tokensModel.active==True).first()
            
            if token_data is None:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Invalid Token", error=[], data={},code="INVALIED_TOKEN")
            
            tokendata = AuthHandler().decode_otp_token(token_data.token)
            
            if tokendata is None :
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="The time you were taken has expired!", error=[], data={},code="INVALIED_TOKEN")
            
            user_obj.token = ''
            user_obj.otp = ''
            user_obj.password =AuthHandler().get_password_hash(password)
            user_obj.status_id = 3
            user_obj.login_fail_count = 0
            token_data.active = False
            
            db.commit()
            rowData = {}
            rowData["user_id"] = user_obj.id
            rowData['name'] = f"""{user_obj.first_name} {user_obj.last_name}"""
            background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject=all_messages.RESET_PASSWORD_SUCCESS, template='reset_password_success.html',data=rowData )               
            #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
            
            return Utility.json_response(status=SUCCESS, message=all_messages.RESET_PASSWORD_SUCCESS, error=[], data={"user_id":user_obj.id,"email":user_obj.email},code="")
        
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/login", response_description="Login")
def login(request: Login, background_tasks:BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        email = request.email
        password = request.password
        user_obj = db.query(AdminUser).filter(AdminUser.email == email)
      
        login_count =0
        if user_obj.count() <= 0:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.EMAIL_NOT_REGISTERED, error=[], data={})
        user_data = user_obj.first()
        
        
        if user_data.status_id !=3:
            
            msg = all_messages.PROFILE_INACTIVE
            if user_data.status_id == 1:
                msg = all_messages.PENDING_PROFILE_COMPLATION
            if user_data.status_id == 2:
                msg = all_messages.PENDING_EMAIL_VERIFICATION
            elif user_data.status_id == 4:
                msg = all_messages.PROFILE_INACTIVE
            elif user_data.status_id == 5:
                msg = all_messages.PROFILE_DELETED
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=msg, error=[], data={})
        else:
            user_dict = Utility.model_to_dict(user_data)
            if user_dict["tenant_id"]:
                user_dict["tenant_details"] = Utility.model_to_dict(user_data.admin_tenant_details)
            if "status_id" in user_dict:
                user_dict["status_details"] = Utility.model_to_dict(user_data.status_details)
            if "role_id" in user_dict:
                user_dict["role_details"] = Utility.model_to_dict(user_data.role_details)
            
            verify_password = AuthHandler().verify_password(str(password), user_data.password)
            current_time = datetime.now(timezone.utc)
            naive_datetime = datetime.now()
            naive_datetime_aware = naive_datetime.replace(tzinfo=timezone.utc)
            if user_data.login_attempt_date is None:
                user_data.login_attempt_date = datetime.now(timezone.utc)


            if user_data.login_attempt_date is not None and user_data.login_attempt_date.tzinfo is None:
                user_data.login_attempt_date = user_data.login_attempt_date.replace(tzinfo=timezone.utc)

            
            if not verify_password:
                login_fail_count = user_data.login_fail_count
                
                if login_fail_count >=3:
                    time_difference = current_time - user_data.login_attempt_date
                    
                    if time_difference >= timedelta(hours=24):
                        print("24 Completed")
                        user_obj.update({ AdminUser.login_attempt_date:datetime.now(timezone.utc),AdminUser.login_fail_count:0}, synchronize_session=False)
                        db.flush()
                        db.commit()
                    else:
                        print("24 Not Completed")
                        # Access denied (less than 24 hours since last login)
                        otp =Utility.generate_otp()
                        token = AuthHandler().encode_token({"otp":otp})
                        user_data.token = token
                        user_data.otp = otp
                        rowData ={}
                        #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
                        rowData["otp"] = otp
                        rowData["user_id"] = user_data.id
                        rowData['name'] = f"""{user_data.first_name} {user_data.last_name}"""
                        rowData["reset_link"] = f'''{WEB_URL}ForgotPassword?token={token}&user_id={user_data.id}'''
                        user_obj.update({ AdminUser.otp:otp,AdminUser.token:token}, synchronize_session=False)
                        db.commit()
                        background_tasks.add_task(Email.send_mail,recipient_email=[user_data.email], subject="Account Locked & Reset Password link", template='invalid_login_attempts.html',data=rowData )               
                    
                        user_obj.update({AdminUser.login_fail_count:AdminUser.login_fail_count+1}, synchronize_session=False)
                        db.flush()
                        db.commit()
                        #ACCOUNT_LOCKED
                        return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.ACCOUNT_LOCKED, error=[], data={})
                    #Wit for 24 Hourse
                else:
                    
                    user_obj.update({ AdminUser.login_attempt_date:datetime.now(timezone.utc),AdminUser.login_fail_count:login_fail_count+1}, synchronize_session=False)
                    db.commit()
                    
                return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_CREDENTIALS, error=[], data={})
            else:
               
                
                if user_data.login_fail_count >=3:
                
                    time_difference = current_time - user_data.login_attempt_date
                    
                    if time_difference >= timedelta(hours=24):
                        print("24 Completed")
                        
                        user_obj.update({ AdminUser.login_attempt_date:datetime.now(timezone.utc),AdminUser.login_fail_count:0}, synchronize_session=False)
                        db.commit()
                    else:        
                        return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.ACCOUNT_LOCKED, error=[], data={})
                login_token = AuthHandler().encode_token(user_dict, 1200)
                if not login_token:
                    # return Utility.json_response(status=FAIL, message=all_messages.INVALIED_CREDENTIALS, error=[], data={})

                    return Utility.json_response(status=FAIL, message=all_messages.SOMTHING_WRONG, error=[], data={})
                    
                else:
                    print("1")                    
                    login_count = user_data.login_count+1                    
                    user_obj.update({ AdminUser.login_fail_count:0,AdminUser.login_count:login_count,AdminUser.last_login:datetime.now(timezone.utc)}, synchronize_session=False)
                    db.commit()
                    print("2")
                    
                    
                    #user_dict = {c.name: getattr(user_data, c.name) for c in user_data.__table__.columns}
                    #print(user_dict)
                    if "password" in user_dict:
                        del user_dict["password"]
                    if "token" in user_dict:
                        del user_dict["token"]
                    if "otp" in user_dict:
                        del user_dict["otp"]
                    if "login_fail_count" in user_dict:
                        del user_dict["login_fail_count"]
                    if "login_attempt_date" in user_dict:
                        del user_dict["login_attempt_date"]
                    if "login_token" in user_dict:
                        del user_dict["login_token"]    
                    user_dict["token"] = login_token
                    if user_data.date_of_birth is not None:
                        user_dict["date_of_birth"] = str(user_data.date_of_birth)
                    #del user_dict.password
                    #del user_dict.otp
                    return Utility.dict_response(status=SUCCESS, message=all_messages.SUCCESS_LOGIN, error=[], data=user_dict)

    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
@router.post("/forgot-password", response_description="Forgot Password")
async def forgot_password(request: ForgotPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        
        email = request.email
        customer = 0
        if request.customer:
            customer = request.customer
        #date_of_birth = request.date_of_birth
        query = db.query(AdminUser).filter(AdminUser.email == email)
        category ="ADMIN_FORGOT_PASSWORD"
        if customer>=1:
            category ="CUSTOMER_FORGOT_PASSWORD"
            query = db.query(CustomerModal).filter(CustomerModal.email == email)

        user_obj = query.first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            if user_obj.status_id ==2 or user_obj.status_id ==3 :
                # if user_obj.date_of_birth != date_of_birth:
                #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.INVALID_BIRTHDATE, error=[], data={},code="")
                
                rowData = {}
                udata = Utility.model_to_dict(user_obj)
                rowData['user_id'] = udata["id"]
                rowData['email'] = user_obj.email
                rowData['first_name'] = user_obj.first_name
                rowData['last_name'] = user_obj.last_name
                #rowData['country_id'] = user_obj.country_id
                #rowData['mobile_no'] = udata.get("mobile_no",'')
                #rowData['date_of_birth'] = udata.get("date_of_birth",'')
                rowData['status_id'] = user_obj.status_id            
                otp =Utility.generate_otp()
                #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
                rowData["otp"] = otp
                rowData["user_id"] = user_obj.id
                rowData['name'] = f"""{user_obj.name}"""
                
                Utility.inactive_previous_tokens(db=db, catrgory = category, user_id = udata["id"])
                user_dict={"user_id":udata["id"],"catrgory":category,"otp":otp}
                token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"role_id":user_obj.role_id,"email":user_obj.email,"name":user_obj.name})
                user_dict["token"]=token
                user_dict["ref_id"]=user_obj.id
                db.add(tokensModel(**user_dict))
                rowData["reset_link"] =  f'''{WEB_URL}set-password?token={token}&user_id={user_obj.id}&customer={customer}''' #f'''{WEB_URL}forgotPassword?token={token}&user_id={user_obj.id}'''
                db.commit()

                background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject="Reset Password link", template='forgot_password.html',data=rowData )               
                return Utility.json_response(status=SUCCESS, message="Reset Password link is sent to your email", error=[], data={"user_id":user_obj.id},code="")
            
            elif  user_obj.status_id == 1:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="PROFILE_COMPLATION_PENDING")
            elif  user_obj.status_id == 2:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="EMAIL_VERIFICATION_PENDING")
            elif user_obj.status_id == 3:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={})
            elif user_obj.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={})
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/resend-activation-link", response_description="Resend Activation Link")
async def forgot_password(request: ForgotPassword,background_tasks: BackgroundTasks,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:

        if auth_user["role_id"] not in [1,2]:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")

        
        email = request.email
        customer = 0
        if request.customer:
            customer = request.customer
        category ="ADMIN_FORGOT_PASSWORD"
        query = db.query(AdminUser).filter(AdminUser.email == email)
        if customer>=1:
            category ="CUSTOMER_FORGOT_PASSWORD"
            query = db.query(CustomerModal).filter(CustomerModal.email == email)
        user_obj = query.first()
        if auth_user["role_id"]==2:
            if user_obj.tenant_id != auth_user["tenant_id"]:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")

        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            if user_obj.status_id ==2 or user_obj.status_id ==3 :
                # if user_obj.date_of_birth != date_of_birth:
                #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.INVALID_BIRTHDATE, error=[], data={},code="")
                
                rowData = {}
                udata = Utility.model_to_dict(user_obj)
                rowData['user_id'] = udata["id"]
                rowData['email'] = user_obj.email
                rowData['first_name'] = user_obj.first_name
                rowData['last_name'] = user_obj.last_name
                #rowData['country_id'] = user_obj.country_id
                #rowData['mobile_no'] = udata.get("mobile_no",'')
                #rowData['date_of_birth'] = udata.get("date_of_birth",'')
                rowData['status_id'] = user_obj.status_id            
                otp =Utility.generate_otp()
                #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
                rowData["otp"] = otp
                rowData["user_id"] = user_obj.id
                rowData['name'] = f"""{user_obj.name}"""
                
                
                Utility.inactive_previous_tokens(db=db, catrgory = category, user_id = udata["id"])
                user_dict={"user_id":udata["id"],"catrgory":category,"otp":otp}
                token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"role_id":user_obj.role_id,"email":user_obj.email,"name":user_obj.name})
                user_dict["token"]=token
                user_dict["ref_id"]=user_obj.id
                db.add(tokensModel(**user_dict))
                rowData["reset_link"] =  f'''{WEB_URL}set-password?token={token}&user_id={user_obj.id}&customer={customer}''' #f'''{WEB_URL}forgotPassword?token={token}&user_id={user_obj.id}'''
                db.commit()

                background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject="Reset Password link", template='forgot_password.html',data=rowData )               
                return Utility.json_response(status=SUCCESS, message="Reset Password link is sent to email", error=[], data={"user_id":user_obj.id},code="")
            
            elif  user_obj.status_id == 1:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="PROFILE_COMPLATION_PENDING")
            elif  user_obj.status_id == 2:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="EMAIL_VERIFICATION_PENDING")
            elif user_obj.status_id == 3:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={})
            elif user_obj.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={})
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/update-password", response_description="Update Admin Password")
async def reset_password(request: UpdateAdminPassword,background_tasks: BackgroundTasks,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        old_password=request.old_password
        password =  request.password
        customer = 0
        if request.customer:
            customer = request.customer
        query = db.query(AdminUser).filter(AdminUser.id == user_id)
        user_obj = query.first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        valid=AuthHandler().verify_password(old_password,user_obj.password)
        if not valid:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Invalid current Password", error=[], data={},code="INVALID_PASSWORD")
        user_obj.password =AuthHandler().get_password_hash(password)
        db.commit()
        rowData = {}                
        rowData["user_id"] = user_obj.id
        rowData['name'] = user_obj.name
        #background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject=all_messages.RESET_PASSWORD_SUCCESS, template='reset_password_success.html',data=rowData )               
        db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
        return Utility.json_response(status=SUCCESS, message=all_messages.RESET_PASSWORD_SUCCESS, error=[], data={"user_id":user_obj.id,"email":user_obj.email},code="")
    except Exception as E:
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/update-status", response_description="Update Admin Password")
async def reset_password(request: UpdateAdminStatus,background_tasks: BackgroundTasks, auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        status_id=request.status_id
        role_id = auth_user["role_id"]
        
        if role_id not in [1,2]:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")
        query = db.query(AdminUser).filter(AdminUser.id == user_id)
        if "tenant_id" in auth_user:
            query = query.filter(AdminUser.tenant_id == auth_user["tenant_id"])
        user_obj = query.first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        
        if user_obj.status_id ==status_id:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_IS_SAME_STATUS, error=[], data={},code="USER_IS_SAME_STATUS")
        else:
            user_obj.status_id = status_id
            db.commit()
            db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
            return Utility.json_response(status=SUCCESS, message=f"{all_messages.USER_STATUS_UPDATED}", error=[], data={"user_id":user_obj.id,"email":user_obj.email},code="USER_STATUS_UPDATED")
    except Exception as E:
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/get-branch-list", response_model=BranchListResponseSchema, response_description="Fetch Users List")
async def get_users(filter_data: GetBranchListRequestSchema,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        #user_obj = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        #AuthHandler().user_validate(user_obj)
        # if auth_user.get("role_id", -1) not in [1]:
        #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")
        
        query = db.query(TenantModel)
        
        if filter_data.search_string:
            search = f"%{filter_data.search_string}%"
            query = query.filter(
                or_(
                    TenantModel.name.ilike(search),
                    TenantModel.email.ilike(search),
                    TenantModel.mobile_no.ilike(search)
                )
            )
        
        # Total count of users matching the filters
        total_count = query.count()
        sort_column = getattr(TenantModel, filter_data.sort_by, None)
        if sort_column:
            
            if filter_data.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc("id"))

        # Apply pagination
        offset = (filter_data.page - 1) * filter_data.per_page
        paginated_query = query.offset(offset).limit(filter_data.per_page).all()
        # Create a paginated response
        rows =[]
        for row in paginated_query:
            rows.append(Utility.model_to_dict(row))
        return BranchListResponseSchema(
            total_count=total_count,
            list=rows,
            page=filter_data.page,
            per_page=filter_data.per_page
        )
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})

@router.post("/list", response_model=PaginatedAdminUserResponse, response_description="Fetch Users List")
async def get_users(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        #user_obj = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        #AuthHandler().user_validate(user_obj)
        if auth_user.get("role_id", -1) not in [1,2,3,4]:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")
        query = db.query(AdminUser).options(
            joinedload(AdminUser.admin_tenant_details),
            joinedload(AdminUser.role_details),
            joinedload(AdminUser.status_details),
            #joinedload(AdminUser.country_details),
            #joinedload(AdminUser.state_details),
            #joinedload(AdminUser.location_details),
            #joinedload(AdminUser.kyc_status)
        )
        query = query.filter(AdminUser.id !=auth_user["id"]) 
        if filter_data.search_string:
            search = f"%{filter_data.search_string}%"
            query = query.filter(
                or_(
                    AdminUser.first_name.ilike(search),
                    AdminUser.last_name.ilike(search),
                    AdminUser.email.ilike(search),
                    AdminUser.mobile_no.ilike(search),
                    AdminUser.tfs_id.ilike(search)
                )
            )
        if filter_data.tenant_id:
            query = query.filter(AdminUser.tenant_id.in_(filter_data.tenant_id))
        else:
            if auth_user.get("role_id", -1) in [2] and "tenant_id" in auth_user:
                query = query.filter(AdminUser.tenant_id == auth_user["tenant_id"])

        if filter_data.role_id:
            query = query.filter(AdminUser.role_id.in_(filter_data.role_id))
        if filter_data.status_ids:
            query = query.filter(AdminUser.status_id.in_(filter_data.status_ids))
        
        # Total count of users matching the filters
        total_count = query.count()
        sort_column = getattr(AdminUser, filter_data.sort_by, None)
        if sort_column:
            
            if filter_data.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc("id"))

        # Apply pagination
        
        offset = (filter_data.page - 1) * filter_data.per_page
        paginated_query = query.offset(offset).limit(filter_data.per_page).all()
        # Create a paginated response
        return PaginatedAdminUserResponse(
            total_count=total_count,
            list=paginated_query,
            page=filter_data.page,
            per_page=filter_data.per_page
        )
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})



@router.post("/invite-tenant", response_description="invitation mail for Tenant")
async def tenant_invitation_mail(request:TenantInvitationSchema,background_tasks: BackgroundTasks,admin_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, request.email):
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_EMAIL, error=[], data={})
        
        role_id = admin_user["role_id"]
        user_id=admin_user["id"]
        if role_id not in [1]:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")
        user_email=db.query(AdminUser).filter(AdminUser.email==request.email).first()
        if user_email:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Email already exists", error=[], data={})

        
        category="INVITE_TENANT"
        otp=str(Utility.generate_otp())
        user_dict={"user_id":user_id,"catrgory":category,"otp":otp}
        token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":3,"email":request.email,"name":request.name})
        user_dict["token"]=token
        user_dict["ref_id"]=user_id
        db.add(tokensModel(**user_dict))
        db.commit()
        link=f'''{WEB_URL}admin/tenantInvitationMail?token={token}'''
        background_tasks.add_task(Email.send_mail, recipient_email=[request.email], subject="Invitation Link", template='invitation_template.html',data={"link":link})
        return Utility.json_response(status=SUCCESS, message="Invitation Sent to the mail", error=[], data={"email":request.email})   
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()


@router.post("/signup-tenant", response_description="Register tenant")
async def signup_tenant_user(request:TenantSchema,background_tasks: BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        file_to_model = { }
        token_data=db.query(tokensModel).filter(tokensModel.token ==request.token).first() 
        if not token_data:
            return Utility.json_response(status=401, message="Invalid Token", error=[], data={},code="INVALID_TOKEN")
        if token_data.active==False:
            return Utility.json_response(status=401, message="Token is expired", error=[], data={},code="TOKEN_EXPIRED")
        user_dict=AuthHandler().decode_token(request.token)
        role_id=user_dict["invite_role_id"]
        email=user_dict["email"]
        row_data={"name":user_dict["name"],"email":email,"mobile_no":request.mobile_no}
        new_tenant=TenantModel(**row_data)
        db.add(new_tenant)
        db.commit()
        tenant_id=new_tenant.id
        password=AuthHandler().get_password_hash(request.password)
        user_data={"user_name":user_dict["name"],"login_token":request.token,"token":request.token,"password":password,"email":email,"mobile_no":request.mobile_no,"role_id":role_id,"status_id":3,"tenant_id":tenant_id}
        db.add(AdminUser(**user_data))
        db.commit()
        def insertBulkData(file_to_model):
            json_directory=Path(__file__).resolve().parent.parent.parent/"master_data"
            batch_size = 500
            print("tyu")
            for filename in os.listdir(json_directory):
                if filename in file_to_model:
                    model=file_to_model[filename]
                    file_path=json_directory / filename
                    with open(file_path, 'r') as file:
                        data = json.load(file)
                    batch=[]
                    for entry in data:
                    # Filter out any keys not matching the model's attributes
                        filtered_entry = {key: value for key, value in entry.items() if hasattr(model, key)}
                        if(filename=="md_kyc_docs.json")and ("tenant_id" in filtered_entry):
                            if "id" in filtered_entry:
                                del filtered_entry["id"]
                                filtered_entry["tenant_id"] = tenant_id
                    
                        print(filtered_entry)
                        record = model(**filtered_entry)
                        batch.append(record)
                        print(batch)
                        if len(batch) >= batch_size:
                            db.bulk_save_objects(batch)
                            batch.clear()

                    if batch:
                        db.bulk_save_objects(batch)
                    db.commit()
        insertBulkData(file_to_model)
        background_tasks.add_task(Email.send_mail, recipient_email=[email], subject="Invitation Link", template='signup_welcome.html',data={"name":user_data["user_name"]})
        token_data.active=False
        db.commit()
        return Utility.json_response(status=SUCCESS, message="User Registered Successfully", error=[], data=user_data)   
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})
    

@router.post("/details", response_model=PaginatedAdminUserResponse, response_description="Fetch Users List")
async def get_users(filter_data: UserDetailsRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        # if auth_user.get("role_id", -1) not in [1,2,3,4]:
        #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")
        
        query = db.query(AdminUser).options(
            joinedload(AdminUser.admin_tenant_details),
            joinedload(AdminUser.role_details),
            joinedload(AdminUser.status_details),
            joinedload(AdminUser.country_details),
            joinedload(AdminUser.state_details),
            joinedload(AdminUser.location_details),
            joinedload(AdminUser.admin_tenant_details),
            
            
        ).filter(AdminUser.id==filter_data.user_id )
        
        if filter_data.tenant_id and filter_data.tenant_id is not None:
            query = query.filter(AdminUser.tenant_id == filter_data.tenant_id)
        else:
            if "tenant_id" in auth_user:
                if auth_user["tenant_id"] is not None:
                    query = query.filter(AdminUser.tenant_id == auth_user["tenant_id"])
        result = query.first()
        if result is not None:
            user_data = Utility.model_to_dict(result)
            if "country_id" in user_data:
                user_data["country_details"] = Utility.model_to_dict(result.country_details)
            if "state_id" in user_data:
                user_data["state_details"] = Utility.model_to_dict(result.state_details)
            if "location_id" in user_data:
                user_data["location_details"] = Utility.model_to_dict(result.location_details)
            if "role_id" in user_data:
                user_data["role_details"] = Utility.model_to_dict(result.role_details)
            if "status_id" in user_data:
                user_data["status_details"] = Utility.model_to_dict(result.status_details)
            if "tenant_id" in user_data:
                user_data["admin_tenant_details"] = Utility.model_to_dict(result.admin_tenant_details)
            if "password" in user_data:
                del user_data["password"]
            # if "passport" in user_data:
            #     if user_data["passport"] is not None:
            #         #passport = json.loads(user_data["passport"].decode("utf-8"))
            #         user_data["passport"] = str(user_data["passport"].decode("utf-8"))
            #         #passport = 
            # if "upload_check" in user_data:
            #     if user_data["upload_check"] is not None:
            #         #passport = json.loads(user_data["passport"].decode("utf-8"))
            #         user_data["upload_check"] = str(user_data["upload_check"].decode("utf-8"))
            # if "aadhaar_card" in user_data:
            #     if user_data["aadhaar_card"] is not None:
            #         user_data["aadhaar_card"] = str(user_data["aadhaar_card"].decode("utf-8"))
            
            # if "selfie" in user_data:
            #     if user_data["selfie"] is not None:
            #         user_data["selfie"] = str(user_data["selfie"].decode("utf-8"))
                     
                
                #file_data = json.loads(user_data["upload_check"])
                #user_data["upload_check"] = file_data
            return Utility.json_response(status=SUCCESS, message="", error=[], data=user_data,code="Retrived")

        else:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.AGENT_NOT_FOUND, error=[], data={},code="AGENT_NOT_FOUND")

        
    except Exception as E:
        print(str(E))
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})
