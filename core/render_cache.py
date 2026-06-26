import hashlib
import json
import os
import time
from functools import wraps
from io import BytesIO
from pathlib import Path

CACHE_DIR = Path("data/cache/cards")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TTL = 600  # 10 minutes


def _serialize(obj) -> str:
    """Convert arbitrary objects to a JSON-safe string for hashing."""
    if obj is None:
        return "null"
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    if isinstance(obj, str):
        return f'"{obj}"'
    if isinstance(obj, bytes):
        return f'"b:{hashlib.md5(obj).hexdigest()}"'
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(_serialize(item) for item in obj) + "]"
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda x: str(x[0]))
        return "{" + ",".join(f'"{k}":{_serialize(v)}' for k, v in items) + "}"
    if hasattr(obj, "__dict__"):
        return _serialize(obj.__dict__)
    if hasattr(obj, "keys"):
        return _serialize(dict(obj))
    return f'"repr:{repr(obj)[:100]}"'


def make_key(func_name: str, *args, **kwargs) -> str:
    """Generate a cache key from function name and arguments."""
    parts = [func_name]
    for arg in args:
        parts.append(_serialize(arg))
    for key in sorted(kwargs.keys()):
        parts.append(f"{key}={_serialize(kwargs[key])}")
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_cached(key: str) -> BytesIO | None:
    """Retrieve cached render result if it exists and is not expired."""
    cache_path = CACHE_DIR / f"{key}.png"
    meta_path = CACHE_DIR / f"{key}.meta"
    if not cache_path.exists() or not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text())
        if time.time() - meta.get("ts", 0) > DEFAULT_TTL:
            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            return None
        return BytesIO(cache_path.read_bytes())
    except Exception:
        return None


def set_cached(key: str, data: BytesIO) -> None:
    """Store render result in cache."""
    cache_path = CACHE_DIR / f"{key}.png"
    meta_path = CACHE_DIR / f"{key}.meta"
    try:
        data.seek(0)
        content = data.read()
        if not content:
            return
        cache_path.write_bytes(content)
        meta_path.write_text(json.dumps({"ts": time.time()}))
    except Exception:
        pass


def clear_expired() -> int:
    """Remove expired cache files. Returns count of removed files."""
    now = time.time()
    removed = 0
    for meta_path in CACHE_DIR.glob("*.meta"):
        try:
            meta = json.loads(meta_path.read_text())
            if now - meta.get("ts", 0) > DEFAULT_TTL:
                key = meta_path.stem
                (CACHE_DIR / f"{key}.png").unlink(missing_ok=True)
                meta_path.unlink()
                removed += 1
        except Exception:
            pass
    return removed


def cached_render(ttl: int = DEFAULT_TTL):
    """Decorator to cache render function results on disk."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = make_key(func.__name__, *args, **kwargs)
            cached = get_cached(key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            if isinstance(result, BytesIO):
                set_cached(key, result)
                result.seek(0)
            return result
        return wrapper
    return decorator