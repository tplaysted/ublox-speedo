# General imports
from machine import UART, Pin, I2C
import uasyncio
from micropyGPS import MicropyGPS
from micropython import RingIO
from math import sqrt
from pages import Default, Quality, Speedometer
from assistnow import assist_now

# display mode flag
mode = 0
change_page = False

async def uart_reader(uart, q):
    # Wrap raw UART in StreamReader
    reader = uasyncio.StreamReader(uart)
    while True:
        # Non-blocking read until newline
        line = await reader.readline()
        if line:
            # print(f"Received: {line.decode().strip()}")
            q.write(line)

        # await uasyncio.sleep_ms(2)


async def gps_updater(gps, q):
    # Continuously update the gps object
    while True:
        while q.any():
            try:
                gps.update(q.read(1).decode("utf-8"))
            except UnicodeError:
                pass

        await uasyncio.sleep_ms(2)


async def printer(gps):
    # Log gps data once a second
    while True:
        print(f'{gps.date_string()}, {gps.time_string()}')
        print(f'{gps.latitude_string()}, {gps.longitude_string()}')
        # print(f'{gps.satellite_data}')
        await uasyncio.sleep_ms(1000)


async def refresh_display(gps):  # update the oled display
    global mode, change_page

    deflt = Default()
    qual = Quality()
    spdo = Speedometer()

    page_list = [deflt, qual, spdo]

    while True:
        page = page_list[mode]

        if change_page:
            change_page = False
            page.load(gps)
            page.refresh(gps)
        else:
            page.refresh(gps)

        await uasyncio.sleep_ms(100)


async def poll_button(pin):
    # Poll the button around ~50Hz for free debouncing
    global mode, change_page
    last = 1

    while True:
        cur = pin.value()

        if last == 1 and cur == 0:  # falling edge
            change_page = True
            mode = (mode + 1) % 3

        last = cur

        await uasyncio.sleep_ms(20)

async def save_content(uart):
    while True:
        uart.write(b'\xb5b\t\x14\x00\x00\x1d')
        uasyncio.sleep(60)


async def main():
    # Create GPS object and circular buffer
    gps = MicropyGPS()
    q = RingIO(10000)
    # lcd = LCD(I2C(scl=Pin(8), sda=Pin(9), freq=100000))
    pin = Pin(5, Pin.IN, Pin.PULL_UP)
    # Initialize UART
    uart = UART(2, baudrate=115200, tx=6, rx=7, rxbuf=10000)  # Use a non-default UART


    # Start the AssistNow task
    uasyncio.create_task(assist_now(uart))

    # Start the UART reader task
    uasyncio.create_task(uart_reader(uart, q))

    # Start the GPS updater
    uasyncio.create_task(gps_updater(gps, q))

    # Start the logger
    uasyncio.create_task(printer(gps))

    # Start the display updater
    uasyncio.create_task(refresh_display(gps))

    # Start the button poller
    uasyncio.create_task(poll_button(pin))

    # Run other tasks
    print("System Running...")
    while True:
        await uasyncio.sleep(1)


# Run the event loop
try:
    uasyncio.run(main())
except KeyboardInterrupt:
    print("Stopped")
