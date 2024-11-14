from sqlalchemy import Column, Integer,Float,INT, String, Text, DateTime, ForeignKey,Enum,Date,Boolean
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
    password = Column(Text)
    token = Column(Text, default="")
    email = Column(String(161), nullable=False )
    mobile_no = Column(String(15), default="")
    alternate_mobile_no = Column(String(15), default="")
    date_of_birth = Column(Date, nullable=True, default="")
    last_login = Column(DateTime, default= datetime.now(timezone.utc) )

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
    service_type_id = Column(Integer, ForeignKey("md_service_types.id"), nullable=False, default=None )
    service_details = relationship("MdServiceTypes", back_populates="user_service")

    loan_applications_list = relationship("LoanapplicationModel", back_populates="subscriber")
    created_by = Column(Integer, ForeignKey("admin.id"), nullable=True, default=None )
    created_by_details = relationship("AdminUser", back_populates="my_users")
    accepted_terms = Column(Boolean, default=False)

    #md_subscription_plans MdSubscriptionPlansModel
    md_subscription_plan_id = Column(Integer, ForeignKey("md_subscription_plans.id"), nullable=True, default=None )
    subscription_plan_details = relationship("MdSubscriptionPlansModel", back_populates="subscription_plan_customers")
    subscription_history = Column(Text, default=None, comment="History of subscription")
    
    class Config:
        from_attributes = True
        str_strip_whitespace = True

class LoanapplicationModel(BaseModel):
    __tablename__ = "application_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subscriber_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), default=None, unique=False, index=True)
    subscriber = relationship("CustomerModal", back_populates="loan_applications_list")
    tenant_id= Column(Integer, default=None,)
    service_type_id = Column(Integer, ForeignKey("md_service_types.id"), nullable=True, default=None )
    detail_of_service = relationship("MdServiceTypes", back_populates="service_lonas_list")

    application_form_id = Column(String(20), default=None)
    loanAmount = Column(Float, primary_key=True)
    lead_sourse_id = Column(Integer, ForeignKey("md_lead_sources.id"), default=None, unique=False, index=True)
    lead_sourse_details = relationship("MdLeadSources", back_populates="lead_subscriber")
    profession_type_id = Column(Integer, ForeignKey("md_profession_types.id"), default=None, unique=False)
    profession_details = relationship("MdProfessionTypes", back_populates="lead_profession")
    
    profession_sub_type_id = Column(Integer, ForeignKey("md_profession_sub_types.id"), default=None, unique=False)
    profession_sub_type_details = relationship("MdProfessionSubTypes", back_populates="lead_profession_sub_type")
    
    #Salaried column fields
    companyName = Column(String(55), default='')
    designation = Column(String(55), default='')
    totalExperience = Column(Float, default=None, comment="Total work experience in years (e.g., 1.5 for one and a half years)")
    present_organization_years =  Column(Integer, default=None)
    workLocation = Column(String(55), default='')
    grossSalary = Column(Float, default=None, comment="gross salary")
    netSalary = Column(Float, default=None, comment="net salary")
    otherIncome = Column(String(6), default="No", comment="net salary")
    Obligations = Column(String(6), default="No", comment="Obligations")
    other_income_list = Column(Text, default=None, comment="JSON stringified list of income sources, e.g., [{'income_type':'job','income':20},{'income_type':'rental','income':10}]")
    obligations_per_month = Column(Integer, default=None)

    #SENP Columns fields
    #company_name = Column(String(55), default='') #already exists
    #designation = Column(String(55), default='') #already exists
    number_of_years = Column(Float, default='')
    location = Column(String(55), default='')
    last_turnover_year = Column(String(55), default='')
    last_year_turnover_amount = Column(Float, default=None)
    last_year_itr =  Column(Float, default=None)
    current_turnover_year = Column(String(55), default='')
    current_year_turnover_amount = Column(Float, default=None)
    current_year_itr =  Column(Float, default=None)
    #already exists above
    #other_income = Column(Text, default=None, comment="JSON stringified list of income sources, e.g., [{'income_type':'job','income':20},{'income_type':'rental','income':10}]")
    avg_income_per_month =  Column(Float, default=None)
    #Obligations = Column(String(6), default="No", comment="Obligations")
    other_obligation = Column(Text, default='', comment="Optional details of other financial obligations as a JSON stringified list of dictionaries.")

    #SEP Column fields
    income_type_id = Column(Integer, ForeignKey("md_income_types.id"), default=None, unique=False)
    income_type_details = relationship("mdIncomeTypes", back_populates="lead_income_type")
    all_obligations = Column(Text, default=None)
    total_obligation_amount_per_month = Column(Float, default=None)
    coapplicant_data = Column(Text, default=None, comment="Json Stringify data")

    agent_id = Column(Integer, nullable=True, default=None )
    salesman_id = Column(Integer, nullable=True, default=None )
    admin_id = Column(Integer, nullable=True, default=None )
    loan_approved_by = Column(Integer, nullable=True, default=None )

    created_by = Column(Integer, ForeignKey("admin.id"), nullable=True, default=None )
    created_by_details = relationship("AdminUser", back_populates="my_applications")
    
    status_id = Column(Integer, ForeignKey("md_loan_application_status.id"), nullable=True, default=1 )
    status_details = relationship("MdLoanApplicationStatus", back_populates="all_applications")




