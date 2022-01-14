from django.contrib import admin
from white_rabbit.admin.user import is_user_admin

from white_rabbit.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    filter_horizontal = ("admins",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "admins":
            kwargs["queryset"] = request.user.employee.company.employees
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(admins=request.user)

    def has_delete_permission(self, request, obj: Company = None):
        if obj is None:
            return True
        return obj.admins.filter(pk=request.user.pk).exists()

    def has_module_permission(self, request) -> bool:
        return is_user_admin(request.user)

    def has_change_permission(self, request, obj: Company = None) -> bool:
        return self.has_delete_permission(request, obj)
