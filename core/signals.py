"""
Signal handlers.

We deliberately do NOT auto-create the UserProfile here, because
registration requires extra fields (phone_number) supplied by the user at
sign-up time - the profile is created explicitly inside the registration
view instead. This module still centralises any post-save behaviour we do
want to run automatically, such as logging.
"""
import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger('core')


@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    """Log every time a User record is created or updated."""
    if created:
        logger.info("New user account created: %s (id=%s)", instance.username, instance.id)
    else:
        logger.debug("User account updated: %s (id=%s)", instance.username, instance.id)
