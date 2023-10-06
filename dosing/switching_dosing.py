# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from pioreactor.automations import events
from pioreactor.automations.dosing.base import DosingAutomationJobContrib
from pioreactor.exc import CalibrationError
from pioreactor.utils import local_persistant_storage


class SwitchingDosing(DosingAutomationJobContrib):
    """
    Run od on the culture until it reaches a certain threshold, at which point it adds alternate media and removes media at the same time until effectively there is only alternate media in the vial, then to switch back when the same od as before is reached, rinse and repeat
    """

    automation_name = "switching_dosing"
    published_settings = {
        "target_od": {"datatype": "float", "settable": True, "unit": "AU"},
        "duration": {"datatype": "float", "settable": True, "unit": "min"},
    }

    def __init__(self, target_od: float | str,  **kwargs) -> None:
        super().__init__(**kwargs)

        with local_persistant_storage("current_pump_calibration") as cache:
            if "media" not in cache:
                raise CalibrationError("Media pump calibration must be performed first.")
            elif "waste" not in cache:
                raise CalibrationError("Waste pump calibration must be performed first.")
            elif "alt_media" not in cache:
                raise CalibrationError("alt_media pump calibration must be performed first.")


        self.target_od = float(target_od)
        self.current_liquid = "media"

    def execute(self) -> Optional[events.DilutionEvent]:
        if self.latest_od['2'] >= self.target_od:

            if self.current_liquid == "media":
                # we are required to dose until self.alt_media_fraction > 0.95
                target = 0.95
                alt_media_ml_moved = 0
                while self.alt_media_fraction <= target:
                    results = self.execute_io_action(alt_media_ml=0.75, waste_ml=0.75)
                    alt_media_moved += results['alt_medial_ml']
                
                self.current_liquid = "alt_media"

                return events.DilutionEvent(f"Replaced until alt_media_fraction={target}, dosed {alt_media_ml_moved}mL alt-media.")

            elif self.current_liquid == "alt_media":
                # we are required to dose until self.alt_media_fraction > 0.95
                target = 0.05
                media_ml_moved = 0
                while self.alt_media_fraction >= target:
                    results = self.execute_io_action(media_ml=0.75, waste_ml=0.75)
                    media_moved += results['medial_ml']

                self.current_liquid = "media"
                return events.DilutionEvent(f"Replaced until alt_media_fraction={target}, dosed {media_ml_moved}mL media.")
                
        else:
            return None
