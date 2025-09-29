import signal
from dyno_v2.Module.ASIDynoModule import ASIDynoModule
from datetime import datetime
from time import sleep


class LoRPMStepDown:

    def __init__(self, dyno: ASIDynoModule):
        self.dyno = dyno
        self.speeds = [180, 150, 120, 75, 38, 30, 20, 10]
        self.durations = [10, 5, 5, 5, 10, 10, 10, 10]

    def test(self):
        startTime = datetime.now()
        self.dyno.start_logging(0.1)
        sleep(5)
        print("Starting Driver")
        for d, speed in zip(self.durations, self.speeds):
            print(f"Target RPM: {speed}")
            self.dyno.DUT.remote_speed_mode(speed=speed, motoring_current=100)
            sleep(d)

        self.dyno.DUT.stop_remote_motor()
        delta = (datetime.now() - startTime).total_seconds() / 60
        print(f"Test duration: {delta:.2f} minutes")


if __name__ == "__main__":
    dyno = ASIDynoModule(config="DYNO-Cedar-PRODUCTION")

    def sigint_handler(signum, frame):
        dyno.stop_test()
        sleep(3)
        dyno.stop_logging()
        exit(-2)

    signal.signal(signal.SIGINT, sigint_handler)

    test = LoRPMStepDown(dyno)
    test.test()
