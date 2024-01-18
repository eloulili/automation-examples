import re
from serial import Serial
from pioreactor.actions.pump import PWMPump
from pioreactor.config import config
from pioreactor.automations.dosing.base import DosingAutomationJobContrib
from pioreactor.automations import events
from pioreactor.hardware import PWM_TO_PIN
from pioreactor.structs import PumpCalibration

SlowPump = PumpCalibration(
    name="SlowCalibration",
    pioreactor_unit="_testing",
    created_at="2024-01-01",
    pump="",
    hz=200.0,
    dc=50.0,
    duration_=1.0,
    bias_=0,
    voltage=-1,
)


def get_weight_from_scale(ser) -> float:
    # maybe this samples quickly, and takes an average?

    while True:
        try:
            ser.write(b"\r")
            raw_result = ser.read_until(b"\r")
            result = raw_result.decode('ascii')
            match = re.search(r'(\d+\.\d+)kg', result)
            weight_kg = float(match.group(1))
            return weight_kg * 1000
        except:
            pass


class ChemostatWithScale(DosingAutomationJobContrib):

    automation_name = "chemostat_with_scale"

    published_settings = {
        "volume": {"datatype": "float", "settable": True, "unit": "mL"},
        "duration": {"datatype": "float", "settable": True, "unit": "min"},
    }

    def __init__(self, volume: float | str, **kwargs) -> None:
        super().__init__(**kwargs)

        self.volume = float(volume)


    def add_media_to_bioreactor(self, ml: float, unit: str, experiment: str, source_of_event: str, mqtt_client) -> float:
        if ml == 0:
            return

        with Serial('/dev/ttyUSB0') as ser:

            initial_weight = get_weight_from_scale(ser)

            pin = PWM_TO_PIN[config.get("PWM_reverse", "media")]

            with PWMPump(unit, experiment, pin, calibration=SlowPump, mqtt_client=mqtt_client) as pump:
                # start pumping, and constantly check the weight.
                pump.continuously(block=False)
                while (get_weight_from_scale(ser) < (initial_weight + ml)) and (self.state == self.READY):
                    pass
                pump.stop()

            self.logger.info(f"Added {ml}ml via weight-based methods.")
            return ml


    def remove_waste_from_bioreactor(self, ml: float, unit: str, experiment: str, source_of_event: str, mqtt_client) -> float:
        if ml == 0:
            return

        with Serial('/dev/ttyUSB0') as ser:

            initial_weight = get_weight_from_scale(ser)

            pin = PWM_TO_PIN[config.get("PWM_reverse", "waste")]

            with PWMPump(unit, experiment, pin, calibration=SlowPump, mqtt_client=mqtt_client) as pump:
                # start pumping, and constantly check the weight.
                pump.continuously(block=False)
                while (get_weight_from_scale(ser) > (initial_weight - ml)) and (self.state == self.READY):
                    pass
                pump.stop()

            self.logger.info(f"Removed {ml}ml via weight-based methods.")
            return ml

    def execute(self) -> events.DilutionEvent:
        volume_actually_cycled = self.execute_io_action(media_ml=self.volume, waste_ml=self.volume)
        return events.DilutionEvent(
            f"exchanged {volume_actually_cycled['waste_ml']}mL",
            data={"volume_actually_cycled": volume_actually_cycled["waste_ml"]},
        )
