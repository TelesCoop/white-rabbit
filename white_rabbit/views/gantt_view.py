import datetime

from django.db.models import Q
from django.views.generic import TemplateView

from white_rabbit.models import Project


class GanttView(TemplateView):
    template_name = "pages/gantt.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        company = user.employee.company
        today = datetime.date.today()

        # Get projects for the next 6 months
        six_months_from_now = today + datetime.timedelta(days=180)

        # Get all regular projects (excluding forecast projects) that are active or will be active in the next 6 months
        # Only include projects that have a start date
        projects = (
            Project.objects.filter(
                company=company,
                is_forecast=False,
                start_date__isnull=False,  # Only projects with start dates
            )
            .filter(Q(end_date__gte=today) | Q(end_date__isnull=True))
            .filter(start_date__lte=six_months_from_now)
            .select_related("category")
            .order_by("start_date", "name")
        )

        # Calculate project data for each project
        projects_data = []
        for project in projects:
            # Use the real start and end dates
            project_start = project.start_date
            project_end = project.end_date or six_months_from_now

            # Calculate project intensity using real project dates
            calendar_days = (project_end - project_start).days + 1
            estimated_days = float(project.estimated_days_count or 0)
            intensity = (
                estimated_days / calendar_days
                if calendar_days > 0 and estimated_days > 0
                else 0
            )

            projects_data.append(
                {
                    "project": project,
                    "start_date": project_start,
                    "end_date": project_end,
                    "duration_days": calendar_days,
                    "estimated_days": estimated_days,
                    "intensity": intensity,
                    "category_color": (
                        project.category.color if project.category else "bg-gray-100"
                    ),
                    "category_name": (
                        project.category.name if project.category else "Non défini"
                    ),
                }
            )

        # Calculate relative intensity and assign colors
        max_intensity = max((p["intensity"] for p in projects_data), default=0)

        for project_data in projects_data:
            if project_data["intensity"] == 0 or max_intensity == 0:
                # Gray for projects with no intensity
                project_data["intensity_color"] = "#9CA3AF"
                project_data["relative_intensity"] = 0
            else:
                # Calculate relative intensity (0-1 scale)
                relative_intensity = project_data["intensity"] / max_intensity
                project_data["relative_intensity"] = relative_intensity

                # Use blue hue with varying intensity (lightness)
                # HSL: hue=210 (blue), saturation=100%, lightness varies from 85% to 35%
                lightness = 85 - (relative_intensity * 50)  # 85% to 35%
                project_data["intensity_color"] = f"hsl(210, 100%, {lightness:.0f}%)"

        return {
            "projects_data": projects_data,
            "today": today,
            "six_months_from_now": six_months_from_now,
            "company": company,
        }
