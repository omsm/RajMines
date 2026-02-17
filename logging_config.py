"""
Logging Configuration Module for Weighbridge Automation System.

This module controls logging verbosity without rebuilding the executable.
After building the EXE, copy this file to the same directory as the executable
to customize logging levels.

Version: 1.0.0
"""
__version__ = "1.0.0"

import logging
CONSOLE_LOG_LEVEL = logging.DEBUG
FILE_LOG_LEVEL = logging.DEBUG
