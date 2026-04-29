"""Redaction module — removes secrets from memory content before storage."""

import re

# Patterns for common secret formats
SECRET_PATTERNS = [
    # OpenAI / Anthropic API keys
    (re.compile(r'(?:sk-[a-zA-Z0-9]{20,})', re.IGNORECASE), '[REDACTED_API_KEY]'),
    # GitHub tokens
    (re.compile(r'(?:ghp_[a-zA-Z0-9]{20,})', re.IGNORECASE), '[REDACTED_GH_TOKEN]'),
    # Bearer tokens
    (re.compile(r'(?:Bearer\s+[a-zA-Z0-9_\-\.]{10,})', re.IGNORECASE), 'Bearer [REDACTED_TOKEN]'),
    # password=xxx, password: xxx
    (re.compile(r'((?:password|passwd|pwd)\s*[=:]\s*)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    # token=xxx, api_token=xxx, api_key=xxx, secret=xxx
    (re.compile(r'((?:token|api_key|api_token|secret_key|secret|access_key|access_token)\s*[=:]\s*)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    # Private key headers
    (re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----.*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----', re.DOTALL), '[REDACTED_PRIVATE_KEY]'),
    # AWS keys
    (re.compile(r'(?:AKIA[0-9A-Z]{16})', re.IGNORECASE), '[REDACTED_AWS_KEY]'),
    # Generic base64-ish long strings after key-like identifiers
    (re.compile(r'((?:key|secret|token|credential)\s*[=:]\s*)(?:[A-Za-z0-9+/]{30,}={0,3})', re.IGNORECASE), r'\1[REDACTED]'),
]


def redact_secrets(text: str) -> str:
    """Replace secrets in text with [REDACTED] placeholders.
    
    Returns the sanitized text.
    """
    result = text
    for pattern, replacement in SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def contains_secrets(text: str) -> bool:
    """Check if text likely contains secrets."""
    for pattern, _ in SECRET_PATTERNS:
        if pattern.search(text):
            return True
    return False
