# ASI Includes
from dyno_v2.TestScript.cyclic_test_jason import *
from dyno_v2.Module.asi_controller import ASIController

class TemperatureMapTest(CyclicTest):

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
        self.temperature_map_args()

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
        self.dyno.parse_cooldown()

        if self.args['brake'] == 2:
            if self.args['device'] == 'motor':
                self.dyno.wait_dut_motor_temp()
            else:
                self.dyno.wait_dut_controller_temp()
        else:
            if self.args['device'] == 'motor':
                self.dyno.wait_brk_motor_temp()
            else:
                self.dyno.wait_brk_controller_temp()

        temp = self.dyno.devices[1 if self.args['brake'] == 2 else 2].read(f'{self.args["device"]} temperature')
        if temp < self.dyno.cooldown_parameters['cooldown']:
            rated_rpm = self.dyno.devices[1 if self.args['brake'] == 2 else 2].read('Rated motor speed')
            self.dyno.devices[1 if self.args['brake'] == 2 else 2].remote_speed_mode(speed=int(0.5 * rated_rpm))
            self.dyno.int_event.wait(5)
            self.dyno.devices[self.args['brake']].start()
            self.dyno.int_event.wait(2)
            self.dyno.devices[self.args['brake']].set_torque(2)

            while temp < self.dyno.cooldown_parameters['cooldown']:
                sleep(1)
                temp = self.dyno.devices[1 if self.args['brake'] == 2 else 2].read(f'{self.args["device"]} temperature')

            self.dyno.stop_test()

        self.dyno.cycle(
            hold_setup=self.dyno.temperature_map_step,
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
        if self.args['note'] is not None and self.args['note'] != '':
            affix = f" - {self.args['note']}"
        else:
            affix = False

        try:
            self.dyno.plot_temperature_map(internal=True,
                                          title=f"Temperature Map{affix if affix else ''}",
                                          ratio=self.args['ratio'],
                                          z_data=f'{"DUT" if self.args["brake"] == 2 else "BRK" } '
                                                 f'{self.args["device"]} temperature',
                                          levels=None,)
            self.dyno.plot_temperature_map(internal=False,
                                          title=f"Temperature Map{affix if affix else ''}",
                                          ratio=self.args['ratio'],
                                          z_data=f'{"DUT" if self.args["brake"] == 2 else "BRK" } '
                                                 f'{self.args["device"]} temperature',
                                          levels=None,)
        except TypeError:
            print("Failed to generate graphs. ")

