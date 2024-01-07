# -*- coding: utf-8 -*-
"""
run on the command line with
$ python3 naive_turbidostat.py

Exit with ctrl-c
"""
from pioreactor.automations.dosing.base import DosingAutomationJobContrib


class NaiveTurbidostat(DosingAutomationJobContrib):

    automation_name = "naive_turbidostat"
    published_settings = {
        "target_od": {"datatype": "float", "settable": True, "unit": "AU"},
    }

    def __init__(self, target_od, **kwargs):
        super().__init__(**kwargs)
        self.target_od = target_od

    def execute(self):
        if self.latest_od > self.target_od:
            self.execute_io_action(media_ml=1.0, waste_ml=1.0)


if __name__ == "__main__":
    from pioreactor.background_jobs.dosing_control import DosingController

    dc = DosingController(
        "naive_turbidostat",
        target_od=2.0,
        duration=1,  # check every 1 minute
        unit="test_unit",
        experiment="test_experiment",
    )
    dc.block_until_disconnected()
