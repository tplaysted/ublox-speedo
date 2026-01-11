# Send configuration messages to the gps module.
# These messages update the config in the flash layer so the module needs a restart before
# any changes are applied

from machine import UART
from utime import sleep

# Initialize UART
uart = UART(2, baudrate=115200, tx=6, rx=7, rxbuf=10000)  # Use a non-default UART

set_baud = bytes.fromhex('b5 62 06 8a 0c 00 00 04 00 00 01 00 52 40 00 c2 01 00 f6 c6') # sets baud to 115200 in flash
set_gst = bytes.fromhex('b5 62 06 8a 09 00 00 04 00 00 d4 00 91 20 01 23 61') # get pseudorange error stats from ublox
set_dyn = bytes.fromhex('b5 62 06 8a 09 00 00 04 00 00 21 00 11 20 04 f3 65') # set dynamic model to automobile (4)

# Poll UBX-SEC-UNIQID from the receiver
CMD_POLL_UNIQID = b"\xb5\x62\x27\x03\x00\x00\x2a\xa5"
# Poll UBX-MON-VER from the receiver
CMD_POLL_MONVER = b"\xb5\x62\x0a\x04\x00\x00\x0e\x34"
# Configure CFG-NAVSPG-ACKAIDING in RAM to enable MGA-ACK messages
CFG_RAM_ACKAIDING = b"\xb5\x62\x06\x8a\x09\x00\x00\x01\x00\x00\x25\x00\x11\x10\x01\xe1\x3e"
# Poll UBX-NAV-STATUS from the receiver
CMD_POLL_NAV_STATUS = b"\xb5\x62\x01\x03\x00\x00\x04\x0d"

uart.write(CMD_POLL_MONVER)

sleep(1)

while True:
    line = uart.readline()
    if line:
        print(line.hex())
        
    sleep(0.01)


