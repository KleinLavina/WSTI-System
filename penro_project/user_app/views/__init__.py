# user_app/views/__init__.py

"""
User App Views
==============

This package contains all views for the user-facing application.
"""

# Dashboard
from .dashboard_views import dashboard

# Work Items
from .work_item_views import (
    user_work_items,
    user_inactive_work_items,
    user_work_item_detail,
    user_work_item_attachments,
    delete_work_item_attachment,
)
from .user_profile_views import user_profile, user_update_image, onboard_unit, onboard_section, onboard_complete, onboard_division, onboard_service
# Threads (if you have a separate threads view)
from .user_work_item_threads import user_work_item_threads

# Notifications
from .notification_views import user_notifications

# Messages / Discussions (NEW - READ RECEIPT SYSTEM)
from .message_views import (
    user_work_item_discussion,
    user_discussions_list,
    user_mark_all_discussions_read,
    user_discussion_stats,
    get_user_total_unread_count,  # Utility function
)


__all__ = [
    # Dashboard
    'dashboard',
    
    # Work Items
    'user_work_items',
    'user_inactive_work_items',
    'user_work_item_detail',
    'user_work_item_attachments',
    'delete_work_item_attachment',
    
    # Threads
    'user_work_item_threads',
    
    # Notifications
    'user_notifications',
    
    # Discussions (Read Receipt System)
    'user_work_item_discussion',
    'user_discussions_list',
    'user_mark_all_discussions_read',
    'user_discussion_stats',
    'get_user_total_unread_count',
]