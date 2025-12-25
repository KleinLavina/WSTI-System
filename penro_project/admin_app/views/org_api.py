from django.http import JsonResponse
from accounts.models import Team


def sections_by_division(request, division_id):
    data = Team.objects.filter(
        team_type="section",
        parent_id=division_id
    ).values("id", "name")
    return JsonResponse(list(data), safe=False)


def services_by_section(request, section_id):
    data = Team.objects.filter(
        team_type="service",
        parent_id=section_id
    ).values("id", "name")
    return JsonResponse(list(data), safe=False)


def units_by_parent(request):
    section_id = request.GET.get("section")
    service_id = request.GET.get("service")

    qs = Team.objects.filter(team_type="unit")

    if service_id:
        qs = qs.filter(parent_id=service_id)
    elif section_id:
        qs = qs.filter(parent_id=section_id)

    return JsonResponse(
        list(qs.values("id", "name")),
        safe=False
    )
