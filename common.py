"""
Deprecated legacy compatibility module.

This module is kept only for old scripts that still import from it.
New code should import directly from v2ray_auto.core.* modules.
"""

import base64
import json
import os
import random
import socket
import subprocess
import uuid

import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.header import Header
