"""
Deprecated legacy logging module.

This module is superseded by v2ray_auto.core.logger.
Kept for historical reference only.
"""

import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
