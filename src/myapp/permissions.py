# permissions.py
from rest_framework.permissions import BasePermission


class IsUserAccess(BasePermission):
    def has_permission(self, request, view):
        user_id = getattr(request, "user_id", None)
        role = getattr(request, "role", None)

        if not user_id:
            return False

        # Check the path to differentiate between 'core' and 'admin'
        is_core_path = request.path.startswith("/api/core/")
        is_admin_path = request.path.startswith("/api/admin/")

        if is_core_path and role == "User":
            return True

        return bool(is_admin_path and role == "Admin")
