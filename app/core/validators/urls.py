from urllib.parse import urlparse


def validate_url(value: str) -> str:
    text = value if isinstance(value, str) else str(value)
    parsed = urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("must be a valid URL")
    return text
