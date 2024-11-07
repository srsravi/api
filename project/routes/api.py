from fastapi import APIRouter
from project.endpoints.user_auth import user_authentication
from project.endpoints.admin_auth import admin_authentication
from ..endpoints.master_data import master_data
from ..endpoints.tickets_request import tickets_request
from ..endpoints.user import user
from ..endpoints.notifications import notifications,admin_notifications

router = APIRouter()

# --------------------Authenticatio Routing---------------------
router.include_router(user_authentication.router)

# --------------------Admin Routing--------------------
router.include_router(admin_authentication.router)


# --------------------User Routing---------------------
router.include_router(user.router)

#--------------------User Routing---------------------
router.include_router(tickets_request.router)


#---------------------notifications---------------------
router.include_router(notifications.router)
router.include_router(admin_notifications.router)
# --------------------master data Routing--------------------
router.include_router(master_data.router)
