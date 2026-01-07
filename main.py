# General imports
import uasyncio
from machine import I2C, UART, Pin
from micropython import RingIO
from pages import Quality

from micropyGPS import MicropyGPS

# Initialize UART
uart = UART(2, baudrate=115200, tx=6, rx=7, rxbuf=10000)  # Use a non-default UART

# display mode flag
mode = 0


async def uart_reader(q):
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
        print(f"{gps.date_string()}, {gps.time_string()}")
        print(f"{gps.latitude_string()}, {gps.longitude_string()}")
        # print(f'{gps.satellite_data}')
        await uasyncio.sleep_ms(1000)


async def refresh_display(gps):  # update the oled display
    qual = Quality()
    qual.load(gps)

    while True:
        qual.refresh(gps)
        await uasyncio.sleep_ms(100)


async def poll_button(pin):
    # Poll the button around ~50Hz for free debouncing
    global mode
    last = 1

    while True:
        cur = pin.value()

        if last == 1 and cur == 0:  # falling edge
            mode = (mode + 1) % 3

        last = cur

        await uasyncio.sleep_ms(20)


async def main():
    # Create GPS object and circular buffer
    gps = MicropyGPS()
    q = RingIO(10000)
    # lcd = LCD(I2C(scl=Pin(8), sda=Pin(9), freq=100000))
    pin = Pin(10, Pin.IN, Pin.PULL_UP)

    # Start the UART reader task
    uasyncio.create_task(uart_reader(q))

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
