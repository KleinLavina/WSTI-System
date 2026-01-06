# user_app/urls.py

from django.urls import path

from .views.dashboard_views import dashboard

from .views.work_item_views import (
    user_work_items,
    user_inactive_work_items,
    user_work_item_detail,
    user_work_item_attachments,
    delete_work_item_attachment,
    toggle_work_item_archive,
)

from .views.user_work_item_threads import user_work_item_threads
from .views.notification_views import user_notifications
from .views.user_profile_views import user_profile, user_update_image, onboard_complete, onboard_division, onboard_service, onboard_section, onboard_unit
# Import message views
from .views.message_views import (
    user_work_item_discussion,
    user_discussions_list,
    user_mark_all_discussions_read,
    user_discussion_stats,
)

app_name = "user_app"


urlpatterns = [
    # ======================
    # DASHBOARD
    # ======================
    path("dashboard/", dashboard, name="dashboard"),
    # user_app/urls.py
    path("profile/", user_profile, name="profile"),
    path("profile/image/", user_update_image, name="profile-image"),

# user_app/urls.py

path("onboard/division/", onboard_division, name="onboard-division"),
path("onboard/section/", onboard_section, name="onboard-section"),
path("onboard/service/", onboard_service, name="onboard-service"),
path("onboard/unit/", onboard_unit, name="onboard-unit"),
path("onboard/complete/", onboard_complete, name="onboard-complete"),

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
    path(
        "work-items/<int:item_id>/toggle-archive/",
        toggle_work_item_archive,
        name="work-item-toggle-archive",
    ),

    # ======================
    # DISCUSSIONS (NEW READ RECEIPT SYSTEM)
    # ======================
    
    # Main discussions list page
    path(
        "discussions/",
        user_discussions_list,
        name="discussions-list"
    ),
    
    # Bulk action: Mark all as read
    path(
        "discussions/mark-all-read/",
        user_mark_all_discussions_read,
        name="discussions-mark-all-read"
    ),
    
    # API endpoint: Get discussion statistics
    path(
        "discussions/stats/",
        user_discussion_stats,
        name="discussion-stats"
    ),
    
    # Individual discussion thread (opens in modal/iframe)
    path(
        "discussions/<int:item_id>/",
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