# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from pioreactor.automations import events
from pioreactor.automations.dosing.base import DosingAutomationJob
from pioreactor.exc import CalibrationError
from pioreactor.utils import local_persistant_storage


class AdaptedTurbidostat(DosingAutomationJob):
    """
    Adapted Turbidostat mode - adjust media volume based on OD levels
    """

    automation_name = "adapted_turbidostat"
    published_settings = {
        "volume": {"datatype": "float", "settable": True, "unit": "mL"},
        "max_od": {"datatype": "float", "settable": True, "unit": "OD"},
        "min_od": {"datatype": "float", "settable": True, "unit": "OD"},
        "max_normalized_od": {"datatype": "float", "settable": True, "unit": "AU"},
        "min_normalized_od": {"datatype": "float", "settable": True, "unit": "AU"},
        "use_normalized_od": {"datatype": "bool", "settable": True},
        "duration": {"datatype": "float", "settable": True, "unit": "min"},
    }

    def __init__(
        self,
        volume: float | str,
        max_od: float,
        min_od: float,
        max_normalized_od: float,
        min_normalized_od: float,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        use_normalized_od = min_normalized_od > 0. and max_normalized_od > 0.
        use_raw_od = min_od > 0. and max_od > 0.
        with local_persistant_storage("current_pump_calibration") as cache:
            if "media" not in cache:
                raise CalibrationError("Media pump calibration must be performed first.")
            elif "waste" not in cache:
                raise CalibrationError("Waste pump calibration must be performed first.")
        if use_normalized_od and use_raw_od:
            raise ValueError("Use only raw Or normalized OD")
        if not (use_raw_od or use_normalized_od):
            raise ValueError("Provide OD values")

        if use_normalized_od:
            self.is_pumping = False
            self.use_normalized_od = True
        else:
            self.is_pumping = False
            self.use_normalized_od = False

        self.volume = float(volume)

    def execute(self) -> Optional[events.DilutionEvent]:
        if self.use_normalized_od:
            if self.latest_normalized_od >= self.max_normalized_od:
                if self.is_pumping:
                    # If the pump is already active and the  OD is still above the maximum, it means that we do not pump fast enough
                    self.volume += 0.1
                # Start or continue pumping if normalized OD is above the maximum threshold
                return self._execute_max_normalized_od()
            elif self.is_pumping and self.latest_normalized_od >= self.min_normalized_od:
                # Continue pumping if already in the pumping state and normalized OD is above the minimum threshold
                return self._execute_pumping()
            else:
                return None
        else:
            if self.latest_od["2"] >= self.max_od:
                if self.is_pumping:
                    # Same as before
                    self.volume += 0.1
                # Start or continue pumping if OD is above the maximum threshold
                return self._execute_max_od()
            elif self.is_pumping and self.latest_od["2"] >= self.min_od:
                # Continue pumping if already in the pumping state and OD is above the minimum threshold
                return self._execute_pumping()
            else:
                return None
            

        # Dans la fonction _execute_max_normalized_od
    def _execute_max_normalized_od(self) -> Optional[events.DilutionEvent]:
        # Start pumping if normalized OD is above the maximum threshold
        self.is_pumping = True
        return self._execute_pumping_normalized_od()

    # Dans la fonction _execute_pumping_normalized_od
    def _execute_pumping_normalized_od(self) -> Optional[events.DilutionEvent]:
        # Continue pumping until normalized OD is below the minimum threshold
        if self.latest_normalized_od >= self.min_normalized_od:
            latest_normalized_od_before_dosing = self.latest_normalized_od
            target_normalized_od_before_dosing = self.min_normalized_od
            results = self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)
            media_moved = results["media_ml"]
            return events.DilutionEvent(
                f"Latest Normalized OD = {latest_normalized_od_before_dosing:.2f} ≥ Min Normalized OD = {target_normalized_od_before_dosing:.2f}; cycled {media_moved:.2f} mL",
                {
                    "latest_normalized_od": latest_normalized_od_before_dosing,
                    "target_normalized_od": target_normalized_od_before_dosing,
                    "volume": media_moved,
                },
            )
        else:
            self.is_pumping = False
            return None


    def _execute_max_od(self) -> Optional[events.DilutionEvent]:
        # Start pumping if OD is above the maximum threshold
        self.is_pumping = True
        return self._execute_pumping()


    def _execute_pumping(self) -> Optional[events.DilutionEvent]:
        # Continue pumping until OD is below the minimum threshold
     if self.latest_od["2"] >= self.min_od:
         latest_od_before_dosing = self.latest_od["2"]
         target_od_before_dosing = self.min_od
         results = self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)
         media_moved = results["media_ml"]
         return events.DilutionEvent(
             f"Latest OD = {latest_od_before_dosing:.2f} ≥ Min OD = {target_od_before_dosing:.2f}; cycled {media_moved:.2f} mL",
             {
                 "latest_od": latest_od_before_dosing,
                 "target_od": target_od_before_dosing,
                 "volume": media_moved,
             },
         )
     else:
         self.is_pumping = False
         return None
