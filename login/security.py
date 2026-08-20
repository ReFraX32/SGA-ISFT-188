from hashlib import sha256
from django.conf import settings
from django.core.cache import cache


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or 'unknown'


def normalize_username(username):
    return (username or '').strip().lower()[:150]


def get_attempt_key(request, username):
    raw_key = f'{get_client_ip(request)}:{normalize_username(username)}'
    digest = sha256(raw_key.encode('utf-8')).hexdigest()
    return f'login:login_attempts:{digest}'


def max_attempts():
    return int(getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5))


def lockout_seconds():
    return int(getattr(settings, 'LOGIN_LOCKOUT_SECONDS', 300))


def is_login_limited(request, username):
    attempts = cache.get(get_attempt_key(request, username), 0)
    return attempts >= max_attempts()


def register_failed_login(request, username):
    key = get_attempt_key(request, username)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=lockout_seconds())
    return attempts


def clear_failed_logins(request, username):
    cache.delete(get_attempt_key(request, username))
