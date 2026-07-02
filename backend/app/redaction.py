import re
from collections.abc import Iterable


REDACTION = "[REDACTED]"
SERPAPI_PATH_AUTH_PATTERN = re.compile(r"(https?://[^/\s]+/)([^/\s]+)(/mcp\b)")


def redact_provider_secrets(value: object, *, secrets: Iterable[str] = ()) -> str:
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTION)
    return SERPAPI_PATH_AUTH_PATTERN.sub(rf"\1{REDACTION}\3", text)
