# ASI Includes
from dyno_v2.Module.ASIDynoModule import ASIDynoModule
from dyno_v2.Module.TestABC import TestABC

from datetime import datetime


class MapleTAKProduction(TestABC):
    def __init__(
            self,
            dyno: ASIDynoModule,
            *args,
            **kwargs
            # use_barcode=False,
            # motor_type=None,
            # barcode=None,
            # sn=None
    ):
        """
        Geared Cedar Production Test

        Parameters:
            dyno : ASIDynoModule, required
            kwargs: dict, required
                {use_barcode : bool, required |
                note : str, required |
                barcode1 : dict, required |
                sn1 : str, required}
        """
        super().__init__(dyno, *args, **kwargs)

    def parse_test_args(self):
        self.maple_tak_production_args()

    def logging_setup(self):
        self.single_logging_setup()

    def test(self):
        self.dyno.maple_tak_production(self.args)

    def post_test(self, **kwargs):
        self.dyno.plot_basic("Maple TAK Production Result")
        self.dyno.plot_over_torque()
        self.dyno.plot_error("DUT warnings")
        self.dyno.plot_error("DUT faults")

    def log_result(self):
        result_txt = self.dyno.logdir / f"{datetime.now().strftime('%H-%M')} Maple TAK Production result.txt"
        with open(result_txt, "a") as txt:
            if self.args['use_barcode']:
                txt.write("Barcode:")
                txt.write(str(self.dyno.devices[1].barcode))
            txt.write("End of test temperatures:")
            txt.write(f"DUT {self.dyno.devices[1].read('controller temperature')}\u00B0C\n"
                      f"Motor {self.dyno.devices[1].read('motor temperature')}\u00B0C\n")

            txt.write(f"Test Result: {'PASS' if self.dyno.test_outputs['test_result'] else 'FAILED'}\n")
            txt.write(f"DUT init. controller temperature: {self.dyno.test_outputs['init_controller_temp']}\u00B0C\n")
            txt.write(f"DUT init. motor temperature: {self.dyno.test_outputs['init_controller_temp']}\u00B0C\n")
