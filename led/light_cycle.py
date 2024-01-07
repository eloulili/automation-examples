# -*- coding: utf-8 -*-
from __future__ import annotations
import signal
from pioreactor.automations.led.base import LEDAutomationJobContrib
from pioreactor.automations import events
from pioreactor.types import LedChannel
from math import exp

__plugin_summary__ = "An LED automation for smooth light cycles"
__plugin_version__ = "0.0.1"
__plugin_name__ = "Light Cycle LED automation"


def logistic(t, k, d):
    return 1 / (1 + exp(-k * (t - d)))


def light_at_time_t(t):
    t = t % 24
    if t < 16:
        return logistic(t, 1.5, 5)
    else:
        return logistic(t, -1.5, 5 + 16)


class LightCycle(LEDAutomationJobContrib):

    automation_name: str = "light_cycle"
    published_settings: dict[str, dict] = {
        "duration": {
            "datatype": "float",
            "settable": False,
            "unit": "min",
        },  # doesn't make sense to change duration.
        "max_light_intensity": {"datatype": "float", "settable": True, "unit": "%"},
    }

    def __init__(self, max_light_intensity: float, **kwargs):
        super().__init__(**kwargs)
        self.hours_online: int = -1
        self.channels: list[LedChannel] = [LedChannel("B"), LedChannel("C")]
        self.max_light_intensity = float(max_light_intensity)

    def execute(self) -> events.AutomationEvent:
        self.hours_online += 1
        new_intensity = self.max_light_intensity * light_at_time_t(self.hours_online)
        for channel in self.channels:
            self.set_led_intensity(channel, new_intensity)
        return events.ChangedLedIntensity(f"Changed intensity to {new_intensity:0.2f}%")


if __name__ == "__main__":
    from pioreactor.background_jobs.led_control import LEDController
    from pioreactor.whoami import get_unit_name, get_latest_experiment_name

    lc = LEDController(
        led_automation="light_cycle",
        max_light_intensity=2.0,
        duration=0.03,  # every Xmin we "wake up" and decide what to do.
        unit=get_unit_name(),
        experiment=get_latest_experiment_name(),
    )

    lc.block_until_disconnected()
