from datetime import datetime, timezone,timedelta
from sqlalchemy import and_
from sqlalchemy.sql import select, and_, or_, not_,func
from sqlalchemy.future import select
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from ...models.tickets_model import TicketsModel
from ...models.user_model import CustomerModal
from ...models.master_data_models import MdUserRole,MdUserStatus

from . import APIRouter, Utility, SUCCESS, FAIL, EXCEPTION ,WEB_URL, API_URL, INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
import re
from ...schemas.tickets_schema import TicketRequest,TicketResponse,PaginatedTicketResponse,TicketListRequest
from fastapi import BackgroundTasks
from ...schemas.login import Login
from ...constant import messages as all_messages
from ...common.mail import Email
import json
from ...models.user_model import AdminNotificationModel
from sqlalchemy.orm import  joinedload
from sqlalchemy import desc, asc
from ...models.admin_user import AdminUser



# APIRouter creates path operations for product module

router = APIRouter(
    prefix="/support",
    tags=["Support Tickets"],
    responses={404: {"description": "Not found"}},
)

@router.post("/ticket-request", response_description="Create Support Ticket")
def request_ticket(request: TicketRequest,background_tasks: BackgroundTasks, auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        #print(auth_user["tenant_details"]["email"])
        # if auth_user["role_id"] !=2:            
        #     return Utility.json_response(status=500, message=all_messages.NO_PERMISSIONS, error=[], data={},code="LOGOUT_ACCOUNT")            
        
        user_id = auth_user["id"]
        description=request.description
        subject = request.subject
        user_obj = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if auth_user["role_id"] ==5:
            user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        if user_obj is None:            
            return Utility.json_response(status=500, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="LOGOUT_ACCOUNT")            
        # elif user_obj.role_id !=2:            
        #     return Utility.json_response(status=500, message=all_messages.NO_PERMISSIONS, error=[], data={},code="LOGOUT_ACCOUNT")            
        # elif user_obj.status_id == 1:
        #         return Utility.json_response(status=500, message=all_messages.PENDING_PROFILE_COMPLATION, error=[], data={},code="LOGOUT_ACCOUNT")
        
        # elif user_obj.status_id == 2:
        #     return Utility.json_response(status=500, message=all_messages.PENDING_EMAIL_VERIFICATION, error=[], data={},code="LOGOUT_ACCOUNT")            
        # elif user_obj.status_id == 4:
        #     return Utility.json_response(status=500, message=all_messages.PROFILE_INACTIVE, error=[], data={},code="LOGOUT_ACCOUNT")            
        # elif user_obj.status_id == 5:
        #     return Utility.json_response(status=500, message=all_messages.PROFILE_DELETED, error=[], data={},code="LOGOUT_ACCOUNT")
        
        reference = Utility.generate_tfs_code("SUPPORT_TICKET")
        ticket_data = TicketsModel(subject =subject, description=description,reference= reference)
        if auth_user["role_id"] ==5: 
            ticket_data.created_by_user_id = user_id
        else:
            ticket_data.created_by_admin_id = user_id
        if "tenant_id" in auth_user:
            if auth_user["tenant_id"]  is not None:
                ticket_data.tenant_id = auth_user["tenant_id"]
        elif request.tenant_id is not None:
            ticket_data.tenant_id = request.tenant_id
            

        db.add(ticket_data)
        db.commit()
        #Send acknowledge mail to user 
        mail_data = {"user_name":user_obj.first_name +" "+user_obj.last_name,"subject":subject,"description":description,"mail_to":"user","reference":reference}
        background_tasks.add_task(Email.send_mail, recipient_email=[user_obj.email], subject="Ticket Acknowledge", template='ticket_created.html',data=mail_data )
       
        #Send mail to tenant admin
        
        if auth_user.get("tenant_details",False):
            if auth_user["tenant_details"].get("email",False):
                admin_id = auth_user["tenant_details"]["id"]
                
                admin_mail_data = {"user_name":user_obj.first_name +" "+user_obj.last_name, "admin_name":auth_user["tenant_details"]["name"],"subject":subject, "description":description,"mail_to":"admin","reference":reference}
                background_tasks.add_task(Email.send_mail,recipient_email=[auth_user["tenant_details"]["email"]], subject="Ticket Created", template='ticket_created.html',data=admin_mail_data )
            if ticket_data.id:
                admin_notification = AdminNotificationModel(user_id=user_id,admin_id=admin_id,description=description,category="TICKET",ref_id=ticket_data.id)
                db.add(admin_notification)
                db.commit()
        return Utility.json_response(status=SUCCESS, message=all_messages.TICKET_CREATED, error=[], data={},code="")

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/ticketRequest-list", response_model=PaginatedTicketResponse, response_description="Fetch ticket List")
async def get_users(filter_data: TicketListRequest,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        # if auth_user.get("role_id", -1) not in [1]:
        #     return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.NO_PERMISSIONS, error=[], data={},code="NO_PERMISSIONS")

        tenant_id = None
        query = db.query(TicketsModel)
        if auth_user["role_id"] ==5:
            
            query = query.filter( TicketsModel.created_by_user_id == auth_user["id"] )
        elif auth_user["role_id"] ==4:
            query = query.filter( TicketsModel.created_by_admin_id == auth_user["id"] )
        if "tenant_id" in auth_user:
            if auth_user["tenant_id"]  is not None:
                query = query.filter( TicketsModel.tenant_id == auth_user["tenant_id"] )
        elif filter_data.tenant_id is not None:
            query = query.filter( TicketsModel.tenant_id == filter_data.tenant_id )

        if filter_data.search_string:
            search = f"%{filter_data.search_string}%"
            query = query.filter( or_(
                 TicketsModel.description.ilike(search),
                 TicketsModel.subject.ilike(search),
                  TicketsModel.reference.ilike(search)
                 
                                       ) )   
        # if filter_data.created_on and filter_data.created_to and ( isinstance(filter_data.created_on, date) and isinstance(filter_data.created_to, date)):
        #     query = query.filter(TicketsModel.created_on > filter_data.created_on)
        #     query = query.filter(TicketsModel.created_on < filter_data.created_to)
        
        # Total count of users matching the filters
        total_count = query.count()
        print(total_count)
        sort_column = getattr(TicketsModel, str(filter_data.sort_by), None)
        query = query.order_by(desc(sort_column))

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
        lst =[]
        for item in paginated_query:
            dct = Utility.model_to_dict(item)
            if item.created_by_admin_id:
                
                created_by_admin_details = Utility.model_to_dict(item.created_by_admin_details)
                dct["created_by_details"] = {
                    "first_name":created_by_admin_details["first_name"],
                    "last_name":created_by_admin_details["last_name"],
                    "name":created_by_admin_details["name"],
                    "email":created_by_admin_details["email"],
                    "mobile_no":created_by_admin_details["mobile_no"],
                    "id":created_by_admin_details["id"],
                     "role_id":created_by_admin_details["role_id"],
                }
            if item.created_by_user_id:
                
                created_by_details = Utility.model_to_dict(item.created_by_details)
                dct["created_by_details"] = {
                    "first_name":created_by_details["first_name"],
                    "last_name":created_by_details["last_name"],
                    "name":created_by_details["name"],
                    "email":created_by_details["email"],
                    "mobile_no":created_by_details["mobile_no"],
                    "id":created_by_details["id"],
                     "role_id":created_by_details["role_id"],
                }    
            lst.append(dct)
        # Create a paginated response
        response_data = { "total_count":total_count, "list":lst,  "page":filter_data.page,  "per_page":filter_data.per_page }
        return Utility.json_response(status=SUCCESS, message="Successfully retrieved", error=[], data=response_data,code="")
        
    except Exception as E:
        
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
