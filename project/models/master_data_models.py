from sqlalchemy import Column, Integer,INT, String, Text, DateTime, ForeignKey,Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
#Base = declarative_base()
from  .base_model import BaseModel
class MdUserRole(BaseModel):
    __tablename__ = "md_user_roles"
    id = Column(Integer, primary_key=True, autoincrement=True)  # Ensure this is the primary key
    name = Column(Text, index=True)
    user = relationship('CustomerModal', back_populates='role_details')
    admin_user = relationship('AdminUser', back_populates='role_details')

    class Config:
        from_attributes = True
        str_strip_whitespace = True

class MdUserStatus(BaseModel):
    
    __tablename__ = "md_user_status"
    id = Column(Integer, primary_key=True, autoincrement=True)  # Ensure this is the primary key
    name = Column(Text )
    user_status = relationship('CustomerModal', back_populates='status_details')
    admin_user_status = relationship('AdminUser', back_populates='status_details')

class MdCountries(BaseModel):
    __tablename__ = "md_countries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    shortName = Column(String(100), default='')
    name = Column(String(100), default='' )
    phoneCode = Column(Integer, default=None)
    order = Column(Integer, default=None)
    currencySymbol = Column(String(100), default='' )
    currencyCode = Column(String(100), default='' )
    zipcodeLength = Column(Integer, default=10)
    allowNumAndCharInZipcode = Column(String(100), default='' )
    mapName = Column(String(100), default="")
    currency_name = Column(String(100), default='' )
    #flag = Column(String(100), default='' )

    #user_country = relationship("CustomerModal", back_populates="country_details")
    country_users = relationship('AdminUser', back_populates='country_details')

    

#md_states.json
class MdStates(BaseModel):
    __tablename__ = "md_states"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name =   Column(String(100),default='' )
    mapName=  Column(String(100),default='' )
    countryId = Column(Integer, default=None)
    state_users = relationship('AdminUser', back_populates='state_details')

class MdLocations(BaseModel):
    __tablename__ = "md_locations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name =   Column(String(100),default='' )
    stateId=  Column(Integer,default=None)
    countryId = Column(Integer, default=None)
    location_users = relationship('AdminUser', back_populates='location_details')


#md_reminder_status
class MdReminderStatus(BaseModel):
    
    __tablename__ = "md_reminder_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    


#md_task_status.json
class MdTaskStatus(BaseModel):
    __tablename__ = "md_task_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    

#md_tenant_status
class MdTenantStatus(BaseModel):
    __tablename__ = "md_tenant_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    

#md_timezone.json
class MdTimeZone(BaseModel):
    __tablename__ = "md_timezones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    zone =  Column(String(55) )
    name = Column(String(55) )

class MdServiceTypes(BaseModel):
    __tablename__ = "md_service_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), default='')
    status = Column(Boolean, default=True)
    description = Column(Text, default='')
    user_service = relationship("CustomerModal", back_populates="service_details")
    service_lonas_list = relationship("LoanapplicationModel", back_populates="detail_of_service")
    enquiry_service = relationship("EnquiryModel", back_populates="enquir_service_details")
    service_configuration = relationship('ServiceConfigurationModel', back_populates='service_details')
    
    
    class Config:
        from_attributes = True
        str_strip_whitespace = True

#md_lead_sources
class MdLeadSources(BaseModel):
    
    __tablename__ = "md_lead_sources"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    lead_customer = relationship("LoanapplicationModel", back_populates="lead_sourse_details")
    

#md_profession_types
class MdProfessionTypes(BaseModel):

    __tablename__ = "md_profession_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    lead_profession = relationship("LoanapplicationModel", back_populates="profession_details")

class MdProfessionSubTypes(BaseModel):
    __tablename__ = "md_profession_sub_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    profession_type_id = Column(Integer, default=None)
    lead_profession_sub_type = relationship("LoanapplicationModel", back_populates="profession_sub_type_details")

class mdIncomeTypes(BaseModel):
    #md_income_types.json ,mdIncomeTypes
    __tablename__ = "md_income_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    lead_income_type = relationship("LoanapplicationModel", back_populates="income_type_details")
class MdOtherIncomeTypes(BaseModel):
    #md_other_income_types.json,MdOtherIncomeTypes
    __tablename__ = "md_other_income_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )

#md_obligation_types.json
class MdObligationTypes(BaseModel):
    #md_obligation_types.json MdObligationTypes
    __tablename__ = "md_obligation_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )

class MdLoanApplicationStatus(BaseModel):
    #md_loan_application_status.json MdLoanApplicationStatus
    __tablename__ = "md_loan_application_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(55) )
    all_applications = relationship("LoanapplicationModel", back_populates="status_details")
    

class MdSubscriptionPlansModel(BaseModel):
    #md_subscription_plans
    __tablename__ = "md_subscription_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), default='')
    status = Column(Boolean, default=True)
    description = Column(Text, default='')
    subscription_plan_customers = relationship("CustomerModal", back_populates="subscription_plan_details")
    
    class Config:
        from_attributes = True
        str_strip_whitespace = True

#service_configuration
class ServiceConfigurationModel(BaseModel):
    #md_subscription_plans
    __tablename__ = "service_configurations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_type_id = Column(Integer, ForeignKey('md_service_types.id'), nullable=True,default=None)
    service_details = relationship('MdServiceTypes', back_populates='service_configuration')
    user_id = Column(Integer, ForeignKey('admin.id'), nullable=True,default=None)
    user_details = relationship('AdminUser', back_populates='user_configuration')
    tenant_id = Column(Integer, ForeignKey("tenants.id"), default=1, unique=False, index=True)
    conf_tenant_details = relationship('TenantModel', back_populates='tenant_config')
    
    
    class Config:
        from_attributes = True
        str_strip_whitespace = True

class MdEnquiryStatusModel(BaseModel):
    __tablename__ = "md_enquiry_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), default='')
    enquiryes = relationship("EnquiryModel", back_populates="enquir_status_details")
    
    
    class Config:
        from_attributes = True
        str_strip_whitespace = True

"""
"CITY1": "MUMBAI",
        "CITY2": "GREATER MUMBAI",
        "STATE": "MAHARASHTRA",
        "STD CODE": "0.0",
        "PHONE": "9653261383.0"

Keyword arguments:
argument -- description
Return: return_description
"""

class MdIfscCodes(BaseModel):
     __tablename__ = "md_ifsc_codes"
     id = Column(Integer, primary_key=True, autoincrement=True)
     BANK = Column(String(50), default='',index=True)
     IFSC = Column(String(50), default='' ,index=True)
     BRANCH = Column(String(50), default='',index=True)
     ADDRESS = Column(Text, default='')
     CITY1 = Column(String(100), default='',index=True)
     CITY2 = Column(String(100), default='',index=True)
     STATE = Column(String(100), default='',index=True)
     STD_CODE = Column(String(100), default='')
     PHONE = Column(String(100), default='')
     
     class Config:
        from_attributes = True
        str_strip_whitespace = True



