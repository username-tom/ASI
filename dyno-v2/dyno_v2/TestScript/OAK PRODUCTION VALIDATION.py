from ASIDynoModule import ASIDynoModule
from production_validation import ProductionValidation
from time import sleep
import signal

if __name__ == "__main__":
    dyno = ASIDynoModule(config="OAK_PV", log_folder="C:\\ProductionValidation\\OAK")

    def sigint_handler(signum, frame):
        print(f"\n\n\n\n\n\n\n\nInterrupted")
        dyno.stop_test()
        sleep(3)
        dyno.stop_logging()
        dyno.plot_basic()
        exit(-2)

    signal.signal(signal.SIGINT, sigint_handler)

    test = ProductionValidation(dyno)
    test.production_validation()
