from django.urls import path

from .views.dashboard_views import dashboard

from .views.work_item_views import (
    user_work_items,
    user_inactive_work_items,
    user_work_item_detail,
    user_work_item_attachments,
    delete_work_item_attachment,
)

from .views.user_work_item_threads import user_work_item_threads
from .views.notification_views import user_notifications
from .views.message_views import user_work_item_discussion

app_name = "user_app"


urlpatterns = [
    # ======================
    # DASHBOARD
    # ======================
    path("dashboard/", dashboard, name="dashboard"),

    # ======================
    # WORK ITEMS
    # ======================
    path(
        "work-items/",
        user_work_items,
        name="work-items"
    ),

    path(
        "work-items/archived/",
        user_inactive_work_items,
        name="work-items-archived"
    ),

    path(
        "work-items/<int:item_id>/",
        user_work_item_detail,
        name="work-item-detail"
    ),

    path(
        "work-items/<int:item_id>/attachments/",
        user_work_item_attachments,
        name="work-item-attachments"
    ),

    path(
        "attachments/<int:attachment_id>/delete/",
        delete_work_item_attachment,
        name="delete-attachment"
    ),

    # ======================
    # DISCUSSIONS
    # ======================
    path(
        "discussions/",
        user_work_item_threads,
        name="discussion-list"
    ),

    path(
        "work-items/<int:item_id>/discussion/",
        user_work_item_discussion,
        name="work-item-discussion"
    ),

    # ======================
    # NOTIFICATIONS
    # ======================
    path(
        "notifications/",
        user_notifications,
        name="user-notifications"
    ),
]
