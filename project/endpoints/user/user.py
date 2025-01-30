from datetime import datetime, timezone,timedelta
from datetime import datetime
from ...models.user_model import CustomerModal
from ...models.master_data_models import MdUserRole,MdUserStatus,MdCountries
from fastapi import FastAPI, HTTPException
import requests
from requests.auth import HTTPBasicAuth
from . import APIRouter, Utility, SUCCESS, FAIL, WEB_URL, EXCEPTION ,INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.user_schema import UpdatePassword,OrderIDRequest,UserFilterRequest,ApplyLoanSchema,EnquiryDetailsSchema,getCustomerDetails,getloanApplicationDetails,UserListResponse, UpdateKycDetails,UpdateProfile,BeneficiaryRequest,BeneficiaryEdit, GetBeneficiaryDetails, ActivateBeneficiary,UpdateBeneficiaryStatus, ResendBeneficiaryOtp,BeneficiaryResponse
from ...schemas.user_schema import UpdateKycStatus
from ...models.user_model import NotificationModel
#import pytz
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
from ...models.user_model import CustomerModal,LoanapplicationModel,EnquiryModel,SubscriptionModel,CustomerDetailsModel
from typing import Dict
from ...models.master_data_models import ServiceConfigurationModel,MdSubscriptionPlansModel
from ...aploger import AppLogger

# APIRouter creates path operations for product module
router = APIRouter(
    prefix="/customer",
    tags=["Customer"],
    responses={404: {"description": "Not found"}},
)

@router.post("/enquiry/list", response_description="Fetch Users List")
async def get_enquiry(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    
    try:
        today = datetime.today()
        query = db.query(EnquiryModel).options(
            joinedload(EnquiryModel.enquiry_tenant_details),
            joinedload(EnquiryModel.enquir_status_details),
            joinedload(EnquiryModel.enquir_service_details)
            ).filter(EnquiryModel.status_id !=2)
        
        query = query.filter(or_(
            (EnquiryModel.status_id == 1) & (EnquiryModel.followupdate ==None),
            (EnquiryModel.followupdate !=None) & (today >=EnquiryModel.followupdate),
            
        ))
        


        if filter_data.search_string:
            search = f"%{filter_data.search_string}%"
            query = query.filter(
                or_(
                    EnquiryModel.name.ilike(search),
                    EnquiryModel.description.ilike(search),
                    EnquiryModel.email.ilike(search),
                    EnquiryModel.mobile_no.ilike(search),
                    EnquiryModel.tfs_id.ilike(search),
                    
                )
            )
        if filter_data.tenant_id:
            query = query.filter(EnquiryModel.tenant_id.in_(filter_data.tenant_id))
        if filter_data.status_ids:
            query = query.filter(EnquiryModel.status_id.in_(filter_data.status_ids))
        
        total_count = query.count()
        sort_column = getattr(EnquiryModel, filter_data.sort_by, None)
        if sort_column:
            
            if filter_data.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc("status_id"))

        # Apply pagination
        offset = (filter_data.page - 1) * filter_data.per_page
        paginated_query = query.offset(offset).limit(filter_data.per_page).all()
        # Create a paginated response
        users_list =[]
        for item in paginated_query:
            temp_item = Utility.model_to_dict(item)
            
            # if "tenant_id" in temp_item and temp_item["tenant_id"] is not None:
                
            #     temp_item["tenant_details"] = Utility.model_to_dict(item.enquiry_tenant_details)
            #     if item.enquiry_tenant_details.tenant_admin:
            #         temp_item["tenant_details"]["admin"] = {}
            #         for admin in item.enquiry_tenant_details.tenant_admin:
            #             details = Utility.model_to_dict(admin)
            #             if details["status_id"] ==3 and  details["role_id"] ==2:
            #                 temp_item["tenant_details"]["admin"]["id"] = details["id"]
            #                 temp_item["tenant_details"]["admin"]["tfs_id"] = details["tfs_id"]
            #                 temp_item["tenant_details"]["admin"]["first_name"] = details["first_name"]
            #                 temp_item["tenant_details"]["admin"]["last_name"] = details["last_name"]
            #                 temp_item["tenant_details"]["admin"]["name"] = details["name"]
            #                 temp_item["tenant_details"]["admin"]["email"] = details["email"]
            #                 temp_item["tenant_details"]["admin"]["role_details"] = Utility.model_to_dict(admin.role_details)

            if "service_type_id" in temp_item and temp_item["service_type_id"] is not None:
                temp_item["service_details"] = Utility.model_to_dict(item.enquir_service_details)
            if "status_id" in temp_item:
                temp_item["status_details"] = Utility.model_to_dict(item.enquir_status_details)
            
            users_list.append(temp_item)

        response_data = {
            "total_count":total_count,
            "list":users_list,
            "page":filter_data.page,
            "per_page":filter_data.per_page
        }
        return Utility.json_response(status=SUCCESS, message="Successfully retrieved", error=[], data=response_data,code="")
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
@router.post("/enquiry/details", response_description="enquiry details")
async def get_enquiry(filter_data: EnquiryDetailsSchema,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    
    try:
        today = datetime.today()
        query = db.query(EnquiryModel).options(
            joinedload(EnquiryModel.enquiry_tenant_details),
            joinedload(EnquiryModel.enquir_status_details),
            joinedload(EnquiryModel.enquir_service_details)
            ).filter(EnquiryModel.id ==filter_data.enquiry_id)
        paginated_query = query.one()
        # Create a paginated response
        if paginated_query is not None:
            response_data = Utility.model_to_dict(paginated_query)
        return Utility.json_response(status=SUCCESS, message="Successfully retrieved", error=[], data=response_data,code="")
    except Exception as E:
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


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
        AppLogger.error(str(E))
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
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/list", response_description="Fetch Users List")
async def get_customers(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    #user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
    #AuthHandler().user_validate(user_obj)
    # if auth_user.get("role_id", -1) not in [1,2]:
    #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")

    
    query = db.query(CustomerModal).options(
        joinedload(CustomerModal.tenant_details),
        joinedload(CustomerModal.role_details),
        joinedload(CustomerModal.status_details),
        joinedload(CustomerModal.created_by_details),
        joinedload(CustomerModal.service_details),
        joinedload(CustomerModal.loan_applications_list),
        joinedload(CustomerModal.current_plan_details)
    ).filter(CustomerModal.current_plan_id ==None)

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
    if auth_user.get("role_id", -1) ==3:
        query = query.filter(CustomerModal.salesman_id == auth_user["id"] )
    if auth_user.get("role_id", -1) ==4:
        query = query.filter(CustomerModal.agent_id == auth_user["id"] )
        
    
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
            loan_applications_list =[]
            for loan in item.loan_applications_list:
                loan_applications_list.append(Utility.model_to_dict(loan))
            temp_item["loan_applications_list"] = sorted(loan_applications_list, key=lambda x: x['id'], reverse=True)
        
        if "status_id" in temp_item:
            temp_item["status_details"] = Utility.model_to_dict(item.status_details)
        if "current_plan_id" in temp_item:
            temp_item["current_plan_details"] =  Utility.model_to_dict(item.current_plan_details)
        del temp_item["password"]
        users_list.append(temp_item)

    response_data = {
        "total_count":total_count,
        "list":users_list,
        "page":filter_data.page,
        "per_page":filter_data.per_page
    }
    return Utility.json_response(status=SUCCESS, message="User Details successfully retrieved", error=[], data=response_data,code="")
@router.post("/subscribers-list", response_description="Fetch Users List")
async def get_customers(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    #user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
    #AuthHandler().user_validate(user_obj)
    # if auth_user.get("role_id", -1) not in [1,2]:
    #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")

    
    query = db.query(CustomerModal).options(
        joinedload(CustomerModal.tenant_details),
        joinedload(CustomerModal.role_details),
        joinedload(CustomerModal.status_details),
        joinedload(CustomerModal.created_by_details),
        joinedload(CustomerModal.service_details),
        joinedload(CustomerModal.loan_applications_list),
        joinedload(CustomerModal.current_plan_details)
    ).filter(CustomerModal.current_plan_id >=1)

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
    if auth_user.get("role_id", -1) ==3:
        query = query.filter(CustomerModal.salesman_id == auth_user["id"] )
    if auth_user.get("role_id", -1) ==4:
        query = query.filter(CustomerModal.agent_id == auth_user["id"] )
        
    
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
            loan_applications_list =[]
            for loan in item.loan_applications_list:
                loan_applications_list.append(Utility.model_to_dict(loan))
            temp_item["loan_applications_list"] = sorted(loan_applications_list, key=lambda x: x['id'], reverse=True)
        
        if "status_id" in temp_item:
            temp_item["status_details"] = Utility.model_to_dict(item.status_details)
        if "current_plan_id" in temp_item:
            temp_item["current_plan_details"] =  Utility.model_to_dict(item.current_plan_details)
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
async def get_customer_details( request: getCustomerDetails,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        """
        customer_id -->customer_basic_details
        service_type_id -->customer_service_detail
        lead_sourse_id --> leadsourse_details
        profession_type_id --->customer_profession_details
        profession_sub_type_id -->customer_profession_sub_type_details
        income_type_id ---> customer_income_type_details
        updated_by -->updated_by_details
       
        agent_id = Column(Integer, nullable=True, default=None )
        salesman_id = Column(Integer, nullable=True, default=None )
        admin_id = Column(Integer, nullable=True, default=None )
        loan_approved_by = Column(Integer, nullable=True, default=None )

        """
        role_id = auth_user["role_id"]

        
        customer_id = request.customer_id
        customer_query = db.query(CustomerModal).options(
        joinedload(CustomerModal.tenant_details),
        joinedload(CustomerModal.role_details),
        joinedload(CustomerModal.status_details),
        joinedload(CustomerModal.created_by_details),
        joinedload(CustomerModal.service_details),
        joinedload(CustomerModal.loan_applications_list),
        joinedload(CustomerModal.current_plan_details)
    ).filter(CustomerModal.id ==customer_id)
        if role_id !=1 and auth_user["tenant_id"] is not None:
            customer_query = customer_query.filter(CustomerModal.tenant_id == auth_user["tenant_id"])
        
        customer = customer_query.one_or_none()
        if customer is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={})
        # elif  customer.status_id == 1:
        #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="LOGOUT_ACCOUNT")
        # elif  customer.status_id == 2:
        #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="LOGOUT_ACCOUNT")
        # elif customer.status_id == 4:
        #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_INACTIVE, error=[], data={},code="LOGOUT_ACCOUNT")
        # elif customer.status_id == 5:
        #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.PROFILE_DELETED, error=[], data={},code="LOGOUT_ACCOUNT")

        query = db.query(CustomerDetailsModel).filter(CustomerDetailsModel.customer_id == customer_id)
        if role_id !=1 and auth_user["tenant_id"] is not None:
            query = query.filter(CustomerDetailsModel.tenant_id == auth_user["tenant_id"])
        dbcursor = query.first()
        if dbcursor is None:
            customer_details ={}
            applicant_details = Utility.model_to_dict(customer)
            del applicant_details["password"]
            customer_details ={}
            customer_details["applicant_details"] = applicant_details
            return Utility.json_response(status=SUCCESS, message=all_messages.CUSTOMER_DETAILS_NOT_FOUND, error=[], data=customer_details,code="CUSTOMER_DETAILS_NOT_FOUND")

        application_data = Utility.model_to_dict(dbcursor)
        if dbcursor.customer_id and dbcursor.customer_basic_details is not None:
            application_data["applicant_details"] = Utility.model_to_dict(dbcursor.customer_basic_details)
            del application_data["applicant_details"]["password"]

        if dbcursor.service_type_id and dbcursor.customer_service_detail is not None:
            application_data["detail_of_service"] = Utility.model_to_dict(dbcursor.customer_service_detail)
        #lead_sourse_id --> lead_sourse_details
        if dbcursor.lead_sourse_id and dbcursor.leadsourse_details is not None:
            application_data["lead_sourse_details"] = Utility.model_to_dict(dbcursor.leadsourse_details)
        #profession_type_id --->profession_details
        if dbcursor.profession_type_id and dbcursor.customer_profession_details is not None:
            application_data["profession_details"] = Utility.model_to_dict(dbcursor.customer_profession_details)
        
        #profession_sub_type_id --->profession_sub_type_details
        if dbcursor.profession_sub_type_id and dbcursor.customer_profession_sub_type_details is not None:
            application_data["profession_sub_type_details"] = Utility.model_to_dict(dbcursor.customer_profession_sub_type_details)
        #income_type_id --->income_type_details
        if dbcursor.income_type_id and dbcursor.customer_income_type_details is not None:
            application_data["income_type_details"] = Utility.model_to_dict(dbcursor.customer_income_type_details)
        #created_by -->created_by_details
        if dbcursor.updated_by and dbcursor.updated_by_details is not None:
            application_data["updated_by_details"] = Utility.model_to_dict(dbcursor.updated_by_details)
        
        
        if customer.tenant_id and customer.tenant_details:
            #get agent details from Adminuser Modal
            application_data["tenant_details"] = {}
            application_data["tenant_details"]["email"] =customer.tenant_details.email
        if customer.created_by and customer.created_by_details:
            
            application_data["applicant_details"]["created_by_details"] =  Utility.model_to_dict(customer.created_by_details)
        
        if customer.agent_id :
            #get agent details from Adminuser Modal
            pass
        if customer.salesman_id :
            #get salesman details from Adminuser Modal
            pass
        print("dhgdhghdkghd")
        return Utility.json_response(status=SUCCESS, message="Details successfully retrieved", error=[], data=application_data,code="")

    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

#create-update-customer-details
@router.post("/create-update-customer-details",response_model=UserListResponse, response_description="Get User Details")
async def update_customer_details( request: Dict, background_tasks: BackgroundTasks, auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
       
        role_id = auth_user["role_id"]
        tenant_id = 1
        if "tenant_id"  in auth_user:
            tenant_id = auth_user["tenant_id"]
        enquiry_id = request["enquiry_id"]
        #loan_application_form_id = request["loan_application_form_id"]
        query = db.query(EnquiryModel).filter(EnquiryModel.id == enquiry_id)
        enquiry_data = query.one()
        #CustomerModal
        new_customer = CustomerModal(                                    
                                      first_name=enquiry_data.name,
                                      last_name=enquiry_data.name,
                                      name=enquiry_data.name,
                                      role_id =5,
                                      status_id=2,
                                      email=enquiry_data.email,
                                      mobile_no=enquiry_data.mobile_no,
                                      password=str(Utility.uuid()),
                                      tenant_id=tenant_id,
                                      service_type_id=request.get("service_type_id",None),
                                      date_of_birth = request.get("date_of_birth",None)
                                      )
        db.add(new_customer)
        db.commit()
        enquiry_data.status_id =2
        if new_customer.id:
            mail_data = {"body":"Welcome to TFS"}
            otp =str(Utility.generate_otp())
            category ="SIGNUP_CUSTOMER"
            customer_id = new_customer.id
            new_customer.status_id = 2
            new_customer.tfs_id = f"{Utility.generate_tfs_code(5)}{new_customer.id}"
            user_dict={"user_id":new_customer.id,"catrgory":category,"otp":otp}
            token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":5,"email":new_customer.email,"name":new_customer.name},43200)
            user_dict["token"]=token
            user_dict["ref_id"]=new_customer.id
            db.add(tokensModel(**user_dict))
            #db.query(CustomerModal).filter(CustomerModal.email == user_data.email).update({"status_id": 2}, synchronize_session=False)
            db.commit()
            link = f'''{WEB_URL}set-customer-password?token={token}&user_id={new_customer.id}'''
            background_tasks.add_task(Email.send_mail, recipient_email=[new_customer.email], subject="Welcome to TFS", template='add_user.html',data={"name":new_customer.name,"link":link})
            
            dbcursor =  CustomerDetailsModel(customer_id=customer_id,service_type_id=request.get("service_type_id",None),tenant_id=tenant_id)
            
            configuration =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.service_type_id==request.get("service_type_id",None),ServiceConfigurationModel.tenant_id==tenant_id).first()
            loan_id = Utility.generate_tfs_code("LOAN")
            new_lead =  LoanapplicationModel(customer_id=customer_id,tfs_id=loan_id,service_type_id=request.get("service_type_id",None),tenant_id=tenant_id)
            db.add(new_lead)
            if configuration is not None: 
                new_lead.salesman_id = configuration.user_id
                new_customer.salesman_id = configuration.user_id    
            if auth_user["role_id"] ==3:
                dbcursor.salesman_id = auth_user["id"]
                new_lead.salesman_id  = auth_user["id"]
                new_customer.salesman_id = auth_user["id"]  
            if auth_user["role_id"] ==4:
                dbcursor.agent_id = auth_user["id"]
            db.add(dbcursor)
            db.commit()
        
        if dbcursor is None:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.LOAN_APPL_FORM_NOT_FOUND, error=[], data={},code="LOAN_APPL_FORM_NOT_FOUND")
        
        # if request.get("date_of_birth",False):
        #     dbcursor.date_of_birth = request["date_of_birth"]

        # if request.get("alternate_mobile_no",False):
        #     dbcursor.alternate_mobile_no = request["alternate_mobile_no"]

        dbcursor.sepType = request.get("sepType",None)
        dbcursor.service_type_id = request.get("service_type_id",None)
        dbcursor.loanAmount = request.get("loanAmount",None)
        dbcursor.profession_type_id = request.get("profession_type_id",None)
        dbcursor.lead_sourse_id = request.get("lead_sourse_id",None)
        dbcursor.profession_sub_type_id = request.get("profession_sub_type_id",None)
        dbcursor.companyName = request.get("companyName",'')
        dbcursor.designation = request.get("designation",'')
        dbcursor.totalExperience = request.get("totalExperience",None)
        dbcursor.present_organization_years = request.get("present_organization_years",None)
        dbcursor.workLocation = request.get("workLocation",'')
        dbcursor.grossSalary = request.get("grossSalary",None)
        dbcursor.netSalary = request.get("netSalary",None)
        dbcursor.otherIncome = request.get("otherIncome","No")
        dbcursor.other_income_list ='[]'
        if request.get("otherIncome","No")=="Yes":
            dbcursor.other_income_list = request.get("other_income_list","")
        dbcursor.Obligations = request.get("Obligations","No")
        dbcursor.all_obligations ='[]'
        dbcursor.other_obligation = "[]"
        if request.get("Obligations","No")=="Yes":
            dbcursor.all_obligations = request.get("all_obligations","")
            dbcursor.other_obligation = request.get("all_obligations","")
        
        dbcursor.obligations_per_month = request.get("obligations_per_month",None)


        #SENP
        
        if request.get("number_of_years",0):
            dbcursor.number_of_years=request.get("number_of_years",None)

        dbcursor.location=request.get("location",'')
        dbcursor.last_turnover_year=request.get("last_turnover_year",'')
        dbcursor.last_year_turnover_amount=request.get("last_year_turnover_amount",None)
        dbcursor.last_year_itr=request.get("last_year_itr",'')
        dbcursor.lastYearITRamount=request.get("lastYearITRamount",None)
        dbcursor.current_turnover_year=request.get("current_turnover_year",'')
        dbcursor.current_year_turnover_amount=request.get("current_year_turnover_amount",None)
        dbcursor.current_year_itr=request.get("current_year_itr",'')
        dbcursor.presentYearITRamount=request.get("presentYearITRamount",None)
        dbcursor.avg_income_per_month=request.get("avg_income_per_month",None)

        dbcursor.eligible=request.get("eligible","No")
        dbcursor.fdir=request.get("fdir","")
        dbcursor.description=request.get("description",None)
        dbcursor.loan_eligible_type= None
        dbcursor.loan_eligible_amount= None
        if request.get("eligible","No")=="Yes":
            dbcursor.loan_eligible_type=request.get("loan_eligible_type",None)
            dbcursor.loan_eligible_amount=request.get("loan_eligible_amount",None)

        #SEP Column fields
        #income_type_id
        dbcursor.income_type_id = request.get("income_type_id",None)
        dbcursor.total_obligation_amount_per_month = request.get("total_obligation_amount_per_month",None)
        # if request.get("eligible","No")=="Yes":
        #     dbcursor.status_id =2

        db.commit()
        return Utility.json_response(status=SUCCESS, message="Details  are updated successfully", error=[], data=request,code="")

    except Exception as E:
        print("ERROR")
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/update-customer-details",response_model=UserListResponse, response_description="Get User Details")
async def update_customer_details( request: Dict,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        
       
        role_id = auth_user["role_id"]
        tenant_id = 1
        if "tenant_id"  in auth_user:
            tenant_id = auth_user["tenant_id"]
        loan_application_form_id = request["loan_application_form_id"]
        customer = db.query(CustomerModal).filter(CustomerModal.id == loan_application_form_id).one()
        if customer is None:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        

        query = db.query(CustomerDetailsModel).filter(CustomerDetailsModel.customer_id == loan_application_form_id)
        dbcursor = query.first()
       
        if dbcursor is  None:
            dbcursor =  CustomerDetailsModel(customer_id=loan_application_form_id,service_type_id=request.get("service_type_id",None),tenant_id=tenant_id)
            if auth_user["role_id"] ==3:
                dbcursor.salesman_id = auth_user["id"]
            if auth_user["role_id"] ==4:
                dbcursor.agent_id = auth_user["id"]
            db.add(dbcursor)
            db.commit()
        
        if dbcursor is None:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        
        print(dbcursor.id) 
        # if request.get("date_of_birth",False):
        #     dbcursor.date_of_birth = request["date_of_birth"]

        # if request.get("alternate_mobile_no",False):
        #     dbcursor.alternate_mobile_no = request["alternate_mobile_no"]
     
        customer.date_of_birth = request.get("date_of_birth",None)
        dbcursor.sepType = request.get("sepType",None)
        dbcursor.service_type_id = request.get("service_type_id",None)
        dbcursor.loanAmount = request.get("loanAmount",None)
        dbcursor.profession_type_id = request.get("profession_type_id",None)
        dbcursor.lead_sourse_id = request.get("lead_sourse_id",None)
        dbcursor.profession_sub_type_id = request.get("profession_sub_type_id",None)
        dbcursor.companyName = request.get("companyName",'')
        dbcursor.designation = request.get("designation",'')
        dbcursor.totalExperience = request.get("totalExperience",None)
        dbcursor.present_organization_years = request.get("present_organization_years",None)
        dbcursor.workLocation = request.get("workLocation",'')
        dbcursor.grossSalary = request.get("grossSalary",None)
        dbcursor.netSalary = request.get("netSalary",None)
        dbcursor.otherIncome = request.get("otherIncome","No")
        dbcursor.other_income_list ='[]'
        if request.get("otherIncome","No")=="Yes":
            dbcursor.other_income_list = request.get("other_income_list","")
        dbcursor.Obligations = request.get("Obligations","No")
        dbcursor.all_obligations ='[]'
        dbcursor.other_obligation = "[]"
        if request.get("Obligations","No")=="Yes":
            dbcursor.all_obligations = request.get("all_obligations","")
            dbcursor.other_obligation = request.get("all_obligations","")
        
        dbcursor.obligations_per_month = request.get("obligations_per_month",None)


        #SENP
        
        if request.get("number_of_years",0):
            dbcursor.number_of_years= request.get("number_of_years",0) #round(float(request.get("number_of_years",0)), 2)

        dbcursor.location=request.get("location",'')
        dbcursor.last_turnover_year=request.get("last_turnover_year",'')
        dbcursor.last_year_turnover_amount=request.get("last_year_turnover_amount",None)
        dbcursor.last_year_itr=request.get("last_year_itr",'')
        dbcursor.lastYearITRamount=request.get("lastYearITRamount",None)
        dbcursor.current_turnover_year=request.get("current_turnover_year",'')
        dbcursor.current_year_turnover_amount=request.get("current_year_turnover_amount",None)
        dbcursor.current_year_itr=request.get("current_year_itr",'')
        dbcursor.presentYearITRamount=request.get("presentYearITRamount",None)
        dbcursor.avg_income_per_month=request.get("avg_income_per_month",None)

        dbcursor.eligible=request.get("eligible","No")
        dbcursor.fdir=request.get("fdir","")
        dbcursor.description=request.get("description",None)
        dbcursor.loan_eligible_type= None
        dbcursor.loan_eligible_amount= None
        if request.get("eligible","No")=="Yes":
            dbcursor.loan_eligible_type=request.get("loan_eligible_type",None)
            dbcursor.loan_eligible_amount=request.get("loan_eligible_amount",None)

        #SEP Column fields
        #income_type_id
        dbcursor.income_type_id = request.get("income_type_id",None)
        dbcursor.total_obligation_amount_per_month = request.get("total_obligation_amount_per_month",None)
        # if request.get("eligible","No")=="Yes":
        #     dbcursor.status_id =2

        db.commit()
        return Utility.json_response(status=SUCCESS, message="Details  are updated successfully", error=[], data=request,code="")

    except Exception as E:
        print("ERROR")
        AppLogger.error(f"update customer details {str(E)}")
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

#getloan-application-details
@router.post("/getloan-application-details",response_model=UserListResponse, response_description="Get User Details")
async def get_loan_application_details( request: getloanApplicationDetails,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        """
        customer_id -->customer_details
        service_type_id -->detail_of_service
        lead_sourse_id --> lead_sourse_details
        profession_type_id --->profession_details
        profession_sub_type_id -->profession_sub_type_details
        income_type_id ---> income_type_details
        created_by -->created_by_details
        status_id -->  status_details


        agent_id = Column(Integer, nullable=True, default=None )
        salesman_id = Column(Integer, nullable=True, default=None )
        admin_id = Column(Integer, nullable=True, default=None )
        loan_approved_by = Column(Integer, nullable=True, default=None )

        """
        role_id = auth_user["role_id"]

        
        loan_application_form_id = request.loan_application_form_id
        query = db.query(LoanapplicationModel).filter(LoanapplicationModel.id == loan_application_form_id)
        
        if role_id !=1 and auth_user["tenant_id"] is not None:
            query = query.filter(LoanapplicationModel.tenant_id == auth_user["tenant_id"])



        dbcursor = query.first()
        if dbcursor is None:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.LOAN_APPL_FORM_NOT_FOUND, error=[], data={},code="LOAN_APPL_FORM_NOT_FOUND")

        application_data = Utility.model_to_dict(dbcursor)
        if dbcursor.customer_id and dbcursor.customer_details is not None:
            application_data["applicant_details"] = Utility.model_to_dict(dbcursor.customer_details)
            del application_data["applicant_details"]["password"]

        if dbcursor.service_type_id and dbcursor.detail_of_service is not None:
            application_data["detail_of_service"] = Utility.model_to_dict(dbcursor.detail_of_service)
        #lead_sourse_id --> lead_sourse_details
        if dbcursor.lead_sourse_id and dbcursor.lead_sourse_details is not None:
            application_data["lead_sourse_details"] = Utility.model_to_dict(dbcursor.lead_sourse_details)
        #profession_type_id --->profession_details
        if dbcursor.profession_type_id and dbcursor.profession_details is not None:
            application_data["profession_details"] = Utility.model_to_dict(dbcursor.profession_details)
        
        #profession_sub_type_id --->profession_sub_type_details
        if dbcursor.profession_sub_type_id and dbcursor.profession_sub_type_details is not None:
            application_data["profession_sub_type_details"] = Utility.model_to_dict(dbcursor.profession_sub_type_details)
        #income_type_id --->income_type_details
        if dbcursor.income_type_id and dbcursor.income_type_details is not None:
            application_data["income_type_details"] = Utility.model_to_dict(dbcursor.income_type_details)
        #created_by -->created_by_details
        if dbcursor.created_by and dbcursor.created_by_details is not None:
            application_data["created_by_details"] = Utility.model_to_dict(dbcursor.created_by_details)
        if dbcursor.status_id and dbcursor.status_details is not None:
            application_data["status_details"] = Utility.model_to_dict(dbcursor.status_details)
        
        if dbcursor.agent_id :
            #get agent details from Adminuser Modal
            pass
        if dbcursor.salesman_id :
            #get salesman details from Adminuser Modal
            pass
        if dbcursor.admin_id :
            #get admin details from Adminuser Modal
            pass
        if dbcursor.loan_approved_by :
            #get loan_approved_by details from Adminuser Modal
            pass
        return Utility.json_response(status=SUCCESS, message="Loan Application Details successfully retrieved", error=[], data=application_data,code="")

    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/update-loan-application-details",response_model=UserListResponse, response_description="Get User Details")
async def update_loan_application_details( request: Dict,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
       
        role_id = auth_user["role_id"]
        loan_application_form_id = request["loan_application_form_id"]
        query = db.query(LoanapplicationModel).filter(LoanapplicationModel.id == loan_application_form_id)
        
        if role_id !=1 and auth_user["tenant_id"] is not None:
            query = query.filter(LoanapplicationModel.tenant_id == auth_user["tenant_id"])

        

        dbcursor = query.first()
        if dbcursor is None:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.LOAN_APPL_FORM_NOT_FOUND, error=[], data={},code="LOAN_APPL_FORM_NOT_FOUND")
        
        
        # if request.get("date_of_birth",False):
        #     dbcursor.date_of_birth = request["date_of_birth"]

        # if request.get("alternate_mobile_no",False):
        #     dbcursor.alternate_mobile_no = request["alternate_mobile_no"]

        
        dbcursor.sepType = request.get("sepType",None)
        dbcursor.service_type_id = request.get("service_type_id",None)
        dbcursor.loanAmount = request.get("loanAmount",None)
        dbcursor.profession_type_id = request.get("profession_type_id",None)
        dbcursor.lead_sourse_id = request.get("lead_sourse_id",None)
        dbcursor.profession_sub_type_id = request.get("profession_sub_type_id",None)
        dbcursor.companyName = request.get("companyName",'')
        dbcursor.designation = request.get("designation",'')
        dbcursor.totalExperience = request.get("totalExperience",None)
        dbcursor.present_organization_years = request.get("present_organization_years",None)
        dbcursor.workLocation = request.get("workLocation",'')
        dbcursor.grossSalary = request.get("grossSalary",None)
        dbcursor.netSalary = request.get("netSalary",None)
        dbcursor.otherIncome = request.get("otherIncome","No")
        dbcursor.other_income_list ='[]'
        if request.get("otherIncome","No")=="Yes":
            dbcursor.other_income_list = request.get("other_income_list","")
        dbcursor.Obligations = request.get("Obligations","No")
        dbcursor.all_obligations ='[]'
        dbcursor.other_obligation = "[]"
        if request.get("Obligations","No")=="Yes":
            dbcursor.all_obligations = request.get("all_obligations","")
            dbcursor.other_obligation = request.get("all_obligations","")
        
        dbcursor.obligations_per_month = request.get("obligations_per_month",None)


        #SENP
        # if request.get("number_of_years",0)>0:
        #     dbcursor.number_of_years=request.get("number_of_years",None)

        dbcursor.location=request.get("location",'')
        dbcursor.last_turnover_year=request.get("last_turnover_year",'')
        dbcursor.last_year_turnover_amount=request.get("last_year_turnover_amount",None)
        dbcursor.last_year_itr=request.get("last_year_itr",'')
        dbcursor.lastYearITRamount=request.get("lastYearITRamount",None)
        dbcursor.current_turnover_year=request.get("current_turnover_year",'')
        dbcursor.current_year_turnover_amount=request.get("current_year_turnover_amount",None)
        dbcursor.current_year_itr=request.get("current_year_itr",'')
        dbcursor.presentYearITRamount=request.get("presentYearITRamount",None)
        dbcursor.avg_income_per_month=request.get("avg_income_per_month",None)

        dbcursor.eligible=request.get("eligible","No")
        dbcursor.fdir=request.get("fdir","")
        dbcursor.description=request.get("description",None)
        dbcursor.loan_eligible_type= None
        dbcursor.loan_eligible_amount= None
        if request.get("eligible","No")=="Yes":
            dbcursor.loan_eligible_type=request.get("loan_eligible_type",None)
            dbcursor.loan_eligible_amount=request.get("loan_eligible_amount",None)

        #SEP Column fields
        #income_type_id
        dbcursor.income_type_id = request.get("income_type_id",None)
        dbcursor.total_obligation_amount_per_month = request.get("total_obligation_amount_per_month",None)
        if request.get("eligible","No")=="Yes":
            dbcursor.status_id =2

        db.commit()
        return Utility.json_response(status=SUCCESS, message="Loan Application Details successfully retrieved", error=[], data=request,code="")

    except Exception as E:
        AppLogger.error(str(E))
        AppLogger.error(f"update loan application details {str(E)}")
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})



@router.post("/applications-list", response_description="Fetch Applications List")
async def applications_list(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
    
        query = db.query(LoanapplicationModel).options(
            joinedload(LoanapplicationModel.customer_details),
            joinedload(LoanapplicationModel.detail_of_service),
            joinedload(LoanapplicationModel.created_by_details),
            joinedload(LoanapplicationModel.lead_sourse_details),
            joinedload(LoanapplicationModel.profession_details),
            joinedload(LoanapplicationModel.profession_sub_type_details),
            joinedload(LoanapplicationModel.income_type_details),
            joinedload(LoanapplicationModel.created_by_details),
            joinedload(LoanapplicationModel.status_details),
            
        )#.join(LoanapplicationModel.customer_details)
        if(auth_user["role_id"] ==5):
            query = query.filter(LoanapplicationModel.customer_id==auth_user["id"])
        
        
        if filter_data.search_string:
            search = f"%{filter_data.search_string}%"
            query = query.filter(
                or_(
                    LoanapplicationModel.tfs_id.ilike(search),
                    #LoanapplicationModel.customer_details.name.ilike(search),
                    #LoanapplicationModel.customer_details.email.ilike(search),
                    
                )
            )
         
        if filter_data.tenant_id:
            query = query.filter(LoanapplicationModel.tenant_id.in_(filter_data.tenant_id))
        
        
        if filter_data.status_ids:
            query = query.filter(LoanapplicationModel.status_id.in_(filter_data.status_ids))
        
        # Total count of users matching the filters
        
        total_count = query.count()
        sort_column = getattr(LoanapplicationModel, filter_data.sort_by, None)
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
            joinedload(LoanapplicationModel.customer_details),
            joinedload(LoanapplicationModel.detail_of_service),
            joinedload(LoanapplicationModel.created_by_details),
            joinedload(LoanapplicationModel.lead_sourse_details),
            joinedload(LoanapplicationModel.profession_details),
            joinedload(LoanapplicationModel.profession_sub_type_details),
            joinedload(LoanapplicationModel.income_type_details),
            joinedload(LoanapplicationModel.created_by_details),
            joinedload(LoanapplicationModel.status_details),
            """
            if "customer_id" in temp_item and temp_item["customer_id"] is not None:
                temp_item["customer_details"] = Utility.model_to_dict(item.customer_details)

            if "service_type_id" in temp_item and temp_item["service_type_id"] is not None:
                temp_item["detail_of_service"] = Utility.model_to_dict(item.detail_of_service)
            
            if "created_by" in temp_item and temp_item["created_by"] is not None:
                temp_item["created_by_details"] = Utility.model_to_dict(item.created_by_details)

            if "lead_sourse_id" in temp_item and temp_item["lead_sourse_id"] is not None:
                temp_item["lead_sourse_details"] = Utility.model_to_dict(item.lead_sourse_details)
            
            if "profession_type_id" in temp_item and temp_item["profession_type_id"] is not None:
                temp_item["profession_details"] = Utility.model_to_dict(item.profession_details)
            
            if "profession_sub_type_id" in temp_item and temp_item["profession_sub_type_id"] is not None:
                temp_item["profession_sub_type_details"] = Utility.model_to_dict(item.profession_sub_type_details)
            if "income_type_id" in temp_item and temp_item["income_type_id"] is not None:
                temp_item["income_type_details"] = Utility.model_to_dict(item.income_type_details)
            if "status_id" in temp_item:
                temp_item["status_details"] = Utility.model_to_dict(item.status_details)
            users_list.append(temp_item)

        response_data = {
            "total_count":total_count,
            "list":users_list,
            "page":filter_data.page,
            "per_page":filter_data.per_page
        }
        return Utility.json_response(status=SUCCESS, message="List successfully retrieved", error=[], data=response_data,code="")
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


#apply-loan
@router.post("/apply-loan", response_description="Fetch Applications List")
async def apply_loan(request: ApplyLoanSchema,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        # service_type_id:int
        # user_id:int
        # tenant_id:Optional[int] =1
        tenant_id = 1
        user_id = request.user_id
        service_type_id = request.service_type_id
        if auth_user["role_id"] ==1:
            tenant_id = request.tenant_id
        else:
            tenant_id = auth_user["tenant_id"]
        customer = db.query(CustomerModal).filter(CustomerModal.id==user_id,CustomerModal.tenant_id==tenant_id).first()    
        if customer is None:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.CUSTOMER_NOT_FOUND, error=[], data={},code="CUSTOMER_NOT_FOUND")
        else:
            # if customer.status_id !=3:
            #     return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.CUSTOMER_NOT_ACTIVE, error=[], data={},code="CUSTOMER_NOT_ACTIVE")
            loan_id = Utility.generate_tfs_code("LOAN")
            new_lead =  LoanapplicationModel(customer_id=user_id,tfs_id=loan_id,service_type_id=service_type_id,tenant_id=tenant_id)
            if auth_user["role_id"] ==3:
                new_lead.salesman_id = auth_user["id"]
            if auth_user["role_id"] ==4:
                new_lead.agent_id = auth_user["id"]
            db.add(new_lead)
            db.commit()
            if new_lead.id:
                return Utility.json_response(status=SUCCESS, message=all_messages.LOAN_APPLICATION_CREATED, error=[], data={"new_lead":new_lead.id})
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
    

                
    except Exception as E:
        
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/user-subscriptions-list", response_description="Fetch Applications List")
async def applications_list(filter_data: UserFilterRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
    
        query = db.query(SubscriptionModel).options(
            joinedload(SubscriptionModel.customer),
            joinedload(SubscriptionModel.plan),
            
            
        )
        if(auth_user["role_id"] ==5):
            query = query.filter(SubscriptionModel.customer_id==auth_user["id"])
        

        if filter_data.search_string:
            search = f"%{filter_data.search_string}%"
            query = query.filter(
                or_(
                    SubscriptionModel.customer.name.ilike(search),
                    SubscriptionModel.customer.email.ilike(search),
                    
                )
            )
        if filter_data.tenant_id:
            query = query.filter(SubscriptionModel.tenant_id.in_(filter_data.tenant_id))
        
        
        
        # Total count of users matching the filters
        
        total_count = query.count()
        sort_column = getattr(SubscriptionModel, filter_data.sort_by, None)
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
           
            if "customer_id" in temp_item and temp_item["customer_id"] is not None:
                temp_item["customer_details"] = Utility.model_to_dict(item.customer)
            if "plan_id" in temp_item and temp_item["plan_id"] is not None:
                temp_item["plan_details"] = Utility.model_to_dict(item.plan)
            if "razorpay_signature" in temp_item:
                del temp_item["razorpay_signature"]

            if "razorpay_payment_id" in temp_item:
                del temp_item["razorpay_payment_id"]

            users_list.append(temp_item)

        response_data = {
            "total_count":total_count,
            "list":users_list,
            "page":filter_data.page,
            "per_page":filter_data.per_page
        }
        return Utility.json_response(status=SUCCESS, message="List successfully retrieved", error=[], data=response_data,code="")
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/check-payment-status/")
async def check_payment_status(order: OrderIDRequest, auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        order_id = order.order_id
        url = f"https://api.razorpay.com/v1/orders/{order_id}"
        subscription = db.query(SubscriptionModel).filter(SubscriptionModel.razorpay_order_id==order_id).one()
        if subscription is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Not Found", error=[], data={})
        
        response = requests.get(url, auth=HTTPBasicAuth("rzp_live_cPBJOHgDRsgEzg", "WG3HbZSO2izDGu1UbsSaTtCC"))
        if response.status_code == 200:
            order_data = response.json()
            if order_data["status"]=="paid":
                customer = db.query(CustomerModal).filter(CustomerModal.id==subscription.customer_id)
                subscription.status="paid"
                unix_timestamp = order_data["payment"]["captured_at"]
                #india_tz = pytz.timezone('Asia/Kolkata')
                #date_time = datetime.fromtimestamp(unix_timestamp, india_tz)
                date_time = datetime.utcfromtimestamp(unix_timestamp)
                subscription.start_date = date_time
                db.commit()
                
            data= {"order_id": order_data["id"], "status": order_data["status"]}
            return Utility.json_response(status=SUCCESS, message="", error=[], data=data)
        else:
            return Utility.json_response(status=INTERNAL_ERROR, message="Failed to fetch order details", error=[], data={})
            #raise HTTPException(status_code=response.status_code, detail="Failed to fetch order details")
    except Exception as E:
        AppLogger.error(str(E))
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
