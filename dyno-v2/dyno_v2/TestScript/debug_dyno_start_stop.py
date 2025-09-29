from dyno_v2.Module.TestABC import TestABC
from dyno_v2.Module.ASIDynoModule import *


class DebugStartStop(TestABC):

    def __init__(self, dyno: ASIDynoModule):
        # self.dyno = dyno
        # self.line = None
        # self.testing = True
        super().__init__(dyno)

    def debug(self):
        start_time = datetime.now()
        self.dyno.start_logging(1)
        sleep(2)
        self.dyno.DUT.remote_speed_mode(speed=2000)
        sleep(2)
        self.dyno.BRK.start()
        self.dyno.BRK.set_torque(0)
        sleep(2)
        for _ in range(10):
            try:
                self.dyno.BRK.set_torque(self.dyno.BRK.cur_torque + 1)
                self.status(start_time)
            except AttributeError:
                pass
            if not self.testing:
                break
            sleep(1)
            print(f"\33[{len(self.line)}A")
        if self.dyno is not None and self.dyno.is_logging_enabled:
            self.dyno.stop_test()
            self.dyno.stop_logging()
        print()

    run = debug

    def interrupt(self):
        self.testing = False

    def status(self, start):
        self.line = ["", "", "", "", "", "", ""]
        self.line[0] = f"{'TEST': ^76s}"
        self.line[1] = f"{'DUT': ^18s}|{'BRK': ^18s}|{'YOKO': ^18s}|{'Time': ^18s}|"
        done = "#" * int(self.dyno.BRK.cur_torque / 10 * 16)

        self.line[2] = (f"{'curAmp'}: {self.dyno.DUT.read('motor current'):.2f} A",
                        f"{'Torque'}: {self.dyno.BRK.cur_torque} %",
                        f"{'Torque'}: ",
                        f"{'Duration'}: {(datetime.now() - start).total_seconds():.1f}")
        self.line[3] = (f"{'Speed'}: {str(self.dyno.DUT.get_rpm())}",
                        f"{'Speed' if isinstance(self.dyno.BRK, ASIController) else ''}: "
                        f"{self.dyno.BRK.get_rpm() if isinstance(self.dyno.BRK, ASIController) else ''}",
                        f"{'Speed'}: ",
                        f"{'Est.Time'}: 10s")
        self.line[4] = (f"{'DUT. FB'}: {self.dyno.DUT.in_foldback()}",
                        f"",
                        f"",
                        f"")
        self.line[5] = (f"{'D.C. Temp'}: {self.dyno.DUT.read('controller temperature')}",
                        f"{'B.C. Temp'}: "
                        f"{self.dyno.BRK.read('controller temperature') if isinstance(self.dyno.BRK, ASIController) else ''}",
                        f"",
                        f"")
        self.line[6] = (f"{'D.M. Temp'}: {self.dyno.DUT.read('motor temperature')}",
                        f"{'B.M. Temp'}: "
                        f"{self.dyno.BRK.read('motor temperature') if isinstance(self.dyno.BRK, ASIController) else ''}",
                        f"",
                        f"[{done: <16s}]")

        print(f"{self.line[0]}\n{self.line[1]}")
        for i in range(len(self.line) - 2):
            for l in self.line[i + 2]:
                print(f"{l: <18s}", end="")
                print(f"|", end="")
            print()

