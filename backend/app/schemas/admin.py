from pydantic import BaseModel, condecimal
from typing import Optional, List
from datetime import datetime

class AdminDepositRequest(BaseModel):
    amount: condecimal(gt=0, decimal_places=2)

class AdminPermissionUpdate(BaseModel):
    can_deposit: bool
    can_delete: bool
    can_suspend: bool
    can_manage_admins: bool
    max_deposit_limit: int

class AdminRoleUpdate(BaseModel):
    role: str # user, admin, super_admin

class AdminLogResponse(BaseModel):
    id: int
    admin_id: int
    admin_name: str
    action: str
    target_user_id: Optional[int]
    target_user_name: Optional[str]
    details: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class AdminPermissionsResponse(BaseModel):
    can_deposit: bool
    can_delete: bool
    can_suspend: bool
    can_manage_admins: bool
    max_deposit_limit: int

    class Config:
        from_attributes = True

class AdminUserActionsResponse(BaseModel):
    show_deposit: bool
    show_suspend: bool
    show_delete: bool
    show_role_toggle: Optional[str] # "promote", "demote", or None
    show_permissions_panel: bool
    is_self: bool
    message: Optional[str]
