from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render

from white_rabbit.models import Project, Alias


class AliasInline(admin.StackedInline):
    model = Alias
    can_delete = True
    verbose_name_plural = "Aliases"

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Alias.objects.all()
        return Alias.objects.filter(project__company__admins=request.user)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    fields = ("name",)
    list_display = ("name",)
    inlines = (AliasInline,)
    search_fields = ["aliases__name", "name"]
    actions = ["transform_project_to_alias"]

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(company__admins=request.user)

    def transform_project_to_alias(self, request, queryset):
        if "apply" in request.POST:
            selected_project_id = int(request.POST.get("selected_project"))
            for project_to_transform in queryset:
                Alias(
                    name=project_to_transform.name, project_id=selected_project_id
                ).save()
                project_to_transform.delete()

            # Redirect to our admin view after our update has completed
            self.message_user(
                request, "Changed status on {} orders".format(queryset.count())
            )
            return HttpResponseRedirect(request.get_full_path())

        projects = Project.objects.exclude(
            name__in=queryset.values_list("name", flat=True)
        )
        return render(
            request,
            "admin/project_to_alias_intermediate.html",
            context={"new_aliases": queryset, "projects": projects, "action": True},
        )

    transform_project_to_alias.short_description = (
        "Transformer en alias d'un autre projet"
    )
