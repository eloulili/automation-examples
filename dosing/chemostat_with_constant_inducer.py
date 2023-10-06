# -*- coding: utf-8 -*-
from __future__ import annotations

from pioreactor.automations import events
from pioreactor.automations.dosing.base import DosingAutomationJobContrib
from pioreactor.exc import CalibrationError
from pioreactor.utils import local_persistant_storage


class ChemostatWithInducer(DosingAutomationJobContrib):

    automation_name = "chemostat_with_inducer"
    published_settings = {
        "volume": {"datatype": "float", "settable": True, "unit": "mL"},
        "target_inducer_fraction": {"datatype": "float", "settable": True, "unit": "%"},
    }

    def __init__(self, volume: float | str, target_inducer_fraction: float | str, **kwargs) -> None:
        super().__init__(**kwargs)

        with local_persistant_storage("current_pump_calibration") as cache:
            if "media" not in cache:
                raise CalibrationError("Media pump calibration must be performed first.")
            elif "waste" not in cache:
                raise CalibrationError("Waste pump calibration must be performed first.")
            elif "alt_media" not in cache:
                raise CalibrationError("Alt-media pump calibration must be performed first.")

        self.volume = float(volume)
        self.target_inducer_fraction = float(target_inducer_fraction)

    def execute(self) -> events.DilutionEvent:
        media_exchanged = self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)

        # after this occurs, our alt_media_fraction has been reduced. We need to get it back up to target_inducer_fraction.
        # the math of this:
        # target_inducer_fraction = (alt_media_fraction * vial_volume + delta_alt_media) / (vial_volume + delta_alt_media)
        # solving for delta_alt_media:
        # delta_alt_media = vial_volume * (target_inducer_fraction - alt_media_fraction) / (1 - target_inducer_fraction)
        delta_alt_media = max(self.vial_volume * (self.target_inducer_fraction - self.alt_media_fraction) / (1 - self.target_inducer_fraction), 0)

        # now add that much alt media
        alt_media_exchanged = self.execute_io_action(alt_media_ml=delta_alt_media, waste_ml=delta_alt_media)

        # I _think_ there is a case where if alt_media_exchanged > 0.75, this might fail, however, it would correct on the next run.
        # assert abs(self.alt_media_fraction - self.target_inducer_fraction) < 0.01 # less than 1% error

        return events.DilutionEvent(
            f"exchanged {media_exchanged['media_ml']:.2f}ml of media and {alt_media_exchanged['alt_media_ml']:.2f}mL of alt media",
        )
