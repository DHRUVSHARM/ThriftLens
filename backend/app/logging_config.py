import logging
from typing import Any

from app.redaction import redact_provider_secrets


_DEFAULT_LOG_RECORD_FACTORY = logging.getLogRecordFactory()
_REDACTION_CONFIGURED = False


def configure_secret_redaction_logging() -> None:
    global _REDACTION_CONFIGURED
    if _REDACTION_CONFIGURED:
        return

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = _DEFAULT_LOG_RECORD_FACTORY(*args, **kwargs)
        message = record.getMessage()
        redacted = redact_provider_secrets(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return record

    logging.setLogRecordFactory(record_factory)
    _REDACTION_CONFIGURED = True
