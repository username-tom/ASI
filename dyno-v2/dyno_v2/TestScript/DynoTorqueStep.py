import signal
import sys
from time import sleep

from dyno_v2.Module.ASIDynoModule import ASIDynoModule


class DynoTorqueStep:

    def __init__(self, dyno: ASIDynoModule):
        self.dyno = dyno
        self.torque_ratio = 5
        
    def step(self, torque=15., speed=2000., step=5, period=2.):
        self.dyno.start_logging(0.1)
        print("Starting driver")
        self.dyno.DUT.remote_speed_mode(speed=speed, motoring_current=100, braking_current=100)
        sleep(3)
        while self.dyno.DUT.get_rpm() < speed * 0.9:
            sleep(3)
        sleep(3)
        print("Starting brake")
        self.dyno.BRK.start()
        # self.dyno.BRK.set_torque(self.torque_ratio * torque)
        self.dyno.BRK.ramp_to(target=self.torque_ratio * torque, step=step, period=period)

        sleep(1)
        
        current_rpm = self.dyno.DUT.get_rpm()
        while abs(self.dyno.DUT.get_rpm() - current_rpm) > 5 and abs(self.dyno.DUT.get_rpm()) < 3000:
            try:
                sleep(1)
                current_rpm = self.dyno.DUT.get_rpm()
            except TypeError:
                continue
        sleep(5)
        self.dyno.stop_test()
        sleep(3)
        self.dyno.stop_logging()
        self.dyno.plot_basic()


if __name__ == "__main__":

    dyno = ASIDynoModule(config="HiSpeed-Cedar-PRODUCTION")

    def sigint_handler(signum, frame):
        dyno.stop_test()
        sleep(3)
        dyno.stop_logging()
        dyno.plot_basic()
        exit(-2)
        
    signal.signal(signal.SIGINT, sigint_handler)

    test = DynoTorqueStep(dyno)
    if len(sys.argv) == 5:
        test.step(float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]))
    elif len(sys.argv) == 2 and "-h" in str(sys.argv[1]):
        print(f"py DynoTorqueStep.py [float: max torque] [test speed] [int: ramp step] [float: ramp period]\n"
              f"                     -help, -h for info")
    else:
        print(f"Invalid number of arguments\nFor more info use -help or -h")
        exit(-1)

