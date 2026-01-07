from color_setup import ssd
from gui.core.nanogui import refresh
from gui.widgets.dial import Dial, Pointer
from gui.widgets.label import Label  # Import any widgets you plan to use

refresh(ssd, True)  # Initialise and clear display.

import math

from gui.core.writer import Writer  # Renders color text
from gui.fonts import arial10


class Quality:
    def __init__(self):
        # Writer for gui elements
        Writer.set_textpos(ssd, 0, 0)  # In case previous tests have altered it

        # Instantiate any Writers to be used (one for each font)
        self.wri = Writer(ssd, arial10, verbose=False)  # Monochrome display uses Writer
        self.wri.set_clip(True, True, False)
        self.siv_lbl = Label(self.wri, 2, 68, 59)
        self.pre_lbl = Label(self.wri, 26, 68, 59)
        self.alt_lbl = Label(self.wri, 50, 68, 59)

        self.sat_labels = {}  # Label widgets for each satellite we have seen

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
        val = "-" if data[2] is None else int(data[2] / 10.0)
        lbl.value(f"{val}", invert=True)

    def update_sat_labels(self, gps):
        for (
            svid,
            lbl,
        ) in self.sat_labels.items():  # backward pass to de-render missing sats
            if svid not in gps.satellite_data:  # de-render sat
                lbl.value("")  # this should de-render the Label

        self.circles()

        for (
            svid,
            data,
        ) in (
            gps.satellite_data.items()
        ):  # forward pass to update existing and add new sats
            if svid in self.sat_labels:  # update label
                lbl = self.sat_labels[svid]
            else:  # add label
                lbl = Label(self.wri, 0, 0, 10)
                self.sat_labels[svid] = lbl

            self.draw_sat(lbl, data)

    def circles(self):
        ssd.ellipse(32, 32, 14, 14, 0xFFFF)
        ssd.ellipse(32, 32, 28, 28, 0xFFFF)

    def load(self, gps):  # to be called when changing to this page
        refresh(ssd, True)  # Initialise and clear display.
        self.circles()
        self.siv_lbl.value(f"In view: {gps.satellites_in_view}")
        Label(self.wri, 16, 68, "Horiz. PRE")
        self.pre_lbl.value(f" = {math.sqrt(gps.std_lat**2 + gps.std_lon**2):.2f} m")
        Label(self.wri, 40, 68, "Alt. error")
        self.alt_lbl.value(f" = {gps.std_alt:.2f} m")

        refresh(ssd)

    def refresh(self, gps):  # to be called at around 10 Hz
        self.siv_lbl.value(f"In view: {gps.satellites_in_view}")
        self.pre_lbl.value(f" = {math.sqrt(gps.std_lat**2 + gps.std_lon**2):.2f} m")
        self.alt_lbl.value(f" = {gps.std_alt:.2f} m")
        self.update_sat_labels(gps)
        refresh(ssd)
