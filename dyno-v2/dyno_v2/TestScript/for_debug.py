from tkinter import messagebox
from time import sleep
from datetime import datetime, timedelta
from dyno_v2.Module.TestABC import TestABC
from dyno_v2.Module.exceptions import TestInterrupt


class ForDebug(TestABC):

    def __init__(self, dyno, *args, **kwargs):
        super().__init__(dyno, **kwargs)

    def parse_test_args(self):
        self.debug_args()

    def test(self):
        # self.logging_setup()
        self.dyno.devices[1].remote_speed_mode(speed=200)
        # startTime = datetime.now()
        endTime = self.startTime + timedelta(seconds=int(float(self.dyno.config["basic_testtime"])))
        # while datetime.now() < endTime:
        for _ in range(self.args['total_cycles']):
            try:
                self.dyno.test_outputs['current_cycle'] += 1
                self.wait(1)
                if endTime != self.startTime + timedelta(seconds=float(self.dyno.config["basic_testtime"])):
                    endTime = self.startTime + timedelta(seconds=float(self.dyno.config["basic_testtime"]))
            except TestInterrupt:
                break

    # run = debug

    def interrupt(self):
        print('pre-interrupt')
        self.testing = False
        self.dyno.testing = False
        if self.watchdog:
            self.stop_watchdog()
        raise TestInterrupt

    def logging_setup(self):
        self.debug_logging_setup()

    def log_result(self, cycle=None, i=None, start=None):
        print(self.dyno.test_outputs['current_cycle'])

    def post_test(self, **kwargs):
        print('post test')