# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from pioreactor.automations import events
from pioreactor.automations.dosing.base import DosingAutomationJob
from pioreactor.exc import CalibrationError
from pioreactor.utils import local_persistant_storage


class PIDTurbidostat(DosingAutomationJob):
    """
    Turbidostat mode - try to keep cell density constant by dosing whenever the target is surpassed
    """

    automation_name = "pid_turbidostat"
    published_settings = {
        "target_normalized_od": {"datatype": "float", "settable": True, "unit": "AU"},
        "target_od": {"datatype": "float", "settable": True, "unit": "OD"},
        "duration": {"datatype": "float", "settable": True, "unit": "min"},
    }
    target_od = None
    target_normalized_od = None
    VIAL_VOLUME = config.getfloat("bioreactor", "max_volume_ml", fallback=14)

    def __init__(
        self,
        target_normalized_od: Optional[float | str] = None,
        target_od: Optional[float | str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)


        with local_persistant_storage("current_pump_calibration") as cache:
            if "media" not in cache:
                raise CalibrationError("Media pump calibration must be performed first.")
            elif "waste" not in cache:
                raise CalibrationError("Waste pump calibration must be performed first.")

        if target_normalized_od is not None and target_od is not None:
            raise ValueError("Only provide target nOD or target OD, not both.")
        elif target_normalized_od is None and target_od is None:
            raise ValueError("Provide a target nOD or target OD.")

        


        Kp = config.getfloat("dosing_automation.pid_turbidostat", "Kp")
        Ki = config.getfloat("dosing_automation.pid_turbidostat", "Ki")
        Kd = config.getfloat("dosing_automation.pid_turbidostat", "Kd")

        if target_normalized_od is not None:
            self.set_target_nod(target_normalized_od)
            self.pid = PID(
            -Kp,
            -Ki,
            -Kd,
            setpoint=self.target_normalized_od,
            output_limits=(0, 14),
            sample_time=None,
            unit=self.unit,
            experiment=self.experiment,
            job_name=self.job_name,
            target_name="normalized_od",
        )
        elif target_od is not None:
            self.set_target_od(target_od)
            self.pid = PID(
            -Kp,
            -Ki,
            -Kd,
            setpoint=self.target_od,
            output_limits=(0, 14),
            sample_time=None,
            unit=self.unit,
            experiment=self.experiment,
            job_name=self.job_name,
            target_name="od",
        )


        assert isinstance(self.duration, float)
        self.volume = 0.

    @property
    def is_targeting_nOD(self) -> bool:
        return self.target_normalized_od is not None

    def execute(self) -> Optional[events.DilutionEvent]:
        if self.is_targeting_nOD:
            return self._execute_target_nod()
        else:
            return self._execute_target_od()




    def _execute_target_od(self) -> Optional[events.DilutionEvent]:
        assert self.target_od is not None
        if self.latest_od["2"] >= self.target_od:
            latest_od_before_dosing = self.latest_od["2"]
            target_od_before_dosing = self.target_od
            self.volume = self.pid.update(self.latest_od, dt=self.duration / 60)

            results = self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)
            media_moved = results["media_ml"]
            return events.DilutionEvent(
                f"Latest Normalized OD = {latest_od_before_dosing:.2f} ≥ Target  nOD = {target_od_before_dosing:.2f}; cycled {media_moved:.2f} mL",
                {
                    "latest_normalized_od": latest_od_before_dosing,
                    "target_normalized_od": target_od_before_dosing,
                    "volume": media_moved,
                },
            )
        else:
            return None
    def _execute_target_nod(self) -> Optional[events.DilutionEvent]:
        assert self.target_normalized_od is not None
        if self.latest_normalized_od >= self.target_normalized_od:
            latest_normalized_od_before_dosing = self.latest_normalized_od
            target_normalized_od_before_dosing = self.target_normalized_od
            self.volume = self.pid.update(self.latest_normalized_od, dt=self.duration / 60)

            results = self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)
            media_moved = results["media_ml"]
            return events.DilutionEvent(
                f"Latest Normalized OD = {latest_normalized_od_before_dosing:.2f} ≥ Target  nOD = {target_normalized_od_before_dosing:.2f}; cycled {media_moved:.2f} mL",
                {
                    "latest_normalized_od": latest_normalized_od_before_dosing,
                    "target_normalized_od": target_normalized_od_before_dosing,
                    "volume": media_moved,
                },
            )
        else:
            return None
        

    def set_target_od(self, value: str | float | int):
        if self.is_targeting_nOD:
            self.logger.warning("You are currently targeting nOD, and can only change that.")
        else:
            self.target_od = float(value)
            with suppress(AttributeError):
                self.pid.set_setpoint(self.target_od)

    def set_target_nod(self, value: str | float | int):
        if not self.is_targeting_nOD:
            self.logger.warning("You are currently targeting OD, and can only change that.")
        else:
            self.target_normalized_od = float(value)
            with suppress(AttributeError):
                self.pid.set_setpoint(self.target_normalized_od)








