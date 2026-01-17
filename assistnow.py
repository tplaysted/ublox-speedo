import utime as time
import ntptime
import network
import requests
import uasyncio
import aiohttp

from machine import UART
from utime import sleep, localtime, time, mktime

from credentials import *

def ubx_chksum(arr): # ubx checksum from a byte array
    ck_a, ck_b = 0, 0
    
    for b in arr:
        ck_a = (ck_a + b) & 0xFF
        ck_b = (ck_b + ck_a) & 0xFF
        
    return (ck_a, ck_b)

def ubx_mga_ini_utc(rtc): # get ubx time init msg
    t = localtime(rtc.getUnixTime())
    preamble = [0xb5, 0x62, 0x13, 0x40, 0x18, 0x00]
    payload = [0x10, 0x00, 0x00, 0x00, t[0] & 0x00FF, (t[0] & 0xFF00) >> 8, t[1], t[2], t[3], t[4], t[5], 
               0x00, 0x00, 0x00, 0x00, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    ck_a, ck_b = ubx_chksum(preamble[2:] + payload)
    
    msg = b''
    
    for b in preamble:
        msg += b.to_bytes()
        
    for b in payload:
        msg += b.to_bytes()
        
    msg += ck_a.to_bytes()
    msg += ck_b.to_bytes()
    
    return msg

def ubx_mga_ini_pos(): # get initial position estimate message
    lines = []
    
    with open('lkc', 'r') as f:
        for line in f:
            lines += [line.strip()]
            
    lat = int(float(lines[0]) * 1e7).to_bytes(4, 'little', True)
    lon = int(float(lines[1]) * 1e7).to_bytes(4, 'little', True)
    alt = int(float(lines[2]) * 1e2).to_bytes(4, 'little', True)
    err = int(1000 * 1e2).to_bytes(4, 'little', False)
    
    preamble = [0xb5, 0x62, 0x13, 0x40, 0x14, 0x00]
    payload = [0x01, 0x00, 0x00, 0x00,
               lat[0], lat[1], lat[2], lat[3],
               lon[0], lon[1], lon[2], lon[3],
               alt[0], alt[1], alt[2], alt[3],
               err[0], err[1], err[2], err[3]]
    ck_a, ck_b = ubx_chksum(preamble[2:] + payload)
    
    msg = b''
    
    for b in preamble:
        msg += b.to_bytes()
        
    for b in payload:
        msg += b.to_bytes()
        
    msg += ck_a.to_bytes()
    msg += ck_b.to_bytes()
    
    return msg

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

async def assist_now(uart, rtc):
    # enable station interface and connect to WiFi access point
    nic = network.WLAN(network.WLAN.IF_STA)
    nic.active(True)
    
    try:
        nic.connect(SSID, PASSWORD)
    except OSError:
        print(f'Failed to connect to access point {SSID}')
        return
    
    tries = 0
    max_tries = 100
    
    while not nic.isconnected():
        tries += 1
        
        if tries > max_tries:
            print('Couldn\'t connect, giving up')
            return
        
        await uasyncio.sleep_ms(100)
        
    try:
        ntptime.settime()
        rtc.setUnixTime(time()) # update the rtc when we can
    except:
        pass
        
    print(f'Connected on {nic.ifconfig()[0]}')
    print(f'Requesting assistnow data...')
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://AssistNow.services.u-blox.com/GetAssistNowData.ashx?chipcode={CHIPCODE}&gnss=gps,gal&data=ulorb_l1,ukion,usvht,ualm') as response:     
            data = await response.read()
            messages = list(split_ubx_messages(data))
            
            print(f'Got {len(messages)} rows of data, updating receiver...')

            for msg in messages:
                uart.write(msg)

            print(f'Successfully updated receiver. Disconnecting...')

    nic.disconnect()
    
async def caching(gps, rtc):
    cached_gps_time = False
    signs = {'N': 1, 'E': 1, 'S': -1, 'W': -1}
    while True:
        if not gps.valid:
            await uasyncio.sleep(10)
            continue
        
        with open('lkc', 'w') as lkc:
            lat = gps._latitude
            lat = signs[lat[2]] * (lat[0] + lat[1] / 60.0)
            
            lon = gps._longitude
            lon = signs[lon[2]] * (lon[0] + lon[1] / 60.0)
            
            alt = gps.altitude
            
            print(lat, file=lkc)
            print(lon, file=lkc)
            print(alt, file=lkc)
            
        if not cached_gps_time:
            rtc.setUnixTime(mktime(gps.get_local_time(utc_offset=0)))
            cached_gps_time = True
            
        await uasyncio.sleep(10)