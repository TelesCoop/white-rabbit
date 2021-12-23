from django.contrib import admin

from white_rabbit.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        if request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(admins=request.user)

    def has_delete_permission(self, request, obj: Company = None):
        if obj is None:
            return True
        return obj.admins.filter(pk=request.user.pk).exists()
