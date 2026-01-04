# user_app/context_processors.py

"""
Context Processors for User App
================================

Add global template variables, specifically for unread message counts.

To enable, add to settings.py:

TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... other processors ...
                'user_app.context_processors.unread_discussions',
            ],
        },
    },
]
"""

from accounts.models import WorkItemMessage
from django.db.models import Q
from django.core.cache import cache


def unread_discussions(request):
    """
    Add unread discussion count to all templates.
    
    Usage in templates:
        {% if has_unread_discussions %}
            <span class="badge">{{ unread_discussions_count }}</span>
        {% endif %}
    
    Returns:
        dict: {
            'unread_discussions_count': int,
            'has_unread_discussions': bool,
        }
    """
    
    if not request.user.is_authenticated:
        return {
            'unread_discussions_count': 0,
            'has_unread_discussions': False,
        }
    
    # Get unread count (fresh query every time)
    unread_count = WorkItemMessage.objects.filter(
        work_item__owner=request.user,
        work_item__is_active=True,
        is_read=False
    ).exclude(
        sender=request.user
    ).count()
    
    return {
        'unread_discussions_count': unread_count,
        'has_unread_discussions': unread_count > 0,
    }


def unread_discussions_cached(request):
    """
    Cached version of unread discussions counter.
    
    ⚡ BETTER PERFORMANCE - Recommended for production
    
    Cache expires every 60 seconds to reduce database queries.
    Cache is automatically invalidated when new messages are created
    (if you implement the signals).
    
    To invalidate cache manually:
        from django.core.cache import cache
        cache.delete(f'unread_count_{user.id}')
    
    Returns:
        dict: {
            'unread_discussions_count': int,
            'has_unread_discussions': bool,
        }
    """
    
    if not request.user.is_authenticated:
        return {
            'unread_discussions_count': 0,
            'has_unread_discussions': False,
        }
    
    cache_key = f'unread_count_{request.user.id}'
    unread_count = cache.get(cache_key)
    
    if unread_count is None:
        # Cache miss - query database
        unread_count = WorkItemMessage.objects.filter(
            work_item__owner=request.user,
            work_item__is_active=True,
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        
        # Cache for 60 seconds
        cache.set(cache_key, unread_count, 60)
    
    return {
        'unread_discussions_count': unread_count,
        'has_unread_discussions': unread_count > 0,
    }


def invalidate_unread_cache(user):
    """
    Invalidate unread count cache for a specific user.
    
    Call this after:
    - New message created
    - Message marked as read
    - Work item becomes inactive
    
    Args:
        user: User instance
    
    Usage:
        from user_app.context_processors import invalidate_unread_cache
        invalidate_unread_cache(request.user)
    """
    cache.delete(f'unread_count_{user.id}')