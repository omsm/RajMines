"""
Data Conversion Module for Weighbridge Automation System.

This module handles site-specific data conversion for RFID and Digitizer.
Modify these classes based on the specific hardware at each client site.

When debugging new hardware:
1. Run the application and observe raw data in logs
2. Modify the conversion methods to parse the specific format
3. Test and verify the output

RFID_Convert: Converts raw RFID data to 24-char hex string
Digitizer_Convert: Converts raw serial data to weight in KGs

Version: 1.0.0
"""
__version__ = "1.0.0"

import logging
import re
from typing import Optional, List

logger = logging.getLogger("weighbridge.conversion")


class RFID_Convert:
    """
    RFID Data Conversion Class.
    
    Converts raw RFID data from the reader to a standardized format.
    
    Modify this class based on the specific RFID reader at the client site.
    
    Usage:
        converter = RFID_Convert()
        rfid = converter.convert(raw_bytes)
        # Returns: "E200001234567890ABCDEF12" or None if invalid
    
    Debugging Steps:
        1. Enable debug logging to see raw data
        2. Check the format of raw_data in logs
        3. Modify convert() method to parse your specific format
        4. Test with actual RFID cards
    """
    
    def __init__(self):
        """Initialize RFID converter"""
        self._last_raw_data: bytes = b""
        self._last_converted: str = ""
        logger.debug("RFID_Convert initialized")
    
    def convert(self, raw_data: bytes) -> Optional[str]:
        """
        Convert raw RFID data to 24-character hex string.
        
        This is the main conversion method. Modify this based on your RFID reader format.
        
        Args:
            raw_data: Raw bytes received from RFID reader socket
            
        Returns:
            24-character hex string (e.g., "E200001234567890ABCDEF12")
            or None if conversion fails
        
        Common RFID Formats:
            - Binary with E2 prefix (UHF ISO 18000-6C)
            - STX/ETX framed ASCII
            - Plain ASCII hex string
            - Custom vendor format
        """
        # Store for debugging
        self._last_raw_data = raw_data
        
        # Log raw data for debugging (INFO level so it shows in console)
        logger.debug(f"RFID raw data received - Hex: {raw_data.hex()}, Length: {len(raw_data)} bytes")
        
        try:
            # Try to decode as string for logging
            try:
                raw_str = raw_data.decode('ascii', errors='replace')
                logger.debug(f"RFID raw data (ascii): {raw_str}")
            except:
                pass
            
            # =================================================================
            # CONVERSION LOGIC - SUPPORTS MULTIPLE RFID READER FORMATS
            # =================================================================
            # 
            # Supported Readers:
            # - Identium IDS-002: Header (36 chars) + RFID (24 chars) + Suffix (2 chars)
            # - Zebra: Direct 24/32 char hex output
            # - Secureye: Direct 24/32 char hex output
            # - Generic UHF readers with E2 prefix
            #
            # RFID Tag Formats:
            # - 96-bit  = 24 hex chars = 12 bytes (most common)
            # - 128-bit = 32 hex chars = 16 bytes
            # =================================================================
            
            rfid = None
            
            # Check if raw_data is already an ASCII hex string (common for some readers)
            # If so, use it directly; otherwise convert bytes to hex
            try:
                # Try to decode as ASCII - if successful and looks like hex, use it directly
                ascii_str = raw_data.decode('ascii', errors='strict').strip()
                # Remove any whitespace, CRLF, etc.
                ascii_str = ascii_str.replace('\r', '').replace('\n', '').replace(' ', '').replace('\t', '')
                # Check if it's a valid hex string (24 or 32 chars, or longer with valid hex)
                if all(c in '0123456789ABCDEFabcdef' for c in ascii_str):
                    if len(ascii_str) == 24:
                        # Perfect 24-char hex string - use it directly
                        hex_str = ascii_str.upper()
                    elif len(ascii_str) == 32:
                        # 32-char hex string - use it directly
                        hex_str = ascii_str.upper()
                    elif len(ascii_str) > 24:
                        # Longer than expected - try to extract 24-char RFID
                        # Some readers might send RFID with extra characters
                        # Look for a 24-char sequence that looks like RFID
                        hex_chars_only = ''.join(c for c in ascii_str if c in '0123456789ABCDEFabcdef')
                        if len(hex_chars_only) >= 24:
                            # Take first 24 chars of valid hex
                            hex_str = hex_chars_only[:24].upper()
                        else:
                            # Not enough hex chars, convert bytes to hex
                            hex_str = raw_data.hex().upper()
                    else:
                        # Too short, convert bytes to hex
                        hex_str = raw_data.hex().upper()
                else:
                    # Not a valid hex string, convert bytes to hex
                    hex_str = raw_data.hex().upper()
            except (UnicodeDecodeError, AttributeError):
                # Not ASCII, convert bytes to hex
                hex_str = raw_data.hex().upper()
            
            logger.debug(f"Processing hex string: {hex_str} (length: {len(hex_str)} chars)")
            
            # -----------------------------------------------------------------
            # FORMAT 1: Identium Reader Format
            # -----------------------------------------------------------------
            # Pattern: FF0100140300000000003000010101XX050C + RFID(24) + 00
            # Header is 36 chars, RFID starts at position 36
            # Examples:
            #   ff0100140300000000003000010101e3050ce200001d7507013115006bb900
            #   ff0100140300000000003000010101cf050c34161fa820328ee8303efaa000
            
            if hex_str.startswith('FF01') and len(hex_str) >= 62:
                # Identium format detected
                # Extract RFID from position 36, take 24 chars (96-bit)
                rfid = hex_str[36:60]
                logger.debug(f"RFID decoded [Identium FF01 format]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 1B: CF Prefix Reader Format (26 bytes total)
            # -----------------------------------------------------------------
            # Pattern: CF 00 00 01 12 00 FD XX 01 00 0C + RFID(12 bytes) + Checksum(2 bytes)
            # Header is 22 hex chars (11 bytes), RFID starts at position 22
            # Total = 52 hex chars (26 bytes)
            # Examples:
            #   cf0000011200fd3a01000ce28069950000400a8f3981330a1d
            #   cf0000011200fd9e01000ce28069950000400a8f398133Mk
            
            elif hex_str.startswith('CF') and len(hex_str) >= 46:
                # CF prefix format detected
                # Header: 11 bytes = 22 hex chars
                # RFID: 12 bytes = 24 hex chars (position 22-46)
                # Suffix: 2 bytes = 4 hex chars (checksum)
                rfid = hex_str[22:46]
                logger.debug(f"RFID decoded [CF prefix format]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 1C: 11 00 EE 00 FE Prefix Reader Format (18 bytes total)
            # -----------------------------------------------------------------
            # Pattern: 11 00 EE 00 FE + RFID(12 bytes) + Checksum(2 bytes)
            # Header is 10 hex chars (5 bytes), RFID starts at position 10
            # Total = 36 hex chars (18 bytes)
            # Example: 1100EE00FED7383354314CBA00001590A284
            #          |--header(10)--||----RFID(24)-----||suffix(4)|
            
            elif hex_str.startswith('1100EE00FE') and len(hex_str) >= 34:
                # 11 00 EE 00 FE prefix format detected (variant 1: with FE)
                # Header: 5 bytes = 10 hex chars (1100EE00FE)
                # RFID: 12 bytes = 24 hex chars (position 10-34)
                # Suffix: 2 bytes = 4 hex chars (checksum)
                rfid = hex_str[10:34]
                logger.debug(f"RFID decoded [11 00 EE 00 FE prefix format]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 1C2: 11 00 EE 00 Prefix Reader Format (17-18 bytes total)
            # -----------------------------------------------------------------
            # Pattern: 11 00 EE 00 + RFID(12 bytes) + Checksum(1-2 bytes)
            # Header is 8 hex chars (4 bytes), RFID starts at position 8
            # Total = 34 hex chars (17 bytes) or 36 hex chars (18 bytes)
            # Example: 1100EE0034161FA820328EE82AAE5D600AEC
            #          |--header(8)--||----RFID(24)-----||suffix(2)|
            # RFID: 34161FA820328EE82AAE5D600A (removing prefix 1100EE00 and suffix EC)
            
            elif hex_str.startswith('1100EE00') and len(hex_str) >= 32:
                # 11 00 EE 00 prefix format detected (variant 2: without FE)
                # Header: 4 bytes = 8 hex chars (1100EE00)
                # RFID: 12 bytes = 24 hex chars (position 8-32)
                # Suffix: 1-2 bytes = 2-4 hex chars (checksum, e.g., EC)
                rfid = hex_str[8:32]
                logger.debug(f"RFID decoded [11 00 EE 00 prefix format]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 1D: FastTag Format (CCFFFF prefix, 25 bytes total)
            # -----------------------------------------------------------------
            # Pattern: CC FF FF XX XX XX XX XX XX + RFID(12 bytes) + Checksum(4 bytes)
            # Header is 18 hex chars (9 bytes), RFID starts at position 18
            # Total = 50 hex chars (25 bytes)
            # Example: CCFFFF20051200340034161FA820328A522B629740A704B6C7
            #          |--header(18)--||----RFID(24)-----||suffix(8)|
            # RFID: 34161FA820328A522B629740
            # 
            # Variant: CCFFFF with E2-prefixed RFID tag
            # Example: CCFFFF200512003400E28011700000021B09926B1705CCBA23
            #          |--header(18)--||----RFID(24)-----||suffix(8)|
            # RFID: E28011700000021B09926B17
            
            elif hex_str.startswith('CCFFFF') and len(hex_str) >= 24:
                # FastTag format detected - try multiple extraction methods
                rfid_extracted = False
                
                # Method 1: Look for E2-prefixed RFID tag (EPC Gen2 indicator)
                # This is more reliable as E2 is a standard prefix for UHF tags
                e2_pos = hex_str.find('E2', 6)  # Search after CCFFFF (6 hex chars)
                if e2_pos >= 6 and e2_pos + 24 <= len(hex_str):
                    # Found E2 tag, extract 24 hex chars starting from E2
                    rfid = hex_str[e2_pos:e2_pos+24]
                    logger.debug(f"RFID decoded [FastTag CCFFFF format, E2 at pos {e2_pos}]: {rfid}")
                    rfid_extracted = True
                
                # Method 2: Standard format (9-byte header, RFID at position 18)
                # Use this if E2 not found or if we want to try standard position
                if not rfid_extracted and len(hex_str) >= 42:
                    # Standard FastTag format: CCFFFF + 6 bytes header + 12 bytes RFID + 4 bytes suffix
                    rfid = hex_str[18:42]
                    logger.debug(f"RFID decoded [FastTag CCFFFF format, standard position 18]: {rfid}")
                    rfid_extracted = True
                
                # Method 3: Try to extract any 24-char sequence that looks valid
                if not rfid_extracted and len(hex_str) >= 30:
                    # Try position 18 even if total length is less than 42
                    if len(hex_str) >= 42:
                        rfid = hex_str[18:42]
                        logger.debug(f"RFID decoded [FastTag CCFFFF format, fallback]: {rfid}")
                    else:
                        # Extract available data from position 18, pad if needed
                        available = hex_str[18:]
                        if len(available) >= 24:
                            rfid = available[:24]
                            logger.debug(f"RFID decoded [FastTag CCFFFF format, partial]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 2: Direct output with E2 prefix (EPC Gen2 tags)
            # -----------------------------------------------------------------
            # Used by: Zebra, Secureye, and many other readers
            # Pattern: E2XXXXXXXXXXXXXXXXXXXXXX (24 chars for 96-bit)
            # Example: e200001d7507013115006bb9
            # Note: Some readers may send the tag twice (48 chars), extract only first 24
            
            elif hex_str.startswith('E2') and len(hex_str) >= 24:
                # Direct EPC Gen2 tag
                # Check if tag is duplicated (e.g., "E200001D...E200001D...")
                if len(hex_str) >= 48:
                    # Likely duplicated tag - check if first 24 chars repeat
                    first_24 = hex_str[:24]
                    second_24 = hex_str[24:48] if len(hex_str) >= 48 else ""
                    if second_24 == first_24:
                        # Tag is duplicated, take only first 24 chars
                        rfid = first_24
                        logger.debug(f"RFID decoded [EPC Gen2 96-bit, duplicated tag filtered]: {rfid}")
                    else:
                        # Not duplicated, might be 128-bit or concatenated data
                        rfid = hex_str[:24]  # Take first 24 for 96-bit
                        logger.debug(f"RFID decoded [EPC Gen2 96-bit, long data]: {rfid}")
                elif len(hex_str) >= 32:
                    rfid = hex_str[:32]  # 128-bit
                    logger.debug(f"RFID decoded [EPC Gen2 128-bit]: {rfid}")
                else:
                    rfid = hex_str[:24]  # 96-bit
                    logger.debug(f"RFID decoded [EPC Gen2 96-bit]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 3: Direct output without E2 prefix (proprietary tags)
            # -----------------------------------------------------------------
            # Used by: Some readers output raw tag data
            # Pattern: XXXXXXXXXXXXXXXXXXXXXXXX (24 chars for 96-bit)
            # Example: 34161fa820328ee8303efaa0
            
            elif len(hex_str) == 24 and all(c in '0123456789ABCDEF' for c in hex_str):
                # Exactly 24 hex chars - likely 96-bit direct output
                rfid = hex_str
                logger.debug(f"RFID decoded [Direct 96-bit]: {rfid}")
            
            elif len(hex_str) == 32 and all(c in '0123456789ABCDEF' for c in hex_str):
                # Exactly 32 hex chars - likely 128-bit direct output
                rfid = hex_str
                logger.debug(f"RFID decoded [Direct 128-bit]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 4: Find E2 prefix anywhere in the data
            # -----------------------------------------------------------------
            # Some readers add prefix/suffix around the E2 tag
            
            elif rfid is None:
                e2_pos = hex_str.find('E2')
                if e2_pos >= 0 and len(hex_str) - e2_pos >= 24:
                    rfid_portion = hex_str[e2_pos:]
                    
                    # Check if tag is duplicated (e.g., "E200001D...E200001D...")
                    if len(rfid_portion) >= 48:
                        first_24 = rfid_portion[:24]
                        second_24 = rfid_portion[24:48] if len(rfid_portion) >= 48 else ""
                        if second_24 == first_24:
                            # Tag is duplicated, take only first 24 chars
                            rfid = first_24
                            logger.debug(f"RFID decoded [E2 found at pos {e2_pos}, duplicated tag filtered]: {rfid}")
                        else:
                            # Not duplicated, extract normally (prefer 96-bit = 24 chars)
                            rfid = rfid_portion[:24]
                    elif len(rfid_portion) >= 32:
                        rfid = rfid_portion[:32]  # 128-bit
                    else:
                        rfid = rfid_portion[:24]  # 96-bit
                    logger.debug(f"RFID decoded [E2 found at pos {e2_pos}]: {rfid}")
            
            # -----------------------------------------------------------------
            # FORMAT 5: STX/ETX framed (0x02 = STX, 0x03 = ETX)
            # -----------------------------------------------------------------
            
            if rfid is None and (b'\x02' in raw_data or b'\x03' in raw_data):
                stx_pos = raw_data.find(b'\x02')
                etx_pos = raw_data.find(b'\x03')
                if etx_pos > stx_pos and stx_pos >= 0:
                    content = raw_data[stx_pos + 1:etx_pos]
                    try:
                        # Remove any CRLF or whitespace
                        ascii_str = content.decode('ascii').strip().replace('\r', '').replace('\n', '')
                        if len(ascii_str) >= 24 and all(c in '0123456789ABCDEFabcdef' for c in ascii_str):
                            # Support 24, 26, or 32 char RFIDs
                            if len(ascii_str) >= 32:
                                rfid = ascii_str[:32].upper()
                            elif len(ascii_str) >= 26:
                                rfid = ascii_str[:26].upper()  # Some readers output 26 chars
                            else:
                                rfid = ascii_str[:24].upper()
                            logger.debug(f"RFID decoded [STX/ETX framed]: {rfid}")
                    except:
                        pass
            
            # -----------------------------------------------------------------
            # FORMAT 6: ASCII hex string with delimiters
            # -----------------------------------------------------------------
            
            if rfid is None:
                try:
                    ascii_str = raw_data.decode('ascii', errors='ignore').strip()
                    ascii_str = ascii_str.replace('\r', '').replace('\n', '').replace(' ', '')
                    hex_chars = ''.join(c for c in ascii_str if c in '0123456789ABCDEFabcdef').upper()
                    
                    if len(hex_chars) >= 24:
                        # Check for E2 prefix
                        e2_pos = hex_chars.find('E2')
                        if e2_pos >= 0:
                            rfid_portion = hex_chars[e2_pos:]
                            
                            # Check if tag is duplicated
                            if len(rfid_portion) >= 48:
                                first_24 = rfid_portion[:24]
                                second_24 = rfid_portion[24:48] if len(rfid_portion) >= 48 else ""
                                if second_24 == first_24:
                                    # Tag is duplicated, take only first 24 chars
                                    rfid = first_24
                                else:
                                    # Not duplicated, extract normally
                                    rfid = rfid_portion[:24] if len(rfid_portion) < 32 else rfid_portion[:32]
                            else:
                                rfid = rfid_portion[:24] if len(rfid_portion) < 32 else rfid_portion[:32]
                        else:
                            # No E2 prefix, take first 24 or 32 chars
                            rfid = hex_chars[:24] if len(hex_chars) < 32 else hex_chars[:32]
                        logger.debug(f"RFID decoded [ASCII hex]: {rfid}")
                except:
                    pass
            
            # -----------------------------------------------------------------
            # FORMAT 7: Fallback - extract any 24+ hex chars
            # -----------------------------------------------------------------
            
            if rfid is None and len(hex_str) >= 24:
                # Last resort: take first 24 chars if valid hex
                rfid = hex_str[:24]
                logger.warning(f"RFID decoded [Fallback]: {rfid}")
            
            # =================================================================
            # END OF CONVERSION LOGIC
            # =================================================================
            
            # Validate result (support both 96-bit/24-char and 128-bit/32-char)
            if rfid and len(rfid) in (24, 32) and all(c in '0123456789ABCDEF' for c in rfid):
                self._last_converted = rfid
                bits = len(rfid) * 4
                logger.debug(f"RFID validated: {rfid} ({bits}-bit)")
                return rfid
            elif rfid:
                # RFID found but wrong length - log for debugging
                logger.warning(f"RFID invalid length ({len(rfid)} chars): {rfid}")
                logger.warning(f"Raw data was: {raw_data.hex()}")
                return None
            else:
                logger.warning(f"RFID conversion failed. Raw data: {raw_data.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"RFID conversion error: {e}")
            logger.error(f"Raw data that caused error: {raw_data.hex()}")
            return None
    
    def get_last_raw_data(self) -> bytes:
        """Get the last raw data received (for debugging)"""
        return self._last_raw_data
    
    def get_last_converted(self) -> str:
        """Get the last successfully converted RFID"""
        return self._last_converted
    
    def debug_print(self, raw_data: bytes) -> None:
        """
        Print detailed debug information about raw data.
        
        Call this method to analyze unknown RFID data formats.
        """
        # print("\n" + "=" * 60)
        # print("RFID DEBUG INFORMATION")
        # print("=" * 60)
        # print(f"Raw bytes length: {len(raw_data)}")
        # print(f"Raw bytes (hex): {raw_data.hex()}")
        # print(f"Raw bytes (repr): {repr(raw_data)}")
        
        # try:
        #     print(f"ASCII decode: {raw_data.decode('ascii', errors='replace')}")
        # except:
        #     print("ASCII decode: Failed")
        
        # try:
        #     print(f"UTF-8 decode: {raw_data.decode('utf-8', errors='replace')}")
        # except:
        #     print("UTF-8 decode: Failed")
        
        # print("\nByte-by-byte breakdown:")
        for i, b in enumerate(raw_data):
            char_repr = chr(b) if 32 <= b <= 126 else '.'
            # print(f"  [{i:3d}] 0x{b:02X} ({b:3d}) '{char_repr}'")
        
        # print("=" * 60 + "\n")


class Digitizer_Convert:
    """
    Digitizer (Weight Scale) Data Conversion Class.
    
    Converts raw serial data from digitizer to weight in KGs.
    
    Modify this class based on the specific digitizer at the client site.
    
    Usage:
        converter = Digitizer_Convert()
        weight = converter.convert(raw_bytes)
        # Returns: 30000 (weight in kg) or None if invalid
    
    Debugging Steps:
        1. Enable debug logging to see raw data
        2. Check the format of raw_data in logs
        3. Modify convert() method to parse your specific format
        4. Test with actual weight readings
    
    Common Digitizer Formats:
        - STX + data + ETX + CR/LF
        - Plain ASCII with spaces
        - Fixed-width numeric fields
        - Character-by-character streaming
    """
    
    def __init__(self):
        """Initialize Digitizer converter"""
        self._buffer: str = ""  # Buffer for accumulating character-by-character data
        self._raw_buffer: bytes = b""  # Buffer for accumulating raw bytes until we find "Wt:"
        self._last_raw_data: bytes = b""
        self._last_weight: Optional[float] = None
        logger.debug("Digitizer_Convert initialized")
    
    
    def convert(self, raw_data: bytes) -> Optional[float]:
        """
        Convert raw digitizer data to weight in KGs.
        
        This is the main conversion method. Modify this based on your digitizer format.
        
        Args:
            raw_data: Raw bytes received from serial port
            
        Returns:
            Weight in KG as float (e.g., 30000.0)
            or None if conversion fails
        
        Common Digitizer Formats:
            - STX (0x02) + space + digits + ETX (0x03) + CR/LF
            - Plain ASCII: "  12345" (space-padded)
            - Continuous stream: one character at a time
        """
        # Store for debugging
        self._last_raw_data = raw_data
        
        # Log raw data for debugging
        # Show first 50 hex chars to avoid flooding
        # hex_preview = raw_data.hex()[:50] + "..." if len(raw_data) > 25 else raw_data.hex()
        # logger.debug(f"Digitizer raw data - Hex: {hex_preview}, Length: {len(raw_data)} bytes")  # Removed to reduce log spam
        
        try:
            # Try to decode as string for logging
            try:
                raw_str = raw_data.decode('ascii', errors='replace')
                # Show control characters clearly for debugging
                visible_str = ""
                for c in raw_str:
                    if ord(c) == 0x02:
                        visible_str += "<STX>"
                    elif ord(c) == 0x03:
                        visible_str += "<ETX>"
                    elif ord(c) == 0x0D:
                        visible_str += "<CR>"
                    elif ord(c) == 0x0A:
                        visible_str += "<LF>"
                    elif ord(c) == 0x20:
                        visible_str += " "  # Space
                    elif ord(c) < 32:
                        visible_str += f"<{ord(c):02X}>"
                    else:
                        visible_str += c
                logger.debug(f"Digitizer raw data: '{visible_str}' (hex: {raw_data.hex()[:60]}...)")
            except:
                logger.debug(f"Digitizer raw data (hex): {raw_data.hex()[:60]}...")
            
            # =================================================================
            # CONVERSION LOGIC - MODIFY THIS SECTION FOR YOUR DIGITIZER
            # =================================================================
            
            weight = None
            
            # First, decode to string
            try:
                text = raw_data.decode('ascii', errors='ignore')
            except:
                text = ""
            
            # Method 7: Bracketed format - CHECK THIS FIRST (highest priority)
            # Format: [000000][000000][000000]... (multiple weight readings in brackets, single line)
            # Examples:
            #   "[000000][000000][000000][000000][000000]" -> extract "0" (0kg)
            #   "[000080][000080][000080][000080][000080]" -> extract "80" (80g = 0.08kg)
            # Pattern: [digits] repeated multiple times, extract the last (most recent) value
            if weight is None:
                # Find all bracketed values: [digits]
                bracket_matches = re.findall(r'\[(\d+)\]', text)
                if bracket_matches:
                    # Use the last (most recent) bracketed value
                    # All values should be the same, but use last one to be safe
                    weight_str = bracket_matches[-1]
                    weight = float(weight_str)  # Convert grams to kg (000080 = 80g = 0.08kg)
                    logger.info(f"Weight decoded via bracketed format (PRIORITY): {weight} kg from '[{weight_str}]' (found {len(bracket_matches)} brackets, using last)")
            
            # Method 6: "kg" format - CHECK THIS SECOND
            # Format: {spaces}{number} kg    G 000000 A
            # Examples:
            #   "     20 kg    G 000000 A" -> extract "20"
            #   "     00 kg    G 000000 A" -> extract "0"
            #   "    -40 kg    G 000000 A" -> extract "-40"
            # Pattern: optional spaces, optional minus sign, digits, space, "kg"
            if weight is None:
                # Try to find pattern: {spaces}{optional_sign}{digits} kg
                match = re.search(r'([+-]?\d+)\s+kg', text)
                if match:
                    weight = float(match.group(1))
                    logger.debug(f"Weight decoded via 'kg' format (PRIORITY): {weight} kg from '{match.group(0)}'")
            
            # Method 5: Wt: format - CHECK THIS SECOND
            # Format: Wt:     {spaces}{weight_digits}{non-digit}Wt:...
            # Examples:
            #   "Wt:  58940♥0⚠Wt:" -> extract "58940" (stop at ♥)
            #   "Wt:     50G0GWt:" -> extract "50" (stop at G)
            # Logic:
            #   1. Accumulate data in buffer until we find "Wt:"
            #   2. After "Wt:" (after the colon), skip spaces
            #   3. Extract all consecutive digits until first non-digit (like ♥, G, etc.)
            #   4. Return the weight as-is (no auto-division)
            
            # Add current data to buffer
            self._raw_buffer += raw_data
            
            # Limit buffer size to prevent memory issues (keep last 200 bytes to handle multiple Wt: patterns)
            if len(self._raw_buffer) > 200:
                self._raw_buffer = self._raw_buffer[-200:]
            
            # Find the LAST "Wt:" in the buffer (most recent reading)
            # Check if "Wt:" exists in the accumulated buffer (case insensitive)
            wt_pattern = b'Wt:'
            wt_pos = -1
            search_pos = 0
            # Find the last occurrence of "Wt:"
            while True:
                pos = self._raw_buffer.find(wt_pattern, search_pos)
                if pos == -1:
                    break
                wt_pos = pos
                search_pos = pos + 1
            
            # If not found, try lowercase
            if wt_pos == -1:
                wt_pattern = b'wt:'
                search_pos = 0
                while True:
                    pos = self._raw_buffer.find(wt_pattern, search_pos)
                    if pos == -1:
                        break
                    wt_pos = pos
                    search_pos = pos + 1
            
            if wt_pos >= 0:
                # Found "Wt:", now read after the colon
                # Position after "Wt:" is wt_pos + 3 (W, t, :)
                after_colon_pos = wt_pos + 3
                
                if after_colon_pos < len(self._raw_buffer):
                    # Extract portion after "Wt:"
                    after_wt = self._raw_buffer[after_colon_pos:]
                    
                    # Decode to string (control characters will be handled)
                    after_str = after_wt.decode('ascii', errors='ignore')
                    
                    # Skip ONLY spaces at the start (not tabs, newlines, etc.)
                    # Find the first non-space character
                    start_idx = 0
                    while start_idx < len(after_str) and after_str[start_idx] == ' ':
                        start_idx += 1
                    
                    # Now extract all consecutive digits from this position
                    weight_digits = ""
                    found_separator = False
                    for i in range(start_idx, len(after_str)):
                        char = after_str[i]
                        if char.isdigit():
                            weight_digits += char
                        else:
                            # Stop at first non-digit character (could be ♥, G, space, letter, symbol, etc.)
                            found_separator = True
                            break
                    
                    # Only extract if we have digits AND we found a non-digit separator after them
                    # This ensures we have the complete number (e.g., "5950♥" not just "595")
                    # Exception: if there's another "Wt:" pattern after this one, it means this reading is complete
                    if weight_digits and found_separator:
                        # Convert to float and return as-is (no auto-division)
                        weight = float(weight_digits)
                        logger.debug(f"Weight decoded via Wt: format (PRIORITY): {weight} kg from '{weight_digits}' (raw after colon: {repr(after_str[:40])})")
                        
                        # Clear buffer after successful extraction (keep last 30 bytes in case next "Wt:" starts soon)
                        if len(self._raw_buffer) > 30:
                            # Keep last 30 bytes to handle cases where next "Wt:" might be starting
                            self._raw_buffer = self._raw_buffer[-30:]
                        else:
                            # If buffer is small, clear it completely
                            self._raw_buffer = b""
                    elif weight_digits and not found_separator:
                        # We have digits but no separator - might be incomplete (e.g., "595" when "5950" is coming)
                        # Check if there's another "Wt:" pattern after this one (indicating this reading is complete)
                        next_wt_pos = self._raw_buffer.find(wt_pattern, wt_pos + 1)
                        if next_wt_pos >= 0:
                            # There's another "Wt:" after this one, so this reading is complete
                            # Extract the digits we have
                            weight = float(weight_digits)
                            logger.debug(f"Weight decoded via Wt: format (PRIORITY): {weight} kg from '{weight_digits}' (no separator but next Wt: found, raw: {repr(after_str[:40])})")
                            
                            # Clear buffer after successful extraction
                            if len(self._raw_buffer) > 30:
                                self._raw_buffer = self._raw_buffer[-30:]
                            else:
                                self._raw_buffer = b""
                        # else: don't extract yet, wait for more data or separator
            
            # Method 1: STX/ETX framed data (only if Method 5 didn't find "Wt:")
            # Format: STX (0x02) + data + ETX (0x03)
            # Also handles:
            #   - STX STX + spaces + digits (e.g., "\x02\x02 0049510")
            #   - spaces + digits + STX STX (e.g., " 0044050\x02\x02" or "0000050\x02\x02")
            # Check both raw_data and buffer to handle fragmented reads
            if weight is None and (b'\x02' in raw_data or b'\x02' in self._raw_buffer or b'\x03' in raw_data or b'\x03' in self._raw_buffer):
                logger.debug(f"STX pattern detected - raw_data length: {len(raw_data)}, buffer length: {len(self._raw_buffer)}, raw_data hex: {raw_data.hex()[:40]}")
                # First, check the buffer (accumulated data) for complete patterns
                # This handles cases where data comes in fragments
                buffer_to_check = self._raw_buffer if len(self._raw_buffer) > len(raw_data) else raw_data
                
                # Check for STX at the beginning: STX STX + spaces + digits (e.g., "\x02\x02 0049510")
                if buffer_to_check.startswith(b'\x02'):
                    # Count consecutive STX characters
                    stx_count = 0
                    pos = 0
                    while pos < len(buffer_to_check) and buffer_to_check[pos] == 0x02:
                        stx_count += 1
                        pos += 1
                    
                    # Skip spaces after STX
                    while pos < len(buffer_to_check) and buffer_to_check[pos] in (0x20, 0x00):  # Space or null
                        pos += 1
                    
                    # Extract digits from this position
                    if pos < len(buffer_to_check):
                        remaining = buffer_to_check[pos:]
                        try:
                            remaining_str = remaining.decode('ascii', errors='ignore')
                            # Match digits (with optional leading zeros, e.g., "0049510" -> 49510)
                            # Stop at first non-digit (like STX character)
                            digit_match = re.match(r'([+-]?\d+)', remaining_str)
                            if digit_match:
                                weight_str = digit_match.group(1)
                                weight = float(weight_str)  # float() automatically handles leading zeros
                                logger.debug(f"Weight decoded via STX+spaces+digits format: {weight} kg from '{weight_str}' (STX count: {stx_count})")
                                # Clear buffer after successful extraction
                                if len(self._raw_buffer) > 30:
                                    self._raw_buffer = self._raw_buffer[-30:]
                                else:
                                    self._raw_buffer = b""
                        except:
                            pass
                
                # Check for STX at the end: digits + STX STX (e.g., "0000050\x02\x02" or " 0044050\x02\x02")
                if weight is None and buffer_to_check.endswith(b'\x02'):
                    # Find the last STX position
                    last_stx_pos = buffer_to_check.rfind(b'\x02')
                    if last_stx_pos > 0:
                        # Check if there are multiple STX at the end (need at least 2 STX)
                        stx_count = 0
                        pos = last_stx_pos
                        while pos >= 0 and buffer_to_check[pos] == 0x02:
                            stx_count += 1
                            pos -= 1
                        stx_start = pos + 1
                        
                        # Need at least 2 STX characters to consider this a valid pattern
                        if stx_count >= 2:
                            # Extract data before STX
                            data_before_stx = buffer_to_check[:stx_start]
                            
                            # Skip leading spaces (but keep leading zeros - they're part of the number)
                            digit_start = 0
                            while digit_start < len(data_before_stx) and data_before_stx[digit_start] == 0x20:  # Space only, not null or zero
                                digit_start += 1
                            
                            # Extract digits (including leading zeros, e.g., "0000050" -> 50.0, "0000000" -> 0.0)
                            if digit_start < len(data_before_stx):
                                remaining = data_before_stx[digit_start:]
                                try:
                                    remaining_str = remaining.decode('ascii', errors='ignore')
                                    # Match digits (with optional leading zeros, e.g., "0000050" -> 50.0, "0000000" -> 0.0)
                                    # The regex will match all consecutive digits, and float() will handle leading zeros correctly
                                    digit_match = re.match(r'([+-]?\d+)', remaining_str)
                                    if digit_match:
                                        weight_str = digit_match.group(1)
                                        weight = float(weight_str)  # float() automatically handles leading zeros (0000050 -> 50.0)
                                        logger.debug(f"Weight decoded via digits+STX format: {weight} kg from '{weight_str}' (STX count: {stx_count} at end)")
                                        # Clear buffer after successful extraction
                                        if len(self._raw_buffer) > 30:
                                            self._raw_buffer = self._raw_buffer[-30:]
                                        else:
                                            self._raw_buffer = b""
                                except:
                                    pass
                
                # Also check raw_data directly (for immediate matches)
                if weight is None and (b'\x02' in raw_data or b'\x03' in raw_data):
                    # Check for STX at the beginning: STX STX + spaces + digits (e.g., "\x02\x02 0049510")
                    if raw_data.startswith(b'\x02'):
                        # Count consecutive STX characters
                        stx_count = 0
                        pos = 0
                        while pos < len(raw_data) and raw_data[pos] == 0x02:
                            stx_count += 1
                            pos += 1
                        
                        # Skip spaces after STX
                        while pos < len(raw_data) and raw_data[pos] in (0x20, 0x00):  # Space or null
                            pos += 1
                        
                        # Extract digits from this position
                        if pos < len(raw_data):
                            remaining = raw_data[pos:]
                            try:
                                remaining_str = remaining.decode('ascii', errors='ignore')
                                # Match digits (with optional leading zeros, e.g., "0049510" -> 49510)
                                digit_match = re.match(r'([+-]?\d+)', remaining_str)
                                if digit_match:
                                    weight_str = digit_match.group(1)
                                    weight = float(weight_str)  # float() automatically handles leading zeros
                                    logger.debug(f"Weight decoded via STX+spaces+digits format (raw_data): {weight} kg from '{weight_str}' (STX count: {stx_count})")
                            except:
                                pass
                    
                    # Check for STX at the end: spaces + digits + STX STX (e.g., " 0044050\x02\x02")
                    if weight is None and raw_data.endswith(b'\x02'):
                        # Find the last STX position
                        last_stx_pos = raw_data.rfind(b'\x02')
                        if last_stx_pos > 0:
                            # Check if there are multiple STX at the end
                            stx_count = 0
                            pos = last_stx_pos
                            while pos >= 0 and raw_data[pos] == 0x02:
                                stx_count += 1
                                pos -= 1
                            stx_start = pos + 1
                            
                            # Need at least 2 STX characters to consider this a valid pattern
                            if stx_count >= 2:
                                # Extract data before STX
                                data_before_stx = raw_data[:stx_start]
                                
                                # Skip leading spaces
                                digit_start = 0
                                while digit_start < len(data_before_stx) and data_before_stx[digit_start] in (0x20, 0x00):  # Space or null
                                    digit_start += 1
                                
                                # Extract digits
                                if digit_start < len(data_before_stx):
                                    remaining = data_before_stx[digit_start:]
                                    try:
                                        remaining_str = remaining.decode('ascii', errors='ignore')
                                        # Match digits (with optional leading zeros, e.g., "0044050" -> 44050)
                                        digit_match = re.match(r'([+-]?\d+)', remaining_str)
                                        if digit_match:
                                            weight_str = digit_match.group(1)
                                            weight = float(weight_str)  # float() automatically handles leading zeros
                                            logger.debug(f"Weight decoded via spaces+digits+STX format (raw_data): {weight} kg from '{weight_str}' (STX count: {stx_count} at end)")
                                    except:
                                        pass
                
                # Fallback to original STX/ETX method if STX patterns didn't work
                if weight is None:
                    # Remove STX/ETX
                    text = text.replace('\x02', '').replace('\x03', '')
                    text = text.replace('\r', '').replace('\n', '').strip()
                    
                    logger.debug(f"STX/ETX framed text after cleanup: '{text}' (len={len(text)})")  # Removed to reduce log spam
                    
                    # Check if it's all spaces/empty (weight = 0)
                    if len(text) == 0 or text.strip() == '':
                        weight = 0.0
                        logger.debug("STX/ETX data is empty/spaces only, weight = 0")  # Removed to reduce log spam
                    else:
                        # Extract numeric value
                        match = re.search(r'[-+]?\s*(\d+(?:\.\d+)?)', text)
                        if match:
                            weight = float(match.group(1))
                            logger.debug(f"Weight decoded via STX/ETX method: {weight} kg")  # Removed to reduce log spam
                        # else:
                        #     logger.debug(f"STX/ETX: No numeric match in '{text}'")  # Removed to reduce log spam
            
            # Method 2: Character-by-character accumulation
            # Some digitizers send one character at a time
            # We accumulate in buffer until we get a complete reading
            elif len(raw_data) == 1 or len(raw_data) <= 3:
                # Accumulate characters
                self._buffer += text.replace('\r', '').replace('\n', '')
                
                # Check if we have a complete number (ends with newline or buffer is long enough)
                if '\n' in text or '\r' in text or len(self._buffer) >= 8:
                    # Try to extract weight from buffer
                    match = re.search(r'[-+]?\s*(\d+(?:\.\d+)?)', self._buffer)
                    if match:
                        weight = float(match.group(1))
                        logger.debug(f"Weight decoded via buffer method: {weight} kg")  # Removed to reduce log spam
                    # Clear buffer
                    self._buffer = ""
            
            # Method 3: ST,GS format (e.g., "ST,GS,+0040740kg")
            # Format: ST,GS,{sign}{digits}kg
            # Example: ST,GS,+0040740kg -> weight = 40740.0 kg
            if weight is None:
                text = text.replace('\r', '').replace('\n', '').strip()
                # Check for ST,GS format
                if text.startswith('ST,GS,') or 'ST,GS,' in text:
                    # Extract the numeric part after ST,GS,
                    # Pattern: ST,GS,+0040740kg or ST,GS,-0012345kg
                    match = re.search(r'ST,GS,([+-]?\d+(?:\.\d+)?)', text)
                    if match:
                        weight = float(match.group(1))
                        logger.debug(f"Weight decoded via ST,GS format: {weight} kg")  # Removed to reduce log spam
            
            # Method 4: Weight prefix format (e.g., "0`PF%q▒▒" or "50ePG%w▒▒")
            # Format: {weight}{control_chars}{trailing_chars}
            # Examples: "0`PF%q▒▒" -> 0 kg, "50ePG%w▒▒" -> 50 kg
            # Pattern: Weight number at the start, followed by control characters
            if weight is None:
                text = text.replace('\r', '').replace('\n', '').strip()
                # Try to match weight at the beginning of the string
                # Pattern: digits (with optional decimal) at the start, followed by non-numeric chars
                # This handles formats like "0`PF%q", "50ePG%w", etc.
                match = re.match(r'^([+-]?\d+(?:\.\d+)?)', text)
                if match:
                    weight = float(match.group(1))
                    logger.debug(f"Weight decoded via prefix format: {weight} kg (from '{text[:20]}...')")  # Removed to reduce log spam
            
            
            # Method 6: Plain ASCII with spaces/padding
            # Format: "  12345" or " 12345.00 kg" or " 0002000" (space + digits)
            if weight is None:
                # Don't strip leading spaces yet - we need them for the pattern
                text_no_crlf = text.replace('\r', '').replace('\n', '')
                # Remove common units
                text_clean = re.sub(r'[kKgG]', '', text_no_crlf)
                
                # Match pattern: optional sign, optional spaces, digits (e.g., " 0002000" or "  12345")
                # The regex should match even with leading spaces
                match = re.search(r'[-+]?\s*(\d+(?:\.\d+)?)', text_clean)
                if match:
                    weight_str = match.group(1)
                    weight = float(weight_str)  # float() handles leading zeros (0002000 -> 2000.0)
                    logger.debug(f"Weight decoded via plain ASCII method: {weight} kg from '{weight_str}' (raw: '{text_clean[:30]}...')")
                else:
                    logger.warning(f"Plain ASCII method failed - text: '{text_clean[:50]}...' (len={len(text_clean)}, hex: {raw_data.hex()[:40]}...)")
            
            # =================================================================
            # END OF CONVERSION LOGIC
            # =================================================================
            
            # Validate result
            if weight is not None:
                # Sanity check: weight should be reasonable (0 to 200,000 kg = 200 tons)
                if 0 <= weight <= 200000:
                    self._last_weight = weight
                    # Only log if weight changed or is non-zero (to reduce log noise)
                    if weight != 0:
                        logger.debug(f"Weight converted: {weight} kg")
                        pass
                    else:
                        logger.debug(f"Weight converted: {weight} kg")
                        pass
                    return weight
                elif weight > 200000:
                    return int(weight) / 10
                else:
                    logger.warning(f"Weight out of range: {weight} kg")
                    return None
            else:
                logger.debug(f"Weight conversion returned None for data: {raw_data.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"Digitizer conversion error: {e}")
            logger.error(f"Raw data that caused error: {raw_data.hex()}")
            return None
    
    def convert_accumulated(self, raw_data: bytes) -> Optional[float]:
        """
        Alternative conversion for character-by-character data.
        
        Accumulates data in buffer and returns weight only when complete.
        Call this for digitizers that send one character at a time.
        
        Args:
            raw_data: Raw bytes (may be single character)
            
        Returns:
            Weight in KG when complete reading available, None otherwise
        """
        try:
            # Add to buffer
            text = raw_data.decode('ascii', errors='ignore')
            self._buffer += text
            
            logger.debug(f"Buffer now: '{self._buffer}'")
            
            # Check for end-of-reading markers
            # Common markers: CR, LF, ETX (0x03)
            if '\r' in self._buffer or '\n' in self._buffer or '\x03' in self._buffer:
                # Extract weight from buffer
                clean = self._buffer.replace('\r', '').replace('\n', '').replace('\x03', '').strip()
                
                # Extract numeric value
                match = re.search(r'[-+]?\s*(\d+(?:\.\d+)?)', clean)
                if match:
                    weight = float(match.group(1))
                    logger.debug(f"Weight from accumulated data: {weight} kg")
                    self._buffer = ""  # Clear buffer
                    self._last_weight = weight
                    return weight
                
                # Clear buffer if no valid number found
                self._buffer = ""
            
            return None
            
        except Exception as e:
            logger.error(f"Accumulated conversion error: {e}")
            self._buffer = ""
            return None
    
    def clear_buffer(self) -> None:
        """Clear the accumulation buffer"""
        self._buffer = ""
        logger.debug("Digitizer buffer cleared")
    
    def get_buffer(self) -> str:
        """Get current buffer contents (for debugging)"""
        return self._buffer
    
    def get_last_raw_data(self) -> bytes:
        """Get the last raw data received (for debugging)"""
        return self._last_raw_data
    
    def get_last_weight(self) -> Optional[float]:
        """Get the last successfully converted weight"""
        return self._last_weight
    
    def debug_print(self, raw_data: bytes) -> None:
        """
        Print detailed debug information about raw data.
        
        Call this method to analyze unknown digitizer data formats.
        """
        print("\n" + "=" * 60)
        print("DIGITIZER DEBUG INFORMATION")
        print("=" * 60)
        print(f"Raw bytes length: {len(raw_data)}")
        print(f"Raw bytes (hex): {raw_data.hex()}")
        print(f"Raw bytes (repr): {repr(raw_data)}")
        
        try:
            print(f"ASCII decode: '{raw_data.decode('ascii', errors='replace')}'")
        except:
            print("ASCII decode: Failed")
        
        print(f"Current buffer: '{self._buffer}'")
        
        print("\nByte-by-byte breakdown:")
        for i, b in enumerate(raw_data):
            char_repr = chr(b) if 32 <= b <= 126 else '.'
            print(f"  [{i:3d}] 0x{b:02X} ({b:3d}) '{char_repr}'")
        
        print("=" * 60 + "\n")


# =============================================================================
# CONVENIENCE INSTANCES
# =============================================================================

# Global converter instances (can be used directly or create new instances)
rfid_converter = RFID_Convert()
digitizer_converter = Digitizer_Convert()


def convert_rfid(raw_data: bytes) -> Optional[str]:
    """
    Convenience function to convert RFID data.
    
    Args:
        raw_data: Raw bytes from RFID reader
        
    Returns:
        24-char hex string or None
    """
    return rfid_converter.convert(raw_data)


def convert_weight(raw_data: bytes) -> Optional[float]:
    """
    Convenience function to convert weight data.
    
    Args:
        raw_data: Raw bytes from digitizer
        
    Returns:
        Weight in KG or None
    """
    return digitizer_converter.convert(raw_data)
