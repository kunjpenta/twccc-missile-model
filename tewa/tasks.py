# tewa/tasks.py

from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
def compute_threats_task():
    """
    Celery task to run the compute_threats management command periodically.
    """
    try:
        call_command('compute_threats')  # Calls the management command
        logger.info("Threat scores computation task completed successfully.")
    except Exception as e:
        logger.error(f"Error during compute_threats task: {str(e)}")
