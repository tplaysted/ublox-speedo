import time, math
from micropython import RingIO, schedule, alloc_emergency_exception_buf
from machine import UART, Timer, Pin, disable_irq, enable_irq
from micropyGPS import MicropyGPS

alloc_emergency_exception_buf(100)

uart = UART(2, baudrate=115200, tx=14, rx=12, rxbuf=10000) # Use a non-default UART
buffer = RingIO(10000)
gps = MicropyGPS()

baud_uart1 = bytes.fromhex('b5 62 06 8a 0c 00 00 04 00 00 01 00 52 40 00 c2 01 00 f6 c6') # sets baud to 115200 in flash
set_gst = bytes.fromhex('b5 62 06 8a 09 00 00 04 00 00 d4 00 91 20 01 23 61') # get pseudorange error stats from ublox
set_vtg = bytes.fromhex('b5 62 06 8a 09 00 00 04 00 00 b1 00 91 20 01 00 b2') # set vtg at 1Hz
set_dyn = bytes.fromhex('b5 62 06 8a 09 00 00 04 00 00 21 00 11 20 04 f3 65') # set dynamic model to automobile (4)

# uart.write(set_dyn)

class DataReader(object):
    def __init__(self):
        self.lines = {}
        timer = Timer(1)
        timer.init(callback=self.update, freq=100, mode=Timer.PERIODIC)
        
        p_timer = Timer(2)
        p_timer.init(callback=self.write_gps, period=1000, mode=Timer.PERIODIC)
        
    def update(self, _): # this only reads ONE line
        if buffer.any() > 0:
            line = buffer.readline().decode('utf-8')           
            self.lines[line[1:6]] = line
            
    def write_gps(self, _):
        for line in self.lines.values():
            for x in line:
                gps.update(x)
                
        print(f'Speed: {gps.speed_string()}, PRE = {math.sqrt(gps.std_lat**2 + gps.std_lon**2)}')
            
reader = DataReader() # instantiate the timer
        
def uart_handler(uart_instance):
    data = uart_instance.readline()
    if data is not None:
        buffer.write(data)

# Attach the interrupt handler
# Trigger on RX
uart.irq(handler=uart_handler, trigger=UART.IRQ_RX, hard=False)

print("UART Interrupts Active. Waiting for data...")

# Main loop
while True:
    # Main program execution continues here
    time.sleep(10)
