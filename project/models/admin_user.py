from sqlalchemy import Column,LargeBinary, Integer,Float, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
#from project.database.database import Base
from datetime import datetime,timezone
#Base = declarative_base()
from .base_model import BaseModel

class AdminUser(BaseModel):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, autoincrement=True)
    details = relationship("AdminUserModel", back_populates="admin_user_details")
    tfs_id =  Column(String(150), unique=True,index=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    name = Column(String(150), default=None)
    password = Column(Text, default=None)
    login_token = Column(Text)
    token = Column(Text)
    otp=Column(String(61))
    email = Column(String(161))
    mobile_no = Column(String(15))
    alternate_mobile_no = Column(String(15),default=None)
    gender = Column(String(15),default=None)
    

    passport = Column(Text, default="")
    aadhaar_card  = Column(Text, default="")
    selfie = Column(Text, default="")

    country_id = Column(Integer, ForeignKey('md_countries.id'), nullable=True,default=None)
    country_details = relationship('MdCountries', back_populates='country_users')
    
    
    state_id = Column(Integer, ForeignKey('md_states.id'), nullable=True,default=None)
    state_details = relationship('MdStates', back_populates='state_users')
    

    location_id = Column(Integer, ForeignKey('md_locations.id'), nullable=True,default=None)
    location_details = relationship('MdLocations', back_populates='location_users')
    
    pincode = Column(Text,default=None)
    present_address = Column(Text,default=None)
    present_occupation = Column(Text,default=None)
    employer_name = Column(Text,default=None)
    qualification = Column(Text,default=None)

    
    account_holder_name = Column(Text,default=None)
    bank_name = Column(Text,default=None)
    bank_account_number = Column(Text,default=None)
    ifsc_code = Column(Text,default=None)
    upload_check = Column(Text, default="")
    referrals = Column(Text,default=None)


    last_login = Column(DateTime, default= datetime.now(timezone.utc))
    login_count =  Column(Integer, default=0,comment='User Login count') 
    login_fail_count =  Column(Integer, default=0,comment='User Login Fail count')
    login_attempt_date = Column(DateTime, default= None,comment='Last Login Attempt date' )
    date_of_birth = Column(Date, nullable=True, default=None)
    experience = Column(Float, default=None)
    profile_image = Column(String(50))
    role_id = Column(Integer, ForeignKey('md_user_roles.id'), nullable=False,default=1)  # Ensure this matches UserRole.id
    role_details = relationship('MdUserRole', back_populates='admin_user')
    status_id = Column(Integer, ForeignKey('md_user_status.id'),  nullable=False,default=1)
    status_details = relationship('MdUserStatus', back_populates='admin_user_status')
    

    created_by = Column(Integer, default=None)
    created_by_role = Column(Integer, default=None)
    
    tenant_id = Column(Integer, ForeignKey("tenants.id"), default=None, unique=False, index=True)
    admin_tenant_details = relationship('TenantModel', back_populates='tenant_admin')

    my_users = relationship("CustomerModal", back_populates="created_by_details")
    my_applications = relationship("LoanapplicationModel", back_populates="created_by_details")
    user_configuration = relationship('ServiceConfigurationModel', back_populates='user_details')
    my_customers = relationship("CustomerDetailsModel", back_populates="updated_by_details")
    my_comments_ticket = relationship("TicketCommentsModel", back_populates="admin_details")  
    my_tickets = relationship("TicketsModel", back_populates="created_by_admin_details")


    class Config:
        from_attributes = True
        str_strip_whitespace = True

class AdminUserModel(BaseModel):
    __tablename__ = "admin_user_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(Integer, ForeignKey("admin.id"), nullable=True, default=None )
    admin_user_details = relationship("AdminUser", back_populates="details")
    pancard_or_passport = Column(String(50))
    aadhaar_card = Column(String(50))
    
    present_address = Column(Text)
    present_occupation = Column(String(60))
    employer_name =  Column(String(60))
    qualification = Column(String(60))

    #Bank Details
    account_holder_name = Column(String(60))
    bank_name = Column(String(60))
    bank_account_number = Column(String(60))
    ifsc_code = Column(String(60))
    empty_check = Column(String(60))

    #Referral Details
    referral_name_one = Column(String(60))
    referral_mobile_number_one = Column(String(15))
    referral_address_one = Column(Text)

    referral_name_two = Column(String(60))
    referral_mobile_number_two = Column(String(15))
    referral_address_two = Column(Text)

