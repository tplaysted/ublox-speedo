from color_setup import ssd

from gui.core.nanogui import refresh
from gui.widgets.label import Label, ALIGN_RIGHT  # Import any widgets you plan to use
from gui.widgets.dial import Dial, Pointer

from gui.core.writer import Writer  # Renders color text
from gui.fonts import mono10, mono16bold, mono32bold

import math
import utime

refresh(ssd, True)  # Initialise and clear display.

class Quality:
    def __init__(self):
        # Writer for gui elements
        Writer.set_textpos(ssd, 0, 0)  # In case previous tests have altered it

        # Instantiate any Writers to be used (one for each font)
        self.wri = Writer(ssd, mono10, verbose=False)  # Monochrome display uses Writer
        self.wri.set_clip(True, True, False)
        self.siv_lbl = Label(self.wri, 2, 68, 59)
        self.pre_lbl = Label(self.wri, 26, 68, 59)
        self.alt_lbl = Label(self.wri, 50, 68, 59)

        self.sat_labels = {} # Label widgets for each satellite we have seen
        self.refresh_count = 0

    def elev_to_rad(self, elev):
        return math.cos(elev) * 28

    def get_sat_xy(self, data):
        rad = self.elev_to_rad(math.radians(data[0]))
        x = 32 + int(rad * math.sin(math.radians(data[1])))
        y = 32 + int(rad * math.cos(math.radians(data[1])))

        return x, y

    def draw_sat(self, lbl, data):
        if data[0] is None or data[1] is None:
            lbl
            return

        x, y = self.get_sat_xy(data)
        lbl.row = y - 3
        lbl.col = x - 3
        val = '?' if data[2] is None else int(data[2] / 10.0)
        lbl.value(f'{val}', invert=True)

    def update_sat_labels(self, gps):
        for svid, lbl in self.sat_labels.items(): # backward pass to de-render missing sats
            if svid not in gps.satellite_data: # de-render sat
                lbl.value('') # this should de-render the Label

        self.circles()

        for svid, data in gps.satellite_data.items(): # forward pass to update existing and add new sats
            if svid in self.sat_labels: # update label
                lbl = self.sat_labels[svid]
            else: # add label
                lbl = Label(self.wri, 0, 0, 6)
                self.sat_labels[svid] = lbl

            self.draw_sat(lbl, data)


    def circles(self):
        ssd.ellipse(32, 32, 14, 14, 0xffff)
        ssd.ellipse(32, 32, 28, 28, 0xffff)

    def load(self, gps): # to be called when changing to this page
        refresh(ssd, True)  # Initialise and clear display.
        self.refresh_count = 0
        self.circles()
        self.siv_lbl.value(f'In view:{gps.satellites_in_view}')
        Label(self.wri, 16, 68, 'Horiz.PRE')
        
        pre = math.sqrt(gps.std_lat**2 + gps.std_lon**2)
        pre_str = ">999 m" if pre > 999 else f"{pre:.2f} m"
        self.pre_lbl.value(f' ={pre_str}')
        Label(self.wri, 40, 68, 'Alt.error')
        alt_str = ">999 m" if gps.std_alt > 999 else f"{gps.std_alt:.2f} m"
        self.alt_lbl.value(f' ={alt_str}')

        refresh(ssd)

    def refresh(self, gps): # to be called at around 10 Hz
        if self.refresh_count > 600: # full refresh every minute
            self.load(gps)
            return
    
        self.siv_lbl.value(f'In view:{gps.satellites_in_view}')
        pre = math.sqrt(gps.std_lat**2 + gps.std_lon**2)
        pre_str = ">999 m" if pre > 999 else f"{pre:.2f}"
        self.pre_lbl.value(f' ={pre_str} m')
        alt_str = ">999 m" if gps.std_alt > 999 else f"{gps.std_alt:.2f}"
        self.alt_lbl.value(f' ={alt_str} m')
        self.update_sat_labels(gps)

        refresh(ssd)
        self.refresh_count += 1
        
class Default:
    def __init__(self):
        # Writer for gui elements
        Writer.set_textpos(ssd, 0, 0)  # In case previous tests have altered it

        # Instantiate any Writers to be used (one for each font)
        self.wri = Writer(ssd, mono10, verbose=False)  # Monochrome display uses Writer
        self.wri.set_clip(True, True, False)

        self.date_lbl = Label(self.wri, 2, 2, 120)
        self.time_lbl = Label(self.wri, 12, 2, 120)
        self.lat_lbl = Label(self.wri, 32, 2, 120)
        self.lon_lbl = Label(self.wri, 42, 2, 120)
        self.alt_lbl = Label(self.wri, 52, 2, 120)

    def load(self, gps): # to be called when changing to this page
        refresh(ssd, True)  # Initialise and clear display.
        self.date_lbl.value(f'{gps.date_string()}')
        self.time_lbl.value(f'{gps.time_string()}')
        self.lat_lbl.value(f'Lat. {gps.latitude_string()}')
        self.lon_lbl.value(f'Lon. {gps.longitude_string()}')
        self.alt_lbl.value(f'Alt. {gps.altitude:.1f} m')
        refresh(ssd)

    def refresh(self, gps): # to be called at around 10 Hz
        self.date_lbl.value(f'{gps.date_string()}')
        self.time_lbl.value(f'{gps.time_string()}')
        self.lat_lbl.value(f'Lat. {gps.latitude_string()}')
        self.lon_lbl.value(f'Lon. {gps.longitude_string()}')
        self.alt_lbl.value(f'Alt. {gps.altitude:.1f} m')

        refresh(ssd)

class Speedometer:
    def __init__(self):
        # Writer for gui elements
        Writer.set_textpos(ssd, 0, 0)  # In case previous tests have altered it

        # Instantiate any Writers to be used (one for each font)
        self.wri = Writer(ssd, mono10, verbose=False)  # Monochrome display uses Writer
        self.wri_bold = Writer(ssd, mono32bold, verbose=False)  # For speed whole part
        self.wri_med = Writer(ssd, mono16bold, verbose=False)  # For speed decimal part
        
        self.wri.set_clip(True, True, False)
        self.wri_bold.set_clip(True, True, False)

        self.speed_whl_lbl = Label(self.wri_bold, 2, 2, 36, align=ALIGN_RIGHT) # label for speed whole part
        self.speed_dec_lbl = Label(self.wri_med, 15, 36, 18) # label for speed decimal part
        # self.acc_label = Label(self.wri, 24, 2, 62) # label for acceleration
        self.hdg_lbl = Label(self.wri, 36, 2, 62) # label for heading
        self.time_lbl = Label(self.wri, 50, 2, 62) # label for time display
        
        self.compass = Dial(self.wri, 12, 77, height=40, style=Dial.COMPASS, ticks=16)
        self.pointer = Pointer(self.compass)
        
        self._v = [0.0, 0.0, 0.0, 0.0]
        self.acc = 0
        self.count = 0
        self.ticks = utime.ticks_ms()
        
    def draw_compass(self, hdg):
        v = 0.8 * math.sin(math.radians(hdg)) + math.cos(math.radians(hdg)) * 0.8j
        self.pointer.value(v)

    def load(self, gps): # to be called when changing to this page
        refresh(ssd, True)  # Initialise and clear display.
        f, i = math.modf(gps.speed[2])
        self.speed_whl_lbl.value(f'{i:.0f}')
        self.speed_dec_lbl.value(f'.{f * 10:.0f}')
        Label(self.wri, 6, 47, 'kph')
        Label(self.wri, 1, 95, 'N')
        Label(self.wri, 52, 95, 'S')
        Label(self.wri, 27, 69, 'W')
        Label(self.wri, 27, 119, 'E')
        # self.acc_label.value(f'={self.acc:.1f} m/s^2 ')
        # Label(self.wri, 25, 2, 'Heading')
        self.hdg_lbl.value(f'HDG: {gps.course:.0f}°')
        self.time_lbl.value(f'{gps.time_string(seconds=False)}')
        self.draw_compass(gps.course)
        self._v = [0.0, 0.0, 0.0, 0.0]
        refresh(ssd)

    def refresh(self, gps): # to be called at around 10 Hz
#         if self.count >= 5: # recalculate acceleration
#             now = utime.ticks_ms()
#             dt = (now - self.ticks) / 1000 # needed for finite diff approximation
#             self.ticks = now
#             
#             self._v = self._v[1:] + [gps.speed[2] / 3.6]
#             v3, v2, v1, v0 = self._v
#             self.acc = ((2 * v0) - (5 * v1) + (4 * v2) - v3) / (dt ** 3) # backward diff
#             self.count = 0
#         else:
#             self.count += 1
        
        f, i = math.modf(round(gps.speed[2], 1))
        self.speed_whl_lbl.value(f'{i:.0f}')
        self.speed_dec_lbl.value(f'.{f * 10:.0f}')
        # acc_str = f'={self.acc:.1f} m/s^2 ' if self.acc >= 0 else f'={self.acc:.1f}m/s^2 '
        # self.acc_label.value(acc_str)
        # Label(self.wri, 25, 2, 'Heading')
        self.time_lbl.value(f'{gps.time_string()}')
        if gps.speed[2] > 1.0: # freeze compass at low speed
            self.hdg_lbl.value(f'HDG: {gps.course:.0f}°')
            self.draw_compass(gps.course)
        refresh(ssd)
