from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _

from white_rabbit.models import Employee, Company

admin.site.site_header = "Administration de Lapin Blanc"
admin.site.index_title = ""
admin.site.site_title = "Lapin Blanc"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        if request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(admins=request.user)


class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name_plural = "salarié"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Only show companies where user is admin."""
        if db_field.name == "company" and not request.user.is_superuser:
            kwargs["queryset"] = Company.objects.filter(admins=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Employee.objects.all()
        return Employee.objects.filter(company__admins=request.user)

    def has_module_permission(self, request):
        return UserAdmin.has_permission(self, request)

    def has_add_permission(self, request, obj):
        return UserAdmin.has_permission(self, request)

    def get_formset(self, request, obj=None, **kwargs):
        """Pre-fill company field."""
        form = super().get_formset(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.form.base_fields["company"].initial = request.user.companies.first().pk
        return form


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff"),
            },
        ),
    )
    inlines = (EmployeeInline,)

    def has_permission(self, request):
        if request.user.is_anonymous:
            return False

        if request.user.is_superuser:
            return True

        # if admin of at least one company
        if Company.objects.filter(admins=request.user).exists():
            print("IS ADMIN")
            return True
        print("### NOT ADMIN")
        return False

    def has_module_permission(self, request):
        return self.has_permission(request)

    def has_add_permission(self, request):
        return self.has_permission(request)

    def has_change_permission(self, request, obj: User = None):
        if obj is None:
            return self.has_permission(request)
        return obj.employee.company.admins.filter(pk=request.user.pk).exists()

    def get_queryset(self, request):
        if request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(employee__company__admins=request.user)


admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
