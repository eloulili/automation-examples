# -*- coding: utf-8 -*-
"""
run on the command line with
$ python3 new_turbidostat.py

Exit with ctrl-c
"""
from pioreactor.automations.dosing.base import DosingAutomationJobContrib


class AdaptedTurbidostat(DosingAutomationJobContrib):

    automation_name = "adapted_turbidostat"
    published_settings = {
        "max_od": {"datatype": "float", "settable": True, "unit": "AU"},
        "min_od": {"datatype": "float", "settable": True, "unit": "AU"},
        "volume": {"datatype": "float", "settable": True, "unit": "mL"}
    }

    def __init__(self, max_od, min_od, volume ,**kwargs):
        super().__init__(**kwargs)


        self.max_od = max_od
        self.min_od = min_od
        self.volume = volume 
        self.is_pumping = False

    def execute(self):
        if self.latest_od > self.max_od:
            if self.is_pumping : 
                self.volume += 0.1
                # if we are already pumping but the od is still above the maximum
                # it means that we do not pump enough, and then we increase the volume pumped
            self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)
            self.is_pumping = True
        elif self.latest_od > self.min_od and self.is_pumping :
            self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)
        elif self.latest_od < self.min_od :
            self.is_pumping = False


if __name__ == "__main__":
    from pioreactor.background_jobs.dosing_control import DosingController

    dc = DosingController(
        "adapted_turbidostat",
        max_od=2.0,
        min_od= 1.9,
        volume = 0.1,
        duration=1,  # check every 1 minute
        unit="test_unit",
        experiment="test_experiment",
    )
    dc.block_until_disconnected()
