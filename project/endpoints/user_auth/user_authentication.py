from datetime import datetime, timezone,timedelta
from sqlalchemy import and_
from datetime import datetime
from ...models.user_model import CustomerModal,LoanapplicationModel
from ...models.master_data_models import MdUserRole,MdUserStatus

from . import APIRouter, Utility, SUCCESS, FAIL, EXCEPTION ,WEB_URL, API_URL, INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.register import createCustomerSchema, SignupOtp,ForgotPassword,CompleteSignup,VerifyAccount,resetPassword
import re
from ...schemas.login import Login
from ...constant import messages as all_messages
from ...common.mail import Email
import json
from fastapi import BackgroundTasks
from ...models.admin_user import AdminUser
from ...models.admin_configuration_model import tokensModel

# APIRouter creates path operations for product module
router = APIRouter(
    prefix="/auth",
    tags=["User Authentication"],
    responses={404: {"description": "Not found"}},
)
#createCustomerSchema
@router.post("/invite-customer", response_description="Invite Customer")
async def invite_customer(request: createCustomerSchema,background_tasks: BackgroundTasks,login_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        tenant_id = 1
        mobile_no = request.mobile_no
        email = request.email
        first_name = request.first_name
        last_name = request.last_name
        if request.tenant_id is not None:
            tenant_id = request.tenant_id
        service_type_id = request.service_type_id
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, email):
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_EMAIL, error=[], data={})
        if len(str(mobile_no)) < 7 or len(str(mobile_no)) > 15:
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_MOBILE,error=[], data={})
        user_obj = db.query(CustomerModal).filter(CustomerModal.email == email)
        otp =str(Utility.generate_otp())
        name =  first_name
        category ="SIGNUP_CUSTOMER"
        if last_name:
            name = f"{first_name} last_name"
        if user_obj.count() <=0:
            user_data = CustomerModal(
                                    
                                      first_name=first_name,
                                      last_name=last_name,
                                      name=name,
                                      role_id =5,
                                      status_id=2,
                                      email=email,
                                      mobile_no=mobile_no,
                                      password=str(Utility.uuid()),
                                      tenant_id=tenant_id,
                                      service_type_id=service_type_id
                                      )
            #Send Mail to user with active link
            mail_data = {"body":"Welcome to TFS"}
            db.add(user_data)
            db.flush()
            db.commit()
            if user_data.id:
                new_lead =  LoanapplicationModel(subscriber_id=user_data.id,service_type_id=service_type_id)
                db.add(new_lead)
                user_data.tfs_id = f"{Utility.generate_tfs_code(5)}{user_data.id}"
                udata =  Utility.model_to_dict(user_data)
                rowData = {}
                rowData['user_id'] = udata["id"]
                rowData['first_name'] = udata.get("first_name","")
                rowData['last_name'] = udata.get("last_name","")
                rowData['mobile_no'] = udata.get("mobile_no",'')
                rowData['date_of_birth'] = udata.get("date_of_birth",'')
                otp = str(Utility.generate_otp())
                category = "ADD_USER"
                link = f'''{WEB_URL}set-customer-password?token={new_token}&user_id={user_data.id}'''
                token = AuthHandler().encode_token({"user_id":user_data.id,"catrgory":category,"otp":otp,"invite_role_id":user_data.role_id,"email":user_data.email,"name":user_data.name})
                user_dict={"user_id":user_data.id,"catrgory":category,"otp":otp,"token":token,"ref_id":user_data.id}
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Welcome to TFS", template='add_user.html',data={"name":user_data.name,"link":link})
                return Utility.json_response(status=SUCCESS, message=all_messages.REGISTER_SUCCESS, error=[],data=rowData,code="SIGNUP_PROCESS_PENDING")
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
        else:
            otp =str(Utility.generate_otp())
            existing_user = user_obj.one()
            udata =  Utility.model_to_dict(existing_user)
            rowData = {}
            rowData['user_id'] = udata["id"]
            rowData['email'] = udata.get("email","")
            rowData['first_name'] = udata.get("first_name","")
            rowData['last_name'] = udata.get("last_name","")
            rowData['country_id'] = udata.get("country_id",None)
            rowData['mobile_no'] = udata.get("mobile_no",'')
            rowData['date_of_birth'] = udata.get("date_of_birth",'')
            rowData['status_id'] = existing_user.status_id
            rowData["status_details"] = Utility.model_to_dict(existing_user.status_details)
            
            #del existing_user.otp
            #del existing_user.password
            new_token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name})
            link = f'''{WEB_URL}set-customer-password?token={new_token}&user_id={existing_user.id}'''
          
            user_dict={"user_id":existing_user.id,"catrgory":category,"otp":otp}
            user_dict["token"]=new_token
            user_dict["ref_id"]=existing_user.id
            if  existing_user.status_id == 1 or existing_user.status_id == 2 :
                otp = str(Utility.generate_otp())
                category = "ADD_USER"
                token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name})
                user_dict={"user_id":existing_user.id,"catrgory":category,"otp":otp,"token":token,"ref_id":existing_user.id}
                
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[existing_user.email], subject="Welcome to TFS", template='add_user.html',data={"name":existing_user.name,"link":link})
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.OTP_VERIVICARION_SUCCESS, error=[], data=rowData,code="OTP_VERIVICARION_SUCCESS")
            
            elif  existing_user.status_id == 3:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.ALREADY_USER_PROFILE_IS_ACTIVE, error=[], data=rowData,code="ALREADY_USER_PROFILE_IS_ACTIVE")
            elif existing_user.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_PROFILE_INACTIVE, error=[], data=rowData)
            elif existing_user.status_id == 5:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_PROFILE_DELETED, error=[], data=rowData)
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/signup-customer", response_description="Customer Signup")
async def register_customer(request: createCustomerSchema,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        tenant_id = None
        mobile_no = request.mobile_no
        email = request.email
        first_name = request.first_name
        last_name = request.last_name
        if request.tenant_id is not None:
            tenant_id = request.tenant_id
        service_type_id = request.service_type_id
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, email):
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_EMAIL, error=[], data={})
        if len(str(mobile_no)) < 7 or len(str(mobile_no)) > 15:
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_MOBILE,error=[], data={})
        user_obj = db.query(CustomerModal).filter(CustomerModal.email == email)
        otp =str(Utility.generate_otp())
        name =  request.first_name
        category ="SIGNUP_CUSTOMER"
        if last_name:
            name = f"{request.first_name} {request.last_name}"
        if user_obj.count() <=0:
            user_data = CustomerModal(
                                    
                                      first_name=first_name,
                                      last_name=last_name,
                                      name=name,
                                      role_id =5,
                                      status_id=1,
                                      email=email,
                                      mobile_no=mobile_no,
                                      password=str(Utility.uuid()),
                                      tenant_id=tenant_id,
                                      service_type_id=service_type_id
                                      )
            #Send Mail to user with active link
            mail_data = {"body":"Welcome to TFS"}
            db.add(user_data)
            db.flush()
            db.commit()
            if user_data.id:
                new_lead =  LoanapplicationModel(subscriber_id=user_data.id,service_type_id=service_type_id,tenant_id=tenant_id)
                db.add(new_lead)
                user_data.tfs_id = f"{Utility.generate_tfs_code(5)}{user_data.id}"
                udata =  Utility.model_to_dict(user_data)
                rowData = {}
                rowData['user_id'] = udata["id"]
                rowData['first_name'] = udata.get("first_name","")
                rowData['last_name'] = udata.get("last_name","")
                rowData['mobile_no'] = udata.get("mobile_no",'')
                rowData['date_of_birth'] = udata.get("date_of_birth",'')
                mail_data = {}
                mail_data["name"]= f'''{udata.get("first_name","")} {udata.get("last_name","")}'''
                mail_data["otp"] = otp
                
                user_dict={"user_id":udata["id"],"catrgory":category,"otp":otp}
                token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":5,"email":request.email,"name":name})
                user_dict["token"]=token
                user_dict["ref_id"]=udata["id"]
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail,recipient_email=[udata["email"]], subject=all_messages.PENDING_EMAIL_VERIFICATION_OTP_SUBJ, template='email_verification_otp.html',data=mail_data )
                return Utility.json_response(status=SUCCESS, message=all_messages.REGISTER_SUCCESS, error=[],data=rowData,code="SIGNUP_PROCESS_PENDING")
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
        else:
            otp =str(Utility.generate_otp())
            existing_user = user_obj.one()
            udata =  Utility.model_to_dict(existing_user)
            rowData = {}
            rowData['user_id'] = udata["id"]
            rowData['email'] = udata.get("email","")
            rowData['first_name'] = udata.get("first_name","")
            rowData['last_name'] = udata.get("last_name","")
            rowData['country_id'] = udata.get("country_id",None)
            rowData['mobile_no'] = udata.get("mobile_no",'')
            rowData['date_of_birth'] = udata.get("date_of_birth",'')
            rowData['status_id'] = existing_user.status_id
            rowData["status_details"] = Utility.model_to_dict(existing_user.status_details)
            
            #del existing_user.otp
            #del existing_user.password
            new_token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name})
            link = f'''{WEB_URL}set-customer-password?token={new_token}&user_id={existing_user.id}'''
          
            user_dict={"user_id":existing_user.id,"catrgory":category,"otp":otp}
            user_dict["token"]=new_token
            user_dict["ref_id"]=existing_user.id
            if existing_user.status_id == 1:
                otp = str(Utility.generate_otp())
                msg = all_messages.ACCOUNT_EXISTS_PENDING_EMAIL_VERIFICATION
                code = "SIGNUP_VERIFICATION_PENDING"                
                
                mail_data = {}
                mail_data["name"]= f'''{udata.get("first_name","")} {udata.get("last_name","")}'''
                mail_data["otp"] = otp
                
                user_dict={"user_id":udata["id"],"catrgory":category,"otp":otp}
                token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":5,"email":request.email,"name":name})
                user_dict["token"]=token
                user_dict["ref_id"]=udata["id"]
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail,recipient_email=[udata["email"]], subject=all_messages.PENDING_EMAIL_VERIFICATION_OTP_SUBJ, template='email_verification_otp.html',data=mail_data )
                   
                
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=msg, error=[], data=rowData,code=code)
            elif  existing_user.status_id == 2:
                otp = str(Utility.generate_otp())
                category = "ADD_USER"
                token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name})
                user_dict={"user_id":existing_user.id,"catrgory":category,"otp":otp,"token":token,"ref_id":existing_user.id}
                
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[existing_user.email], subject="Welcome to TFS", template='add_user.html',data={"name":existing_user.name,"link":link})
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.OTP_VERIVICARION_SUCCESS, error=[], data=rowData,code="OTP_VERIVICARION_SUCCESS")
            
            elif  existing_user.status_id == 3:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.ALREADY_PROFILE_IS_ACTIVE, error=[], data=rowData,code="ALREADY_PROFILE_IS_ACTIVE")
            elif existing_user.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data=rowData)
            elif existing_user.status_id == 5:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data=rowData)
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/verify-account", response_description="Send User Signup OTP")
async def verify_account(request: VerifyAccount,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
               
        user_id = request.user_id
        otp = str(request.otp)
        category ="ADD_USER"
        user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            rowData = {}
            rowData['user_id'] = user_obj.id
            rowData['email'] = user_obj.email
            rowData['first_name'] = user_obj.first_name
            rowData['last_name'] = user_obj.last_name
            rowData['status_id'] = user_obj.status_id
            new_token = AuthHandler().encode_token({"user_id":user_obj.id,"catrgory":category,"otp":otp,"invite_role_id":user_obj.role_id,"email":user_obj.email,"name":user_obj.name})
            link = f'''{WEB_URL}set-customer-password?token={new_token}&user_id={user_obj.id}'''
           #rowData["country_details"] = Utility.model_to_dict(user_obj.country_details)
            #rowData["status_details"] = Utility.model_to_dict(user_obj.status_details)
            user_dict={"user_id":user_obj.id,"catrgory":category,"otp":otp}
            user_dict["token"]=new_token
            user_dict["ref_id"]=user_obj.id
            if user_obj.status_id == 1:
                token_data = db.query(tokensModel).filter(tokensModel.otp == otp, tokensModel.user_id == user_id, tokensModel.catrgory == "SIGNUP_CUSTOMER").first()
                tokendata = AuthHandler().decode_otp_token(token_data.token)
                if otp ==  token_data.otp:
                    user_obj.status_id = 2
                    user_obj.otp = ''
                    token_data.active = False
                    db.commit()
                    mail_data ={"name": user_obj.first_name+" "+user_obj.last_name }
                    #background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject="Welcome to TFS!", template='signup_welcome.html',data=mail_data )
                    
                    db.add(tokensModel(**user_dict))
                    db.commit()
                    background_tasks.add_task(Email.send_mail, recipient_email=[user_obj.email], subject="Welcome to TFS", template='add_user.html',data={"name":user_obj.name,"link":link})
                
                    return Utility.json_response(status=SUCCESS, message=all_messages.OTP_VERIVICARION_SUCCESS, error=[], data=rowData,code="OTP_VERIVICARION_SUCCESS")
           
                else:
                    return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.INVALIED_OTP, error=[], data={},code="INVALIED_OTP")
            elif  user_obj.status_id == 2:
                otp = str(Utility.generate_otp())
                category = "ADD_USER"
                token = AuthHandler().encode_token({"user_id":user_obj.id,"catrgory":category,"otp":otp,"invite_role_id":user_obj.role_id,"email":user_obj.email,"name":user_obj.name})
                user_dict={"user_id":user_obj.id,"catrgory":category,"otp":otp,"token":token,"ref_id":user_obj.id}
                
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[user_obj.email], subject="Welcome to TFS", template='add_user.html',data={"name":user_obj.name,"link":link})
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.OTP_VERIVICARION_SUCCESS, error=[], data=rowData,code="OTP_VERIVICARION_SUCCESS")
            
            
            elif  user_obj.status_id == 3:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.ALREADY_PROFILE_IS_ACTIVE, error=[], data=rowData,code="ALREADY_PROFILE_IS_ACTIVE")
            elif user_obj.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data=rowData,code="PROFILE_INACTIVE")
            elif user_obj.status_id == 5:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data=rowData,code="PROFILE_DELETED")
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/login", response_description="Login")
def login(request: Login, background_tasks:BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        email = request.email
        password = request.password
        user_obj = db.query(CustomerModal,
                        #CustomerModal.email,
                        #CustomerModal.status_id,
                        #CustomerModal.user_name,
                        #CustomerModal.token,
                        #CustomerModal.password,
                        #CustomerModal.id
                        ).filter(CustomerModal.email == email)
      
        login_count =0
        if user_obj.count() <= 0:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.EMAIL_NOT_REGISTERED, error=[], data={})
        user_data = user_obj.one()
        
        
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
            #user_dict["country_details"] =  Utility.model_to_dict(user_data.country_details)
            #user_dict["kyc_status"] = Utility.model_to_dict(user_data.kyc_status)
            if user_data.tenant_details:
                user_dict["tenant_details"] = Utility.model_to_dict(user_data.tenant_details)
            
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
                        user_obj.update({ CustomerModal.login_attempt_date:datetime.now(timezone.utc),CustomerModal.login_fail_count:0}, synchronize_session=False)
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
                        user_obj.update({ CustomerModal.otp:otp,CustomerModal.token:token}, synchronize_session=False)
                        db.commit()
                        background_tasks.add_task(Email.send_mail,recipient_email=[user_data.email], subject="Account Locked & Reset Password link", template='invalid_login_attempts.html',data=rowData )               
                    
                        user_obj.update({CustomerModal.login_fail_count:CustomerModal.login_fail_count+1}, synchronize_session=False)
                        db.flush()
                        db.commit()
                        #ACCOUNT_LOCKED
                        return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.ACCOUNT_LOCKED, error=[], data={})
                    #Wit for 24 Hourse
                else:
                    
                    user_obj.update({ CustomerModal.login_attempt_date:datetime.now(timezone.utc),CustomerModal.login_fail_count:login_fail_count+1}, synchronize_session=False)
                    #db.flush(CustomerModal)
                    db.commit()
                    
                return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_CREDENTIALS, error=[], data={})
            else:
               
                
                if user_data.login_fail_count >=3:
                
                    time_difference = current_time - user_data.login_attempt_date
                    
                    if time_difference >= timedelta(hours=24):
                        print("24 Completed")
                        
                        user_obj.update({ CustomerModal.login_attempt_date:datetime.now(timezone.utc),CustomerModal.login_fail_count:0}, synchronize_session=False)
                        db.commit()
                    else:        
                        return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.ACCOUNT_LOCKED, error=[], data={})
                login_token = AuthHandler().encode_token(user_dict)
                if not login_token:
                    # return Utility.json_response(status=FAIL, message=all_messages.INVALIED_CREDENTIALS, error=[], data={})

                    return Utility.json_response(status=FAIL, message=all_messages.SOMTHING_WRONG, error=[], data={})
                    
                else:
                    print("1")                    
                    login_count = user_data.login_count+1                    
                    user_obj.update({ CustomerModal.login_fail_count:0,CustomerModal.login_count:login_count,CustomerModal.last_login:datetime.now(timezone.utc)}, synchronize_session=False)
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
                    user_dict["token"] = login_token
                    if user_data.date_of_birth is not None:
                        user_dict["date_of_birth"] = str(user_data.date_of_birth)
                    #del user_dict.password
                    #del user_dict.otp
                    return Utility.dict_response(status=SUCCESS, message=all_messages.SUCCESS_LOGIN, error=[], data=user_dict)

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})



@router.post("/resend-otp", response_description="Re-send Signup OTP")
async def resend_otp(request: SignupOtp,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        
        email = request.email
        user_obj = db.query(CustomerModal).filter(CustomerModal.email == email).first()
        
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            rowData = {}
            rowData['user_id'] = user_obj.id
            rowData['email'] = user_obj.email
            rowData['first_name'] = user_obj.first_name
            rowData['last_name'] = user_obj.last_name
            rowData['country_id'] = user_obj.country_id
            #rowData['mobile_no'] = udata.get("mobile_no",'')
            #rowData['date_of_birth'] = udata.get("date_of_birth",'')
            rowData['status_id'] = user_obj.status_id
            #rowData["country_details"] = Utility.model_to_dict(user_obj.country_details)
            #rowData["status_details"] = Utility.model_to_dict(user_obj.status_details)
            if  user_obj.status_id ==1:
                code = "SIGNUP_PROCESS_PENDING"
                msg =all_messages.SIGNUP_PROCESS_PENDING                           
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=msg, error=[], data=rowData,code=code)
            
            elif user_obj.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={})
            elif user_obj.status_id == 5:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={})
            
            elif  user_obj.status_id ==2 or user_obj.status_id ==3:
                otp =Utility.generate_otp()
                mail_data = {"otp":str(otp),"name":user_obj.first_name +" "+user_obj.last_name}
                user_obj.token = AuthHandler().encode_token({"otp":otp})
                user_obj.otp = otp
                db.commit()
                #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
                background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject=all_messages.PENDING_EMAIL_VERIFICATION_OTP_SUBJ, template='email_verification_otp.html',data=mail_data )
                return Utility.json_response(status=SUCCESS, message=all_messages.RESEND_EMAIL_VERIFICATION_OTP, error=[], data=rowData,code="")
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/forgot-password", response_description="Forgot Password")
async def forgot_password(request: ForgotPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        
        email = request.email
        date_of_birth = request.date_of_birth
        user_obj = db.query(CustomerModal).filter(CustomerModal.email == email).first()
        
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            if user_obj.status_id ==3:
                if user_obj.date_of_birth != date_of_birth:
                    return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.INVALID_BIRTHDATE, error=[], data={},code="")
                else:
                    rowData = {}
                    udata = Utility.model_to_dict(user_obj.country_details)
                    rowData['user_id'] = udata["id"]
                    rowData['email'] = user_obj.email
                    rowData['first_name'] = user_obj.first_name
                    rowData['last_name'] = user_obj.last_name
                    rowData['country_id'] = user_obj.country_id
                    #rowData['mobile_no'] = udata.get("mobile_no",'')
                    #rowData['date_of_birth'] = udata.get("date_of_birth",'')
                    rowData['status_id'] = user_obj.status_id            
                    otp =Utility.generate_otp()
                    token = AuthHandler().encode_token({"otp":otp})
                    user_obj.token = token
                    user_obj.otp = otp
                    db.commit()
                    #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
                    rowData["otp"] = otp
                    rowData["user_id"] = user_obj.id
                    rowData['name'] = f"""{user_obj.first_name} {user_obj.last_name}"""
                    rowData["reset_link"] = f'''{WEB_URL}ForgotPassword?token={token}&user_id={user_obj.id}'''

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
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/reset-password", response_description="Forgot Password")
async def reset_password(request: resetPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        token = str(request.token)
        password =  request.password
        user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            if token !=user_obj.token:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Invalid Token", error=[], data={},code="INVALIED_TOKEN")
            if user_obj.status_id ==3:
                user_obj.token = ''
                user_obj.otp = ''
                user_obj.password =AuthHandler().get_password_hash(password)
                user_obj.login_fail_count = 0
                db.commit()
                rowData = {}                
                rowData["user_id"] = user_obj.id
                rowData['name'] = f"""{user_obj.first_name} {user_obj.last_name}"""
                background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject=all_messages.RESET_PASSWORD_SUCCESS, template='reset_password_success.html',data=rowData )               
                #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
                return Utility.json_response(status=SUCCESS, message=all_messages.RESET_PASSWORD_SUCCESS, error=[], data={"user_id":user_obj.id,"email":user_obj.email},code="")
            elif  user_obj.status_id == 1:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="PENDING_PROFILE_COMPLATION")
            elif  user_obj.status_id == 2:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="PENDING_EMAIL_VERIFICATION")
            elif user_obj.status_id == 3:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={})
            elif user_obj.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={})
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/set-password", response_description="Forgot Password")
async def reset_password(request: resetPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        token = str(request.token)
        password =  request.password
        user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        
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
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


