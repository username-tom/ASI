# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep

# COM & Motor parameters for TC 10.1.2
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1
REMOTE_SPEED_COMMAND = 50
REMOTE_MOTORING_CURRENT = 25
REMOTE_BRAKING_CURRENT = 25

if __name__ == "__main__":
    parameters = {"Control command source": 0,
                  "Speed regulator mode": 0,
                  "Remote maximum motoring current": REMOTE_MOTORING_CURRENT,
                  "Remote maximum braking current": REMOTE_BRAKING_CURRENT,
                  "Remote speed command": REMOTE_SPEED_COMMAND}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Initialization successful!")

    # TC 10.1.1 parameters
    parameters = {"TE Configuration": 1}

    # running without TE pedal mode
    watchdog.dut.start_remote_motor()
    sleep(1.25)
    watchdog.dut.stop_remote_motor()
    sleep(2)

    watchdog.dut.start_remote_motor()
    sleep(3)
    watchdog.dut.stop_remote_motor()
    sleep(2)

    if watchdog.dut.get_rpm() == 0:
        print("Controller operational without TE pedal mode!")
    else:
        print("Controller not operational, even without TE pedal mode!")

    watchdog.dut.set_access_level(4)
    watchdog.update_params(**parameters)
    watchdog.dut.set_access_level(0)
    print("TE pedal mode on!")

    # running with TE pedal mode
    watchdog.dut.start_remote_motor()
    sleep(1.25)
    watchdog.dut.stop_remote_motor()
    sleep(2)

    watchdog.dut.start_remote_motor()
    sleep(3)
    watchdog.dut.stop_remote_motor()
    sleep(2)

    print("Controller should be in risk address mode")
    watchdog.dut.read("Remote state command")
    sleep(1)

