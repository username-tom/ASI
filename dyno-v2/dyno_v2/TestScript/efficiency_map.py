# ASI Includes
from dyno_v2.TestScript.cyclic_test_jason import *
from dyno_v2.Module.asi_controller import ASIController

class EfficiencyMapTest(CyclicTest):

    def __init__(
            self,
            dyno,
            *args,
            **kwargs
            # use_barcode=False,
            # motor_type=None,
            # barcode=None,
            # sn=None
    ):
        """
        Efficiency Map Test

        Parameters:
            dyno : ASIDynoModule, required
            kwargs: dict, required
                {use_barcode : bool, required |
                barcode1 : dict, required |
                sn1 : str, required |
                note : str, required}
        """
        super().__init__(dyno, *args, **kwargs)

    def parse_test_args(self):
        self.efficiency_map_args()

    def logging_setup(self):
        self.single_logging_setup()

    def test(self):
        # self.logging_setup()
        # self.parse_cooldown()

        # Load test variables

        # self.log_barcode()
        #
        # # self.dyno.backup_parameters()
        # self.dyno.DUT.backup_parameters(f"{self.dyno.logdir / 'DUT Efficiency mapping parameters.xml'}")
        # if isinstance(self.dyno.BRK, ASIController):
        #     self.dyno.BRK.backup_parameters(f"{self.dyno.logdir / 'BRK parameters.xml'}")
        #
        # startTime = datetime.now()
        # try:
        self.dyno.cycle(
            hold_setup=self.dyno.efficiency_map_step,
            **self.args
        )
            # for cycle in range(self.cycle):
            #
            #     # Reset return parameters
            #     extra = f"{speeds[cycle]}"
            #     header = self.dyno.getcsvline(getnames=True)
            #     header.append('Efficiency Map Flag')
            #     self.dyno.extra_logging(file_name=extra, header=header)
            #
            #     self.current_cycle = cycle + 1
            #     print(f"-------------------\n{datetime.now()} - Starting cycle {self.current_cycle}/{self.cycle}")
            #     print(f"Testing speed: {int(speeds[cycle])} rpm")
            #
            #     startRun = datetime.now()
            #
            #     def efficiency_map_flag(torque):
            #         torque_slope = (self.max_torque - torque) / self.settleTime
            #         if self.dyno.DUT.log_params['motor rpm'].Value > int(speeds[cycle]) - 40:  # Before motor slows down
            #             return 1
            #         elif self.dyno.DUT.log_params['motor current'].Value <= self.rated_motor_current - 2:  # Motor on boundary curve
            #             return 2
            #         elif self.dyno.DUT.log_params['motor current'].Value > self.rated_motor_current - 2:
            #             if torque_slope < 1.5 / self.settleTime:
            #                 return 3
            #             else:
            #                 return 2
            #         else:
            #             return 0
            #
            #     #### Start of Efficiency Map duplicate ###
            #     self.dyno.DUT.remote_speed_mode(speed=int(speeds[cycle]), motoring_current=motoring[cycle])
            #     sleep(2)
            #
            #     self.dyno.BRK.start()
            #     self.dyno.BRK.set_torque(0)
            #     sleep(2)
            #     faults = self.dyno.DUT.check_faults()
            #
            #     if faults:
            #         print(f"Registered faults: {faults}")
            #         if str(faults).find("over current"):
            #             # print("Assuming Inst. Over-current and trying to baby it...")
            #             self.dyno.DUT.remote_speed_mode(speed=int(speeds[cycle]) / 2.0, motoring_current=25)
            #             self.dyno.DUT.clear_faults()
            #             sleep(10)
            #             self.dyno.DUT.remote_speed_mode(speed=int(speeds[cycle]), motoring_current=25)
            #             sleep(10)
            #             self.dyno.DUT.remote_speed_mode(speed=int(speeds[cycle]), motoring_current=motoring[cycle])
            #             faults = self.dyno.DUT.check_faults()
            #             if faults:
            #                 print(f"This fault won't clear! Test aborted\n{faults}")
            #                 self.testing = False
            #                 self.dyno.testing = False
            #
            #
            #     # settle after initial speed command
            #     sleep(5)
            #
            #     # ramp torque with constant-time wait, and log SS dataline
            #     cur_torque = int(MinTorque[cycle])
            #
            #     while (cur_torque < MaxTorque[cycle] and
            #            self.dyno.PA.getMeasurement("Torque") < LoadCellLimit[cycle] - 0.5):
            #         self.dyno.BRK.ramp_to(target=cur_torque, step=10, period=self.settleTime)
            #
            #         # curSpeed = self.dyno.PA.getMeasurement("Motor Speed")  # doesn't consistently represent current RPM
            #         curSpeed = self.dyno.DUT.get_rpm()
            #         pre_torque = self.max_torque
            #         try:
            #             t = self.dyno.PA.getMeasurement("Torque")
            #             if self.max_torque < t:
            #                 self.max_torque = t
            #             me = self.dyno.PA.getMeasurement("Motor Efficiency")
            #             if self.max_efficiency < me < 100:
            #                 self.max_efficiency = me
            #         except (TypeError, AttributeError):
            #             pass
            #
            #         if curSpeed > (50 if int(speeds[cycle]) >= 1000 else 10):
            #             sleep(self.settleTime)
            #             to_log = self.dyno.getcsvline()
            #             to_log.append(efficiency_map_flag(pre_torque))
            #             self.dyno.extra_line(file_name=extra, custom=True, data=to_log)
            #             cur_torque += TorqueStep[cycle]
            #         else:
            #             break
            #     #### End of Efficiency Map duplicate ###
            #
            #     self.dyno.stop_test()
            #     self.log_result(cycle, startRun, int(speeds[cycle]))
            #     self.max_efficiency = 0
            #     self.max_torque = 0
            #     # if self.testing and self.dyno.testing:
            #     if cycle + 1 < self.cycle:
            #         print(f'-------------------\n{datetime.now()} - Cooldown\n')
            #         self.handle_cooldown()
            #     else:
            #         break
        # except TestInterrupt:
        #     pass
        # finally:
        #
        #     print('\n-------------------\nEnd of Test\n')
        #     self.dyno.stop_logging()
        #     delta = (datetime.now() - startTime).total_seconds() / 60
        #     print(f"Run duration: {delta:.2f} minutes")

    def post_test(self):
        if len(self.dyno.extra_files) == self.args['total_steps']:
            if self.args['note'] is not None and self.args['note'] != '':
                affix = f" - {self.args['note']}"
            else:
                affix = False

            if self.args['effi_target']:  # motor
                self.dyno.plot_efficiency_map(internal=True,
                                              title=f"Efficiency Map{affix if affix else ''}",
                                              ratio=self.args['ratio'],
                                              cutoff_data='Motor Efficiency',
                                              cutoff=(0, 87))
                self.dyno.plot_efficiency_map(internal=False,
                                              title=f"Efficiency Map{affix if affix else ''}",
                                              ratio=self.args['ratio'],
                                              cutoff_data='Motor Efficiency',
                                              cutoff=(0, 87))
                self.dyno.plot_torque_constant(internal=True,
                                               title=f"Torque Constant{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Motor Efficiency',
                                               cutoff=(0, 87))
                self.dyno.plot_torque_constant(internal=False,
                                               title=f"Torque Constant{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Motor Efficiency',
                                               cutoff=(0, 87))
                self.dyno.plot_motor_power_map(internal=False,
                                               title=f"Motor Power Map{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Motor Efficiency',
                                               cutoff=(0, 87))
                self.dyno.plot_motor_power_map(internal=True,
                                               title=f"Motor Power Map{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Motor Efficiency',
                                               cutoff=(0, 87))
            else:  # controller
                self.dyno.plot_efficiency_map(internal=True,
                                              title=f"Efficiency Map{affix if affix else ''}",
                                              z_data='Controller Efficiency',
                                              ratio=self.args['ratio'],
                                              cutoff_data='Controller Efficiency',
                                              cutoff=(0, 100))
                self.dyno.plot_efficiency_map(internal=False,
                                              title=f"Efficiency Map{affix if affix else ''}",
                                              z_data='Controller Efficiency',
                                              ratio=self.args['ratio'],
                                              cutoff_data='Controller Efficiency',
                                              cutoff=(0, 100))
                self.dyno.plot_torque_constant(internal=True,
                                               title=f"Torque Constant{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Controller Efficiency',
                                               cutoff=(0, 100))
                self.dyno.plot_torque_constant(internal=False,
                                               title=f"Torque Constant{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Controller Efficiency',
                                               cutoff=(0, 100))
                self.dyno.plot_motor_power_map(internal=False,
                                               title=f"Motor Power Map{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Controller Efficiency',
                                               cutoff=(0, 100))
                self.dyno.plot_motor_power_map(internal=True,
                                               title=f"Motor Power Map{affix if affix else ''}",
                                               ratio=self.args['ratio'],
                                               cutoff_data='Controller Efficiency',
                                               cutoff=(0, 100))

    # run = cyclic_test

    # def log_result(self, cycle=None, start=None, speed=None):
    #     result_txt = self.dyno.logdir / "Efficiency Mapping result.txt"
    #     txt = open(result_txt, "a")
    #     txt.write(f'Cycle {cycle + 1}/{self.cycle}\n')
    #     print(f'Cycle {cycle + 1}/{self.cycle}')
    #
    #     txt.write(f'Speed {speed}\n')
    #     print(f'Speed {speed}\n')
    #
    #     result = f"Duration: {(datetime.now() - start).total_seconds() / 60:.1f} minutes\n"
    #     print(result)
    #     txt.write(result)
    #
    #     result = f"Max Torque: {self.max_torque}\n" \
    #              f"Max Motor Efficiency: {self.max_efficiency}\n"
    #     print(result)
    #     txt.write(result)
    #
    #     faults = self.dyno.DUT.check_faults()
    #     if len(faults) == 0:
    #         result = f"No warnings or faults\n"
    #     else:
    #         result = f"Faults: {self.dyno.DUT.check_faults()}\n"
    #     print(result)
    #     txt.write(f"{result}\n\n")
    #     txt.close()

