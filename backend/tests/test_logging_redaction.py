import logging

from app.logging_config import configure_secret_redaction_logging


def test_logging_redacts_serpapi_path_auth_url(caplog) -> None:
    configure_secret_redaction_logging()
    logger = logging.getLogger("httpx")

    with caplog.at_level(logging.INFO, logger="httpx"):
        logger.info(
            'HTTP Request: POST https://mcp.serpapi.com/secret-serpapi-key/mcp "HTTP/1.1 200 OK"'
        )

    assert "secret-serpapi-key" not in caplog.text
    assert "https://mcp.serpapi.com/[REDACTED]/mcp" in caplog.text


def test_logging_redaction_is_idempotent(caplog) -> None:
    configure_secret_redaction_logging()
    configure_secret_redaction_logging()
    logger = logging.getLogger("app.test")

    with caplog.at_level(logging.INFO, logger="app.test"):
        logger.info("GET https://mcp.serpapi.com/another-secret/mcp")

    assert "another-secret" not in caplog.text
    assert caplog.text.count("[REDACTED]") == 1
