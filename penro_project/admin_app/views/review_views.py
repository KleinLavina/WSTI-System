from django.shortcuts import get_object_or_404, render, redirect
from accounts.models import WorkItem

def review_work_item(request, item_id):
    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle").prefetch_related("attachments"),
        id=item_id,
        status="done"
    )

    if request.method == "POST" and request.POST.get("action") == "update_review":
        decision = request.POST.get("review_decision")
        if decision in {"pending", "approved", "revision"}:
            work_item.review_decision = decision
            work_item.save(update_fields=["review_decision"])

        return redirect("admin_app:work-item-review", item_id=item_id)

    return render(
        request,
        "admin/page/review_work_item.html",
        {
            "work_item": work_item,
        }
    )
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages

from accounts.models import WorkItem, WorkItemMessage


@login_required
def admin_work_item_discussion(request, item_id):
    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle"),
        id=item_id
    )

    if request.method == "POST":
        text = request.POST.get("message", "").strip()
        if text:
            WorkItemMessage.objects.create(
                work_item=work_item,
                sender=request.user,
                sender_role=request.user.login_role,
                message=text
            )
            messages.success(request, "Message posted.")
            return redirect(
                "admin_app:work-item-discussion",
                item_id=work_item.id
            )

    messages_qs = work_item.messages.select_related("sender")

    return render(
        request,
        "admin/page/work_item_discussion.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
        }
    )
