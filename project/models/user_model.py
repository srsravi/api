from sqlalchemy import Column, Integer,Float,INT, Numeric,String, Text, DateTime, ForeignKey,Enum,Date,Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
#from project.database.database import Base
#Base = declarative_base()
from  .base_model import BaseModel
from datetime import datetime,timezone
from enum import Enum as PyEnum
class kycStatus(PyEnum):
    PENDING = 0
    COMPLETED = 1



class TenantModel(BaseModel):
    __tablename__ = "tenants" 
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), default='')
    email = Column(String(161), nullable=False )
    mobile_no = Column(String(15), default="")
    tenant_user = relationship('CustomerModal', back_populates='tenant_details')
    tenant_admin = relationship('AdminUser', back_populates='admin_tenant_details')
    tenant_enquiryes = relationship('EnquiryModel', back_populates='enquiry_tenant_details')
    tenant_config = relationship('ServiceConfigurationModel', back_populates='conf_tenant_details')

   
    class Config:
        from_attributes = True
        str_strip_whitespace = True
   
class NotificationModel(BaseModel):
    __tablename__ = "user_notificatuions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("customers.id"), index=True)
    tenant_id = Column(Integer, default=None)
    category = Column(String(50), default = None)
    status_category= Column(String(50), default = None)
    ref_id = Column(Integer,default=None)
    application_details = relationship('CustomerModal', back_populates='user_notifications',foreign_keys=[user_id] )
    
    class Config:
        from_attributes = True
        str_strip_whitespace = True
class AdminNotificationModel(BaseModel):
    __tablename__ = "admin_notificatuions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    admin_id = Column(Integer, ForeignKey("admin.id"), unique=False, index=True)
    user_id = Column(Integer,ForeignKey("customers.id"), index=True)
    category = Column(String(50), default = None)
    status_category= Column(String(50), default = None)
    ref_id = Column(Integer,default=None)
    application_details = relationship('CustomerModal',  back_populates='admin_notificatuions',foreign_keys=[user_id])
    

    
    class Config:
        from_attributes = True
        str_strip_whitespace = True
   
   

class CustomerModal(BaseModel):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tfs_id =  Column(String(30), unique=True, index=True)
    referer_id = Column(Integer,default=None)
    first_name = Column(String(50))
    last_name = Column(String(50))
    name = Column(String(150), default='')
    gender = Column(String(150), default='')
    password = Column(Text)
    token = Column(Text, default="")
    email = Column(String(161), nullable=False )
    mobile_no = Column(String(15), default=None)
    alternate_mobile_no = Column(String(15), default=None)
    date_of_birth = Column(Date, nullable=True, default=None)
    last_login = Column(DateTime, default= datetime.now(timezone.utc) )
    pan_card_number = Column(String(55), default=None)
    aadhaar_card_number = Column(String(55), default=None)
    nominee = Column(String(100), default="")
    relation_with_nominee = Column(String(200), default=None)    
    aadhaar_card = Column(Text(), default=None)
    canceled_cheque = Column(Text(), default=None)
    selfie = Column(Text(), default=None)    
    reference_id = Column(String(100), default=None)

    agent_id = Column(Integer, nullable=True, default=None )
    salesman_id = Column(Integer, nullable=True, default=None )

    login_count =  Column(Integer, default=0,comment='User Login count')
    login_fail_count =  Column(Integer, default=0,comment='User Login Fail count')
    login_attempt_date = Column(DateTime, default= None,comment='Last Login Attempt date' )
    otp=Column(String(61))
    #tenant_id = Column(Integer, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), default=None, unique=False, index=True)
    tenant_details = relationship('TenantModel', back_populates='tenant_user')

    role_id = Column(Integer, ForeignKey('md_user_roles.id'), nullable=False,default=1)  # Ensure this matches UserRole.id
    role_details = relationship('MdUserRole', back_populates='user')
    status_id = Column(Integer, ForeignKey('md_user_status.id'),  nullable=False,default=1)
    status_details = relationship('MdUserStatus', back_populates='user_status')
    
    #country_id = Column(Integer, ForeignKey("md_countries.id"), nullable=False, default=None )
    #country_details = relationship("MdCountries", back_populates="user_country")
    #state_id = Column(Integer, ForeignKey("md_states.id"), nullable=True, default=None )
    #location_id = Column(Integer, ForeignKey("md_locations.id"), nullable=True, index=True )

    
    user_notifications = relationship('NotificationModel', back_populates='application_details',foreign_keys='NotificationModel.user_id' )
    admin_notificatuions = relationship('AdminNotificationModel',  back_populates='application_details', foreign_keys='AdminNotificationModel.user_id')
    service_type_id = Column(Integer, ForeignKey("md_service_types.id"), nullable=True, default=None )
    service_details = relationship("MdServiceTypes", back_populates="user_service")

    loan_applications_list = relationship("LoanapplicationModel", back_populates="customer_details")
    customer_all_details = relationship("CustomerDetailsModel", back_populates="customer_basic_details")
    created_by = Column(Integer, ForeignKey("admin.id"), nullable=True, default=None )
    created_by_details = relationship("AdminUser", back_populates="my_users")
    accepted_terms = Column(Boolean, default=False)

    #md_subscription_plans MdSubscriptionPlansModel
    current_plan_id = Column(Integer, ForeignKey("md_subscription_plans.id"), nullable=True, default=None )
    current_plan_details = relationship("MdSubscriptionPlansModel", back_populates="subscription_plan_customers")
    subscription = relationship('SubscriptionModel', back_populates='customer')
    class Config:
        from_attributes = True
        str_strip_whitespace = True

class CustomerDetailsModel(BaseModel):
    __tablename__ = "customer_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), default=None, unique=True, index=True)
    customer_basic_details = relationship("CustomerModal", back_populates="customer_all_details")
    tenant_id= Column(Integer, default=None,)
    service_type_id = Column(Integer, ForeignKey("md_service_types.id"), nullable=True, default=None )
    customer_service_detail = relationship("MdServiceTypes", back_populates="service_customers_list")

    
    loanAmount = Column(String(50), nullable=True, default="0")
    lead_sourse_id = Column(Integer, ForeignKey("md_lead_sources.id"),nullable=True, default=None, unique=False, index=True)
    leadsourse_details = relationship("MdLeadSources", back_populates="customer_leads")
    
    profession_type_id = Column(Integer, ForeignKey("md_profession_types.id"),nullable=True, default=None, unique=False)
    customer_profession_details = relationship("MdProfessionTypes", back_populates="customers_profession")
    
    
    profession_sub_type_id = Column(Integer, ForeignKey("md_profession_sub_types.id"),nullable=True, default=None, unique=False)
    customer_profession_sub_type_details = relationship("MdProfessionSubTypes", back_populates="customer_profession_sub_type")
    sepType = Column(String(20), default=None,nullable=True)
    #Salaried column fields
    companyName = Column(String(55), default='',nullable=True)
    designation = Column(String(55), default='' ,nullable=True)
    totalExperience = Column(Numeric(10, 2), default=None, comment="Total work experience in years (e.g., 1.5 for one and a half years)")
    present_organization_years =  Column(Numeric(10, 2), default=None ,nullable=True)
    workLocation = Column(String(55), default='',nullable=True)
    grossSalary = Column(Numeric(10, 2), default=None, comment="gross salary" ,nullable=True)
    netSalary = Column(Numeric(10, 2), default=None, comment="net salary" ,nullable=True)
    otherIncome = Column(String(6), default="No", comment="net salary" ,nullable=True)
    Obligations = Column(String(6), default="No", comment="Obligations" ,nullable=True)
    other_income_list = Column(Text, default=None, nullable=True,  comment="JSON stringified list of income sources, e.g., [{'income_type':'job','income':20},{'income_type':'rental','income':10}]")
    obligations_per_month = Column(Numeric(10, 2), default=None ,nullable=True)

    #SENP Columns fields
    #company_name = Column(String(55), default='') #already exists
    #designation = Column(String(55), default='') #already exists
    number_of_years = Column(Numeric(10, 2), default=None, nullable=True)
    location = Column(String(55), default='', nullable=True)
    last_turnover_year = Column(String(55), default='')
    last_year_turnover_amount = Column(Numeric(10, 2), default=None, nullable=True)
    last_year_itr =  Column(String(55), default=None, nullable=True)
    lastYearITRamount =Column(Numeric(10, 2), default=None, nullable=True)
    current_turnover_year = Column(String(55), default='')
    current_year_turnover_amount = Column(Numeric(10, 2), default=None, nullable=True)
    current_year_itr =  Column(String(55), default=None, nullable=True)
    presentYearITRamount = Column(Numeric(10, 2), default=None, nullable=True)
    #already exists above
    #other_income = Column(Text, default=None, comment="JSON stringified list of income sources, e.g., [{'income_type':'job','income':20},{'income_type':'rental','income':10}]")
    avg_income_per_month =  Column(Numeric(10, 2), default=None, nullable=True)
    #Obligations = Column(String(6), default="No", comment="Obligations")
    other_obligation = Column(Text, default='', comment="Optional details of other financial obligations as a JSON stringified list of dictionaries.")

    #SEP Column fields
    income_type_id = Column(Integer, ForeignKey("md_income_types.id"), default=None, unique=False)
    customer_income_type_details = relationship("mdIncomeTypes", back_populates="customer_income_type")
    
    all_obligations = Column(Text, default=None)
    total_obligation_amount_per_month = Column(Numeric(10, 2), default=None, nullable=True)
    coapplicant_data = Column(Text, default=None, comment="Json Stringify data")

    agent_id = Column(Integer, default=None, nullable=True)
    salesman_id = Column(Integer, default=None, nullable=True)
    admin_id = Column(Integer, default=None, nullable=True)
    loan_approved_by = Column(Integer, default=None, nullable=True)

    eligible = Column(String(5), nullable=True, default="No" )
    loan_eligible_type =Column(Integer, nullable=True, default=None )
    loan_eligible_amount =  Column(Numeric(10, 2), default=None ,nullable=True)
    fdir = Column(Text, nullable=True, default=None )
    description = Column(Text, default=None, comment="description")


    updated_by = Column(Integer, ForeignKey("admin.id"), nullable=True, default=None )
    updated_by_details = relationship("AdminUser", back_populates="my_customers")
    
    


class SubscriptionModel(BaseModel):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'),unique=False)
    plan_id = Column(Integer, ForeignKey('md_subscription_plans.id'))
    start_date = Column(DateTime, nullable=True, default=datetime.now(timezone.utc))
    end_date = Column(DateTime,nullable=True,)
    payment_status = Column(String(100), default="Pending")  # Payment status (Pending, Success, Failed)
    payment_amount = Column(Numeric(10, 2), default=None ,nullable=True)
    invoice_id = Column(String(100), index=True,default=None)
    razorpay_order_id = Column(String(100), index=True,default=None)  # Razorpay order ID
    razorpay_payment_id = Column(String(100), index=True,default=None)  # Razorpay payment ID
    status = Column(Boolean, default=False, comment="Is status ==True plan is active, if False == plan inactive")
    payment_link = Column(Text(), index=True,default=None) 
    customer = relationship('CustomerModal', back_populates='subscription')
    plan = relationship('MdSubscriptionPlansModel', back_populates='subscriptions')
    tenant_id = Column(Integer, default=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate payment amount when initializing a new subscription
        if self.payment_amount <= 0:
            raise ValueError('Payment amount must be positive')
        
class LoanapplicationModel(BaseModel):
    __tablename__ = "application_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tfs_id = Column(String(20), default=None,nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), default=None, unique=False, index=True)
    customer_details = relationship("CustomerModal", back_populates="loan_applications_list")
    tenant_id= Column(Integer, default=None,)
    service_type_id = Column(Integer, ForeignKey("md_service_types.id"), nullable=True, default=None )
    detail_of_service = relationship("MdServiceTypes", back_populates="service_lonas_list")

    application_form_id = Column(String(20), default=None,nullable=True,)
    loanAmount = Column(String(50), nullable=True, default="0")
    lead_sourse_id = Column(Integer, ForeignKey("md_lead_sources.id"),nullable=True, default=None, unique=False, index=True)
    lead_sourse_details = relationship("MdLeadSources", back_populates="lead_customer")
    profession_type_id = Column(Integer, ForeignKey("md_profession_types.id"),nullable=True, default=None, unique=False)
    profession_details = relationship("MdProfessionTypes", back_populates="lead_profession")
    
    profession_sub_type_id = Column(Integer, ForeignKey("md_profession_sub_types.id"),nullable=True, default=None, unique=False)
    profession_sub_type_details = relationship("MdProfessionSubTypes", back_populates="lead_profession_sub_type")
    sepType = Column(String(20), default=None,nullable=True,)
    #Salaried column fields Column(Numeric(10, 2), default=None ,nullable=True)
    companyName = Column(String(55), default='',nullable=True)
    designation = Column(String(55), default='' ,nullable=True)
    totalExperience = Column(Numeric(10, 2), default=None, comment="Total work experience in years (e.g., 1.5 for one and a half years)")
    present_organization_years =  Column(Numeric(10, 2), default=None ,nullable=True)
    workLocation = Column(String(55), default='',nullable=True)
    grossSalary = Column(Numeric(10, 2), default=None ,nullable=True)
    netSalary = Column(Numeric(10, 2), default=None ,nullable=True)
    otherIncome = Column(String(6), default="No", comment="net salary" ,nullable=True)
    Obligations = Column(String(6), default="No", comment="Obligations" ,nullable=True)
    other_income_list = Column(Text, default=None, nullable=True,  comment="JSON stringified list of income sources, e.g., [{'income_type':'job','income':20},{'income_type':'rental','income':10}]")
    obligations_per_month = Column(Numeric(10, 2), default=None ,nullable=True)

    #SENP Columns fields
    #company_name = Column(String(55), default='') #already exists
    #designation = Column(String(55), default='') #already exists
    number_of_years = Column(Numeric(10, 2), default=None ,nullable=True)
    location = Column(String(55), default=None)
    last_turnover_year = Column(String(55), default=None)
    last_year_turnover_amount =Column(Numeric(10, 2), default=None ,nullable=True)
    last_year_itr =  Column(String(55), default=None, nullable=True)
    lastYearITRamount = Column(Numeric(10, 2), default=None ,nullable=True)
    current_turnover_year = Column(String(55), default=None, nullable=True)
    current_year_turnover_amount = Column(Numeric(10, 2), default=None ,nullable=True)
    current_year_itr =  Column(String(55), default=None, nullable=True)
    presentYearITRamount = Column(Numeric(10, 2), default=None ,nullable=True)
    #already exists above
    #other_income = Column(Text, default=None, comment="JSON stringified list of income sources, e.g., [{'income_type':'job','income':20},{'income_type':'rental','income':10}]")
    avg_income_per_month =  Column(Numeric(10, 2), default=None ,nullable=True)
    #Obligations = Column(String(6), default="No", comment="Obligations")
    other_obligation = Column(Text, default='', comment="Optional details of other financial obligations as a JSON stringified list of dictionaries.")

    #SEP Column fields
    income_type_id = Column(Integer, ForeignKey("md_income_types.id"), default=None, unique=False)
    income_type_details = relationship("mdIncomeTypes", back_populates="lead_income_type")
    all_obligations = Column(Text, default=None)
    total_obligation_amount_per_month = Column(Numeric(10, 2), default=None ,nullable=True)
    coapplicant_data = Column(Text, default=None, comment="Json Stringify data")

    agent_id = Column(Integer, nullable=True, default=None )
    salesman_id = Column(Integer, nullable=True, default=None )
    admin_id = Column(Integer, nullable=True, default=None )
    loan_approved_by = Column(Integer, nullable=True, default=None )

    eligible = Column(String(5), nullable=True, default="No" )
    loan_eligible_type =Column(Integer, nullable=True, default=None )
    loan_eligible_amount =  Column(Numeric(10, 2), default=None ,nullable=True)
    fdir = Column(Text, nullable=True, default=None )
    description = Column(Text, default=None, comment="description")


    created_by = Column(Integer, ForeignKey("admin.id"), nullable=True, default=None )
    created_by_details = relationship("AdminUser", back_populates="my_applications")
    
    status_id = Column(Integer, ForeignKey("md_loan_application_status.id"), nullable=True, default=1 )
    status_details = relationship("MdLoanApplicationStatus", back_populates="all_applications")


class EnquiryModel(BaseModel):
    __tablename__ = "enquiries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tfs_id = Column(String(150), default='')
    name = Column(String(150), default='')
    email = Column(String(161), nullable=False )
    mobile_no = Column(String(15), default="")
    description = Column(Text, default="")
    tenant_id = Column(Integer,ForeignKey("tenants.id"), nullable=False, default=None )
    enquiry_tenant_details = relationship('TenantModel', back_populates='tenant_enquiryes')
    
    
    service_type_id = Column(Integer, ForeignKey("md_service_types.id"), nullable=True, default=None )
    enquir_service_details = relationship("MdServiceTypes", back_populates="enquiry_service")
    
    status_id = Column(Integer, ForeignKey("md_enquiry_status.id"), nullable=False, default=1 )
    enquir_status_details = relationship("MdEnquiryStatusModel", back_populates="enquiryes")
    description = Column(Text,default="")
    followupdate = Column(DateTime, default=None)
    


