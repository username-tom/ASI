# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime

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
    watchdog.dut.set_access_level(4)
    watchdog.dut.write("TE Configuration", 0)
    watchdog.dut.set_access_level(0)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Initialization successful!")

    parameters = {"TE Configuration": 3}
    run_for = 8
    watchdogInt = 0.25
    print("Watchdog interval: " + str(watchdogInt) + "s")

    # tests 1: Ensure heartbeat signal can keep the controller alive
    watchdog.update_timeout(1000, 750)

    print("Motor running with timeout threshold for " + str(watchdogInt * 2 * run_for) + "s")
    watchdog.run_for(watchdogInt, run_for)

    # tests 2: Ensure heartbeat signal works with TE Configuration -> 3
    watchdog.dut.set_access_level(4)
    print("Changing TE Configuration at " + str(datetime.now().time().isoformat()))
    watchdog.update_params(**parameters)
    # watchdog.dut.set_access_level(0)

    print("Motor running with TE Configuration for " + str(watchdogInt * 2 * run_for) + "s")
    watchdog.run_till_fault(watchdogInt, run_for)

    # tests 3: Ensure risk address state is triggered by slow comm
    watchdogInt = 3.2
    print("Watchdog interval: " + str(watchdogInt) + "s")
    print("Timeout threshold -> 3000ms")
    watchdog.update_timeout(3000, 2600)

    print("Controller should be in risk address mode")
    watchdog.run_till_fault(watchdogInt, run_for)
