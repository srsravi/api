
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
#from project.database.database import Base 
#from .admin_user import MdUserRole,MdUserStatus
from .master_data_models import MdUserRole, MdUserStatus 
from .user_model import CustomerModal
from .admin_user import AdminUser


