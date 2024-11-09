from datetime import datetime, timezone
from sqlalchemy import and_
from datetime import datetime
from ...models.admin_user import AdminUser
from ...models.master_data_models import MdUserRole,MdUserStatus

from . import APIRouter,Utility, SUCCESS, FAIL, EXCEPTION ,INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.register import addSalesUserSchema, TenantSchema,TenantInvitationSchema,AdminRegister,InvitationSchema,TenantUserSchema,resetPassword,ForgotPasswordLinkSchema,SetPasswordSchema,UpdateAdminPassword,ForgotPassword
import re
from ...schemas.register import addSalesUserSchema
from ...schemas.login import Login
from fastapi import BackgroundTasks
from ...common.mail import Email
from ...constant.status_constant import WEB_URL
import os
import json
from pathlib import Path
from ...models.user_model import TenantModel

from...models.admin_configuration_model import tokensModel

from ...schemas.transaction import CreateCharges,EditCharges, ChargesListReqSchema,UpdateStatusSchema
from ...constant import messages as all_messages
from sqlalchemy.orm import  joinedload
from sqlalchemy import desc, asc
from sqlalchemy.sql import select, and_, or_, not_,func
from datetime import date, datetime,timezone,timedelta
from ...schemas.user_schema import UpdatePassword,UserFilterRequest,PaginatedAdminUserResponse,PaginatedBeneficiaryResponse,GetUserDetailsReq,UserListResponse, UpdateKycDetails,UpdateProfile,BeneficiaryRequest,BeneficiaryEdit, GetBeneficiaryDetails, ActivateBeneficiary,UpdateBeneficiaryStatus, ResendBeneficiaryOtp,BeneficiaryResponse

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
        print(E)
        db.rollback()
        return Utility.json_response(status=FAIL, message="Something went wrong", error=[], data={})


@router.post("/login", response_description="Login")
def login(request: Login, background_tasks:BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        email = request.email
        password = request.password
        user_obj = db.query(AdminUser).filter(AdminUser.email == email)
      
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
            if user_dict["tenant_id"]:
                user_dict["tenant_details"] = Utility.model_to_dict(user_data.admin_tenant_details)
            if "status_id" in user_dict:
                user_dict["status_details"] = Utility.model_to_dict(user_data.status_details)
            if "role_id" in user_dict:
                user_dict["role_details"] = Utility.model_to_dict(user_data.status_details)
            
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
                login_token = AuthHandler().encode_token(user_dict)
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
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/update-password", response_description="Update Admin Password")
async def reset_password(request: UpdateAdminPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        old_password=request.old_password
        password =  request.password
        user_obj = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        valid=AuthHandler().verify_password(old_password,user_obj.password)
        if not valid:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Invalid current Password", error=[], data={},code="INVALID_PASSWORD")
        user_obj.password =AuthHandler().get_password_hash(password)
        db.commit()
        rowData = {}                
        rowData["user_id"] = user_obj.id
        rowData['name'] = user_obj.user_name
        background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject=all_messages.RESET_PASSWORD_SUCCESS, template='reset_password_success.html',data=rowData )               
        db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
        return Utility.json_response(status=SUCCESS, message=all_messages.RESET_PASSWORD_SUCCESS, error=[], data={"user_id":user_obj.id,"email":user_obj.email},code="")
    except Exception as E:
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
 
@router.post("/forgot-password", response_description="Forgot Password")
async def forgot_password(request: ForgotPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        
        email = request.email
        date_of_birth = request.date_of_birth
        user_obj = db.query(AdminUser).filter(AdminUser.email == email).first()
        
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            if user_obj.status_id ==3:
                if user_obj.date_of_birth != date_of_birth:
                    return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.INVALID_BIRTHDATE, error=[], data={},code="")
                else:
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
                    
                    category ="ADMIN_FORGOT_PASSWORD"
                    Utility.inactive_previous_tokens(db=db, catrgory = category, user_id = udata["id"])
                    user_dict={"user_id":udata["id"],"catrgory":category,"otp":otp}
                    token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"role_id":user_obj.role_id,"email":user_obj.email,"name":user_obj.name})
                    user_dict["token"]=token
                    user_dict["ref_id"]=user_obj.id
                    db.add(tokensModel(**user_dict))
                    rowData["reset_link"] = f'''{WEB_URL}forgotPassword?token={token}&user_id={user_obj.id}'''
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
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/reset-password", response_description="Forgot Password")
async def reset_password(request: resetPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        token = str(request.token)
        password =  request.password
        user_obj = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        if  user_obj.status_id == 1:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="PENDING_PROFILE_COMPLATION")
        elif  user_obj.status_id == 2:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="PENDING_EMAIL_VERIFICATION")
        elif user_obj.status_id == 4:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={})
    
        else:
            category ="ADMIN_FORGOT_PASSWORD"
            token_query = db.query(tokensModel).filter(tokensModel.catrgory ==category, tokensModel.user_id==user_id, tokensModel.token == token,tokensModel.active==True).first()
            if token_query is None:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.INVALIED_TOKEN, error=[], data={},code="")
                         
            token_data = AuthHandler().decode_otp_token(token_query.token)
            user_obj.password =AuthHandler().get_password_hash(password)
            user_obj.login_fail_count = 0
            token_query.active =False
            db.commit()
            rowData = {}                
            rowData["user_id"] = user_obj.id
            rowData['name'] = f"""{user_obj.first_name} {user_obj.last_name}"""
            background_tasks.add_task(Email.send_mail,recipient_email=[user_obj.email], subject=all_messages.RESET_PASSWORD_SUCCESS, template='reset_password_success.html',data=rowData )               
            #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
            return Utility.json_response(status=SUCCESS, message=all_messages.RESET_PASSWORD_SUCCESS, error=[], data={"user_id":user_obj.id,"email":user_obj.email},code="")
        

    except Exception as E:
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/list", response_model=PaginatedAdminUserResponse, response_description="Fetch Users List")
async def get_users(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        #user_obj = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        #AuthHandler().user_validate(user_obj)
        if auth_user.get("role_id", -1) not in [1,2]:
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
                    AdminUser.mobile_no.ilike(search)
                )
            )
        if filter_data.tenant_id:
            query = query.filter(AdminUser.tenant_id.in_(filter_data.tenant_id))
        if filter_data.role_id:
            query = query.filter(AdminUser.role_id.in_(filter_data.role_id))
        if filter_data.status_ids:
            query = query.filter(AdminUser.status_id.in_(filter_data.status_ids))
        if filter_data.country_id:
            query = query.filter(AdminUser.country_id.in_(filter_data.country_id))
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
        print(E)
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})

@router.post("/add-user", response_description="add user")
async def invitation_mail(request:addSalesUserSchema,background_tasks: BackgroundTasks,login_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        if login_user["role_id"] not in [1,2]:
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
        otp=str(Utility.generate_otp())
        #profile_image =  request.first_name
        exist_user=db.query(AdminUser).filter(AdminUser.email==request.email).first()
        if exist_user:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Email already exists", error=[], data={})
        password=AuthHandler().get_password_hash(otp)
        name = first_name
        if first_name and last_name:
            name = first_name+" "+last_name
        user_data={"tenant_id":tenant_id,"first_name":first_name,"last_name":last_name, "name":name,"password":password,"email":email,"mobile_no":mobile_no,"role_id":role_id,"status_id":2}
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
            new_user.tfs_id = f"{tfs_id}-{new_user.id}"
            db.commit()
            return Utility.json_response(status=SUCCESS, message=all_messages.REGISTER_SUCCESS, error=[], data={})
        else:
            db.rollback()
            return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})


    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})
    
@router.post("/reset-password", response_description="Forgot Password")
async def reset_password(request: resetPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        token = str(request.token)
        password =  request.password
        user_obj = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            token_data = db.query(tokensModel).filter(tokensModel.token == token, tokensModel.user_id==user_id, tokensModel.active==True).first()
            if token_data is None:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Invalid Token", error=[], data={},code="INVALIED_TOKEN")
            user_obj.token = ''
            user_obj.otp = ''
            user_obj.password =AuthHandler().get_password_hash(password)
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
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/invite-user", response_description="invitation mail for maker checker")
async def invitation_mail(request:InvitationSchema,background_tasks: BackgroundTasks,admin_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        if admin_user["role_id"] not in [1,2]:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={})
       
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, request.email):
            return Utility.json_response(status=BAD_REQUEST, message=all_messages.INVALIED_EMAIL, error=[], data={})
       
        role_id = admin_user["role_id"]
        user_id=admin_user["id"]
        if admin_user["role_id"] ==1:
            tenant_id=request.tenant_id
        else:
            tenant_id=admin_user["tenant_id"]
        user_email=db.query(AdminUser).filter(AdminUser.email==request.email).first()
        if user_email:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Email already exists", error=[], data={})
        
        
        category="INVITE_USER"
        otp=str(Utility.generate_otp())
        user_dict={"user_id":user_id,"catrgory":category,"otp":otp,"invite_by_role_id":role_id,"invited_by":user_id}
        token = AuthHandler().encode_token({"tenant_id":tenant_id,"user_id":user_id,"catrgory":category,"otp":otp,"invite_role_id":request.role_id,"email":request.email})
        user_dict["token"]=token
        user_dict["ref_id"]=user_id
        db.add(tokensModel(**user_dict))
        db.commit()
        link=f'''{WEB_URL}admin/invitationMail?token={token}'''
        background_tasks.add_task(Email.send_mail, recipient_email=[request.email], subject="Invitation Link", template='invitation_template.html',data={"link":link})
        return Utility.json_response(status=SUCCESS, message="Invitation Sent to the mail", error=[], data={"email":request.email})   
    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})
    
@router.post("/signup-tenant-user", response_description="Register tenant user")
async def signup_tenant_user(request:TenantUserSchema,background_tasks: BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        token_data=db.query(tokensModel).filter(tokensModel.token ==request.token).first() 
        if not token_data:
            return Utility.json_response(status=401, message="Invalid Token", error=[], data={},code="INVALID_TOKEN")
        if token_data.active==False:
            return Utility.json_response(status=401, message="Token is expired", error=[], data={},code="TOKEN_EXPIRED")
        user_dict=AuthHandler().decode_token(request.token)
        role_id=user_dict["invite_role_id"]
        email=user_dict["email"]
        tenant_id=user_dict["tenant_id"]
        password=AuthHandler().get_password_hash(request.password)
        user_data={"tenant_id":tenant_id,"user_name":request.first_name+" "+request.last_name,"password":password,"email":email,"mobile_no":request.mobile_no,"role_id":role_id,"status_id":3}
        db.add(AdminUser(**user_data))
        db.commit()
        background_tasks.add_task(Email.send_mail, recipient_email=[email], subject="Welcome to TFS", template='signup_welcome.html',data={"name":user_data["user_name"]})
        token_data.active=False
        db.commit()
        return Utility.json_response(status=SUCCESS, message="User Registered Successfully", error=[], data=user_data)   
    except Exception as E:
        print(E)
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
        print(E)
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
        print(E)
        db.rollback()
        return Utility.json_response(status=EXCEPTION, message="Something went wrong", error=[], data={})