from datetime import datetime, timedelta
from celery import Task
from app.core.celery_app import celery_app
from app.db.session import get_db_session
from app.models.audit_log import AuditLog
from sqlalchemy import delete
import structlog

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3)
def cleanup_old_audit_logs(self, days: int = 90):
    """Clean up audit logs older than specified days"""
    try:
        db = next(get_db_session())
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = db.execute(
            delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
        )
        db.commit()
        
        logger.info("audit_logs_cleaned", deleted_count=result.rowcount, days=days)
        return {"status": "success", "deleted_count": result.rowcount}
    except Exception as exc:
        logger.error("cleanup_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(bind=True)
def recalculate_daily_balances(self):
    """Recalculate material balances for all process units daily"""
    try:
        db = next(get_db_session())
        # TODO: Implement balance recalculation logic
        logger.info("daily_balances_recalculated")
        return {"status": "success"}
    except Exception as exc:
        logger.error("balance_recalculation_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=600)


@celery_app.task(bind=True)
def generate_report(self, report_type: str, params: dict):
    """Generate and export reports (PDF/Excel)"""
    try:
        # TODO: Implement report generation
        logger.info("report_generated", report_type=report_type)
        return {"status": "success", "report_type": report_type}
    except Exception as exc:
        logger.error("report_generation_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=120)
