from django.template.defaulttags import register


@register.simple_tag
def project_name(project_details, project_id):
    return project_details[project_id]["name"]
