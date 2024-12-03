from pydantic import BaseModel
from pydantic import BaseModel, Field,field_validator,EmailStr,model_validator
from typing import Optional
from ..constant.messages import COUNTRY_STATES_LIST, STATE_LOCATION_LIST 
from datetime import date,timedelta,datetime

from ..schemas.user_schema import ListRequestBase
class getMasterData(BaseModel):
    categories:list = Field(...,  description='''Available categories ===> 
                md_countries ,\n
                md_states , \n 
                md_locations ,
                md_locations ,\n
                md_task_status ,\n
                md_tenant_status ,\n
                md_timezone, \n
                md_user_roles, \n
                md_user_status,\n
                md_tanants , \n 
                md_service_types , \n
                md_lead_sources , \n
                md_profession_types , \n
                md_profession_sub_types ,\n
                md_income_types , \n
                md_obligation_types , \n
                md_loan_application_status , \n
                            md_ifsc_codes, \n
                            ''')
    country_id:Optional[int] = Field(None,  description=COUNTRY_STATES_LIST)
    state_id:Optional[int] = Field(None,  description=STATE_LOCATION_LIST  )
    

class Document(BaseModel):
    name: str
    content_type: str
    path: str
    size: int
    md_doc_id:int
    class Config:
        #orm_mode = True
        from_attributes = True
        str_strip_whitespace = True
class DownloadFile(BaseModel):
    path: str

class CalculateCurrency(BaseModel):
    from_currency:str ="EUR"
    to_currency:Optional[str]

class KycDocsListReq(ListRequestBase):
    status:Optional[bool] =None
    required:Optional[bool] = None
    search_string: Optional[str] = None  # Search string on string based columns
    page:int = 1
    per_page:int =25
    created_on: Optional[date] = Field(default_factory=lambda: date(1970, 1, 1))  # Default to '1970-01-01' if None
    created_to: Optional[date] = Field(default_factory=date.today)  # Default to today's date if None
    # created_on: Optional[date] = date(1970, 1, 1)
    # created_to: Optional[date] = date.today()
    sort_by: Optional[str] = "id"  # Default sort by 'created_on'
    sort_order: Optional[str] = "desc"

    @field_validator('created_on', mode='before')
    def created_on_convert_datetime_to_date(cls, v):
        if v in (None, ''):  # Handle None or empty string inputs
            return date(1970, 1, 1)  # Default value
        if isinstance(v, datetime):
            return (v - timedelta(days=1)).date()
        elif isinstance(v, date):
            return (v - timedelta(days=1))
        return v
        
    @field_validator('created_to', mode='before')
    def created_to_convert_datetime_to_date(cls, v):
        if v in (None, ''):  # Handle None or empty string inputs
            return date.today()  # Default value
        if isinstance(v, datetime):
            return (v + timedelta(days=1)).date()
        elif isinstance(v, date):
            return (v + timedelta(days=1))
        return v
    
class Kycheck(BaseModel):
    status:bool
    
class Kycenable(BaseModel):
    id : int
    status : int

class CreateKycSchema(BaseModel):
  
    name : str
    required : bool
    #doc_type : str
    #size :  int
    status :bool
    description : str
    users_list : Optional[list]
    share_type:str =Field("ALL_USERS", description="share_type should be SPECIFIC_USERS or UPCOMMING_USERS OR ALL_USERS"  )
    # email:Optional[EmailStr] =None
    @field_validator("description", mode='before')
    def validate_description(cls, v,info):
        v = v.strip()
        if v is None or v =='':
            raise ValueError('Description is required')
        return v
    
    @field_validator("share_type", mode='before')
    def validate_share_type(cls, v,info):
        if v not in ["ALL_USERS","SPECIFIC_USERS","UPCOMMING_USERS"]:
            raise ValueError('share_type should be SPECIFIC_USERS OR UPCOMMING_USERS OR ALL_USERS')
        return v
    
    @model_validator(mode='before')
    def check_users_list_if_specific(self):
        if self["share_type"] == "SPECIFIC_USERS" and (not self["users_list"] or len(self["users_list"]) == 0):
            raise ValueError("users_list must contain at least one user when share_type is SPECIFIC_USERS.")
        return self

    class Config:
        #orm_mode = True
        from_attributes = True
        str_strip_whitespace = True
class kycDocDetailsReqSchema(BaseModel):
    md_doc_id:int

class EditKycSchema(CreateKycSchema):
    md_doc_id:int

class GetIfscCodeSchema(ListRequestBase):
    search_string: Optional[str] = None 

    

