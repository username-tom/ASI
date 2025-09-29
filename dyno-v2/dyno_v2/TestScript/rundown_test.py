# ASI Includes
import pandas as pd

from dyno_v2.Module.asi_controller import ASIController
from dyno_v2.Module.abb_acs800 import AbbAcs800
from dyno_v2.Module.exceptions import *
from time import sleep
from datetime import datetime
from dyno_v2.Module.TestABC import TestABC


class RundownTest(TestABC):

    def __init__(
            self,
            dyno,
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
        Rundown Test

        Parameters:
            dyno : ASIDynoModule, required
            args : list, optional [
                use_barcode : bool, required
                barcode1 : dict, required
                sn1 : str, required
                note : str, required]
            kwargs: dict, required
                {use_barcode : bool, required |
                barcode1 : dict, required if use_barcode is True |
                sn1 : str, required if use_barcode is False |
                motor_type : str, required |
                zoom : bool, required |
                zoom_lo : int, required if zoom is True |
                zoom_hi : int, required if zoom is True}
        """
        super().__init__(dyno, *args, **kwargs)

    def parse_test_args(self):
        self.rundown_args()

    def logging_setup(self):
        self.rundown_logging_setup()
    #     if self.args['use_barcode']:
    #         output = self.args['barcode1']['serial_num']
    #         parameter = self.args['barcode1']['parameter']
    #         if str(parameter).startswith('92-000308') or '22' in self.args['motor_type']:
    #             self.args['torque_target'] = 15
    #         elif str(parameter).startswith('92-000311') or '18' in self.args['motor_type']:
    #             self.args['torque_target'] = 12
    #     else:
    #         try:
    #             sn, idx = self.args['sn1'].split("-")
    #             output = f"{int(sn)}-{int(idx):05d}"
    #         except (AttributeError, TypeError, ValueError):
    #             output = f"0000-00000"
    #         if '22' in self.args['motor_type'] or \
    #                 'scythe' in self.args['motor_type'] or \
    #                 'maple' in self.args['motor_type']:
    #             self.args['torque_target'] = 15
    #         elif '18' in self.args['motor_type']:
    #             self.args['torque_target'] = 12
    #
    #     self.dyno.start_logging(1, run_down=f"{output} ({self.args['motor_type']})")

    def test(self):
        print(f"Testing speed: {int(self.args['speed'])} rpm | "
              f"Target torque: {self.args['torque_target'] if self.args['torque_target'] > 0 else 'N/A'} Nm")

        #### Start of Efficiency Map duplicate ###
        # try:
        self.dyno.devices[1].remote_speed_mode(speed=int(self.args['speed']), motoring_current=self.args['motoring'])
        sleep(2)

        self.dyno.devices[2].start()
        self.dyno.devices[2].set_torque(0)
        sleep(2)

        self.dyno.babying('speed', speed=int(self.args['speed']), motoring_current=self.args['motoring'])

        # faults = self.dyno.devices[1].check_faults()
        #
        # if faults:
        #     print(f"Registered faults: {faults}")
        #     if str(faults).find("over current"):
        #         # print("Assuming Inst. Over-current and trying to baby it...")
        #         self.dyno.devices[1].remote_speed_mode(speed=int(speed) / 2.0, motoring_current=25)
        #         self.dyno.devices[1].clear_faults()
        #         sleep(10)
        #         self.dyno.devices[1].remote_speed_mode(speed=int(speed), motoring_current=25)
        #         sleep(10)
        #         self.dyno.devices[1].remote_speed_mode(speed=int(speed), motoring_current=motoring)
        #         faults = self.dyno.devices[1].check_faults()
        #         if faults:
        #             print(f"This fault won't clear! Test aborted\n{faults}")
        #             return self.max_torque, self.max_efficiency, extra

        # settle after initial speed command
        sleep(5)

        self.dyno.rundown(**self.args)
            # ramp torque with constant-time wait, and log SS dataline
            # cur_torque = int(MinTorque)
            # # startRun = datetime.now()
            # while (cur_torque < MaxTorque and
            #        self.dyno.devices[PA].getMeasurement("Torque") < LoadCellLimit - 0.5):
            #     if self.args['zoom'] and (self.dyno.devices[PA].getMeasurement("Torque") < self.args['zoom_lo'] or
            #                               self.dyno.devices[PA].getMeasurement("Torque") > self.args['zoom_hi']) :
            #         self.dyno.devices[2].set_torque(target=cur_torque)
            #         sleep(self.settleTime * 10)
            #     else:
            #         self.dyno.devices[2].ramp_to(target=cur_torque, step=10, period=self.settleTime)
            #
            #     # curSpeed = self.dyno.devices[PA].getMeasurement("Motor Speed")  # doesn't consistently represent current RPM
            #     curSpeed = self.dyno.devices[1].get_rpm()
            #
            #     if curSpeed > 30:
            #         self.dyno.extra_line(file_name=extra)
            #         cur_torque += TorqueStep
            #     else:
            #         break
            #     #### End of Efficiency Map duplicate ###
            #     try:
            #         t = self.dyno.devices[PA].getMeasurement("Torque")
            #         if self.max_torque < t:
            #             self.max_torque = t
            #         me = self.dyno.devices[PA].getMeasurement("Motor Efficiency")
            #         if self.max_efficiency < me:
            #             self.max_efficiency = me
            #     except (TypeError, AttributeError):
            #         pass
            #
            # self.dyno.stop_test()
            # self.dyno.stop_logging()

            # self.max_efficiency = self.dyno.test_outputs['max_efficiency']
            # self.max_torque = self.dyno.test_outputs['max_torque']

            # Cooldown between speeds
            # if i < len(opSpeeds):
            #     print(f"Completed rundown at {speed} RPM! Cooling down for {tCooldown}min...")
                # for t in range(int(tCooldown)):
                #     print(f"{tCooldown - t:.1f} min left", end="\r")
                #     sleep(60)
        # except (KeyboardInterrupt, TestInterrupt):
        #     print(f"\n\nInterrupted")
        #     # self.dyno.stop_test()
        #     # self.dyno.stop_logging()
        #     # delta = (datetime.now() - self.startTime).total_seconds() / 60
        #     # print(f"Run duration: {delta:.2f} minutes")
        #     # self.dyno.devices[1].backup_parameters(f"{self.dyno.logdir / 'parameters.xml'}")
        #     # self.dyno.plot_basic("Rundown Result")
        #     # self.dyno.plot_error("DUT warnings")
        #     # self.dyno.plot_error("DUT faults")
        #     # return self.dyno.test_outputs['max_torque'], self.max_efficiency
        # except TestError as e:
        #     print(e)
        #     # delta = (datetime.now() - self.startTime).total_seconds() / 60
        #     # print(f"Run duration: {delta:.2f} minutes")
        #     # self.dyno.devices[1].backup_parameters(f"{self.dyno.logdir / 'parameters.xml'}")
        #     # self.dyno.plot_basic("Rundown Result")
        #     # self.dyno.plot_error("DUT warnings")
        #     # self.dyno.plot_error("DUT faults")
        #     # return self.dyno.test_outputs['max_torque'], self.max_efficiency
        # finally:
        #     self.dyno.stop_test()
        #     self.dyno.stop_logging()
        #     self.log_result()
        #     delta = (datetime.now() - self.startTime).total_seconds() / 60
        #     print(f"Run duration: {delta:.2f} minutes")
            # self.dyno.devices[1].backup_parameters(f"{self.dyno.logdir / 'parameters.xml'}")

    def post_test(self, **kwargs):
        self.dyno.plot_basic("Rundown Result")
        self.dyno.plot_over_torque()
        self.dyno.plot_error("DUT warnings")
        self.dyno.plot_error("DUT faults")
        self.dyno.summarize_extra_log(filename='rundown ')

    # run = rundown_test

    def interrupt(self):
        self.args['settleTime'] = 0.1
        self.testing = False
        self.dyno.testing = False
        if self.watchdog:
            self.stop_watchdog()
        raise TestInterrupt

    def log_result(self):
        result_txt = self.dyno.logdir / f"{datetime.now().strftime('%H-%M')} rundown result.txt"
        with open(result_txt, "a") as txt:
            if self.args['use_barcode']:
                txt.write("Barcode:")
                txt.write(str(self.dyno.devices[1].barcode))
            txt.write(f"DUT {self.dyno.devices[1].read('controller temperature')}C / "
                      f"Motor {self.dyno.devices[1].read('motor temperature')}C\n")
            txt.write(f"Maximum Torque: {self.dyno.test_outputs['max_torque']} Nm\n")
            if self.dyno.test_outputs['max_torque'] > self.args['torque_target']:
                result = f"PASSED: Target torque reached"
            else:
                result = f"FAILED: Target torque NOT REACHED!!!"
            print(result)
            txt.write(f"{result}\n")

            if not pd.isna(self.args['target_efficiency']) and not pd.isna(self.args['target_efficiency_window']):
                lo_range = self.args['target_efficiency'] - self.args['target_efficiency_window']
                hi_range = self.args['target_efficiency'] + self.args['target_efficiency_window']
                if hi_range > lo_range:
                    print(f"Target Motor Efficiency: {lo_range} - {hi_range}%")
                    txt.write(f"Target Motor Efficiency: {lo_range} - {hi_range}\n")
                    if lo_range < self.dyno.test_outputs['max_efficiency'] < hi_range:
                        result = f"PASSED: Target motor efficiency reached @ {self.dyno.test_outputs['max_efficiency']}%!"
                    else:
                        result = f"FAILED: Target motor efficiency not reached @ {self.dyno.test_outputs['max_efficiency']}%"
                    print(f"{result}")
                    txt.write(f"{result}\n")
                elif hi_range == lo_range:
                    print(f"Target Motor Efficiency: {lo_range}%")
                    txt.write(f"Target Motor Efficiency: {lo_range}\n")
                    if lo_range < self.dyno.test_outputs['max_efficiency']:
                        result = f"PASSED: Target motor efficiency reached @ {self.dyno.test_outputs['max_efficiency']}%!"
                    else:
                        result = f"FAILED: Target motor efficiency not reached @ {self.dyno.test_outputs['max_efficiency']}%"
                    print(f"{result}")
                    txt.write(f"{result}\n")

            temp = self.dyno.devices[1].read('controller temperature')
            if temp <= 40:
                result = f"PASSED: Controller within temperature range of {40}C"
            else:
                result = f"FAILED: Controller overheat {temp}C"
            print(result)
            txt.write(f"{result}\n")
            temp = self.dyno.devices[1].read('motor temperature')
            if temp <= 80:
                result = f"PASSED: Motor within temperature range of {80}C"
            else:
                result = f"FAILED: Motor overheat {temp}C"
            print(result)
            txt.write(f"{result}\n")
            faults = self.dyno.devices[1].check_faults()
            if len(faults) == 0:
                result = f"PASSED: No warnings or faults"
            else:
                result = f"Faults: {self.dyno.devices[1].check_faults()}"
            print(result)
            txt.write(f"{result}\n")
