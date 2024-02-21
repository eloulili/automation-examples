# -*- coding: utf-8 -*-
from __future__ import annotations

from pioreactor.automations.temperature.base import TemperatureAutomationJobContrib

from random import randrange

class RandomTemperature(TemperatureAutomationJobContrib):
    automation_name = "random_profile"
    published_settings = {"Min_Temperature": {"datatype": "float", "unit": "°C", "settable": True},
                        "Max_Temperature": {"datatype": "float", "unit": "°C", "settable": True}}

    def __init__(self, min_temperature, max_temperature, **kwargs) -> None:
        super(RandomTemperature, self).__init__(**kwargs)
        self.min_temperature = min_temperature
        self.max_temperature = max_temperature

    def execute(self) -> None:
        self.update_heater(randrange(self.min_temperature, self.max_temperature))
