"""Custom decorators used across the VTU platform's views."""
import functools
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

logger = logging.getLogger('core')


def profile_required(view_func):
    """
    Ensure the logged-in user has a UserProfile before entering the view.
    Combines login_required + a profile existence check into one decorator.
    """
    @login_required
    @functools.wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'profile'):
            messages.error(request, "Your account profile could not be found. Please contact support.")
            logger.warning("User %s has no profile.", request.user.username)
            return redirect('logout')
        return view_func(request, *args, **kwargs)
    return _wrapped


def ajax_login_required(view_func):
    """Like login_required, but returns 401 JSON instead of redirecting (for AJAX endpoints)."""
    @functools.wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped
