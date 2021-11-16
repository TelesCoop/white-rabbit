from django.contrib import admin
from django.contrib.auth.models import User, Group

from .project import ProjectAdmin  # noqa: F401
from .company import CompanyAdmin  # noqa: F401
from .user import UserAdmin  # noqa: F401

admin.site.site_header = "Administration de Lapin Blanc"
admin.site.index_title = ""
admin.site.site_title = "Lapin Blanc"

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
