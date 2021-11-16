from django.contrib import admin

from white_rabbit.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        if request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(admins=request.user)
