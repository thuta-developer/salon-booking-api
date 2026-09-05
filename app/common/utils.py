"""Small shared utility helpers."""
import re


def slugify(value: str) -> str:
    """Convert arbitrary text into a URL-friendly slug."""
    if not value:
        return ""
    value = value.strip().lower()
    slug = re.sub(r"[^\w\-]+", "-", value)
    slug = re.sub(r"\-{2,}", "-", slug)
    return slug.strip("-")


def normalize_email(email: str) -> str:
    """Lower-case and strip an email address."""
    return (email or "").strip().lower()


def strip_optional(value):
    """Return stripped string or None for optional text inputs."""
    if value is None:
        return None
    value = value.strip()
    return value or None