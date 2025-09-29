# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime

# COM & Motor parameters for TC 10.9.1 Throttle Sensitivity
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

if __name__ == "__main__":
    parameters = {"Control command source": 1,  # Throttle
                  "Speed regulator mode": 0,  # Speed
                  "Throttle sensor source": 5,  # Network
                  "Remote Throttle Voltage": 1,
                  "Throttle off voltage": 1,
                  "Throttle full voltage": 4,
                  "Features2": 0}  # 0000 0000 0000 0000
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Initialization successful!")

    # Check off state
    if watchdog.dut.read("throttle setpoint") != 0:
        print("FAILED: Throttle not off at off state!")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        exit()

    # Check midpoint without throttle sensitivity
    print("Setting Remote Throttle Voltage to 2.5\nThrottle Setpoint should be 0.5")
    watchdog.dut.write("Remote Throttle Voltage", 2.5)
    sleep(1)

    # Check throttle setpoint
    setpoint = watchdog.dut.read("throttle setpoint")
    if 0.495 <= setpoint <= 0.505:
        pass
    else:
        print(f"FAILED: Throttle setpoint {setpoint} not in 0.495 - 0.505 range!")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        exit()

    # Throttle back to off
    print("Setting Remote Throttle Voltage to 1")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    # Enabling throttle sensitivity
    print("Setting Features2 bit 12 to 1\nEnabling Throttle Sensitivity")
    watchdog.dut.write("Features2", 1 << 12)
    sleep(1)

    # Check throttle sensitivity bit
    if watchdog.dut.read("Features2") != (1 << 12):
        print("FAILED: Features2 Not updated!")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        exit()

    # Check throttle sensitivity = 1
    print("Setting Throttle Sensitivity to 1\nThrottle should behave the same")
    watchdog.dut.write("Throttle Sensitivity", 1)
    sleep(0.5)

    # Check midpoint
    print("Setting Remote Throttle Voltage to 2.5\nThrottle Setpoint should be 0.5")
    watchdog.dut.write("Remote Throttle Voltage", 2.5)
    sleep(1)

    setpoint = watchdog.dut.read("throttle setpoint")
    if 0.495 <= setpoint <= 0.505:
        pass
    else:
        print(f"FAILED: Throttle setpoint {setpoint} not in 0.495 - 0.505 range!")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        exit()

    # Throttle back to off
    print("Setting Remote Throttle Voltage to 1")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    # Check throttle sensitivity = 0
    print("Setting Throttle Sensitivity to 1\nThrottle should behave the same")
    watchdog.dut.write("Throttle Sensitivity", 0)
    sleep(0.5)

    # Check midpoint
    print("Setting Remote Throttle Voltage to 2.5\nThrottle Setpoint should be 0.5")
    watchdog.dut.write("Remote Throttle Voltage", 2.5)
    sleep(1)

    setpoint = watchdog.dut.read("throttle setpoint")
    if 0.495 <= setpoint <= 0.505:
        pass
    else:
        print(f"FAILED: Throttle setpoint {setpoint} not in 0.495 - 0.505 range!")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        exit()

    # Throttle back to off
    print("Setting Remote Throttle Voltage to 1")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    # Check throttle sensitivity = 0.5
    print("Setting Throttle Sensitivity to 1\nThrottle should behave the same")
    watchdog.dut.write("Throttle Sensitivity", 0.5)
    sleep(0.5)

    # Check midpoint
    print(f"Setting Remote Throttle Voltage to 2.5\nThrottle Setpoint should be {(0.5 ** 0.5):03f}")
    watchdog.dut.write("Remote Throttle Voltage", 2.5)
    sleep(1)

    setpoint = watchdog.dut.read("throttle setpoint")
    if 0.704 <= setpoint <= 0.709:
        pass
    else:
        print(f"FAILED: Throttle setpoint {setpoint} not in 0.704 - 0.709 range!")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        exit()

    # Throttle back to off
    print("Setting Remote Throttle Voltage to 1")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    # Check throttle sensitivity = 2
    print("Setting Throttle Sensitivity to 1\nThrottle should behave the same")
    watchdog.dut.write("Throttle Sensitivity", 2)
    sleep(0.5)

    # Check midpoint
    print(f"Setting Remote Throttle Voltage to 2.5\nThrottle Setpoint should be {(0.5 ** 2):03f}")
    watchdog.dut.write("Remote Throttle Voltage", 2.5)
    sleep(1)

    setpoint = watchdog.dut.read("throttle setpoint")
    if 0.245 <= setpoint <= 0.255:
        pass
    else:
        print(F"FAILED: Throttle setpoint {setpoint} not in 0.245 - 0.255 range!")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        exit()

    # Throttle back to off
    print("Setting Remote Throttle Voltage to 1")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    print("PASSED: Throttle Sensitivity Test Finished\nPower cycle to reset parameters")