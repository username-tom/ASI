# ASI Includes
from simple_pid import PID
from dyno_v2.Module.ASIDynoModule import ASIDynoModule
from dyno_v2.Module.asi_controller import ASIController
from dyno_v2.Module.TestABC import TestABC
from dyno_v2.Module.abb_acs800 import AbbAcs800
from dyno_v2.Module.exceptions import *
from time import sleep
from datetime import datetime, timedelta


class ControllerThermalMax(TestABC):
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
        Controller Thermal Max Test

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
        self.ctm_args()

    # # Tested with a Cedar motor and an ABB controller as the torque / brake
    # def hold_current(self, targetI):
    #     kp = float(self.dyno.config["ctm_kp_current"])
    #     ki = float(self.dyno.config["ctm_ki_current"])
    #     # set up PID controller with Ks appropriate for holding current
    #     self.dyno.start_pid(self.dyno.pid_parameters['interval'], 'BRK', kp, ki, 0, 'motor current', targetI)
    #     # self._PID = PID(Kp=kp, Ki=ki, Kd=0, setpoint=targetI, sample_time=self.dyno.tPID, output_limits=(0, 100))
    #     # self._PID.set_auto_mode(False)
    #     # self._PID.set_auto_mode(True, self.dyno.cur_torque)
    #
    #     # time_end = datetime.now() + timedelta(minutes=self.dyno.TestTime)
    #     # time_ss = datetime.now() + timedelta(minutes=self.dyno.pid_parameters['ssTime'])
    #
    #     # current = self.dyno.devices[1].read("motor current")
    #     ninety_start = None
    #     # startTime = datetime.now()
    #     while (self.dyno.pid_enabled and self.testing and self.dyno.testing and
    #            not self.dyno.devices[1].in_foldback()):
    #
    #         # speed = self.dyno.devices[PA].getMeasurement("Motor Speed")
    #         # prev_current = current
    #         # current = self.dyno.devices[1].read("motor current")
    #
    #         # try:
    #         #     newTorque = self._PID(current)
    #         # except TypeError:
    #         #     newTorque = self._PID(prev_current)
    #         # if abs(self.dyno.cur_torque - newTorque) > 0.05:
    #         #     time_ss = datetime.now() + timedelta(minutes=self.dyno.SSTime)
    #
    #         # self.dyno.cur_torque = newTorque
    #         # self.dyno.devices[2].set_torque(newTorque)
    #
    #         if ninety_start is None and self.dyno.devices[1].read("motor current") >= 0.9 * targetI:
    #             ninety_start = datetime.now()
    #
    #         sleep(self.dyno.pid_parameters['interval'])
    #
    #         if not self.testing:
    #             self.dyno.stop_test()
    #             self.dyno.stop_logging()
    #             return
    #
    #     self.dyno.test_outputs['ninety'] = (datetime.now() - ninety_start).total_seconds()
    #     self.dyno.stop_pid()
    #
    #     # return current
    #
    # # Tested with a Cedar motor and an ABB controller as the torque / brake
    # def hold_speed(self, holdspeed):
    #     kp = float(self.dyno.config["ctm_kp_speed"])
    #     ki = float(self.dyno.config["ctm_ki_speed"])
    #
    #     self.dyno.devices[1].remote_speed_mode(speed=holdspeed)
    #
    #     # set up PID controller with Ks appropriate for holding speed as a controller folds back
    #     self.dyno.start_pid(self.dyno.pid_parameters['interval'], 'BRK', kp, ki, 0, 'motor rpm',
    #                         holdspeed - int(self.dyno.config["ctm_diff"]))
    #     # self._PID = PID(Kp=kp, Ki=ki, Kd=0, setpoint=holdspeed - int(self.dyno.config["ctm_diff"]),
    #     #                 sample_time=self.dyno.tPID,
    #     #                 output_limits=(0, 100))
    #     # self._PID.set_auto_mode(False)
    #     # self._PID.set_auto_mode(True, self.dyno.cur_torque)
    #
    #     # speed = self.dyno.devices[PA].getMeasurement("Motor Speed")
    #     # startTime = datetime.now()
    #     # time_end = startTime + timedelta(minutes=self.dyno.TestTime)
    #     # time_ss = startTime + timedelta(minutes=self.dyno.pid_parameters['ssTime'])
    #     while self.dyno.pid_enabled and self.testing and self.dyno.testing:
    #
    #         # speed = self.dyno.devices[1].get_rpm()
    #         # current = self.dyno.devices[1].read("motor current")
    #
    #         # try:
    #         #     newTorque = self._PID(speed)
    #         # except TypeError:
    #         #     newTorque = self._PID(self.dyno.devices[PA].getMeasurement("Motor Speed"))
    #         # if abs(self.dyno.cur_torque - newTorque) > 0.05:
    #         #     time_ss = datetime.now() + timedelta(minutes=self.dyno.SSTime)
    #         #
    #         # self.dyno.cur_torque = newTorque
    #         # self.dyno.devices[2].set_torque(self.dyno.cur_torque)
    #
    #         sleep(self.dyno.tPID)
    #
    #         if not self.testing:
    #             self.dyno.stop_test()
    #             self.dyno.stop_logging()
    #             return
    #
    #     self.dyno.stop_pid()
    #
    #         # if time_end != startTime + timedelta(minutes=float(self.dyno.config["basic_testtime"])):
    #         #     time_end = startTime + timedelta(minutes=float(self.dyno.config["basic_testtime"]))
    #
    #     # return speed

    def test(self):

        # self.logging_setup()
        #
        # self.dyno.devices[1].backup_parameters(f"{self.dyno.logdir / 'ThermalMax parameters.xml'}")
        # if isinstance(self.dyno.devices[2], ASIController):
        #     self.dyno.devices[2].backup_parameters(f"{self.dyno.logdir / 'BRK parameters.xml'}")
        #
        # startTime = datetime.now()
        # self.startTime = startTime
        self.dyno.test_outputs['start_temp'] = self.dyno.devices[1].read('controller temperature')

        # try:
        print("Starting Driver")
        self.dyno.devices[1].remote_speed_mode(speed=self.args['opSpeed'])

        sleep(3)

        print("Starting Brake")
        self.dyno.devices[2].start()
        sleep(3)
        # step 1: hold max current until foldback
        # Uncomment below for PID Tuning
        # self.dyno.extra_logging(file_name="PID",
        #                         header=["Time", "Speed", "P", "I", "D", "'-P", "Max - I", "cur_torque"])
        print("CURRENT MODE!!!")
        self.dyno.hold_current(self.args['peakCurrent'])
        try:
            self.dyno.test_outputs['ninety'] = self.dyno.test_outputs['ninety']
        except KeyError:
            self.dyno.test_outputs['ninety'] = -1
        # self.hold_current(targetI=self.args['peakCurrent'])
        if self.args['coarse_speed']:
            self.dyno._logInterval = 60
        self.dyno.test_outputs['foldback_time'] = int((datetime.now() - self.startTime).total_seconds())
        print(f"\n\n")

        # step 2: hold op speed til SS
        print("SPEED MODE!!!")
        print(f"Test time: {self.dyno.TestTime * 60} seconds")
        self.dyno.hold_speed(self.args['opSpeed'])
        # self.hold_speed(holdspeed=self.args['opSpeed'])
        print(f"\n\n")
        # except (KeyboardInterrupt, TestInterrupt):
        #     # print(f"\n\nInterrupted")
        #     pass
        # except TestError as e:
        #     print(e)
        # finally:
        #     self.dyno.stop_test()
        #     self.dyno.stop_logging()
        #     delta = (datetime.now() - startTime).total_seconds() / 60
        #     print(f"Test duration: {delta:.2f} minutes")
        #     self.log_result(start=startTime)

    # run = control_thermal_max

    def interrupt(self):
        self.dyno.pid_parameters['interval'] = 0.1
        self.testing = False
        self.dyno.testing = False
        if self.watchdog:
            self.stop_watchdog()
        raise TestInterrupt

    def log_result(self):
        result_txt = self.dyno.logdir / "ThermalMax result.txt"
        with open(result_txt, "a") as txt:
            for t in [f'ThermalMax Result\n',
                      f'Test started at {self.startTime.strftime("%Y-%m-%d-%H-%M-%S")}\n',
                      f'Starting temperature: {self.dyno.test_outputs["start_temp"]}\u00B0C\n',
                      f'90% Current to Foldback time: {self.dyno.test_outputs["ninety"]:.1f} seconds\n',
                      f'Total foldback time: {self.dyno.test_outputs["foldback_time"]:.1f} seconds\n',
                      f"Test Duration: {(datetime.now() - self.startTime).total_seconds() / 60:.1f} minutes\n"]:
                txt.write(t)
                print(t, end='')

    def post_test(self):
        self.dyno.plot_basic("ControllerThermalMax Result")
        self.dyno.plot_ctm_result()
        self.dyno.plot_ctm_result(title="Pre-foldback", end=self.dyno.test_outputs['foldback_time'])
        self.dyno.plot_error("DUT warnings")
        self.dyno.plot_error("DUT faults")

    def logging_setup(self):
        self.single_logging_setup()

if __name__ == "__main__":
    dyno = ASIDynoModule(config="DYNO-BAC4000-Oak-THERMALMAX-425")

    test = ControllerThermalMax(dyno)
    test.run()
