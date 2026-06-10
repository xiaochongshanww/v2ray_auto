"""Legacy compatibility module.

The destructive refactor moved runtime settings into environment variables and
`v2ray_auto.core.settings`. This file is intentionally kept credential-free so
old imports fail safely instead of exposing secrets.
"""

from v2ray_auto.core.settings import Settings, load_settings

__all__ = ["Settings", "load_settings"]
