"""Template context processors."""


def wallet_context(request):
    """Expose the logged-in user's wallet balance to every template (navbar badge)."""
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        return {'nav_wallet_balance': request.user.profile.wallet_balance}
    return {'nav_wallet_balance': None}
