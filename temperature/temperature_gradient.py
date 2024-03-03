# -*- coding: utf-8 -*-
from __future__ import annotations

from pioreactor.automations.events import UpdatedHeaterDC
from pioreactor.automations.temperature.base import TemperatureAutomationJob
from pioreactor.config import config
from pioreactor.utils import clamp
from pioreactor.utils.streaming_calculations import PID


class TemperatureGradient(TemperatureAutomationJob):
    """
    Uses a PID controller to change the DC% to match a target temperature.
    """

    MAX_TARGET_TEMP = 50
    automation_name = "temperature_gradient"
    published_settings = {"final_target_temperature": {"datatype": "float", "unit": "°C", "settable": True},
                          "start_temperature": {"datatype": "float", "unit": "°C", "settable": True},
                          "time_to_reach": {"datatype": "float", "unit": "min", "settable": True}}

    def __init__(self, final_target_temperature: float | str, start_temperature: float | str, time_to_reach: float | str, **kwargs) -> None:
        super().__init__(**kwargs)
        assert final_target_temperature is not None and start_temperature is not None, "target_temperature must be set"
        self.global_target_temperature = float(final_target_temperature)
        self.current_target_temperature = float(start_temperature)
        self.time_to_reach = float(time_to_reach)
        self.grad_T = (final_target_temperature - start_temperature ) / time_to_reach
        self.current_time = 0.
        self.last_time = 0.


        self.pid = PID(
            Kp=config.getfloat("temperature_automation.thermostat", "Kp"),
            Ki=config.getfloat("temperature_automation.thermostat", "Ki"),
            Kd=config.getfloat("temperature_automation.thermostat", "Kd"),
            setpoint=self.current_target_temperature,
            unit=self.unit,
            experiment=self.experiment,
            job_name=self.job_name,
            target_name="temperature",
            output_limits=(-25, 25),  # avoid whiplashing
        )

    def execute(self) -> UpdatedHeaterDC:
        while not hasattr(self, "pid"):
            # sometimes when initializing, this execute can run before the subclasses __init__ is resolved.
            pass

        assert self.latest_temperature is not None

        if self.current_target_temperature < self.global_target_temperature :
            self.current_target_temperature = min(self.global_target_temperature, self.target_temperature + self.grad_T * (self.current_time - self.last_time)) )

        self.pid = PID(
            Kp=config.getfloat("temperature_automation.thermostat", "Kp"),
            Ki=config.getfloat("temperature_automation.thermostat", "Ki"),
            Kd=config.getfloat("temperature_automation.thermostat", "Kd"),
            setpoint=self.current_target_temperature,
            unit=self.unit,
            experiment=self.experiment,
            job_name=self.job_name,
            target_name="temperature",
            output_limits=(-25, 25),  # avoid whiplashing
        )


        output = self.pid.update(
            self.latest_temperature, dt=1
        )  # 1 represents an arbitrary unit of time. The PID values will scale such that 1 makes sense.
        self.update_heater_with_delta(output)
        self.logger.debug(f"PID output = {output}")

        return UpdatedHeaterDC(
            f"delta_dc={output}",
            data={
                "current_dc": self.heater_duty_cycle,
                "delta_dc": output,
            },
        )

    def set_target_temperature(self, target_temperature: float, update_dc_now: bool = True) -> None:
        """

        Parameters
        ------------

        target_temperature: float
            the new target temperature
        update_dc_now: bool
            if possible, update the DC% to approach the new target temperatur

        """
        target_temperature = float(target_temperature)
        if target_temperature > self.MAX_TARGET_TEMP:
            self.logger.warning(
                f"Values over {self.MAX_TARGET_TEMP}℃ are not supported. Setting to {self.MAX_TARGET_TEMP}℃."
            )

        target_temperature = clamp(0, target_temperature, self.MAX_TARGET_TEMP)
        self.target_temperature = target_temperature
        self.pid.set_setpoint(self.target_temperature)

        # when set_target_temperature is executed, and we wish to update the DC to some new value,
        # it's possible that it isn't updated immediately if set during the `evaluate` routine.
        if update_dc_now and not self.is_heater_pwm_locked():
            assert self.latest_temperature is not None
            output = self.pid.update(
                self.latest_temperature, dt=1
            )  # 1 represents an arbitrary unit of time. The PID values will scale such that 1 makes sense.

            if self.temperature_control_parent.publish_temperature_timer.is_paused:
                self.update_heater_with_delta(output)
            else:
                # if another cycle is occurring very soon, don't bother updating the DC too much, as we don't want to "double dip" and change the dc twice quickly.
                time_to_next_run = self.temperature_control_parent.publish_temperature_timer.time_to_next_run
                duration_of_cycle = 90.0  # approx...
                f = time_to_next_run / duration_of_cycle
                self.update_heater_with_delta((1 - f) * output)
                self.last_time = self.current_time
                self.current_time += time_to_next_run