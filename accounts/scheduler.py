import logging

from django.db import transaction
from django_celery_beat.models import PeriodicTask
from django_celery_beat.models import PeriodicTasks
from django_celery_beat.schedulers import DatabaseScheduler


class DatabaseSchedulerWithCleanup(DatabaseScheduler):
    def setup_schedule(self):
        logging.info("--START SCHEDULER--")
        schedule = self.app.conf.beat_schedule
        with transaction.atomic():
            num, _ = (
                PeriodicTask.objects.exclude(task__startswith="celery.")
                .exclude(name__in=schedule.keys())
                .delete()
            )
            logging.info("Removed %d obsolete periodic tasks.", num)
            if num > 0:
                PeriodicTasks.update_changed()
        super().setup_schedule()
