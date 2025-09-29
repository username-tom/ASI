# ASI Includes
from ASIDynoModule import ASIDynoModule
import rundown_test
import signal
from time import sleep

if __name__ == "__main__":
    dyno = ASIDynoModule(config="HiSpeed-Cedar-PRODUCTION", log_folder="C:\\CEDARTEST\\RESULTS")

    def sigint_handler(signum, frame):
        print(f"\n\n\n\n\n\n\n\nInterrupted")
        dyno.stop_test()
        sleep(3)
        dyno.stop_logging()
        dyno.plot_basic()
        exit(-2)

    signal.signal(signal.SIGINT, sigint_handler)

    rundown_test.rundown_test(dyno)
