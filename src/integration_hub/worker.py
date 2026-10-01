import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.sql.elements import ColumnElement

from integration_hub.database import SessionLocal
from integration_hub.models import Company, Job, Sync, WebhookEvent
from integration_hub.services import delivery

LEASE_DURATION = timedelta(minutes=5)
POLL_INTERVAL_SECONDS = 1
MAX_ATTEMPTS = 5
logger = logging.getLogger(__name__)


def _ready_jobs(now: datetime) -> ColumnElement[bool]:
    return or_(
        and_(
            Job.status.in_(("pending", "retrying")),
            Job.available_at <= now,
        ),
        and_(
            Job.status == "processing",
            Job.locked_at <= now - LEASE_DURATION,
        ),
    )


def next_job_id() -> UUID | None:
    with SessionLocal() as session:
        return session.scalar(
            select(Job.id)
            .where(_ready_jobs(datetime.now(UTC)))
            .order_by(Job.available_at, Job.created_at)
            .limit(1)
        )


def process_job(job_id: UUID) -> bool:
    now = datetime.now(UTC)
    with SessionLocal.begin() as session:
        job = session.scalar(
            select(Job)
            .where(Job.id == job_id, _ready_jobs(now))
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return False

        sync = session.get(Sync, job.sync_id)
        event = session.get(WebhookEvent, sync.event_id)
        company = session.get(Company, job.company_id)
        job.status = sync.status = "processing"
        job.attempts += 1
        sync.attempts = job.attempts
        attempts = job.attempts
        job.locked_at = now
        sync_id = sync.id
        company_slug = company.slug
        source = event.source
        event_type = event.event_type
        event_data = event.payload["data"]

    try:
        delivery.deliver_event(company_slug, source, event_type, event_data)
    except Exception as error:  # noqa: BLE001
        logger.error("Sync %s failed: %s", sync_id, type(error).__name__)
        status = "retrying" if attempts < MAX_ATTEMPTS else "dead_letter"
        last_error = type(error).__name__
    else:
        status = "succeeded"
        last_error = None

    with SessionLocal.begin() as session:
        job = session.get(Job, job_id)
        sync = session.get(Sync, job.sync_id)
        job.status = sync.status = status
        job.last_error = sync.last_error = last_error
        job.locked_at = None
        if status == "retrying":
            job.available_at = datetime.now(UTC) + timedelta(
                seconds=2 ** (attempts - 1)
            )

    return True


def run_worker() -> None:
    while True:
        job_id = next_job_id()
        if job_id is None or not process_job(job_id):
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
