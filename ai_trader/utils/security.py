"""Security utilities including API key encryption and rate limiting."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

from cryptography.fernet import Fernet


class SecureKeyManager:
    def __init__(self) -> None:
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key()
            logging.warning("Generated new encryption key. Set ENCRYPTION_KEY env var for production.")
        if isinstance(self.encryption_key, str):
            self.encryption_key = self.encryption_key.encode()
        self.cipher = Fernet(self.encryption_key)

    def encrypt_api_key(self, api_key: str) -> str:
        try:
            return self.cipher.encrypt(api_key.encode()).decode()
        except Exception as exc:  # noqa: BLE001
            logging.error("Encryption error: %s", exc)
            raise

    def decrypt_api_key(self, encrypted_key: str) -> str:
        try:
            return self.cipher.decrypt(encrypted_key.encode()).decode()
        except Exception as exc:  # noqa: BLE001
            logging.error("Decryption error: %s", exc)
            raise

    def get_secure_api_keys(self) -> dict:
        enc_key = os.getenv("BITGET_API_KEY_ENCRYPTED")
        enc_sec = os.getenv("BITGET_API_SECRET_ENCRYPTED")
        enc_pass = os.getenv("BITGET_API_PASSPHRASE_ENCRYPTED")
        if all([enc_key, enc_sec, enc_pass]):
            return {
                "api_key": self.decrypt_api_key(enc_key),
                "api_secret": self.decrypt_api_key(enc_sec),
                "passphrase": self.decrypt_api_key(enc_pass),
            }
        return {
            "api_key": os.getenv("BITGET_API_KEY"),
            "api_secret": os.getenv("BITGET_API_SECRET"),
            "passphrase": os.getenv("BITGET_API_PASSPHRASE"),
        }


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, half_open_max_calls: int = 3) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0

    def _should_attempt_reset(self) -> bool:
        return self.last_failure_time is not None and (time.time() - self.last_failure_time) > self.recovery_timeout

    def _on_success(self) -> None:
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logging.info("Circuit breaker: CLOSED state (recovered)")
        self.failure_count = 0

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logging.error("Circuit breaker: OPEN state (failures: %s)", self.failure_count)

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                logging.info("Circuit breaker: HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
        if self.state == "HALF_OPEN":
            if self.half_open_calls >= self.half_open_max_calls:
                raise Exception("Circuit breaker: HALF_OPEN max calls exceeded")
            self.half_open_calls += 1
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:  # noqa: BLE001
            self._on_failure()
            raise

    def get_state(self) -> dict:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "half_open_calls": self.half_open_calls,
        }


class RateLimiter:
    def __init__(self, max_calls_per_minute: int = 60) -> None:
        self.max_calls_per_minute = max_calls_per_minute
        self.calls: defaultdict[str, list[datetime]] = defaultdict(list)

    def is_allowed(self, identifier: str = "default") -> bool:
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        self.calls[identifier] = [t for t in self.calls[identifier] if t > minute_ago]
        if len(self.calls[identifier]) >= self.max_calls_per_minute:
            return False
        self.calls[identifier].append(now)
        return True

    def wait_time(self, identifier: str = "default") -> float:
        if not self.calls[identifier]:
            return 0
        oldest = min(self.calls[identifier])
        wait_until = oldest + timedelta(minutes=1)
        now = datetime.utcnow()
        if wait_until > now:
            return (wait_until - now).total_seconds()
        return 0


def rate_limited(max_calls_per_minute: int = 60):
    limiter = RateLimiter(max_calls_per_minute)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ident = func.__name__
            if not limiter.is_allowed(ident):
                wt = limiter.wait_time(ident)
                raise Exception(f"Rate limit exceeded. Wait {wt:.1f} seconds")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
    breaker = CircuitBreaker(failure_threshold, recovery_timeout)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


class BitgetSigner:
    def __init__(self, api_key: str, api_secret: str, api_passphrase: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase

    def sign_request(self, method: str, request_path: str, params: dict | None = None, body: str | None = None) -> dict:
        timestamp = str(int(time.time() * 1000))
        if params:
            query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            request_path = f"{request_path}?{query}"
        body_str = body or ""
        message = f"{timestamp}{method.upper()}{request_path}{body_str}"
        signature = base64.b64encode(hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).digest()).decode()
        headers = {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.api_passphrase,
            "Content-Type": "application/json",
            "User-Agent": "AI-Trader-v2/1.0",
        }
        logging.debug("Request signed: %s %s...", method, request_path[:50])
        return headers

    def validate_response(self, response: dict) -> bool:
        if not response or not isinstance(response, dict):
            raise ValueError("Invalid response format")
        if "code" not in response:
            raise ValueError("Response missing code field")
        if response["code"] != "00000":
            msg = response.get("msg", "Unknown API error")
            raise Exception(f"API Error [{response['code']}]: {msg}")
        return True


class SecurityAuditor:
    def __init__(self) -> None:
        self.security_events: list[dict] = []

    def log_security_event(self, event_type: str, details: str, severity: str = "INFO") -> None:
        event = {
            "timestamp": datetime.utcnow(),
            "type": event_type,
            "details": details,
            "severity": severity,
        }
        self.security_events.append(event)
        if severity == "CRITICAL":
            logging.critical("SECURITY: %s - %s", event_type, details)
        elif severity == "WARNING":
            logging.warning("SECURITY: %s - %s", event_type, details)
        else:
            logging.info("SECURITY: %s - %s", event_type, details)

    def check_api_key_exposure(self, text: str) -> bool:
        patterns = [r"[A-Za-z0-9]{32,}", r"sk-[A-Za-z0-9]+", r"xoxb-[A-Za-z0-9]+"]
        for pattern in patterns:
            if re.search(pattern, text):
                self.log_security_event("POTENTIAL_KEY_EXPOSURE", "Sensitive pattern detected", "WARNING")
                return True
        return False

    def get_security_report(self) -> str:
        if not self.security_events:
            return "No security events recorded"
        events_by_sev: defaultdict[str, int] = defaultdict(int)
        for event in self.security_events:
            events_by_sev[event["severity"]] += 1
        report = (
            "\n=== SECURITY AUDIT REPORT ===\n"
            f"Total Events: {len(self.security_events)}\n"
            f"Critical: {events_by_sev['CRITICAL']}\n"
            f"Warnings: {events_by_sev['WARNING']}\n"
            f"Info: {events_by_sev['INFO']}\n\n"
            "Recent Events:\n"
        )
        for event in self.security_events[-5:]:
            report += f"[{event['timestamp']}] {event['severity']}: {event['type']}\n"
        return report


def auth_headers(method: str, endpoint: str, params: str = "", api_key: str | None = None, api_secret: str | None = None, passphrase: str | None = None) -> dict:
    """Compatibility wrapper returning signed headers for Bitget."""
    manager = SecureKeyManager()
    keys = manager.get_secure_api_keys()
    signer = BitgetSigner(api_key or keys["api_key"], api_secret or keys["api_secret"], passphrase or keys["passphrase"])
    return signer.sign_request(method, endpoint, params=None if not params else dict(p.split("=") for p in params.split("&")))
