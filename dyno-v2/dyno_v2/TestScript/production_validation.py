from dyno_v2.Module.ASIDynoModule import ASIDynoModule
import dyno_v2.TestScript.rundown_test as rundown_test
import pandas as pd
from datetime import datetime
from dyno_v2.Module.TestABC import TestABC


class ProductionValidation(TestABC):

    def __init__(
            self,
            dyno: ASIDynoModule,
            *args,
            **kwargs
            # use_barcode=False,
            # motor_type=None,
            # barcode=None,
            # sn=None,
            # zoom=False,
            # lo=7,
            # hi=11
    ):
        """
        Validation Test

        Parameters:
            dyno : ASIDynoModule, required
            kwargs: dict, required
                {use_barcode : bool, required |
                motor_type : str, required |
                barcode : str, required |
                sn : str, required |
                zoom : bool, required |
                lo : int, required if zoom is True |
                hi : int, required if zoom is True}
        """
        super().__init__(dyno, *args, **kwargs)
        self.rundown = rundown_test.RundownTest(self.dyno, **kwargs)

    def parse_test_args(self):
        self.validation_args()

    def pre_rundown(self):
        # Disabled for DynoController
        # Assuming motor has passed EOL -> should have correct parameter files loaded
        # if not, then load parameter file
        # load_parameter = input(f"Load parameter file? [Y/N] ")
        # if "y" in load_parameter.lower() or "yes" in load_parameter.lower():
        #     print("IMPORTANT: Please make sure the parameter file is in the \"Parameter Files\" folder")
        #     file = input(f"File name: ")
        #     if not file.endswith(".xml"):
        #         file = f"{file}.xml"
        #     print(f"Loading parameter file...")
        #     self.dyno.devices[1].load_parameters(f"Parameter Files\\{file}")
        #     print(f"Finished!")
        # try:
        for i in range(8):
            self.dyno.test_outputs['hallRef'].append(self.dyno.devices[1].read(f"Hall sector[{i}]"))
        self.dyno.test_outputs['offset'] = self.dyno.devices[1].read("Hall offset")
        self.dyno.test_outputs['ratedRPM'] = self.dyno.devices[1].read("Rated motor speed")
        self.dyno.test_outputs['RsLs'] = [self.dyno.devices[1].read("Rs"), self.dyno.devices[1].read("Ls")]

        # startTime = datetime.now()
        # self.startTime = startTime

        print(f"Starting at {self.startTime}")

        # Motor Discovery Mode 1 x3
        print("Motor Discovery 1...")
        Ls_sum = 0.
        Rs_sum = 0.
        autoRsLs = []
        for i in range(3):
            print(f"Run {i + 1}/3: ", end="")
            autoRsLs.extend(self.dyno.devices[1].motor_discovery(1))
            Rs_sum += autoRsLs[i*2]
            Ls_sum += autoRsLs[i*2+1]
            print(f"autotune Rs = {autoRsLs[i*2]} mOhm | autotune Ls = {autoRsLs[i*2+1]} mH")
            # if not self.testing or not self.dyno.testing:
            #     return
        # Average of 3 runs
        self.dyno.test_outputs['avgRsLs'] = [Rs_sum / 3, Ls_sum / 3]
        print(f"Average Rs = {self.dyno.test_outputs['avgRsLs'][0]} mOhm | Ls = {self.dyno.test_outputs['avgRsLs'][1]} mH")

        # Checking results
        Rs_ok = False
        Ls_ok = False
        if abs(self.dyno.test_outputs['RsLs'][0] - self.dyno.test_outputs['avgRsLs'][0]) <= self.args['windowRsLs'][0] * abs(self.dyno.test_outputs['RsLs'][0]):
            self.dyno.devices[1].write("Rs", self.dyno.test_outputs['avgRsLs'][0])
            Rs_ok = True
        else:
            print("Out of window: Autotune Rs")
        if abs(self.dyno.test_outputs['RsLs'][1] - self.dyno.test_outputs['avgRsLs'][1]) <= self.args['windowRsLs'][1] * abs(self.dyno.test_outputs['RsLs'][1]):
            self.dyno.devices[1].write("Ls", self.dyno.test_outputs['avgRsLs'][1])
            Ls_ok = True
        else:
            print("Out of window: Autotune Ls")
        if Rs_ok and Ls_ok:
            print(f"Rs Ls values are good!\nSaving to flash")
            self.dyno.devices[1].save_to_flash()
            print(f"Finished!")
        else:
            print(f"Using default Rs, Ls...")
        print(f"\n---------------------------------------\n")
        # if not self.testing or not self.dyno.testing:
        #     return

        # Motor Discovery Mode 2
        print("Motor Discovery 2...")
        autotune_rpm, autotune_offset, autotune_hall = self.dyno.devices[1].motor_discovery(2)
        # if not self.testing or not self.dyno.testing:
        #     return
        print(f"Autotune rated RPM: {autotune_rpm}\nAutotune hall offset angle: {autotune_offset}")
        # Checking results
        if abs(autotune_rpm - self.dyno.test_outputs['ratedRPM']) > self.args['windowRPM'] * abs(self.dyno.test_outputs['ratedRPM']):
            print("Out of window: Autotune RPM")
        else:
            self.dyno.test_outputs['ratedRPM'] = autotune_rpm
            self.dyno.devices[1].write("Rated motor speed", self.dyno.test_outputs['ratedRPM'])
            print("GOOD VALUE: Autotune RPM")
        if abs(autotune_offset - self.dyno.test_outputs['offset']) > self.args['offsetRef']:
            print("Out of window: Autotune Hall Offset Angle")
        else:
            self.dyno.test_outputs['offset'] = autotune_offset
            self.dyno.devices[1].write("Hall offset", self.dyno.test_outputs['offset'])
            print("GOOD VALUE: Autotune Hall offset")
        hall_errors = 0
        for i in range(6):
            if autotune_hall[i+1] == self.dyno.test_outputs['hallRef'][i+1]:
                continue
            else:
                hall_errors += 1
        if hall_errors == 0:
            self.dyno.test_outputs['hallTableRef'] = autotune_hall
            print("GOOD VALUE: Autotune Hall Sectors")
        elif hall_errors == 1:
            self.dyno.test_outputs['double_test'] = True
            print("1 Hall Sector mismatch... Rerun Motor Discovery Mode 2 at the end...")
        else:
            exit("FATAL: HALL TABLE OUT OF ORDER!")
        print(f"\n---------------------------------------\n")
        # if not self.testing or not self.dyno.testing:
        #     return

    def test(self):
        self.pre_rundown()

        # Rundown
        self.rundown.run()
        # if not self.testing or not self.dyno.testing:
        #     return

        self.post_rundown()

    def post_rundown(self):
        # Checking results
        if self.dyno.test_outputs['max_torque'] >= self.args['targetTorque']:
            print(f"Target Torque {self.args['targetTorque']}Nm Reached: True")
        else:
            print(f"Target Torque {self.args['targetTorque']}Nm Reached: False")
        if self.dyno.test_outputs['max_efficiency'] >= self.args['targetEfficiency']:
            print(f"Target Motor Efficiency {self.args['targetEfficiency'] * 100}% Reached: True")
        else:
            print(f"Target Motor Efficiency {self.args['targetEfficiency'] * 100}% Reached: False")

        # Calculate torque constant Nm/A
        rundown_data = pd.read_csv(f"{self.dyno.logdir / self.dyno.extra_files.keys()[0]}.csv")
        sumConstant = 0.
        counts = len(rundown_data["Time"])
        for j in range(counts):
            sumA = 0.
            for i in range(3):
                sumA += rundown_data[f"Phase RMS Current {i+1}"][j]
            sumConstant += rundown_data["Torque"][j] / (sumA / 3 / 0.707)
        self.dyno.test_outputs['torqueConstant'] = sumConstant / counts
        print(f"Calculated torque constant: {self.dyno.test_outputs['torqueConstant']}")
        if abs(self.dyno.test_outputs['torqueConstant'] - self.args['torqueConstantRef']) <= self.args['windowTorqueConstant'] * self.args['torqueConstantRef']:
            print(f"GOOD VALUE: torque constant within reference window")
        else:
            print(f"Out of window: Calculated torque constant")
        print(f"\n---------------------------------------\n")
        # if not self.testing or not self.dyno.testing:
        #     return

        # Motor Discovery 2: the Reboot
        if self.dyno.test_outputs['double_test']:
            print("Motor Discovery 2: Rerun...")
            _, _, autotune_hall = self.dyno.devices[1].motor_discovery(2)
            # if not self.testing or not self.dyno.testing:
            #     return

            # Checking results
            for i in range(6):
                if autotune_hall[i + 1] == self.dyno.test_outputs['hallRef'][i + 1]:
                    continue
                else:
                    print("FATAL: Hall table out of order after Rundown...\ntests Failed")
                    return
            self.dyno.test_outputs['hallTableRef'] = autotune_hall

            print("SUCCESS: Hall table fixed!")
        print("tests Complete!")

        print(f"tests duration: {(datetime.now() - self.startTime).total_seconds() / 60:.1f} minutes")

        # except (TestInterrupt, KeyboardInterrupt):
        #     print(f"\n\nInterrupted")
        #     self.dyno.stop_test()
        #     self.dyno.stop_logging()
        #     return

    def log_result(self, *args, **kwargs):
        pass

    def post_test(self, **kwargs):
        pass

    def logging_setup(self):
        pass