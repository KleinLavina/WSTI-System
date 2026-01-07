from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from admin_app.views import (
    admin_work_item_discussion, user_profile,
    dashboard, delete_workcycle, inactive_workcycle_list,  toggle_workcycle_archive,
    workcycle_list,  create_workcycle, edit_workcycle, reassign_workcycle, workcycle_assignments,  admin_delete_user, admin_reset_user_password,
    user_update_image, create_user, users, user_update_role,
    completed_work_summary, done_workers_by_workcycle,
    review_work_item, admin_work_item_threads, services_by_section, sections_by_division, units_by_parent,
    # Add onboarding views
    onboard_division, onboard_section, onboard_service, onboard_unit, onboard_complete,
)
from .views.notification_views import admin_notifications
from .views.document_views import admin_documents
from .views.file_manager_views import admin_file_manager, create_folder, move_attachment, move_folder, rename_folder, delete_file, delete_folder, download_file, upload_files
from .views.all_files_views import all_files_uploaded
from .views.organization_views import manage_organization, create_team, edit_team, delete_team, view_hierarchy

app_name = "admin_app"


urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("discussions/", admin_work_item_threads, name="discussion-list"),
    path("notifications/", admin_notifications, name="admin-notifications"),

    # Workcycles
    path("workcycles/", workcycle_list, name="workcycles"),
    path("workcycles/inactive/", inactive_workcycle_list, name="inactive-workcycles"),
    path("workcycles/create/", create_workcycle, name="workcycle-create"),
    path("workcycles/edit/", edit_workcycle, name="workcycle-edit"),
    path("workcycles/reassign/", reassign_workcycle, name="workcycle-reassign"),
    path(
        "workcycles/<int:pk>/assignments/",
        workcycle_assignments,
        name="workcycle-assignments",
    ),
 path(
    "workcycles/<int:pk>/archive/",
    toggle_workcycle_archive,
    name="workcycle-archive",
),
    path(
        "workcycles/<int:pk>/delete/",
        delete_workcycle,
        name="workcycle-delete"
    ),

    # Analytics
    path(
        "analytics/completed-work/",
        completed_work_summary,
        name="completed-work-summary"
    ),
    path(
        "analytics/workcycle/<int:workcycle_id>/done-workers/",
        done_workers_by_workcycle,
        name="done-workers-by-workcycle"
    ),

    # Work Items
    path(
        "work-items/<int:item_id>/discussion/",
        admin_work_item_discussion,
        name="work-item-discussion"
    ),
    path(
        "work-items/<int:item_id>/review/",
        review_work_item,
        name="work-item-review"
    ),

    # Documents
    path(
        "documents/",
        admin_documents,
        name="documents"
    ),
    path(
        "documents/file-manager/",
        admin_file_manager,
        name="file-manager"
    ),
    path(
        "documents/files/<int:folder_id>/",
        admin_file_manager,
        name="file-manager-folder"
    ),
    path("documents/files/create-folder/", create_folder, name="create-folder"),
    path("documents/files/rename-folder/", rename_folder, name="rename-folder"),
    path("documents/files/delete-folder/", delete_folder, name="delete-folder"),
    path("documents/files/delete-file/", delete_file, name="delete-file"),
    path("documents/files/download/<int:attachment_id>/", download_file, name="download-file"),
    path("documents/files/upload/", upload_files, name="upload-files"),
    path("documents/files/move/", move_attachment, name="move-attachment"),
    path("documents/files/move-folder/", move_folder, name="move-folder"),
    path(
        "documents/all-files/",
        all_files_uploaded,
        name="all-files-uploaded"
    ),

    # Users
    path("users/", users, name="users"),
    path("users/create/", create_user, name="user-create"),
    path("users/<int:user_id>/", user_profile, name="user-profile"),
    path("users/<int:user_id>/update-role/", user_update_role, name="user-update-role"),
    path("users/<int:user_id>/update-image/", user_update_image, name="user-update-image"),
    # User Onboarding Flow (New!)
        path(
        "users/<int:user_id>/reset-password/",
        admin_reset_user_password,
        name="user-reset-password"
    ),
    path(
        "users/<int:user_id>/delete/",
        admin_delete_user,
        name="user-delete"
    ),
    path("users/<int:user_id>/onboard/division/", onboard_division, name="onboard-division"),
    path("users/<int:user_id>/onboard/section/", onboard_section, name="onboard-section"),
    path("users/<int:user_id>/onboard/service/", onboard_service, name="onboard-service"),
    path("users/<int:user_id>/onboard/unit/", onboard_unit, name="onboard-unit"),
    path("users/<int:user_id>/onboard/complete/", onboard_complete, name="onboard-complete"),
    
    # Legacy organization assignment (keep for backward compatibility if needed)

    # API Endpoints
    path("api/sections/<int:division_id>/", sections_by_division),
    path("api/services/<int:section_id>/", services_by_section),
    path("api/units/", units_by_parent),


     path('organization/', manage_organization, name='manage-organization'),
    path('organization/create/', create_team, name='create-team'),
    path('organization/edit/', edit_team, name='edit-team'),
    path('organization/delete/', delete_team, name='delete-team'),
    path('organization/hierarchy/<int:team_id>/', view_hierarchy, name='view-hierarchy'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)