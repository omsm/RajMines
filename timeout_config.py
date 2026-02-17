"""

Timeout Configuration Module for Weighbridge Automation System.

This module contains all timeout and timing constants that can be modified
without recompiling the executable. After building the EXE, copy this file
to the same directory as the executable to customize timeouts.

Modify these values based on your site-specific requirements:
- Entry/Exit timeouts: Adjust based on typical vehicle movement times
- Weight capture timeout: Adjust based on digitizer response time
- API timeouts: Adjust based on network/server response times
- Hardware timeouts: Adjust based on device communication speeds
- Safety delays: Adjust based on operational requirements

Version: 1.0.0
"""
__version__ = "1.0.0"

import logging
logger = logging.getLogger("weighbridge.timeout_config")

# Verification logging - confirms this file is loaded from external .py (not cached/bundled)

class TIMEOUTS:
    """All timeout values in seconds"""
    
    # Entry/Exit Timeouts
    ENTRY_TIMEOUT = 120  # Time to wait for vehicle to enter after RFID scan
    EXIT_TIMEOUT = 60  # Time to wait for vehicle to exit
    
    # Weight Capture Timeouts
    WEIGHT_CAPTURE_TIMEOUT = 300  # Max time for weight capture
    WEIGHT_STABLE_DELAY = 0.5  # Delay between weight readings
    
    # API Timeouts
    API_REQUEST_TIMEOUT = 180  # HTTP request timeout
    WEIGHT_VALIDATION_TIMEOUT = 60  # Time to wait for weight validation callback
    
    # Hardware Timeouts
    RFID_RECONNECT_DELAY = 5  # Delay before RFID reconnection attempt
    MODBUS_TIMEOUT = 2  # Modbus communication timeout
    SERIAL_TIMEOUT = 2  # Serial port timeout
    
    # Safety Delays
    POST_EXIT_DELAY = 5  # Wait after vehicle exits before reset
    SENSOR_DEBOUNCE = 0.1  # Sensor debounce time
    
    # RFID API Delay
    RFID_WAIT_TO_API_CALL = 10  # Wait time before making RFID API call


# Weight Constants
DEFAULT_STABLE_COUNT = 5  # Number of identical readings for stable weight
