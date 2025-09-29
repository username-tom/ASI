# ASI Includes
import logging

from dyno_v2.TestScript.cyclic_test_jason import *
from dyno_v2.Module.asi_controller import ASIController

class CyclicOpenLoopTest(CyclicTest):

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
        Cyclic Line Reactor Test

        Parameters:
            dyno : ASIDynoModule, required
            kwargs: dict, required {
                use_barcode : bool, required |
                barcode1 : dict, required |
                sn1 : str, required |
                note : str, required |
                barcode2 : dict, required |
                sn2 : str, required}
        """
        super().__init__(dyno, *args, **kwargs)

    def parse_test_args(self):
        self.open_loop_args()

        self.log_barcode()

    def logging_setup(self):
        self.single_logging_setup()

    def test(self):
        # self.logging_setup()
        #
        # self.log_barcode()
            # self.dyno.devices[1].set_access_level(0)

        # self.dyno.devices[1].backup_parameters(f"{self.dyno.logdir / 'Line Reactor Test.xml'}")

        # if not self.testing or not self.dyno.testing:
        #     return

        # startTime = datetime.now()
        print(f"Open Loop {'Voltage' if self.args['mode'] == 2 else 'Current'} Mode")
        print(f"Total Cycles {self.args['total_cycles']}")
        if self.args['mode'] == 2:
            print(f"Open Loop Modulation {self.args['target']} pu")
        elif self.args['mode'] == 3:
            print(f"Open Loop Current {self.args['target'] * self.args['rated_motor_current']} A")
        print(f"Open Loop Frequency {self.args['frequency']}")
        print(f"Temperature Range [{self.args['lower_limit']} - {self.args['upper_limit']}] \u00B0C")

        # try:
        self.dyno.cycle(
            ramp_command=self.dyno.devices[1].open_loop_ramp,
            hold_condition=self.dyno.cyclic_hold_condition,
            hold_command=self.dyno.cyclic_hold_timeout,
            watchdog=bool(self.dyno.config['watchdog']),
            **self.args
        )
            # for cycle in range(self.cycle):
            #     # if not self.testing or not self.dyno.testing:
            #     #     break
            #
            #     self.current_cycle = cycle + 1
            #     print(f"-------------------\n{datetime.now()} - Starting cycle {self.current_cycle}/{self.cycle}")
            #
            #     startRun = datetime.now()
            #
            #     # Ramping up
            #     for i in range(5):
            #         if self.mode == 2:
            #             self.dyno.devices[1].voltage_mode(motoring_current=100,
            #                                        modulation=self.modulation * (i + 1) / 5,
            #                                        frequency=self.frequency)
            #         elif self.mode == 3:
            #             self.dyno.devices[1].current_mode(motoring_current=100,
            #                                        current=self.rated_motor_current * self.modulation * (i + 1) / 5,
            #                                        frequency=self.frequency)
            #         sleep(self.ramp / 5)
            #
            #     # Wait until controller temperature reach max
            #     while self.dyno.devices[1].read('controller temperature') < self.max_temperature:
            #         sleep(1)
            #         # if not self.testing or not self.dyno.testing:
            #         #     raise TestInterrupt
            #         if (datetime.now() - startRun).total_seconds() >= 600:
            #             logging.error('Current cycle timed out')
            #             raise TestError
            #
            #     self.dyno.stop_test()
            #     self.log_result(cycle, startRun)
            #
            #     # Cooldown
            #     # if self.testing and self.dyno.testing:
            #     if cycle + 1 < self.cycle:
            #         print(f'-------------------\n{datetime.now()} - Cooldown\n')
            #         # Wait until controller temperature cools down to min
            #         while self.dyno.devices[1].read('controller temperature') > self.min_temperature:
            #             sleep(1)
            #                 # if not self.testing:
            #                 #     raise TestInterrupt
            #     else:
            #         break
        # except TestInterrupt:
        #     pass
        # finally:
        #     print('\n-------------------\nEnd of Test\n')
        #     self.dyno.stop_logging()
        #     delta = (datetime.now() - startTime).total_seconds() / 60
        #     print(f"Run duration: {delta:.2f} minutes")

    # run = cyclic_test

    # def log_result(self, cycle=None, start=None, speed=None):
    #     result_txt = self.dyno.logdir / "Line Reactor Test.txt"
    #     txt = open(result_txt, "a")
    #     txt.write(f'Cycle {cycle + 1}/{self.cycle}\n')
    #     print(f'Cycle {cycle + 1}/{self.cycle}')
    #
    #     result = f"Duration: {(datetime.now() - start).total_seconds() / 60:.1f} minutes\n"
    #     print(result)
    #     txt.write(result)
    #
    #     faults = self.dyno.devices[1].check_faults()
    #     if len(faults) == 0:
    #         result = f"No warnings or faults\n"
    #     else:
    #         result = f"Faults: {self.dyno.devices[1].check_faults()}\n"
    #     print(result)
    #     txt.write(f"{result}\n\n")
    #     txt.close()

