import utime as time
import ntptime
import network
import requests
import uasyncio
import aiohttp

from machine import UART
from utime import sleep

from credentials import *

def validate_ubx_message(msg):
    """
    Validate a UBX message at the start of msg.
    Returns:
        * The length of the message if the message is valid
        * 0 if there is no valid UBX message at the start of msg
        * -1 if there is not enough data to validate
    """
    try:
        if msg is None or len(msg) < 8:
            raise RuntimeError("Message is None or too short")
        if msg[0:2] != b'\xB5\x62':
            raise RuntimeError("Message does not start with UBX header")
        payload_len = int.from_bytes(msg[4:6], "little")
        if len(msg) < payload_len + 8:
            print("Warning: Message is truncated, waiting for more data")
            return -1 # Message is truncated, return -1 to indicate this
        msg = msg[:payload_len + 8]  # Trim to the expected length
        chk = [0, 0]
        for i in msg[2:-2]:
            chk[0] = (chk[0] + i) & 0xFF
            chk[1] = (chk[1] + chk[0]) & 0xFF
        if bytes(chk) != msg[-2:]:
            raise RuntimeError("Checksum mismatch")
        return payload_len + 8
    except RuntimeError as e:
        print(f"Error: Failed to validate UBX message: {e}")
        return 0

def split_ubx_messages(msgs):
    """
    Generator method to split a byte sequence into valid UBX messages.
    Assumes msgs is a bytes or bytearray object containing only valid
    UBX messages.
    """
    while msgs:
        msg_len = validate_ubx_message(msgs)
        if msg_len <= 0:
            raise RuntimeError("Failed to split UBX messages")
        yield msgs[:msg_len]  # Yield the valid message
        msgs = msgs[msg_len:] # Remove the valid message from the buffer

# Initialize UART
uart = UART(2, baudrate=115200, tx=6, rx=7, rxbuf=10000)  # Use a non-default UART

async def assist_now(uart):
    # enable station interface and connect to WiFi access point
    nic = network.WLAN(network.WLAN.IF_STA)
    nic.active(True)
    
    try:
        nic.connect(SSID, PASSWORD)
    except OSError:
        print(f'Failed to connect to access point {SSID}')
        return
    
    while not nic.isconnected():
        await uasyncio.sleep_ms(100)
        
    print(f'Connected on {nic.ifconfig()[0]}')
    print(f'Requesting assistnow data...')
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://AssistNow.services.u-blox.com/GetAssistNowData.ashx?chipcode={CHIPCODE}&gnss=gps,gal&data=uporb_1,ualm') as response:     
            data = await response.read()
            messages = list(split_ubx_messages(data))
            
            print(f'Got {len(messages)} rows of data, updating receiver...')

            for msg in messages:
                uart.write(msg)

            print(f'Successfully updated receiver. Disconnecting...')

#     response = requests.get(f'https://AssistNow.services.u-blox.com/GetAssistNowData.ashx?chipcode={CHIPCODE}&gnss=gps,gal&data=uporb_1,ualm')
# 
#     data = response.content
#     messages = list(split_ubx_messages(data))
#     
#     print(f'Got {len(messages)} rows of data, updating receiver...')
# 
#     for msg in messages:
#         uart.write(msg)
# 
#     print(f'Successfully updated receiver. Disconnecting...')

    
    nic.disconnect()
