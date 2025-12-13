from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from accounts.models import WorkItem
from ..services.work_item_service import (
    update_work_item_status,
    submit_work_item,
    add_attachment_to_work_item,
    update_work_item_context,   # 👈 ADD THIS
)



@login_required
def user_work_items(request):
    """
    List ALL work items assigned to the user.
    Inactive ones remain visible but marked.
    """
    work_items = (
        WorkItem.objects
        .select_related("workcycle")
        .filter(owner=request.user)
        .order_by(
            "-is_active",          # active items first
            "workcycle__due_at"
        )
    )

    return render(
        request,
        "user/page/work_items.html",
        {"work_items": work_items}
    )



@login_required
def user_work_item_detail(request, item_id):
    work_item = get_object_or_404(
        WorkItem,
        id=item_id,
        owner=request.user,
        is_active=True
    )

    if request.method == "POST":
        action = request.POST.get("action")

        try:
            if action == "update_status":
                new_status = request.POST.get("status")
                update_work_item_status(work_item, new_status)
                messages.success(request, "Status updated.")

            elif action == "submit_work":
                files = request.FILES.getlist("attachments")
                message = request.POST.get("message", "").strip()

                submit_work_item(
                    work_item=work_item,
                    files=files,
                    message=message,
                    user=request.user
                )
                messages.success(request, "Work submitted successfully.")
            
            elif action == "update_context":
                label = request.POST.get("status_label", "").strip()
                message = request.POST.get("message", "").strip()

                update_work_item_context(
                    work_item=work_item,
                    label=label,
                    message=message,
                )

                messages.success(request, "Work item notes updated.")



            elif action == "add_attachment":
                files = request.FILES.getlist("attachments")
                add_attachment_to_work_item(
                    work_item=work_item,
                    files=files,
                    user=request.user
                )
                messages.success(request, "Attachment added.")

            return redirect("user_app:work-item-detail", item_id=work_item.id)

        except Exception as e:
            messages.error(request, str(e))

    return render(
        request,
        "user/page/work_item_detail.html",
        {
            "work_item": work_item,
            "can_edit": work_item.status != "done",
            "status_choices": WorkItem._meta.get_field("status").choices,
        }
    )
