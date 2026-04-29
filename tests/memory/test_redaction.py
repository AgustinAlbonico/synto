"""Tests for the redaction module."""

from synto.memory.redaction import redact_secrets, contains_secrets


def test_redact_openai_key():
    text = "Use key sk-abc123def456ghi789jkl012mno345 for the API"
    result = redact_secrets(text)
    assert "sk-abc" not in result
    assert "[REDACTED_API_KEY]" in result


def test_redact_github_token():
    text = "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
    result = redact_secrets(text)
    assert "ghp_" not in result or "REDACTED" in result


def test_redact_bearer_token():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123def456"
    result = redact_secrets(text)
    assert "eyJhbG" not in result
    assert "[REDACTED_TOKEN]" in result


def test_redact_password_equals():
    text = "DB_PASSWORD=supersecret123"
    result = redact_secrets(text)
    assert "supersecret" not in result
    assert "[REDACTED]" in result


def test_redact_password_colon():
    text = "password: mysecretvalue"
    result = redact_secrets(text)
    assert "mysecretvalue" not in result


def test_redact_api_key():
    text = 'api_key = "abcd1234efgh5678"'
    result = redact_secrets(text)
    assert "abcd1234" not in result


def test_redact_private_key():
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    result = redact_secrets(text)
    assert "BEGIN RSA" not in result
    assert "[REDACTED_PRIVATE_KEY]" in result


def test_redact_aws_key():
    text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
    result = redact_secrets(text)
    assert "AKIAIOSFODNN" not in result
    assert "[REDACTED_AWS_KEY]" in result


def test_no_secrets_unchanged():
    text = "The system uses SQLite for storage"
    result = redact_secrets(text)
    assert result == text


def test_contains_secrets_true():
    assert contains_secrets("password=secret123") is True
    assert contains_secrets("sk-abc123def456ghi789jkl012mno345") is True


def test_contains_secrets_false():
    assert contains_secrets("hello world normal text") is False


def test_multiple_secrets():
    text = "api_key=abc123 and password=xyz789"
    result = redact_secrets(text)
    assert "abc123" not in result
    assert "xyz789" not in result
    assert result.count("[REDACTED]") >= 1
