from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

from white_rabbit.admin.company import is_user_admin

from white_rabbit.models import Project, Alias


class AliasInline(admin.StackedInline):
    model = Alias
    can_delete = True
    verbose_name_plural = "Aliases"
    exclude = ("lowercase_name",)

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Alias.objects.all()
        return Alias.objects.filter(project__company__admins=request.user)

    def has_module_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj):
        return True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "start_date", "estimated_days_count")
    exclude = ("lowercase_name",)
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

            # if some data has been filled in the alias, prevent deleting it
            project_filled_fields = [
                "estimated_days_count",
                "total_sold",
                "category",
                "start_date",
            ]
            for project_to_transform in queryset:
                if any(
                    getattr(project_to_transform, field)
                    for field in project_filled_fields
                ):
                    messages.error(
                        request,
                        f"Impossible de transformer le projet {project_to_transform.name} en alias car il contient des informations spécifiques, on risquerait de perdre des données. Supprimez toutes les informations telles que date de début, catégories, jours prévus, total vendu et recommencez.",
                    )
                    return redirect(reverse("admin:white_rabbit_project_changelist"))

            for project_to_transform in queryset:
                project_to_transform.aliases.all().update(
                    project_id=selected_project_id
                )
                Alias(
                    name=project_to_transform.name, project_id=selected_project_id
                ).save()
                project_to_transform.delete()

            # Redirect to our admin view after our update has completed
            self.message_user(
                request,
                "{} projets transformés en alias de {}".format(
                    queryset.count(), Project.objects.get(pk=selected_project_id).name
                ),
            )
            return HttpResponseRedirect(request.get_full_path())

        company = queryset.first().company
        if queryset.exclude(company=company).exists():
            messages.error(
                request,
                "Tous les projets selectionnés doivent appartenir à la même entreprise",
            )
            return

        projects = (
            Project.objects.filter(company=company)
            .exclude(name__in=queryset.values_list("name", flat=True))
            .order_by("name")
        )
        return render(
            request,
            "admin/project_to_alias_intermediate.html",
            context={"new_aliases": queryset, "projects": projects, "action": True},
        )

    transform_project_to_alias.short_description = (  # type: ignore
        "Transformer en alias d'un autre projet"
    )

    def has_permission(self, request):
        if request.user.is_anonymous:
            return False

        if request.user.is_superuser:
            return True

        # if admin of at least one company
        if is_user_admin(request.user):
            return True

        return False

    def has_module_permission(self, request):
        return self.has_permission(request)

    def has_add_permission(self, request):
        return self.has_permission(request)

    def has_change_permission(self, request, obj: Project = None):
        if obj is None:
            return self.has_permission(request)
        if request.user.is_superuser:
            return True
        return obj.company.admins.filter(pk=request.user.pk).exists()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)
