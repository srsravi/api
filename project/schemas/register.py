from pydantic import BaseModel, EmailStr, Field, ValidationError, validator,field_validator
from typing import Optional
import phonenumbers
from phonenumbers import NumberParseException, is_valid_number
import re
from datetime import date, datetime



class EnquiryRequestOtpSchema(BaseModel):
    name:str
    email: EmailStr = Field(..., description="The email address of the user.")
    mobile_no: str = Field(..., description="The mobile phone number of the user, including the country code.")
    tenant_id:Optional[int] =1
    description:Optional[str]
    service_type_id:Optional[int] =None

    @field_validator('name', mode='before')
    def validate_name(cls, v, info):
        v = v.strip()
        if not re.match(r'^[A-Za-z ]+$', v):
            raise ValueError('Name must only contain alphabetic characters and cannot include numbers, special characters, or spaces.')
        return v
    @validator('email', always=True)
    def check_email(cls, v):
        if v is None:
            raise ValueError('User email address is required and cannot be None.')
        return v
    @field_validator('mobile_no', mode='before')
    def validate_mobile_no(cls, v, info):
        try:
            if v:
                phone_number = phonenumbers.parse(v)
                if not is_valid_number(phone_number):
                    raise ValueError('Invalid phone number.')
        except NumberParseException:
            raise ValueError('Invalid phone number format.')
        return v

class EnquiryRequestSchema(EnquiryRequestOtpSchema):
    otp:str
    
class EnquiryBecomeCustomer(BaseModel):
    enquiry_id:int
    tenant_id: Optional[int] =1
    service_type_id:Optional[int] = None
    status_id:int
    followupdate:Optional[date] = None
    description:str

    #{"enquiry_id":1,
    # "tenant_id":1,
    # "status_id":2,
    # "service_type_id":1,
    # "followupdate":"2024-12-05",
    # "description":"msh jkhfsfsdhfsf s sd f sd"}
    


class createCustomerSchema(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user.")
    first_name: str
    last_name: str
    reference_id: Optional[str]=''
    service_type_id: int
    tenant_id:Optional[int] =1
    mobile_no: str = Field(..., description="The mobile phone number of the user, including the country code.")
    @validator('email', always=True)
    def check_email(cls, v):
        if v is None:
            raise ValueError('User email address is required and cannot be None.')
        return v
    
    @field_validator('first_name', mode='before')
    def validate_first_name(cls, v, info):
        v = v.strip()
        if not re.match(r'^[A-Za-z]+$', v):
            raise ValueError('First name must only contain alphabetic characters and cannot include numbers, special characters, or spaces.')
        return v
    
    @field_validator('last_name', mode='before')
    def validate_last_name(cls, v, info):
        v = v.strip()
        if not re.match(r'^[A-Za-z]+$', v):
            raise ValueError('Last name must only contain alphabetic characters and cannot include numbers, special characters, or spaces.')
        return v

    @field_validator('mobile_no', mode='before')
    def validate_mobile_no(cls, v, info):
        try:
            phone_number = phonenumbers.parse(v)
            if not is_valid_number(phone_number):
                raise ValueError('Invalid phone number.')
        except NumberParseException:
            raise ValueError('Invalid phone number format.')
        return v

class Register(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user.")
    mobile_no: str = Field(..., description="The mobile phone number of the user, including the country code.")
    country_id: int = Field(..., description="The country id.")

    @field_validator('mobile_no', mode='before')
    def validate_mobile_no(cls, v, info):
        try:
            phone_number = phonenumbers.parse(v)
            if not is_valid_number(phone_number):
                raise ValueError('Invalid phone number.')
        except NumberParseException:
            raise ValueError('Invalid phone number format.')
        return v
        


class CompleteSignup(BaseModel):
    
    user_id: int
    first_name: str
    last_name: str
    country_id: int = Field(..., description="The country id.")
    date_of_birth: date = Field(..., description="Must be at least 18 years old.And format should be YYYY-MM-DD")
    mobile_no: str = Field(..., description="The mobile phone number of the user, including the country code.")
    password: str
    confirm_password: str
    accepted_terms: bool
    

    @field_validator('user_id', mode='before')
    def check_user_id(cls, v, info):
        if v is None or v<=0:
            raise ValueError('User ID is required and cannot be None.')
        return v
    
    @field_validator('password', 'confirm_password', mode='before')
    def passwords_match(cls, v, info):
        v = v.strip()
        password_pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[\W_]).{8,16}$')   
        if not bool(password_pattern.match(v)):
            raise ValueError('Password must be 8-16 characters long and include at least one uppercase letter, one lowercase letter, and one special character.')

        elif len(str(v)) < 8 or len(str(v)) > 16:
            raise ValueError('Password must be 8-16 characters.')
        
        # Access other values from info.
        if info.field_name == 'confirm_password':
            password = info.data.get('password')
            if v != password:
                raise ValueError('Password and Confirm Password do not match.')
        return v

    @field_validator('date_of_birth', mode='before')
    def validate_date_of_birth(cls, v, info):
        # Ensure v is a date object
        if isinstance(v, str):
            v = date.fromisoformat(v)  # Convert from string to date if needed
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('You must be at least 18 years old. And format should be YYYY-MM-DD')
        return v

    
    @field_validator('first_name', mode='before')
    def validate_first_name(cls, v, info):
        v = v.strip()
        if not re.match(r'^[A-Za-z]+$', v):
            raise ValueError('First name must only contain alphabetic characters and cannot include numbers, special characters, or spaces.')
        return v
    
    @field_validator('last_name', mode='before')
    def validate_last_name(cls, v, info):
        v = v.strip()
        if not re.match(r'^[A-Za-z]+$', v):
            raise ValueError('Last name must only contain alphabetic characters and cannot include numbers, special characters, or spaces.')
        return v

    @field_validator('mobile_no', mode='before')
    def validate_mobile_no(cls, v, info):
        try:
            phone_number = phonenumbers.parse(v)
            if not is_valid_number(phone_number):
                raise ValueError('Invalid phone number.')
        except NumberParseException:
            raise ValueError('Invalid phone number format.')
        return v
    
    @field_validator('accepted_terms', mode='before')
    def validate_accepted_terms(cls, v, info):
        if not v:
            raise ValueError('You must accept the terms and conditions.')
        return v

    class Config:
        pass
        # json_schema_extra = {
        #     "example": {
        #         "user_id": 1,
        #         "first_name": "John",
        #         "last_name": "Doe",
        #         "country_id": 100,
        #         "mobile_no": "+1234567890",
        #         "password": "strongpassword",
        #         "confirm_password": "strongpassword",
        #         "accepted_terms": True,
                
        #     }
        # }



class VerifyAccount(BaseModel):
    
    user_id: int
    otp: int

    @field_validator('user_id', mode='before')
    def check_user_id(cls, v, info):
        if v is None or v<=0:
            raise ValueError('User ID is required and cannot be None.')
        return v

    
    @field_validator('otp', mode='before')
    def validate_otp(cls, v, info):
        if v is None:
            raise ValueError('OTP is required and cannot be None.')
        # Ensure OTP is a 6-digit number (adjust if needed)
        v = int(v)
        if not (100000 <= v <= 999999):
            raise ValueError('OTP must be a 6-digit number.')
        return v    
    

class ForgotPasswordLinkSchema(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user.")
    @validator('email', always=True)
    def check_email(cls, v):
        if v is None:
            raise ValueError('User email address is required and cannot be None.')
        return v

class SetPasswordSchema(BaseModel):
    password: str
    confirm_password: str
    token:str
    @field_validator('password', 'confirm_password', mode='before')
    def passwords_match(cls, v, info):
        v = v.strip()
        # Access other values from info.
        if info.field_name == 'confirm_password':
            password = info.data.get('password')
            if v != password:
                raise ValueError('Password and Confirm Password do not match.')
        return v
    @field_validator('token', mode='before')
    def check_token(cls, v,info):
        if v is None:
            raise ValueError('Token is required and cannot be None.')
        return v


class SignupOtp(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user.")
    @validator('email', always=True)
    def check_email(cls, v):
        if v is None:
            raise ValueError('User email address is required and cannot be None.')
        return v



class ForgotPassword(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user.")
    #date_of_birth: date = Field(..., description="Must be at least 18 years old. And format should be YYYY-MM-DD")

    # @field_validator('date_of_birth', mode='before')
    # def validate_date_of_birth(cls, v, info):
    #     # Ensure v is a date object
    #     if isinstance(v, str):
    #         v = date.fromisoformat(v)  # Convert from string to date if needed
    #     today = date.today()
    #     age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
    #     if age < 18:
    #         raise ValueError('You must be at least 18 years old.')
    #     return v

     

    @validator('email', always=True)
    def check_email(cls, v):
        if v is None:
            raise ValueError('User email address is required and cannot be None.')
        return v

class resetPassword(BaseModel):
    #email: EmailStr = Field(..., description="The email address of the user.")
    user_id: int
    password: str
    confirm_password: str
    #otp: int
    token:str

    @field_validator('token', mode='before')
    def check_token(cls, v,info):
        if v is None:
            raise ValueError('Token is required and cannot be None.')
        return v
    
    @field_validator('user_id', mode='before')
    def check_user_id(cls, v, info):
        if v is None or v<=0:
            raise ValueError('User ID is required and cannot be None.')
        return v

    # @field_validator('otp', mode='before')
    # def validate_otp(cls, v, info):
    #     if v is None:
    #         raise ValueError('OTP is required and cannot be None.')
    #     # Ensure OTP is a 6-digit number (adjust if needed)
    #     v = int(v)
    #     if not (100000 <= v <= 999999):
    #         raise ValueError('OTP must be a 6-digit number.')
    #     return v
    
    @field_validator('password', 'confirm_password', mode='before')
    def passwords_match(cls, v, info):
        v = v.strip()
        # Access other values from info.
        if info.field_name == 'confirm_password':
            password = info.data.get('password')
            if v != password:
                raise ValueError('Password and Confirm Password do not match.')
        return v
class UpdateAdminPassword(BaseModel):
    user_id: int
    old_password: str
    password: str
    confirm_password: str
    
    @field_validator('user_id', mode='before')
    def check_user_id(cls, v, info):
        if v is None or v<=0:
            raise ValueError('User ID is required and cannot be None.')
        return v

    @field_validator('password', 'confirm_password', mode='before')
    def passwords_match(cls, v, info):
        v = v.strip()
        # Access other values from info.
        if info.field_name == 'confirm_password':
            password = info.data.get('password')
            if v != password:
                raise ValueError('Password and Confirm Password do not match.')
        return v
class TenantInvitationSchema(BaseModel):
    email: EmailStr
    name:str
    @validator('email', always=True)
    def check_email(cls, v):
        if v is None:
            raise ValueError('User email address is required and cannot be None.')
        return v


class TenantSchema(BaseModel):
    mobile_no: Optional[str]
    password: str
    confirm_password: str
    accepted_terms: bool
    token:str

    @field_validator('accepted_terms', mode='before')
    def validate_accepted_terms(cls, v, info):
        if not v:
            raise ValueError('You must accept the terms and conditions.')
        return v
    @field_validator('token', mode='before')
    def check_token(cls, v,info):
        if v is None:
            raise ValueError('Token is required and cannot be None.')
        return v
    @field_validator('password', 'confirm_password', mode='before')
    def passwords_match(cls, v, info):
        v = v.strip()
        # Access other values from info.
        if info.field_name == 'confirm_password':
            password = info.data.get('password')
            if v != password:
                raise ValueError('Password and Confirm Password do not match.')
        return v


class InvitationSchema(BaseModel):
    email: EmailStr
    role_id:int
    tenant_id:Optional[int] =1
    @validator('email', always=True)
    def check_email(cls, v):
        if v is None:
            raise ValueError('User email address is required and cannot be None.')
        return v


class TenantUserSchema(BaseModel):
    first_name: str
    last_name: str
    mobile_no: Optional[str]
    password: str
    confirm_password: str
    accepted_terms: bool
    token:str

    @field_validator('accepted_terms', mode='before')
    def validate_accepted_terms(cls, v, info):
        if not v:
            raise ValueError('You must accept the terms and conditions.')
        return v
    @field_validator('token', mode='before')
    def check_token(cls, v,info):
        if v is None:
            raise ValueError('Token is required and cannot be None.')
        return v
    
    @field_validator('password', 'confirm_password', mode='before')
    def passwords_match(cls, v, info):
        v = v.strip()
        # Access other values from info.
        if info.field_name == 'confirm_password':
            password = info.data.get('password')
            if v != password:
                raise ValueError('Password and Confirm Password do not match.')
        return v

class AdminRegister(BaseModel):
    email: EmailStr
    mobile_no: str
    user_name: str #constr(min_length=3, max_length=50)
    password: str #constr(min_length=8)

    '''
    @field_validator('passworddd')
    def password_must_contain_digit(cls, value):
        """Ensure the password contains at least one digit."""
        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one digit')
        return value
    
    @field_validator('mobile_no---')
    def validate_mobile_no(cls, value):
        """Validate phone number for all countries."""
        try:
            # Parse the phone number
            phone_number = phonenumbers.parse(value, None)  # None uses the default region
            
            if not is_valid_number(phone_number):
                raise ValueError("Invalid phone number")
            
            return value
        except NumberParseException:
            raise ValueError("Invalid phone number format")
    '''


class addSalesUserSchema(BaseModel):
    email:EmailStr
    first_name: str
    last_name: str
    mobile_no: str
    experience:float
    gender:Optional[str] =""
    role_id:int
    tenant_id:Optional[int]

    
class addAgentUserSchema(BaseModel):
    email:EmailStr
    first_name: str
    last_name: str
    mobile_no: str
    experience:float
    aternate_mobile_no:Optional[str]
    passport:Optional[str]
    aadhaar_card:Optional[str]
    selfie:Optional[str]
    gender:Optional[str]
    date_of_birth: date = Field(..., description="Must be at least 18 years old.And format should be YYYY-MM-DD")
    

    country_id:Optional[int] = None
    state_id:Optional[int] = None
    location_id:Optional[int] = None
    present_address:Optional[str]
    present_occupation:Optional[str]
    pincode:Optional[str]
    employer_name:Optional[str]
    qualification:Optional[str]

    
    account_holder_name:Optional[str]
    bank_name:Optional[str]
    bank_account_number:Optional[str]
    ifsc_code:Optional[str]
    upload_check:Optional[str]
    referrals:Optional[str]
    profile_image:Optional[str]
    role_id:int
    tenant_id:Optional[int]

    @field_validator('date_of_birth', mode='before')
    def validate_date_of_birth(cls, v, info):
        # Ensure v is a date object
        if isinstance(v, str):
            v = date.fromisoformat(v)  # Convert from string to date if needed
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('You must be at least 18 years old. And format should be YYYY-MM-DD')
        return v


    
    