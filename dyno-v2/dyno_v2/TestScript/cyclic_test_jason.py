# ASI Includes
import pandas as pd
from time import sleep
from datetime import datetime
from threading import Thread
from simple_pid import PID
from dyno_v2.Module.TestABC import TestABC
from dyno_v2.Module.ASIDynoModule import ASIDynoModule
from dyno_v2.Module.exceptions import *
import logging
from dyno_v2.Module.email_alerts import *


class CyclicTest(TestABC):

    def __init__(
            self,
            dyno: ASIDynoModule,
            *args,
            **kwargs,
            # use_barcode=False,
            # motor_type=None,
            # barcode=None,
            # barcode2=None,
            # sn=None,
            # sn2=None
    ):
        """
        Cyclic Test

        Parameters:
            dyno : ASIDynoModule, required
            kwargs: dict, required
                {use_barcode : bool, required |
                barcode1 : dict, required |
                sn1 : str, required |
                note : str, required |
                barcode2 : dict, required |
                sn2 : str, required}
        """
        super().__init__(dyno, *args, **kwargs)
        # self.dyno = dyno
        # self.use_barcode = use_barcode
        # self.motor_type = motor_type
        # self.barcode = barcode
        # self.sn = sn
        # self.line = None
        # self.testing = True
        # self.barcode2 = barcode2
        # self.sn2 = sn2

    def parse_test_args(self):
        self.cyclic_args()

        self.log_barcode()

    def logging_setup(self):
        self.double_logging_setup()
        # extra = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')} - RUNDOWN SS Pts"
        # self.dyno.extra_logging(file_name=extra)
        #
        # return extra

    def test(self):
        # self.logging_setup()
        # if self.dyno.devices[1]:
        #     self.dyno.devices[1].backup_parameters(f"{self.dyno.logdir / 'DUT A parameters.xml'}")
        # if self.dyno.devices[2]:
        #     self.dyno.devices[2].backup_parameters(f"{self.dyno.logdir / 'DUT B parameters.xml'}")
        #
        # self.parse_cooldown()



        # if self.dyno.devices[1]:
        #     a_rated_current = float(self.dyno.devices[1].read("Rated motor current"))
        # if self.dyno.devices[2]:
        #     b_rated_current = float(self.dyno.devices[2].read("Rated motor current"))

        # startTime = datetime.now()
        # self.startTime = startTime

        # try:
        self.dyno.cycle(
            ramp_command=self.dyno.cyclic_ramp,
            hold_setup=self.dyno.cyclic_hold_setup,
            watchdog=bool(self.dyno.config['watchdog']),
            **self.args
        )

        # for cycle in range(self.cycle):
        #     self.current_cycle = cycle + 1
        #     cycle_start = datetime.now()
        #     print(f"-------------------\n{datetime.now()} - Starting cycle {self.current_cycle}/{self.cycle}")
        #     for i in range(len(self.total_steps)):
        #         self.current_step = i + 1
        #         print(f"Starting step {i + 1}/{len(self.total_steps)}")
        #         startRun = datetime.now()
        #
        #         # def get_foldbacks():
        #         #     """
        #         #     Obtain regen system foldbacks
        #         #     These foldbacks are meant to reduce the regen current on the load motor if the driving motor is overheating.
        #         #     Foldback should be a number from 0 to 1 and will be multiplied by the required regen current. 1 = 100%, 0 = 0%.
        #         #     """
        #         #     if self.dyno.devices[2]:
        #         #         if float(a_b_lo[i]) != 0 and float(a_b_hi[i]) != 0:
        #         #             a_fdbk_lo = float(a_b_lo[i])
        #         #             a_fdbk_hi = float(a_b_hi[i])
        #         #             self.a_fdbk_coeff = 1.0
        #         #             b_motor_temp = self.dyno.devices[2].read("motor temperature")
        #         #             if a_fdbk_lo <= b_motor_temp <= a_fdbk_hi:
        #         #                 self.a_fdbk_coeff = (b_motor_temp - a_fdbk_lo) / (a_fdbk_hi - a_fdbk_lo)
        #         #                 if self.a_fdbk_coeff < 0:
        #         #                     self.a_fdbk_coeff = 0
        #         #                 if self.a_fdbk_coeff > 1:
        #         #                     self.a_fdbk_coeff = 1
        #         #                 self.a_fdbk_coeff = abs(1 - self.a_fdbk_coeff)
        #         #             elif b_motor_temp > a_fdbk_hi:
        #         #                 self.a_fdbk_coeff = 0.0
        #         #             elif b_motor_temp < a_fdbk_lo:
        #         #                 self.a_fdbk_coeff = 1.0
        #         #         else:
        #         #             self.a_fdbk_coeff = 1.0
        #         #     if self.dyno.devices[1]:
        #         #         if float(b_a_lo[i]) != 0 and float(b_a_hi[i]) != 0:
        #         #             b_fdbk_lo = float(b_a_lo[i])
        #         #             b_fdbk_hi = float(b_a_hi[i])
        #         #             self.b_fdbk_coeff = 1.0
        #         #             a_motor_temp = self.dyno.devices[1].read("motor temperature")
        #         #             if b_fdbk_lo <= a_motor_temp <= b_fdbk_hi:
        #         #                 self.b_fdbk_coeff = (a_motor_temp - b_fdbk_lo) / (b_fdbk_hi - b_fdbk_lo)
        #         #                 if self.b_fdbk_coeff < 0.0:
        #         #                     self.b_fdbk_coeff = 0.0
        #         #                 if self.b_fdbk_coeff > 1.0:
        #         #                     self.b_fdbk_coeff = 1.0
        #         #                 self.b_fdbk_coeff = abs(1 - self.b_fdbk_coeff)
        #         #             elif a_motor_temp > b_fdbk_hi:
        #         #                 self.b_fdbk_coeff = 0.0
        #         #             elif a_motor_temp < b_fdbk_lo:
        #         #                 self.b_fdbk_coeff = 1.0
        #         #         else:
        #         #             self.b_fdbk_coeff = 1.0
        #         #
        #         # get_foldbacks()
        #
        #         # Ramping up
        #         print(f'-------------------\n{datetime.now()} - Starting over {ramp[i]} seconds\n')
        #
        #         self.dyno_speed_ramp(float(self.a[i]), float(self.b[i]), float(ramp[i]))
        #
        #         # Hold for step duration
        #         print(f'-------------------\n{datetime.now()} - Holding: {int(self.total_steps[i])} seconds\n')
        #         if self.foldback_overwrite:
        #             print("Foldback overwrite hold time is ENABLED")
        #         if self.foldback_driver:
        #             print("Foldback based on driving controller")
        #         if self.cd_in_step:
        #             print("Cooldown between total_steps is ENABLED")
        #         if self.cd_on_driver:
        #             print("Cooldown based on driving controller")
        #
        #         startHold = datetime.now()
        #         # print(regen_b[i], self.b_fdbk_coeff, b_rated_current)
        #         if self.watchdog:
        #             self.watchdog_enabled = True
        #         if self.dyno.devices[1] and float(self.a[i]) != 0:
        #             self.driver = 'DUT'
        #             self.dyno.devices[1].remote_speed_mode(speed=float(self.a[i]),
        #                                             motoring_current=float(motoring_a[i]) / a_rated_current * 100,
        #                                             braking_current=float(regen_a[i]) / a_rated_current * 100,
        #                                             watchdog=self.watchdog)
        #             if self.dyno.devices[2]:
        #                 sleep(3)
        #                 if abs(self.dyno.devices[1].get_rpm()) > abs(0.5 * float(self.a[i])):
        #                     self.dyno.devices[2].start(2)
        #                 else:
        #                     print("DUT (A) RPM out of safety range of target holding RPM")
        #                     self.testing = False
        #         elif self.dyno.devices[2] and float(self.b[i]) != 0:
        #             self.driver = 'BRK'
        #             self.dyno.devices[2].remote_speed_mode(speed=float(self.b[i]),
        #                                             motoring_current=float(motoring_b[i]) / b_rated_current * 100,
        #                                             braking_current=float(regen_b[i]) / b_rated_current * 100,
        #                                             watchdog=self.watchdog)
        #             if self.dyno.devices[1]:
        #                 sleep(3)
        #                 if abs(self.dyno.devices[2].get_rpm()) > abs(0.5 * float(self.b[i])):
        #                     self.dyno.devices[1].start(2)
        #                 else:
        #                     print("BRK (DUT B) RPM out of safety range of target holding RPM")
        #                     self.testing = False
        #
        #         if isinstance(ki, list) and isinstance(kp, list):
        #             set_point = 0
        #             if float(self.a[i]) != 0:
        #                 set_point = (abs(int(self.a[i])) / int(self.a[i])) * (abs(int(self.a[i])) - 50)
        #                 # set_point = a_rated_current
        #             elif float(self.b[i]) != 0:
        #                 set_point = (abs(int(self.b[i])) / int(self.b[i])) * (abs(int(self.b[i])) - 50)
        #                 # set_point = b_rated_current
        #             # print(set_point)
        #             self._PID = PID(Kp=float(kp[i]), Ki=float(ki[i]), Kd=0,
        #                             setpoint=set_point,
        #                             sample_time=self.dyno.tPID,
        #                             output_limits=limits)
        #             self._PID.set_auto_mode(False)
        #         else:
        #             self._PID = None
        #
        #         if self._PID:
        #             sleep(1)
        #             self._PID.set_auto_mode(True, 0)
        #
        #         while self.testing and (datetime.now() - startHold).total_seconds() < int(self.total_steps[i]):
        #
        #             # Foldback overwrite
        #             if self.foldback_overwrite:
        #                 if self.foldback_driver:  # Driver based foldback
        #                     if self.driver == 'DUT':
        #                         if self.dyno.devices[1] and self.dyno.devices[1].in_foldback():
        #                             print("DUT (A) in foldback")
        #                             print(self.dyno.devices[1].check_faults())
        #                             break
        #                     elif self.driver == 'BRK':
        #                         if self.dyno.devices[2] and self.dyno.devices[2].in_foldback():
        #                             print("BRK (DUT B) in foldback")
        #                             print(self.dyno.devices[2].check_faults())
        #                             break
        #                 else:  # Any foldback
        #                     if self.dyno.devices[1]:
        #                         if self.dyno.devices[1].in_foldback():
        #                             print("DUT (A) in foldback")
        #                             print(self.dyno.devices[1].check_faults())
        #                             break
        #                     if self.dyno.devices[2]:
        #                         if self.dyno.devices[2].in_foldback():
        #                             print("BRK (DUT B) in foldback")
        #                             print(self.dyno.devices[2].check_faults())
        #                             break
        #
        #             if self._PID:
        #                 new_value = self._PID((abs(self.dyno.devices[1].get_rpm()) + abs(self.dyno.devices[2].get_rpm())) * 0.5)
        #                 if float(self.a[i]) != 0:
        #                     # new_value = self._PID(self.dyno.devices[1].get_rpm())
        #                     # print(new_value)
        #                     self.dyno.cur_torque = new_value
        #                     self.dyno.devices[2].set_torque(new_value)
        #                 elif float(self.b[i]) != 0:
        #                     # new_value = self._PID(self.dyno.devices[2].get_rpm())
        #                     # print(new_value)
        #                     self.dyno.cur_torque = new_value
        #                     self.dyno.devices[1].set_torque(new_value)
        #                 sleep(self.dyno.tPID)
        #             else:
        #                 sleep(1)
        #
        #             # if (self.dyno.devices[1] and self.dyno.devices[1].read('motor current') < float(motoring_a[i]) or
        #             #         self.dyno.devices[2] and self.dyno.devices[2].read('motor current') < float(motoring_b[i])):
        #             #     pid_adjustment = (pid_adjustment + 100) / 2
        #
        #             # get_foldbacks()
        #             # if self.dyno.devices[1]:
        #             #     self.dyno.devices[1].write("Remote maximum braking current",
        #             #                         (float(regen_a[i]) * self.a_fdbk_coeff) / a_rated_current * 100)
        #             # if self.dyno.devices[2]:
        #             #     self.dyno.devices[2].write("Remote maximum braking current",
        #             #                         (float(regen_b[i]) * self.b_fdbk_coeff) / b_rated_current * 100)
        #         if self.watchdog:
        #             self.stop_watchdog()
        #
        #         # Ramping down
        #         print(f'-------------------\n{datetime.now()} - Stopping over {ramp[i]} seconds\n')
        #         if i + 1 == len(self.total_steps):
        #             if self.cooldown_type is None:
        #                 self.dyno_speed_ramp(float(self.a[0]), float(self.b[0]), float(ramp[i]))
        #             else:
        #                 self.dyno_speed_ramp(0, 0, float(ramp[i]))
        #         else:
        #             self.dyno_speed_ramp(float(self.a[i]), float(self.b[i]), float(ramp[i]))
        #
        #         # Cooldown in between total_steps
        #         if self.cd_in_step and i + 1 < len(self.total_steps):
        #             print(f'-------------------\n{datetime.now()} - Cooldown between step\n')
        #             self.handle_cooldown()
        #
        #         self.log_result(cycle, i, startRun)
        #
        #     if cycle + 1 < self.cycle:
        #         print(f'-------------------\n{datetime.now()} - Cooldown between cycle\n')
        #         self.handle_cooldown()
        #         if cycle == 0:
        #             self.dyno.plot_cycle('First Cycle')
        #     self.cycle_duration = (datetime.now() - cycle_start).total_seconds()
        # self.cycle_duration = self.dyno.test_outputs['cycle_duration']
        # except TestInterrupt:
        #     pass
        # except TestError as e:
        #     print(e)
        # finally:
        #     print('\n-------------------\n')
        #     if self.watchdog:
        #         self.stop_watchdog()
        #     self.dyno.stop_test()
        #     self.dyno.stop_logging()
        #     delta = (datetime.now() - startTime).total_seconds() / 60
        #     print(f"Run duration: {delta:.2f} minutes")
        #

    def post_test(self, **kwargs):
        self.dyno.plot_cycle()
        self.dyno.plot_error("DUT warnings")
        self.dyno.plot_error("DUT faults")

    def log_result(self):
        result_txt = self.dyno.logdir / "cyclic result.txt"
        with open(result_txt, "a") as txt:

            result = f"Total Duration: {(datetime.now() - self.startTime).total_seconds() / 60:.1f} minutes\n"
            print(result)
            txt.write(result)

            result = f"Total Cycles Ran: {self.dyno.test_outputs['current_cycle']}/{self.args['total_cycles']}\n"
            print(result)
            txt.write(result)

            # try:
            #     faults = self.dyno.devices[1].check_faults()
            #     if len(faults) == 0:
            #         result = f"No warnings or faults\n"
            #     else:
            #         result = f"Faults: {faults}\n"
            #     print(result)
            #     txt.write(f"{result}\n\n")
            # except AttributeError:
            #     pass

    # def parse_cooldown(self):
    #     if pd.isna(self.dyno.config['cycle_type']) or self.dyno.config['cycle_type'] == '':
    #         return
    #     self.cooldown_type = int(self.dyno.config['cycle_type'])
    #     if pd.isna(self.dyno.config['cycle_cd_driver']):
    #         self.cd_on_driver = False
    #     else:
    #         self.cd_on_driver = bool(self.dyno.config['cycle_cd_driver'])
    #     if self.cooldown_type == 0:
    #         self.cooldown = self.dyno.config['cycle_cd']
    #         if pd.isna(self.cooldown):
    #             self.cooldown = 0
    #         else:
    #             self.cooldown = float(self.cooldown)
    #     elif self.cooldown_type == 1:
    #         self.cooldown = self.dyno.config['cycle_dut_motor_temp']
    #         if pd.isna(self.cooldown):
    #             self.cooldown = self.dyno.devices[1].read('motor temperature') + 10
    #         else:
    #             self.cooldown = int(self.cooldown)
    #     elif self.cooldown_type == 2:
    #         self.cooldown = self.dyno.config['cycle_dut_temp']
    #         if pd.isna(self.cooldown):
    #             self.cooldown = self.dyno.devices[1].read('controller temperature') + 10
    #         else:
    #             self.cooldown = int(self.cooldown)
    #     elif self.cooldown_type == 3:
    #         self.cooldown = self.dyno.config['cycle_brk_motor_temp']
    #         if pd.isna(self.cooldown):
    #             self.cooldown = self.dyno.devices[2].read('motor temperature') + 10
    #         else:
    #             self.cooldown = int(self.cooldown)
    #     elif self.cooldown_type == 4:
    #         self.cooldown = self.dyno.config['cycle_brk_temp']
    #         if pd.isna(self.cooldown):
    #             self.cooldown = self.dyno.devices[2].read('controller temperature') + 10
    #         else:
    #             self.cooldown = int(self.cooldown)
    #     else:
    #         print('Bad cycle type! Will only run 1 iteration')
    #     # print(self.cooldown)
    #
    # def handle_cooldown(self):
    #     if self.cooldown_type is None:
    #         return
    #     if self.dyno.devices[1]:
    #         self.dyno.devices[1].stop_remote_motor()
    #     if self.dyno.devices[2]:
    #         self.dyno.devices[2].stop_remote_motor()
    #     # Cooldown between speeds
    #     if self.cooldown_type == 0:
    #         if self.cooldown > 1:  # Time
    #             for t in range(int(self.cooldown)):
    #                 print(f"{self.cooldown - t:.1f} min left")
    #                 for _ in range(60):
    #                     sleep(1)
    #                     if not self.testing:
    #                         return
    #         elif self.cooldown > 0:
    #             for t in range(int(self.cooldown * 60)):
    #                 sleep(1)
    #                 if not self.testing:
    #                     return
    #     elif self.cooldown_type == 1:
    #         if self.cd_on_driver:
    #             if self.driver == 'DUT' and self.dyno.devices[1]:
    #                 self.wait_dut_motor_temp()
    #             elif self.driver == 'BRK' and self.dyno.devices[2]:
    #                 self.wait_brk_motor_temp()
    #         else:
    #             self.wait_dut_motor_temp()
    #     elif self.cooldown_type == 2:
    #         if self.cd_on_driver:
    #             if self.driver == 'DUT' and self.dyno.devices[1]:
    #                 self.wait_dut_controller_temp()
    #             elif self.driver == 'BRK' and self.dyno.devices[2]:
    #                 self.wait_brk_controller_temp()
    #         else:
    #             self.wait_dut_controller_temp()
    #     elif self.cooldown_type == 3:
    #         if self.cd_on_driver:
    #             if self.driver == 'DUT' and self.dyno.devices[1]:
    #                 self.wait_dut_motor_temp()
    #             elif self.driver == 'BRK' and self.dyno.devices[2]:
    #                 self.wait_brk_motor_temp()
    #         else:
    #             self.wait_brk_motor_temp()
    #     elif self.cooldown_type == 4:
    #         if self.cd_on_driver:
    #             if self.driver == 'DUT' and self.dyno.devices[1]:
    #                 self.wait_dut_controller_temp()
    #             elif self.driver == 'BRK' and self.dyno.devices[2]:
    #                 self.wait_brk_controller_temp()
    #         else:
    #             self.wait_brk_controller_temp()
    #
    # def dyno_speed_ramp(self, dut=2000., brk=1000., duration=10.):
    #     # no ramping when duration <= 0
    #     if duration <= 0 and dut == 0 and brk == 0: # Stop test if all values are 0
    #         self.dyno.stop_test()
    #         return
    #     elif duration <= 0 and dut == 0: # Stop both motor and restart BRK if dut is 0
    #         if self.dyno.devices[1]:
    #             # self.dyno.devices[1].remote_speed_mode(speed=dut, speed_command=0, braking_current=20)
    #             # self.dyno.devices[1].stop()
    #             # sleep(2)
    #             self.dyno.stop_test()
    #         if self.dyno.devices[2]:
    #             self.dyno.devices[2].remote_speed_mode(speed=brk, speed_command=0)
    #         return
    #     elif duration <= 0 and brk == 0: # Stop both motor and restart DUT if brk is 0
    #         if self.dyno.devices[2]:
    #             # self.dyno.devices[1].remote_speed_mode(speed=dut, speed_command=0, braking_current=20)
    #             # self.dyno.devices[2].stop()
    #             self.dyno.stop_test()
    #             # sleep(2)
    #         if self.dyno.devices[1]:
    #             self.dyno.devices[1].remote_speed_mode(speed=dut, speed_command=0)
    #         return
    #     elif duration <= 0: # Run both motors at desired speed if not 0
    #         if self.dyno.devices[1]:
    #             self.dyno.devices[1].remote_speed_mode(speed=dut, speed_command=0, braking_current=10)
    #         if self.dyno.devices[2]:
    #             self.dyno.devices[1].remote_speed_mode(speed=brk, speed_command=0, braking_current=10)
    #         return
    #
    #     # Ramping
    #     try:
    #         if self.dyno.devices[1]:
    #             step_a = (dut - self.dyno.devices[1].get_rpm()) / 10
    #             # step_a = (dut) / 10
    #         if self.dyno.devices[2]:
    #             step_b = (brk - self.dyno.devices[2].get_rpm()) / 10
    #             # step_b = (brk) / 10
    #         for i in range(10):
    #             if self.dyno.devices[1]:
    #                 print('DUT 1')
    #                 self.dyno.devices[1].remote_speed_mode(speed=dut - (9 - i) * step_a, speed_command=0,
    #                                                 braking_current=0 if dut == 0 else 50,
    #                                                 motoring_current=20 if dut == 0 else 100)
    #             if self.dyno.devices[2]:
    #                 print('DUT 2')
    #                 self.dyno.devices[2].remote_speed_mode(speed=brk - (9 - i) * step_b, speed_command=0,
    #                                                 braking_current=0 if brk == 0 else 50,
    #                                                 motoring_current=20 if brk == 0 else 100)
    #             sleep(duration / 10)
    #             if not self.testing:
    #                 self.dyno.stop_test()
    #                 return
    #     except AttributeError:
    #         return
    #     except CommLossError:
    #         self.testing = False
    #         return
    #     # if dut == brk == 0:
    #     #     self.dyno.stop_test()
    #
    # def wait_dut_motor_temp(self):
    #     print(f'Waiting for DUT (A) motor temperature to reach {self.cooldown}\u00B0C')
    #     while self.cooldown < self.dyno.devices[1].read('motor temperature'):
    #         sleep(1)
    #         if not self.testing:
    #             return
    #
    # def wait_brk_motor_temp(self):
    #     print(f'Waiting for BRK (DUT B) motor temperature to reach {self.cooldown}\u00B0C')
    #     while self.cooldown < self.dyno.devices[2].read('motor temperature'):
    #         sleep(1)
    #         if not self.testing:
    #             return
    #
    # def wait_dut_controller_temp(self):
    #     print(f'Waiting for DUT (A) controller temperature to reach {self.cooldown}\u00B0C')
    #     while self.cooldown < self.dyno.devices[1].read('controller temperature'):
    #         sleep(1)
    #         if not self.testing:
    #             return
    #
    # def wait_brk_controller_temp(self):
    #     print(f'Waiting for BRK (DUT B) controller temperature to reach {self.cooldown}\u00B0C')
    #     while self.cooldown < self.dyno.devices[2].read('controller temperature'):
    #         sleep(1)
    #         if not self.testing:
    #             return


