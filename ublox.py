# Send configuration messages to the gps module.
# These messages update the config in the flash layer so the module needs a restart before
# any changes are applied

from machine import UART

uart = UART(2, baudrate=115200, tx=14, rx=12, rxbuf=10000) # Use a non-default UART

set_baud = bytes.fromhex('b5 62 06 8a 0c 00 00 04 00 00 01 00 52 40 00 c2 01 00 f6 c6') # sets baud to 115200 in flash
set_gst = bytes.fromhex('b5 62 06 8a 09 00 00 04 00 00 d4 00 91 20 01 23 61') # get pseudorange error stats from ublox
set_dyn = bytes.fromhex('b5 62 06 8a 09 00 00 04 00 00 21 00 11 20 04 f3 65') # set dynamic model to automobile (4)

uart.write(set_baud)
uart.write(set_gst)
uart.write(set_dyn)
