from datetime import datetime, timezone,timedelta
from datetime import datetime
from ...models.user_model import CustomerModal
from ...models.master_data_models import MdUserRole,MdUserStatus,MdCountries

from . import APIRouter, Utility, SUCCESS, FAIL, EXCEPTION ,INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.user_schema import UpdatePassword,UserFilterRequest,PaginatedUserResponse,PaginatedBeneficiaryResponse,GetUserDetailsReq,UserListResponse, UpdateKycDetails,UpdateProfile,BeneficiaryRequest,BeneficiaryEdit, GetBeneficiaryDetails, ActivateBeneficiary,UpdateBeneficiaryStatus, ResendBeneficiaryOtp,BeneficiaryResponse
from ...schemas.user_schema import UpdateKycStatus
from ...models.user_model import NotificationModel

import re
from ...constant import messages as all_messages
from ...common.mail import Email
from sqlalchemy.sql import select, and_, or_, not_,func
from sqlalchemy.future import select
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.admin_configuration_model import tokensModel
from sqlalchemy import desc, asc
from typing import List
from fastapi import BackgroundTasks
from fastapi_pagination import Params,paginate 
from sqlalchemy.orm import  joinedload
from ...library.webSocketConnectionManager import manager
from ...models.admin_user import AdminUser


# APIRouter creates path operations for product module
router = APIRouter(
    prefix="/customer",
    tags=["Customer"],
    responses={404: {"description": "Not found"}},
)




@router.post("/update-profile", response_description="Update Profile")
async def update_profile(request: UpdateProfile,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        
        user_id = auth_user["id"]
        first_name = request.first_name
        last_name = request.last_name
        date_of_birth = request.date_of_birth #Utility.convert_dtring_to_date(request.date_of_birth)
        mobile_no = request.mobile_no

        user_data = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        if user_data is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="INVALIED_TOKEN")
        if user_data.role_id !=2:
            
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="LOGOUT_ACCOUNT")

        else:
            
            if user_data.status_id ==3:                
                user_data.first_name = first_name
                user_data.last_name = last_name
                user_data.name = f'''{first_name} {last_name}'''
                user_data.date_of_birth = date_of_birth
                user_data.mobile_no = mobile_no
                db.commit()
                db.flush(CustomerModal)
                res_data = {
                    "first_name":user_data.first_name,
                    "last_name":user_data.last_name,
                    "date_of_birth":user_data.date_of_birth,
                    "mobile_no":user_data.mobile_no,
                }

                return Utility.json_response(status=SUCCESS, message=all_messages.PROFILE_UPDATE_SUCCESS, error=[], data={},code="")
            elif  user_data.status_id == 1:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="LOGOUT_ACCOUNT")
            elif  user_data.status_id == 2:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="LOGOUT_ACCOUNT")
            elif user_data.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={},code="LOGOUT_ACCOUNT")
            elif user_data.status_id == 5:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={},code="LOGOUT_ACCOUNT")
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/update-password", response_description="Update Password")
async def update_password(request: UpdatePassword,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        
        user_id = auth_user["id"]
        old_password = str(request.old_password)
        password =  request.password
        user_data = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        if user_data is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            
            verify_password = AuthHandler().verify_password(str(old_password), user_data.password)
            if not verify_password:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.INVALIED_OLD_PASSWORD, error=[], data={})
            if user_data.status_id ==3:
                has_password = AuthHandler().get_password_hash(password)
                user_data.password = has_password
                db.commit()
                #db.flush(user_obj) ## Optionally, refresh the instance from the database to get the updated values
                  #Email.send_mail(recipient_email=[user_obj.email], subject="Reset Password OTP", template='',data=mail_data )
                return Utility.json_response(status=SUCCESS, message=all_messages.UPDATE_PASSWORD_SUCCESS, error=[], data={},code="")
            elif  user_data.status_id == 1:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="LOGOUT_ACCOUNT")
            elif  user_data.status_id == 2:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="LOGOUT_ACCOUNT")
            elif user_data.status_id == 4:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={},code="LOGOUT_ACCOUNT")
            elif user_data.status_id == 5:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={},code="LOGOUT_ACCOUNT")
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
@router.post("/list", response_description="Fetch Users List")
async def get_subscribers(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    #user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
    #AuthHandler().user_validate(user_obj)
    if auth_user.get("role_id", -1) not in [1,2]:
        return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")

    
    query = db.query(CustomerModal).options(
        joinedload(CustomerModal.tenant_details),
        joinedload(CustomerModal.role_details),
        joinedload(CustomerModal.status_details),
        joinedload(CustomerModal.created_by_details),
        joinedload(CustomerModal.service_details),
        joinedload(CustomerModal.loan_applications_list),
        #joinedload(CustomerModal.kyc_status)
    )

    if filter_data.search_string:
        search = f"%{filter_data.search_string}%"
        query = query.filter(
            or_(
                CustomerModal.first_name.ilike(search),
                CustomerModal.last_name.ilike(search),
                CustomerModal.email.ilike(search),
                CustomerModal.mobile_no.ilike(search),
                #CustomerModal.role_details.name.ilike(search)
            )
        )
    if filter_data.tenant_id:
        query = query.filter(CustomerModal.tenant_id.in_(filter_data.tenant_id))

    #if filter_data.role_id:
        #query = query.filter(CustomerModal.role_id == filter_data.role_id)
    if filter_data.status_ids:
        query = query.filter(CustomerModal.status_id.in_(filter_data.status_ids))
    
     # Total count of users matching the filters
    
    total_count = query.count()
    sort_column = getattr(CustomerModal, filter_data.sort_by, None)
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
    users_list =[]
    for item in paginated_query:
        temp_item = Utility.model_to_dict(item)
        """
        joinedload(CustomerModal.tenant_details),
        joinedload(CustomerModal.role_details),
        joinedload(CustomerModal.status_details),
        joinedload(CustomerModal.created_by_details),
        joinedload(CustomerModal.service_details),
        joinedload(CustomerModal.loan_applications_list),
        """
        if "tenant_id" in temp_item and temp_item["tenant_id"] is not None:
            temp_item["tenant_details"] = Utility.model_to_dict(item.tenant_details)

        if "role_id" in temp_item and temp_item["role_id"] is not None:
            temp_item["role_details"] = Utility.model_to_dict(item.role_details)
        
        if "created_by" in temp_item and temp_item["created_by"] is not None:
            temp_item["created_by_details"] = Utility.model_to_dict(item.created_by_details)

        if "service_type_id" in temp_item and temp_item["service_type_id"] is not None:
            temp_item["service_details"] = Utility.model_to_dict(item.service_details)
        if item.loan_applications_list is not None:
            temp_item["loan_applications_list"] = []
            for loan in item.loan_applications_list:
                temp_item["loan_applications_list"].append(Utility.model_to_dict(loan))

        
        if "status_id" in temp_item:
            temp_item["status_details"] = Utility.model_to_dict(item.status_details)
        
        del temp_item["password"]
        users_list.append(temp_item)

    response_data = {
        "total_count":total_count,
        "list":users_list,
        "page":filter_data.page,
        "per_page":filter_data.per_page
    }
    return Utility.json_response(status=SUCCESS, message="User Details successfully retrieved", error=[], data=response_data,code="")
@router.post("/get-customet-details",response_model=UserListResponse, response_description="Get User Details")
async def get_benficiary( request: GetUserDetailsReq,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        
        user_id = auth_user["id"]
        if auth_user.get("role_id", -1) in [1]:
            user_id = request.user_id
        elif auth_user.get("role_id", -1) in [2]:
            user_id = auth_user["id"]
        if auth_user.get("role_id", -1) in [2] and user_id !=request.user_id:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={})

        user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        response_data = Utility.model_to_dict(user_obj)
        response_data["user_id"] = response_data["id"]
        response_data["tenant_details"] = Utility.model_to_dict(user_obj.tenant_details)
        response_data["role_details"] = Utility.model_to_dict(user_obj.role_details)
        response_data["status_details"] = Utility.model_to_dict(user_obj.status_details)
        #response_data["country_details"] = Utility.model_to_dict(user_obj.country_details)
        #response_data["kyc_status"] = Utility.model_to_dict(user_obj.kyc_status)
        
        if "login_fail_count" in response_data:
            del response_data["login_fail_count"]
        if "password" in response_data:
            del response_data["password"]
        if "otp" in response_data:
            del response_data["otp"]
        if "login_attempt_date" in response_data:
            del response_data["login_attempt_date"]    
                
        return Utility.json_response(status=SUCCESS, message="User Details successfully retrieved", error=[], data=response_data,code="")

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
