from datetime import datetime, timezone,timedelta
from sqlalchemy import and_
from datetime import datetime
from ...models.user_model import CustomerModal,CustomerDetailsModel, LoanapplicationModel,EnquiryModel,SubscriptionModel
from ...models.master_data_models import ServiceConfigurationModel,MdSubscriptionPlansModel

from . import APIRouter, Utility, SUCCESS, FAIL, EXCEPTION ,WEB_URL, API_URL, INTERNAL_ERROR,BAD_REQUEST,BUSINESS_LOGIG_ERROR, Depends, Session, get_database_session, AuthHandler
from ...schemas.register import createCustomerSchema, SignupOtp,ForgotPassword,CompleteSignup,VerifyAccount,resetPassword
from ...schemas.register import EnquiryRequestSchema,EnquiryRequestOtpSchema,EnquiryBecomeCustomer,createSubscriberSchema,AddPlanToUserSchema,GetpaymentLink,paymentSuccessSchema
import re
from ...schemas.login import Login
from ...constant import messages as all_messages
from ...common.mail import Email
import json
from fastapi import BackgroundTasks
from ...models.admin_user import AdminUser
from ...models.admin_configuration_model import tokensModel
from ...library.webSocketConnectionManager import manager
from ...common.razorpay_service import RazorpayClient, get_razorpay_client
# APIRouter creates path operations for product module
router = APIRouter(
    prefix="/auth",
    tags=["User Authentication"],
    responses={404: {"description": "Not found"}},
)

@router.post("/enquiry-otp",  response_description="Enquiry Otp")
async def enquiry_otp(request:EnquiryRequestOtpSchema,background_tasks: BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        tenant_id =1
        service_type_id = None
        mobile_no = request.mobile_no
        email = request.email
        name = request.name
        description = request.description
        
        if request.tenant_id is not None:
            tenant_id = request.tenant_id
        if request.service_type_id is not None:
            service_type_id = request.service_type_id
        otp =str(Utility.generate_otp())
        category ="ENQUIRY_OTP"
        new_token = AuthHandler().encode_token({"mobile_no":mobile_no,"catrgory":category,"otp":otp,"email":email,"name":name})
        user_dict={"user_id":1,"catrgory":category,"otp":otp,"token":new_token,"ref_id":1}
        enquiry_data = tokensModel(**user_dict)
        db.add(enquiry_data)
        db.commit()
        if enquiry_data.id:
            background_tasks.add_task(Email.send_mail, recipient_email=[email], subject="Welcome to TFS", template='enquirey_otp.html',data={"name":name,"otp":otp})
            return Utility.json_response(status=SUCCESS, message="Thank you for reaching out to us", error=[],data={},code="SIGNUP_PROCESS_PENDING")
            
        else:            
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
    except Exception as E:
        
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/enquiry",  response_description="Customer enquiry")
async def enquiry(request:EnquiryRequestSchema,background_tasks: BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        tenant_id =1
        service_type_id = None
        mobile_no = request.mobile_no
        email = request.email
        name = request.name
        description = request.description
        otp = request.otp
        token_data = db.query(tokensModel).filter(tokensModel.otp == otp, tokensModel.user_id==1, tokensModel.active==True, tokensModel.catrgory=="ENQUIRY_OTP").first()
        if token_data is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Invalid Token", error=[], data={},code="INVALIED_TOKEN")
        
        tokendata = AuthHandler().decode_otp_token(token_data.token)
        if tokendata is None :
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="The time you were taken has expired!", error=[], data={},code="INVALIED_TOKEN")
        
        
        if request.tenant_id is not None:
            tenant_id = request.tenant_id
        if request.service_type_id is not None:
            service_type_id = request.service_type_id
        tfs_id = Utility.generate_tfs_code("ENQUIRY_OTP")
        tfs_id = f"{tfs_id}-{Utility.generate_otp(5)}"
        enquiry_data = EnquiryModel(tfs_id=tfs_id,name=name,email=email,mobile_no=mobile_no,service_type_id=service_type_id,tenant_id=tenant_id,description=description)
        token_data.active = False
        db.add(enquiry_data)
        db.commit()
        if enquiry_data.id:
            #send mail to user
            background_tasks.add_task(Email.send_mail, recipient_email=[email], subject="Welcome to TFS", template='enquirey.html',data={"name":name,})
            #send mail to admin
            return Utility.json_response(status=SUCCESS, message="Thank you for reaching out to us", error=[],data={},code="SIGNUP_PROCESS_PENDING")
            
        else:
            
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
    except Exception as E:
        
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/enquirer-to-customer",  response_description="enquirer to make as customer")
async def enquiry(request:EnquiryBecomeCustomer,background_tasks: BackgroundTasks,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        """enquiry_id:int
    tenant_id: Optional[int] =1
    service_type_id:Optional[int] = None
    status_id:int
    followupdate:Optional[date] = None
    description:str
        """
        
        enquiry_id =  request.enquiry_id
        tenant_id = 1
        service_type_id =None
        status_id = None
        followupdate = None
        current_plan_id = None
        description = ""
        if request.tenant_id:
            tenant_id = request.tenant_id
        role_id = auth_user["role_id"]
        user_id = auth_user["id"]
        if request.service_type_id is not None:
            service_type_id = request.service_type_id
        if request.status_id:
            status_id = request.status_id
        if request.followupdate:
            followupdate = request.followupdate
        if request.description:
            description = request.description
        
        plan_details =None
        enquiry_data =  db.query(EnquiryModel).filter(EnquiryModel.id==enquiry_id,EnquiryModel.tenant_id==tenant_id).first()
        if status_id ==2:
            if service_type_id is None:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Service Type is required!", error=[], data={})

            if service_type_id ==1:
                if request.current_plan_id is not None:
                    current_plan_id = request.current_plan_id
                if current_plan_id is None:
                    return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription Plan is required!", error=[], data={})
                else:
                    plan_details = db.query(MdSubscriptionPlansModel).filter(MdSubscriptionPlansModel.id==current_plan_id).first()
                    if plan_details is None:
                        return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription Plan is not found!", error=[], data={})

        else:
            if followupdate is None:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Followup date is required", error=[], data={})
 
        if enquiry_data is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Data is not found!", error=[], data={})
        
        enquiry_data.status_id = status_id
        #7827015628
        enquiry_data.followupdate =followupdate
        enquiry_data.description = description
        enquiry_data.service_type_id = service_type_id
        if status_id !=2:
            db.commit()
            return Utility.json_response(status=SUCCESS, message="Update Successfully", error=[], data={})

        existing_customer = db.query(CustomerModal).filter(CustomerModal.email == enquiry_data.email).first()
        configuration =None
        configuration =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.service_type_id==service_type_id,ServiceConfigurationModel.tenant_id==tenant_id).first()
        if existing_customer is None:            
            user_data = CustomerModal(                                    
                                      first_name=enquiry_data.name,
                                      last_name=enquiry_data.name,
                                      name=enquiry_data.name,
                                      role_id =5,
                                      status_id=2,
                                      email=enquiry_data.email,
                                      mobile_no=enquiry_data.mobile_no,
                                      password=str(Utility.uuid()),
                                      tenant_id=tenant_id,
                                      service_type_id=service_type_id
                                      )
            
            mail_data = {"body":"Welcome to TFS"}
            otp =str(Utility.generate_otp())
            category ="SIGNUP_CUSTOMER"
            db.add(user_data)
            db.flush()
            db.commit()
            if user_data.id:
                if role_id == 3:
                    user_data.salesman_id = user_id
                if role_id == 4:
                    user_data.agent_id = user_id
                
                if service_type_id is not None:
                    if service_type_id ==1:                        
                        # this is subscription Functionality
                        razorpay_order_id = None, ##we need to impliment
                        razorpay_payment_id = None
                        new_subscription = SubscriptionModel(
                        customer_id = user_data.id ,
                        plan_id =current_plan_id,
                        start_date = datetime.now(timezone.utc),
                        end_date = None,
                        payment_status = "Pending",  # Payment status (Pending, Success, Failed)
                        payment_amount = plan_details.amount,
                        razorpay_order_id = razorpay_order_id, ##we need to impliment
                        razorpay_payment_id = razorpay_payment_id,
                        tenant_id = user_data.tenant_id ##we need to impliment
                        
                        )
                        db.add(new_subscription)
                        db.commit()
                        if new_subscription.id:
                            user_data.current_plan_id = current_plan_id
                            user_data.status_id = 2
                            user_data.tfs_id = f"{Utility.generate_tfs_code(5)}{user_data.id}"
                            user_dict={"user_id":user_data.id,"catrgory":category,"otp":otp}
                            token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":5,"email":user_data.email,"name":user_data.name},43200)
                            user_dict["token"]=token
                            user_dict["ref_id"]=user_data.id
                            db.add(tokensModel(**user_dict))
                            #db.query(CustomerModal).filter(CustomerModal.email == user_data.email).update({"status_id": 2}, synchronize_session=False)
                            db.commit()
                            link = f'''{WEB_URL}set-customer-password?token={token}&user_id={user_data.id}'''
                            background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Welcome to TFS", template='add_user.html',data={"name":user_data.name,"link":link})
                            db.commit()
                            return Utility.json_response(status=SUCCESS, message="Successfully subscription added", error=[], data={"razorpay_order_id":razorpay_order_id,"razorpay_payment_id":razorpay_payment_id},code="REDIRECT_TO_PAYMENT_GATEWAY")

                        else:
                            db.rollback()
                            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
                    else:
                        new_lead =  LoanapplicationModel(customer_id=user_data.id,tfs_id=f"{Utility.generate_tfs_code("LOAN")}",service_type_id=service_type_id,tenant_id=tenant_id)
                        db.add(new_lead)
                if configuration is not None:
                    if status_id ==2 and  service_type_id !=1 and new_lead is not None:
                        new_lead.salesman_id = configuration.user_id
                    user_data.salesman_id = configuration.user_id
                    
                user_data.tfs_id = f"{Utility.generate_tfs_code(5)}{user_data.id}"
                udata =  Utility.model_to_dict(user_data)
                db.query(EnquiryModel).filter(EnquiryModel.email == enquiry_data.email).update({"status_id": status_id}, synchronize_session=False)
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
                token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":5,"email":user_data.email,"name":user_data.name},43200)
                user_dict["token"]=token
                user_dict["ref_id"]=udata["id"]
                db.add(tokensModel(**user_dict))
                enquiry_data.status_id =2
                db.query(CustomerModal).filter(CustomerModal.email == enquiry_data.email).update({"status_id": 2}, synchronize_session=False)
                db.commit()
                link = f'''{WEB_URL}set-customer-password?token={token}&user_id={user_data.id}'''
                background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Welcome to TFS", template='add_user.html',data={"name":user_data.name,"link":link})
                if new_lead.id:
                    rowData["loanApplicationId"] = new_lead.id
                return Utility.json_response(status=SUCCESS, message=all_messages.REGISTER_SUCCESS, error=[],data=rowData,code="SIGNUP_PROCESS_PENDING")
            else:
                
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
        else:
            if service_type_id ==1:                        
                        # this is subscription Functionality
                        razorpay_order_id = None, ##we need to impliment
                        razorpay_payment_id = None
                        new_subscription = SubscriptionModel(
                        customer_id = existing_customer.id ,
                        plan_id =current_plan_id,
                        start_date = datetime.now(timezone.utc),
                        end_date = None,
                        payment_status = "Pending",  # Payment status (Pending, Success, Failed)
                        payment_amount = plan_details.amount,
                        razorpay_order_id = razorpay_order_id, ##we need to impliment
                        razorpay_payment_id = razorpay_payment_id, ##we need to impliment
                        tenant_id = existing_customer.tenant_id
                        
                        )
                        db.add(new_subscription)
                        db.commit()
                        if new_subscription.id:
                            existing_customer.current_plan_id = current_plan_id
                            db.commit()
                            return Utility.json_response(status=SUCCESS, message="Successfully subscription added", error=[], data={"razorpay_order_id":razorpay_order_id,"razorpay_payment_id":razorpay_payment_id},code="REDIRECT_TO_PAYMENT_GATEWAY")
                        else:
                            db.rollback()
                            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
            new_lead =  LoanapplicationModel(customer_id=existing_customer.id,service_type_id=service_type_id,tenant_id=tenant_id)
            db.add(new_lead)
            db.commit()
            if configuration is not None:
                
                existing_customer.salesman_id = configuration.user_id
            if new_lead.id:
                res_data = {"loanApplicationId":None}
                new_lead.salesman_id = configuration.user_id
                res_data["loanApplicationId"] = new_lead.id
                return Utility.json_response(status=SUCCESS, message="Lead Added successfully", error=[],data=res_data,code="LEAD_CREATED_SUCCESS")
            else:
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
    except Exception as E:
        #print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


#createCustomerSchema
@router.post("/invite-customer", response_description="Invite Customer")
async def invite_customer(request: createCustomerSchema,background_tasks: BackgroundTasks,auth_user=Depends(AuthHandler().auth_wrapper), db: Session = Depends(get_database_session)):
    try:
        tenant_id = 1
        role_id = auth_user["role_id"]
        mobile_no = request.mobile_no
        email = request.email
        first_name = request.first_name
        last_name = request.last_name
        if request.tenant_id is not None and role_id ==1:
            tenant_id = request.tenant_id
        elif auth_user["tenant_id"] and role_id !=1:
            tenant_id = auth_user["tenant_id"]
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
            configuration =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.service_type_id==service_type_id,ServiceConfigurationModel.tenant_id==tenant_id).first()
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
                details =  CustomerDetailsModel(customer_id=user_data.id,service_type_id=service_type_id)
                configuration =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.service_type_id==service_type_id,ServiceConfigurationModel.tenant_id==tenant_id).first()
                new_lead =  LoanapplicationModel(customer_id=user_data.id,tfs_id=f"{Utility.generate_tfs_code("LOAN")}", service_type_id=service_type_id,tenant_id=tenant_id)
                db.add(new_lead)
                db.add(details)
                if configuration is not None:
                    new_lead.salesman_id = configuration.user_id
                    user_data.salesman_id = configuration.user_id
                #assig salse man
                if role_id ==3:
                    new_lead.salesman_id = auth_user["id"]
                    user_data.salesman_id = auth_user["id"]
                elif role_id ==4:
                    #assign agent id
                    new_lead.agent_id = auth_user["id"]
                    user_data.agent_id = auth_user["id"]
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
                token = AuthHandler().encode_token({"user_id":user_data.id,"catrgory":category,"otp":otp,"invite_role_id":user_data.role_id,"email":user_data.email,"name":user_data.name},43200)
                link = f'''{WEB_URL}set-customer-password?token={token}&user_id={user_data.id}'''
                user_dict={"user_id":user_data.id,"catrgory":category,"otp":otp,"token":token,"ref_id":user_data.id}
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Welcome to TFS", template='invite_user.html',data={"name":user_data.name,"link":link})
                return Utility.json_response(status=SUCCESS, message=all_messages.USER_INVITE, error=[], data=rowData,code="OTP_VERIVICARION_SUCCESS")
            
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
            new_token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name},43200)
            link = f'''{WEB_URL}set-customer-password?token={new_token}&user_id={existing_user.id}'''
          
            user_dict={"user_id":existing_user.id,"catrgory":category,"otp":otp}
            user_dict["token"]=new_token
            user_dict["ref_id"]=existing_user.id
            if existing_user.status_id == 1:
                """
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
                """   
                
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="User already exists", error=[], data=rowData,code="USER_ALREADY_EXISTS")
            elif  existing_user.status_id == 2:
                """
                link = f'''{WEB_URL}set-customer-password?token={new_token}&user_id={existing_user.id}'''
                otp = str(Utility.generate_otp())
                category = "ADD_USER"
                token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name})
                user_dict={"user_id":existing_user.id,"catrgory":category,"otp":otp,"token":token,"ref_id":existing_user.id}
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[existing_user.email], subject="Welcome to TFS", template='add_user.html',data={"name":existing_user.name,"link":link})
                """
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="User already exists", error=[], data=rowData,code="USER_ALREADY_EXISTS")
            
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

@router.post("/signup-customer", response_description="Customer Signup")
async def register_customer(request: createCustomerSchema,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        tenant_id = 1
        mobile_no = request.mobile_no
        email = request.email
        first_name = request.first_name
        last_name = request.last_name
        current_plan_id =None
        if request.tenant_id is not None:
            tenant_id = request.tenant_id
        service_type_id = request.service_type_id
        plan_details = None
        if request.current_plan_id:
            current_plan_id = request.current_plan_id
            plan_details = db.query(MdSubscriptionPlansModel).filter(MdSubscriptionPlansModel.id==current_plan_id).first()
            if plan_details is None:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription Plan is not found!", error=[], data={})


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
            configuration =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.service_type_id==service_type_id,ServiceConfigurationModel.tenant_id==tenant_id).first()
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
            if service_type_id==1 and current_plan_id is not None:
                user_data.current_plan_id = current_plan_id
            #Send Mail to user with active link
            mail_data = {"body":"Welcome to TFS"}
            db.add(user_data)
            db.flush()
            db.commit()
            if user_data.id:
                configuration =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.service_type_id==service_type_id,ServiceConfigurationModel.tenant_id==tenant_id).first()
                new_lead =  LoanapplicationModel(tfs_id=f"{Utility.generate_tfs_code("LOAN")}",customer_id=user_data.id,service_type_id=service_type_id,tenant_id=tenant_id)
                db.add(new_lead)
                if configuration is not None:
                    new_lead.salesman_id = configuration.user_id
                    user_data.salesman_id = configuration.user_id
                   
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

                if service_type_id==1 and current_plan_id is not None:
                    user_data.current_plan_id = current_plan_id
                    razorpay_payment_id = None
                    invoice_id = Utility.generate_tfs_code("INVOICE")
                    patment_details = Utility.create_payment_link(plan_details.amount,invoice_id)
                    if patment_details.get("status",False) and patment_details.get("payment_link","") != "" and "razorpay_order_id" in patment_details:
                        #{"status":True,"message": "Payment link sent successfully", "payment_link": link, "razorpay_order_id": razorpay_order_id}
                        mail_data["payment_link"] = patment_details["payment_link"]
                        new_subscription = SubscriptionModel(
                        customer_id = user_data.id ,
                        plan_id =current_plan_id,
                        start_date = None,
                        end_date = None,
                        invoice_id =invoice_id,
                        payment_status = "Initiated",  # Payment status (Pending, Success, Failed)
                        payment_amount = plan_details.amount,
                        razorpay_order_id = patment_details["razorpay_order_id"], ##we need to impliment
                        razorpay_payment_id = patment_details["order_details"]["razorpay_payment_id"],
                        razorpay_signature = patment_details["order_details"]["razorpay_signature"],
                        payment_link=patment_details["payment_link"],
                        tenant_id = user_data.tenant_id ##we need to impliment
                        )
                        db.add(new_subscription)
                        db.commit()
                        if new_subscription.id:
                            link_otp = str(Utility.generate_otp())
                            patment_link_category = "PAYMENT_LINK"
                            token_data={"user_id": udata["id"] ,"catrgory":patment_link_category,"otp":link_otp,"invite_role_id":5,"email":user_data.email,"name":user_data.name}
                            token_data["name"] = user_data.name
                            token_data["email"] = user_data.email
                            token_data["payment_link"] = patment_details["payment_link"]
                            

                            token_data["plan_details"] = {}
                            token_data["plan_details"]["name"] = plan_details.name
                            token_data["plan_details"]["amount"] = plan_details.amount
                            token_data["plan_details"]["validity"] = plan_details.name
                            token_data["subscription_id"]  = new_subscription.id
                            token = AuthHandler().encode_token(token_data,minutes=2880)
                            token_data["link"] = f"{WEB_URL}payment?token={token}"
                            tokenmodel = {"user_id":udata["id"],"catrgory":patment_link_category,"otp":link_otp}
                            tokenmodel["token"]=token
                            tokenmodel["ref_id"]=new_subscription.id
                            db.add(tokensModel(**tokenmodel))
                            db.commit()
                            #background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Subscription Payment Request", template='payment_request.html',data=token_data)
                

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
            new_token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name},43200)
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
                link = f'''{WEB_URL}set-customer-password?token={new_token}&user_id={existing_user.id}'''
                otp = str(Utility.generate_otp())
                category = "ADD_USER"
                token = AuthHandler().encode_token({"user_id":existing_user.id,"catrgory":category,"otp":otp,"invite_role_id":existing_user.role_id,"email":existing_user.email,"name":existing_user.name})
                user_dict={"user_id":existing_user.id,"catrgory":category,"otp":otp,"token":token,"ref_id":existing_user.id}
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[existing_user.email], subject="Welcome to TFS", template='add_user.html',data={"name":existing_user.name,"link":link})
                return Utility.json_response(status=SUCCESS, message=all_messages.OTP_VERIVICARION_SUCCESS, error=[], data=rowData,code="OTP_VERIVICARION_SUCCESS")
            
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
            new_token = AuthHandler().encode_token({"user_id":user_obj.id,"catrgory":category,"otp":otp,"invite_role_id":user_obj.role_id,"email":user_obj.email,"name":user_obj.name},43200)
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
                login_token = AuthHandler().encode_token(user_dict,120)
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



@router.post("/reset-password", response_description="Forgot Password")
async def reset_password(request: resetPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        token = str(request.token)
        password =  request.password
        token_data = db.query(tokensModel).filter(tokensModel.token == token, tokensModel.user_id==user_id, tokensModel.active==True).first()
        user_obj = db.query(CustomerModal).filter(CustomerModal.id == user_id).first()
        if user_obj is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message=all_messages.USER_NOT_EXISTS, error=[], data={},code="USER_NOT_EXISTS")
        else:
            if token !=token_data.token:
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
        category ="CUSTOMER_FORGOT_PASSWORD"
        # if customer>=1:
        #     category ="CUSTOMER_FORGOT_PASSWORD"
        
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
                token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"role_id":user_obj.role_id,"email":user_obj.email,"name":user_obj.name},43200)
                user_dict["token"]=token
                user_dict["ref_id"]=user_obj.id
                db.add(tokensModel(**user_dict))
                rowData["reset_link"] =  f'''{WEB_URL}set-customer-password?token={token}&user_id={user_obj.id}&customer={customer}''' #f'''{WEB_URL}forgotPassword?token={token}&user_id={user_obj.id}'''
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

@router.post("/set-password", response_description="Forgot Password")
async def reset_password(request: resetPassword,background_tasks: BackgroundTasks, db: Session = Depends(get_database_session)):
    try:
        user_id = request.user_id
        token = str(request.token)
        password =  request.password
        customer = 0
        if request.customer:
            customer = request.customer
        # query = db.query(AdminUser).filter(AdminUser.id == user_id)
        # if customer>=1:
        
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
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/add-subscriber",  response_description="enquirer to make as customer")
async def enquiry(request:createSubscriberSchema,background_tasks: BackgroundTasks,auth_user=Depends(AuthHandler().auth_wrapper),razor_pay_client:RazorpayClient =Depends(get_razorpay_client), db: Session = Depends(get_database_session)):
    try:
        enquiry_id =  None
        send_payment_link = False
        tenant_id = 1
        email =  request.email
        first_name = request.first_name
        last_name = request.last_name
        date_of_birth = request.date_of_birth
        gender = ""
        mobile_no = request.mobile_no
        alternate_mobile_no = request.alternate_mobile_no
        pan_card_number = request.pan_card_number
        aadhaar_card_number = request.aadhaar_card_number
        nominee = request.nominee
        relation_with_nominee = request.relation_with_nominee
        service_type_id =None
        current_plan_id = None
        if request.tenant_id:
            tenant_id = request.tenant_id
        if request.send_payment_link:
            send_payment_link = request.send_payment_link
        if request.enquiry_id:
            enquiry_id = request.enquiry_id
        if request.gender:
            gender = request.gender
        
        role_id = auth_user["role_id"]
        user_id = auth_user["id"]
        if request.service_type_id is not None:
            service_type_id = request.service_type_id
        
        
        enquiry_details =  None
        plan_details =None
        if service_type_id is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Service Type is required!", error=[], data={})

        if service_type_id ==1:
            if request.current_plan_id is not None:
                current_plan_id = request.current_plan_id
            if current_plan_id is None:
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription Plan is required!", error=[], data={})
            else:
                plan_details = db.query(MdSubscriptionPlansModel).filter(MdSubscriptionPlansModel.id==current_plan_id).first()
                if plan_details is None:
                    return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription Plan is not found!", error=[], data={})


        if enquiry_id is not None:
            enquiry_details = db.query(EnquiryModel).filter(EnquiryModel.email == email, EnquiryModel.id==enquiry_id).first()
        existing_customer = db.query(CustomerModal).filter(CustomerModal.email == email).first()
        configuration =None
        configuration =  db.query(ServiceConfigurationModel).filter(ServiceConfigurationModel.service_type_id==service_type_id,ServiceConfigurationModel.tenant_id==tenant_id).first()
        if existing_customer is None:            
            user_data = CustomerModal(                                    
                                      first_name=first_name,
                                      last_name=last_name,
                                      name= f"{first_name} {last_name}",
                                      gender= gender,
                                      role_id =5,
                                      status_id=2,
                                      email=email,
                                      mobile_no=mobile_no,
                                      date_of_birth = date_of_birth,
                                      alternate_mobile_no = alternate_mobile_no,
                                      pan_card_number = pan_card_number,
                                      aadhaar_card_number = aadhaar_card_number,
                                      nominee = nominee,
                                      relation_with_nominee = relation_with_nominee,
                                      password=str(Utility.uuid()),
                                      tenant_id=tenant_id,
                                      service_type_id=1,
                                      current_plan_id=current_plan_id,
                                      )
            
            mail_data = {"body":"Welcome to TFS"}
            otp =str(Utility.generate_otp())
            category ="SIGNUP_CUSTOMER"
            db.add(user_data)
            db.flush()
            db.commit()
            if user_data.id:
                user_data.tfs_id = f"{Utility.generate_tfs_code(5)}{user_data.id}"
                if enquiry_details is not None:
                        enquiry_details.status_id = 2
                udata =  Utility.model_to_dict(user_data)
                user_data.created_by = user_id
                if role_id == 3:
                    user_data.salesman_id = user_id
                if role_id == 4:
                    user_data.agent_id = user_id
                if (configuration is not None) and role_id != 3:                
                        user_data.salesman_id = configuration.user_id    
                                           
                # this is subscription Functionality
                
                mail_data = {}
                
                if send_payment_link:
                    invoice_id = Utility.generate_tfs_code("INVOICE")
                    order_details = razor_pay_client.create_order(amount=plan_details.amount, currency="INR" )
                    if order_details.get("status",False) and "razorpay_order_id" in order_details:
                        new_subscription = SubscriptionModel(
                        customer_id = user_data.id ,
                        plan_id =current_plan_id,
                        start_date = None,
                        end_date = None,
                        invoice_id =invoice_id,
                        payment_status = "Initiated",  # Payment status (Pending, Success, Failed)
                        payment_amount = plan_details.amount,
                        razorpay_order_id = order_details["razorpay_order_id"], ##we need to impliment
                        razorpay_payment_id = "",
                        razorpay_signature ="",
                        payment_link="",
                        tenant_id = tenant_id ##we need to impliment
                        )
                        db.add(new_subscription)
                        db.commit()
                        print("new_subscription.id====",new_subscription.id," *****")
                        if new_subscription.id:
                            link_otp = str(Utility.generate_otp())
                            patment_link_category = "PAYMENT_LINK"
                            token_data={"user_id": udata["id"] ,"catrgory":patment_link_category,"otp":link_otp,"invite_role_id":5,"email":user_data.email,"name":user_data.name}
                            token_data["name"] = user_data.name
                            token_data["email"] = user_data.email
                            token_data["plan_details"] = {}
                            token_data["plan_details"]["name"] = plan_details.name
                            token_data["plan_details"]["amount"] = plan_details.amount
                            token_data["plan_details"]["validity"] = plan_details.name
                            token_data["subscription_id"]  = new_subscription.id
                            token_data["order_details"]  = order_details
                            token = AuthHandler().encode_token(token_data,minutes=2880222222)
                            token_data["link"] = f"{WEB_URL}payment?token={token}"
                            token_data["payment_link"] = token_data["link"]
                            
                            user_dict={"user_id":udata["id"],"catrgory":patment_link_category,"otp":link_otp}
                            user_dict["token"]=token
                            user_dict["ref_id"]=new_subscription.id
                            db.add(tokensModel(**user_dict))
                            db.commit()
                            background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Subscription Payment Request", template='payment_request.html',data=token_data)
                
                        
                rowData = {}
                rowData['user_id'] = udata["id"]
                rowData['first_name'] = udata.get("first_name","")
                rowData['last_name'] = udata.get("last_name","")
                rowData['mobile_no'] = udata.get("mobile_no",'')
                rowData['date_of_birth'] = udata.get("date_of_birth",'')
               
                mail_data["name"]= f'''{udata.get("first_name","")} {udata.get("last_name","")}'''
                mail_data["otp"] = otp
                user_dict={"user_id":udata["id"],"catrgory":category,"otp":otp}
                token = AuthHandler().encode_token({"catrgory":category,"otp":otp,"invite_role_id":5,"email":user_data.email,"name":user_data.name},43200)
                user_dict["token"]=token
                user_dict["ref_id"]=udata["id"]
                db.add(tokensModel(**user_dict))
                db.query(CustomerModal).filter(CustomerModal.email == email).update({"status_id": 2}, synchronize_session=False)
                db.commit()
                link = f'''{WEB_URL}set-customer-password?token={token}&user_id={user_data.id}'''
                background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Welcome to TFS", template='add_user.html',data={"name":user_data.name,"link":link})
                
                if user_data.id:
                    rowData["user_id"] = user_data.id
                return Utility.json_response(status=SUCCESS, message=all_messages.REGISTER_SUCCESS, error=[],data=rowData,code="SIGNUP_PROCESS_PENDING")
            else:
                
                db.rollback()
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
        else:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.USER_ALREADY_EXISTS, error=[], data={})
    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/add-plan-touser",  response_description="enquirer to make as customer")
async def add_plan_to_user(request:AddPlanToUserSchema,background_tasks: BackgroundTasks,auth_user=Depends(AuthHandler().auth_wrapper),db: Session = Depends(get_database_session)):
    try:
        tenant_id = 1
        current_plan_id = None
        customer_id = None
        if request.tenant_id:
            tenant_id = request.tenant_id
        if request.current_plan_id is not None:
            current_plan_id = request.current_plan_id
        if request.customer_id is not None:
            customer_id = request.customer_id
        if auth_user["role_id"] ==5:
            customer_id = auth_user["id"]

        plan_details = db.query(MdSubscriptionPlansModel).filter(MdSubscriptionPlansModel.id==current_plan_id).first()
        if plan_details is None:
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription Plan is not found!", error=[], data={})

        user_data = db.query(CustomerModal).filter(CustomerModal.id == customer_id).first()
        invoice_id = Utility.generate_tfs_code("INVOICE")
        if user_data is not None:
            patment_details = Utility.create_payment_link(plan_details.amount)
            new_subscription = SubscriptionModel(
            customer_id = user_data.id ,
            plan_id =current_plan_id,
            start_date = datetime.now(timezone.utc),
            end_date = None,
            payment_status = "Initiated",  # Payment status (Pending, Success, Failed)
            payment_amount = plan_details.amount,
            razorpay_order_id = patment_details["razorpay_order_id"], ##we need to impliment
            razorpay_signature = patment_details["order_details"]["razorpay_signature"],
            razorpay_payment_id = patment_details["order_details"]["razorpay_payment_id"],
            invoice_id = invoice_id ,
            tenant_id = user_data.tenant_id ##we need to impliment
            
            )
            db.add(new_subscription)
            db.commit()
            if new_subscription.id:
                link_otp = str(Utility.generate_otp())
                patment_link_category = "PAYMENT_LINK"
                token_data={"user_id":user_data.id ,"catrgory":patment_link_category,"otp":link_otp,"invite_role_id":5,"email":user_data.email,"name":user_data.name}
                token_data["name"] = user_data.name
                token_data["email"] = user_data.email
                token_data["payment_link"] = patment_details["payment_link"]
                token_data["plan_details"] = {}
                token_data["plan_details"]["name"] = plan_details.name
                token_data["plan_details"]["amount"] = plan_details.amount
                token_data["plan_details"]["validity"] = plan_details.name
                token_data["subscription_id"]  = new_subscription.id
                token = AuthHandler().encode_token(token_data,minutes=2880)
                token_data["link"] = f"{WEB_URL}payment?token={token}"
                user_dict={"user_id":user_data.id,"catrgory":patment_link_category,"otp":link_otp}
                user_dict["token"]=token
                user_dict["ref_id"]=new_subscription.id
                db.add(tokensModel(**user_dict))
                db.commit()
                background_tasks.add_task(Email.send_mail, recipient_email=[user_data.email], subject="Subscription Payment Request", template='payment_request.html',data=token_data)
                return Utility.json_response(status=SUCCESS, message=all_messages.LOAN_APPLICATION_CREATED, error=[],data=token_data,code="subscription")
            else:
                return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

        else:
            return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.USER_ALREADY_EXISTS, error=[], data={})
    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/get-payment-link",  response_description="enquirer to make as customer")
async def get_payment_link(request:GetpaymentLink,background_tasks: BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        
        
        tokendata = AuthHandler().decode_otp_token(request.token)
        if tokendata is None :
            return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="The time you were taken has expired!", error=[], data={},code="INVALIED_TOKEN")
        
            
        customer = db.query(CustomerModal).filter(CustomerModal.id==tokendata["user_id"]).one()
        if tokendata is not None:
            tokendata["customer_details"] = { "email":customer.email, "phone":customer.mobile_no,"name":customer.name,"first_name":customer.first_name,"laste_name":customer.last_name }
        return Utility.json_response(status=SUCCESS, message=all_messages.SOMTHING_WRONG, error=[], data=tokendata)

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})


@router.post("/generate-link",  response_description="enquirer to make as customer")
async def generate_link(background_tasks: BackgroundTasks,db: Session = Depends(get_database_session)):
    try:
        
        data = Utility.create_payment_link(1)
        return Utility.json_response(status=SUCCESS, message=all_messages.SOMTHING_WRONG, error=[], data=data)

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})

@router.post("/user-payment-success",  response_description="enquirer to make as customer")
async def generate_link(request:paymentSuccessSchema,background_tasks: BackgroundTasks,db: Session = Depends(get_database_session),razor_pay_client:RazorpayClient =Depends(get_razorpay_client)):
    try:
        
        razorpay_order_id = request.razorpay_order_id
        razorpay_payment_id = request.razorpay_payment_id
        razorpay_signature = request.razorpay_signature

        if razor_pay_client._validate_signature(razorpay_order_id=razorpay_order_id,razorpay_payment_id=razorpay_payment_id,razorpay_signature=razorpay_signature):
            
            subscription =  db.query(SubscriptionModel).filter(SubscriptionModel.razorpay_order_id==razorpay_order_id,SubscriptionModel.status== False).first()
            if subscription is None: 
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription in not found!", error=[], data={})
            user_id = subscription.customer_id
            customer = db.query(CustomerModal).filter(CustomerModal.id==user_id).one()
            if customer is None: 
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Customer details are not found!", error=[], data={})
            
            plan_id = subscription.plan_id
            plan_details = db.query(MdSubscriptionPlansModel).filter(MdSubscriptionPlansModel.id==plan_id).one()
            if plan_details is None: 
                return Utility.json_response(status=BUSINESS_LOGIG_ERROR, message="Subscription plan details are not found!", error=[], data={})
            
            subscription.razorpay_payment_id =  razorpay_payment_id
            subscription.razorpay_signature =  razorpay_signature
            subscription.start_date =  datetime.now(timezone.utc),
            subscription.end_date =  datetime.now(timezone.utc)+timedelta(days=90),
            customer.current_subscription_id = subscription.id
            subscription.payment_amount = "success"
            subscription.status = True
            db.commit()
            return Utility.json_response(status=SUCCESS, message="Success", error=[], data={})
        else:
            return Utility.json_response(status=INTERNAL_ERROR, message="Invalied signature", error=[], data={})

    except Exception as E:
        print(E)
        db.rollback()
        return Utility.json_response(status=INTERNAL_ERROR, message=all_messages.SOMTHING_WRONG, error=[], data={})
