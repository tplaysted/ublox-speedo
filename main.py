import time
import math
from micropython import RingIO, alloc_emergency_exception_buf
from machine import UART, Timer, Pin, I2C
from lib_lcd1602_2004_with_i2c import LCD
from micropyGPS import MicropyGPS
import _thread

alloc_emergency_exception_buf(100)

uart = UART(2, baudrate=115200, tx=14, rx=12, rxbuf=10000)  # Use a non-default UART
buffer = RingIO(10000)
gps = MicropyGPS()
lcd = LCD(I2C(scl=Pin(26), sda=Pin(27), freq=100000))

baud_uart1 = bytes.fromhex(
    "b5 62 06 8a 0c 00 00 04 00 00 01 00 52 40 00 c2 01 00 f6 c6"
)  # sets baud to 115200 in flash
set_gst = bytes.fromhex(
    "b5 62 06 8a 09 00 00 04 00 00 d4 00 91 20 01 23 61"
)  # get pseudorange error stats from ublox
set_vtg = bytes.fromhex(
    "b5 62 06 8a 09 00 00 04 00 00 b1 00 91 20 01 00 b2"
)  # set vtg at 1Hz
set_dyn = bytes.fromhex(
    "b5 62 06 8a 09 00 00 04 00 00 21 00 11 20 04 f3 65"
)  # set dynamic model to automobile (4)

mode = 0

# uart.write(set_dyn)


class DataReader(object):
    def __init__(self):
        self.lines = {}
        timer = Timer(0)
        timer.init(callback=self.update, freq=100, mode=Timer.PERIODIC)

        p_timer = Timer(1)
        p_timer.init(callback=self.write_gps, period=1000, mode=Timer.PERIODIC)

    def update(self, _):  # this only reads ONE line
        if buffer.any() > 0:
            line = buffer.readline().decode("utf-8")
            self.lines[line[1:6]] = line

    def write_gps(self, _):
        for line in self.lines.values():
            for x in line:
                gps.update(x)

        # print(f'Speed: {gps.speed_string()}, PRE = {math.sqrt(gps.std_lat**2 + gps.std_lon**2)}')


class DisplayUpdater(object):
    def __init__(self):
        self.lines = {}
        timer = Timer(2)
        timer.init(callback=self.refresh, freq=25, mode=Timer.PERIODIC)

    def refresh(self, _):  # this only reads ONE line
        # lcd.clear()
        if mode == 0:
            lat_str = gps.latitude_string()
            lcd.puts(lat_str + " " * max(0, 16 - len(lat_str)))

            lon_str = gps.longitude_string()
            lcd.puts(lon_str + " " * max(0, 16 - len(lat_str)), y=1)

        if mode == 1:
            date_str = gps.date_string()
            lcd.puts(date_str + " " * max(0, 16 - len(date_str)))
            lcd.puts(" " * 16, y=1)

        if mode == 2:
            speed_str = gps.speed_string()
            lcd.puts(speed_str + " " * max(0, 16 - len(speed_str)))
            lcd.puts(" " * 16, y=1)


class Button(object):
    def __init__(self):
        self.timer = Timer(3)
        self.long_acc = 0
        self.last_val = 1
        self.pin = Pin(13, Pin.IN, Pin.PULL_UP)

        self.press_time = 1000

        self.timer.init(callback=self.poll, freq=25, mode=Timer.PERIODIC)

    def poll(self, _):
        if self.last_val == 1 and self.pin.value() == 0:
            self.on_click()

        if self.long_acc >= self.press_time:
            self.long_acc = 0
            self.on_press()

        if self.pin.value() == 0:
            self.long_acc += 40
        else:
            self.long_acc = 0

        self.last_val = self.pin.value()

    def on_click(self):
        global mode
        mode = (mode + 1) % 3

    def on_press(self):
        print("held")


def data_thread():
    reader = DataReader()  # instantiate the timer


_thread.start_new_thread(data_thread, ())
display = DisplayUpdater()
button = Button()


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
