from datetime import datetime, timezone,timedelta
from datetime import datetime
from ...models.user_model import CustomerModal
from ...models.master_data_models import MdUserRole,MdUserStatus,MdCountries

from . import APIRouter, Utility, SUCCESS, FAIL, EXCEPTION ,INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.user_schema import UpdatePassword,UserFilterRequest,PaginatedUserResponse,PaginatedBeneficiaryResponse,GetUserDetailsReq,getloanApplicationDetails,UserListResponse, UpdateKycDetails,UpdateProfile,BeneficiaryRequest,BeneficiaryEdit, GetBeneficiaryDetails, ActivateBeneficiary,UpdateBeneficiaryStatus, ResendBeneficiaryOtp,BeneficiaryResponse
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
from ...models.user_model import CustomerModal,LoanapplicationModel
from typing import Dict

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
    # if auth_user.get("role_id", -1) not in [1,2]:
    #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")

    
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

#getloan-application-details
@router.post("/getloan-application-details",response_model=UserListResponse, response_description="Get User Details")
async def get_loan_application_details( request: getloanApplicationDetails,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        """
        subscriber_id -->subscriber
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
        if dbcursor.subscriber_id and dbcursor.subscriber is not None:
            application_data["applicant_details"] = Utility.model_to_dict(dbcursor.subscriber)
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
        print(E)
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
        dbcursor.number_of_years=request.get("number_of_years",'')
        dbcursor.location=request.get("location",'')
        dbcursor.last_turnover_year=request.get("last_turnover_year",'')
        dbcursor.last_year_turnover_amount=request.get("last_year_turnover_amount",'')
        dbcursor.last_year_itr=request.get("last_year_itr",'')
        dbcursor.lastYearITRamount=request.get("lastYearITRamount",None)
        dbcursor.current_turnover_year=request.get("current_turnover_year",'')
        dbcursor.current_year_turnover_amount=request.get("current_year_turnover_amount",'')
        dbcursor.current_year_itr=request.get("current_year_itr",'')
        dbcursor.presentYearITRamount=request.get("presentYearITRamount",'')
        dbcursor.avg_income_per_month=request.get("avg_income_per_month",'')

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
        
        db.commit()
        return Utility.json_response(status=SUCCESS, message="Loan Application Details successfully retrieved", error=[], data=request,code="")

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
