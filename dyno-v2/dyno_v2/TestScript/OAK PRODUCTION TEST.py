# ASI Includes
from ASIDynoModule import ASIDynoModule
import rundown_test
import signal
from time import sleep

if __name__ == "__main__":
    dyno = ASIDynoModule(config="DYNO-Oak-PRODUCTION", log_folder="C:\\DynoResults\\OAK")

    def sigint_handler(signum, frame):
        print(f"\n\n\n\n\n\n\n\nInterrupted")
        dyno.stop_test()
        sleep(3)
        dyno.stop_logging()
        dyno.plot_basic()
        exit(-2)

    signal.signal(signal.SIGINT, sigint_handler)

    # Motor discovery if driver can't move
    while not dyno.DUT.can_move:
        discovery = dyno.DUT.motor_discovery(9)
        print(f"autotune Rs: {discovery[0]} | autotune Ls: {discovery[1]}")
        print(f"autotune rated rpm: {discovery[2]} | autotune hall offset angle: {discovery[3]}")
        for i, d in enumerate(discovery[4]):
            print(f"Hall sector{i}: {d}")
        dyno.DUT.can_motor_move()

    Rundown_Test.rundown_test(dyno)
