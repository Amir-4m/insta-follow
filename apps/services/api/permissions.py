from rest_framework.permissions import BasePermission


class ServicePermission(BasePermission):
    def has_permission(self, request, view):
        if request.auth is None:
            return False

        return 'service' in request.auth and request.auth['service'].is_enable
