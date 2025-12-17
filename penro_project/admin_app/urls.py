from django.urls import path
from admin_app.views import (
    dashboard,
    workcycle_list, create_workcycle, edit_workcycle, reassign_workcycle, workcycle_assignments,  
    team_views,
    users, create_user, update_user, delete_user,
    completed_work_summary, done_workers_by_workcycle,
    review_work_item, admin_work_item_discussion, admin_work_item_threads,
)

app_name = "admin_app"

urlpatterns = [
    path("", dashboard, name="dashboard"),
       path(
    "discussions/",
    admin_work_item_threads,
    name="discussion-list"
),

    path("workcycles/", workcycle_list, name="workcycles"),
    path("workcycles/create/", create_workcycle, name="workcycle-create"),
    path("workcycles/edit/", edit_workcycle, name="workcycle-edit"),
    path("workcycles/reassign/", reassign_workcycle, name="workcycle-reassign"),
    # admin_app/urls.py
    path(
    "workcycles/<int:pk>/assignments/",
    workcycle_assignments,
    name="workcycle-assignments",
),

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
    path(
    "work-items/<int:item_id>/discussion/",
    admin_work_item_discussion,
    name="work-item-discussion"),
    path(
        "work-items/<int:item_id>/review/",
        review_work_item,
        name="work-item-review"
    ),
 


    path("teams/", team_views, name="teams"),

    path("users/<int:user_id>/update/", update_user, name="user-update"),
    path("users/<int:user_id>/delete/", delete_user, name="user-delete"),
    path("users/create/", create_user, name="user-create"),
    path("users/", users, name="users"),
    

    


    

]
