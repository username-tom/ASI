import sys
sys.path.extend(['C:\\Users\\twu\\PycharmProjects\\dyno-v2'])
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime, timedelta
from threading import Thread

PORT = "COM25"
BAUD_RATE = 115200
# PORT = "PCAN_USBBUS1"
# BAUD_RATE = 500000
MB_ADDRESS = 1
REMOTE_SPEED_COMMAND = 100
REMOTE_MOTORING_CURRENT = 25
REMOTE_BRAKING_CURRENT = 25
THROTTLE_MIN = 0.85
THROTTLE_MAX = 4.12
TEST_TIMEOUT = 60
RESULTS = {
    "Speed Throttle tests":          False,
    "Speed Remote tests":            False,
    "Torque Throttle tests":         False,
    "Torque Pedal tests":            False,
    "Torque Remote tests":           False,
    "Torque Speed Throttle tests":   False,
    "Torque Speed Pedal tests":      False,
    "Torque Speed Remote tests":     False
}


def control_test(watchdog, mode=0):
    rated_rpm = watchdog.dut.read("Rated motor speed")
    throttle_deadband = watchdog.dut.read("Throttle deadband threshold")
    remote_rpm = int(rated_rpm / 2)
    if mode == 0:  # Speed Control
        # TC 10.6.1 Speed Control
        print("TC 10.6.1 Speed Control")
        print("Throttle tests...")
        watchdog.dut.turn_off_communication_timeout()
        throttle = THROTTLE_MIN + throttle_deadband + 0.5
        while watchdog.dut.read("vehicle speed") == 0:
            print(f"Remote Throttle Voltage set to {throttle}")
            watchdog.dut.write("Remote Throttle Voltage", throttle)
            throttle += 0.01
            sleep(2)
        print(f"Motor started with throttle voltage: {throttle - 0.01}")

        throttle_setpoint = watchdog.dut.read("throttle setpoint")
        vehicle_speed = watchdog.dut.read("vehicle speed")
        print(f"Remote Throttle Voltage set to {throttle+1}")
        watchdog.dut.write("Remote Throttle Voltage", throttle + 1)
        sleep(2)
        # increasing throttle setpoint should lead to increase in vehicle speed
        if watchdog.dut.read("throttle setpoint") > throttle_setpoint and watchdog.dut.read(
                "vehicle speed") > vehicle_speed:
            print(f"Remote Throttle Voltage set to {throttle+2}")
            watchdog.dut.write("Remote Throttle Voltage", throttle + 2)
            sleep(2)

            if watchdog.dut.read("throttle setpoint") > throttle_setpoint and watchdog.dut.read(
                    "vehicle speed") > vehicle_speed:
                print(f"Remote Throttle Voltage set to {THROTTLE_MIN}")
                watchdog.dut.write("Remote Throttle Voltage", THROTTLE_MIN)
                print("Throttle test case passed!")
                RESULTS["Speed Throttle tests"] = True
                sleep(2)
        else:
            print("Vehicle speed not increasing responding to throttle increase!")

        # Remote test case
        print("Remote test...")
        p = {"Fault clear": 1,
             "Control command source": 0}  # using remote throttle voltage
        watchdog.update_params(**p)
        print(f"Remote Speed Command in RPM set to {remote_rpm}")
        watchdog.dut.remote_speed_mode(speed=remote_rpm, motoring_current=50)

        startTime = datetime.now()
        running_average = []
        average_window = 5
        average_speed = 0
        while average_speed < remote_rpm * 0.95:
            running_average.append(watchdog.dut.get_rpm())
            if len(running_average) > average_window:
                running_average.pop(0)
                average_speed = sum(running_average) / len(running_average)
            print(f"RPM: {watchdog.dut.get_rpm()}/Average: {average_speed}/{remote_rpm}    ", end="\r")
            sleep(0.5)

            test_duration = (datetime.now() - startTime).total_seconds()
            if test_duration > TEST_TIMEOUT:
                print(f"\nTIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                return
        temp = average_speed
        if (remote_rpm * 0.95) <= average_speed or average_speed <= (remote_rpm * 1.05):
            remote_rpm = int(rated_rpm * 0.75)
            print(f"Remote Throttle Voltage set to {remote_rpm}")
            watchdog.dut.write("Remote Speed Command in RPM", remote_rpm)

            startTime = datetime.now()
            running_average = []
            average_window = 5
            average_speed = 0
            while average_speed < remote_rpm * 0.95:
                running_average.append(watchdog.dut.get_rpm())
                if len(running_average) > average_window:
                    running_average.pop(0)
                    average_speed = sum(running_average) / len(running_average)
                print(f"RPM: {watchdog.dut.get_rpm()}/Average: {average_speed}/{remote_rpm}    ", end="\r")
                sleep(0.5)

                test_duration = (datetime.now() - startTime).total_seconds()
                if test_duration > TEST_TIMEOUT:
                    print(f"\nTIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                    return

            if (temp * 0.95) <= average_speed or average_speed <= (temp * 1.05):
                print("Remote test case passed!")
                RESULTS["Speed Remote tests"] = True
                watchdog.dut.stop_remote_motor()
                sleep(3)

    elif mode == 1:  # Torque Control
        print("TC 10.6.2 Torque Control")
        print("Throttle tests...")
        p = {"Fault clear": 1,
             "Control command source": 4,
             "Speed regulator mode": 1,
             "Throttle sensor source": 5,  # using remote throttle voltage
             "Assist mode source": 0}
        watchdog.update_params(**p)
        watchdog.dut.turn_off_communication_timeout()

        throttle = THROTTLE_MIN + throttle_deadband + 0.5
        while watchdog.dut.read("vehicle speed") == 0:
            print(f"Remote Throttle Voltage set to {throttle}")
            watchdog.dut.write("Remote Throttle Voltage", throttle)
            throttle += 0.01
            sleep(2)

        starting_throttle = throttle-0.01
        print(f"Motor started with throttle voltage: {starting_throttle}")
        sleep(0.01)
        torque_reference = watchdog.dut.read("torque reference")
        vehicle_speed = watchdog.dut.read("vehicle speed")
        print(f"Throttle: {starting_throttle} | Speed: {vehicle_speed} | Torque Ref: {torque_reference}", end="")
        watchdog.dut.write("Remote Throttle Voltage", starting_throttle + 1)
        sleep(3)
        new_torque = watchdog.dut.read("torque reference")
        print(f" | New Torque Ref: {new_torque}")
        if new_torque > torque_reference:
            print("Throttle test passed!")
            RESULTS["Torque Throttle tests"] = True
        else:
            print("Throttle test failed")

        print(f"Remote Throttle Voltage set to {THROTTLE_MIN}")
        watchdog.dut.write("Remote Throttle Voltage", THROTTLE_MIN)
        sleep(2)
        while watchdog.dut.read("vehicle speed") > 0:
            continue

        # Pedal test case
        print("Pedal tests...")
        p = {"Fault clear": 1,
             "Assist mode source": 5,
             "Display assist level command": 0.1}
        watchdog.update_params(**p)
        watchdog.dut.turn_off_communication_timeout()
        try:
            input("Press Enter to start Pedal tests...")
            print("Pedaling...")
            startTime = datetime.now()
            while watchdog.dut.get_rpm() < 0.6 * rated_rpm:
                print(f"RPM: {watchdog.dut.get_rpm()}/{rated_rpm}     ", end="\r")

                test_duration = (datetime.now() - startTime).total_seconds()
                if test_duration > TEST_TIMEOUT:
                    print(f"TIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                    return
            print("")
            test_duration = (datetime.now() - startTime).total_seconds()
            if test_duration > TEST_TIMEOUT:
                print(f"TIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                return

        except KeyboardInterrupt:
            print(f"\nSkipping pedal test")
            return
        else:
            print("RPM reached")
        torque_reference = watchdog.dut.read("torque reference")
        sleep(3)

        input("Press Enter to increase assist level...")
        print("Pedaling...")
        watchdog.dut.write("Display assist level command", 1)
        startTime = datetime.now()
        while watchdog.dut.read("torque reference") < 8 * torque_reference:
            print(f"RPM: {watchdog.dut.get_rpm()}/{rated_rpm}     ", end="\r")

            test_duration = (datetime.now() - startTime).total_seconds()
            if test_duration > TEST_TIMEOUT:
                print(f"\nTIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                return
        print("\nRPM reached")
        print("Pedal test passed!")
        RESULTS["Torque Pedal tests"] = True
        sleep(3)

        # Remote test case
        print("Remote test...")
        torque_command = 1  # % of max torque
        p = {"Fault clear": 1,
             "Control command source": 0}  # using remote throttle voltage
        watchdog.update_params(**p)

        print(f"Remote torque command set to {torque_command}")
        watchdog.dut.remote_torque_mode(torque=torque_command)
        sleep(3)

        vehicle_speed = watchdog.dut.read("vehicle speed")
        print(f"Remote torque command set to {torque_command*5}")
        watchdog.dut.remote_torque_mode(torque=torque_command * 5)
        sleep(3)
        if watchdog.dut.read("vehicle speed") > vehicle_speed:
            print("Remote test passed!")
            RESULTS["Torque Remote tests"] = True
        else:
            print("Remote test failed")

        watchdog.dut.stop_remote_motor()

        while watchdog.dut.read("vehicle speed") > 0:
            continue

    elif mode == 2:  # Torque Control w/ Speed Limit
        print("TC 10.6.3 Torque Control w/ Speed Limit")
        print("Throttle tests...")
        p = {"Fault clear": 1,
             "Control command source": 4,
             "Speed regulator mode": 2,
             "Throttle sensor source": 5,  # using remote throttle voltage
             "Assist mode source": 0}
        watchdog.update_params(**p)
        max_speed = watchdog.dut.read("Vehicle maximum speed (Race mode Throttle max speed)")

        throttle = THROTTLE_MIN + throttle_deadband + 1
        while watchdog.dut.read("vehicle speed") == 0:
            print(f"Remote Throttle Voltage set to {throttle}")
            watchdog.dut.write("Remote Throttle Voltage", throttle)
            throttle += 0.01
            sleep(2)

        starting_throttle = throttle-0.01
        print(f"Motor started with throttle voltage: {starting_throttle}")

        startTime = datetime.now()
        running_average = []
        average_window = 5
        average_speed = 0
        while average_speed < max_speed * 0.95:
            running_average.append(watchdog.dut.read("vehicle speed"))
            if len(running_average) > average_window:
                running_average.pop(0)
                average_speed = sum(running_average) / len(running_average)
            print(f"Speed: {watchdog.dut.read('vehicle speed')}/Average: {average_speed}/{max_speed}    ", end="\r")
            sleep(0.5)

            test_duration = (datetime.now() - startTime).total_seconds()
            if test_duration > TEST_TIMEOUT:
                print(f"\nTIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                return

        temp = average_speed
        print(f"\nIncreasing throttle...")
        watchdog.dut.write("Remote Throttle Voltage", starting_throttle + 1)

        startTime = datetime.now()
        running_average = []
        average_window = 5
        average_speed = 0
        while average_speed < max_speed * 0.95:
            running_average.append(watchdog.dut.read("vehicle speed"))
            if len(running_average) > average_window:
                running_average.pop(0)
                average_speed = sum(running_average) / len(running_average)
            print(f"Speed: {watchdog.dut.read('vehicle speed')}/Average: {average_speed}/{max_speed}    ", end="\r")
            sleep(0.5)

            test_duration = (datetime.now() - startTime).total_seconds()
            if test_duration > TEST_TIMEOUT:
                print(f"TIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                return

        if 0.9 * temp <= average_speed or average_speed <= 0.9 * temp:
            print(f"\nThrottle test passed!")
            RESULTS["Torque Speed Throttle tests"] = True
        else:
            print(f"\nThrottle test failed")

        print(f"Stopping Motor\nRemote Throttle Voltage set to {THROTTLE_MIN}")
        watchdog.dut.write("Remote Throttle Voltage", THROTTLE_MIN)
        while watchdog.dut.read("vehicle speed") > 0:
            continue

        # Pedal test case
        print("Pedal tests...")
        p = {"Fault clear": 1,
             "Assist mode source": 0}
        watchdog.update_params(**p)
        max_speed = watchdog.dut.read("Vehicle maximum speed (Race mode PAS max speed)")
        print("Max speed: " + str(max_speed))
        input("Press Enter to start Pedal tests...")
        print("Pedaling...")

        startTime = datetime.now()
        running_average = []
        average_window = 5
        average_speed = 0
        try:
            while average_speed < max_speed * 0.95:
                running_average.append(watchdog.dut.read("vehicle speed"))
                if len(running_average) > average_window:
                    running_average.pop(0)
                    average_speed = sum(running_average) / len(running_average)
                print(f"Speed: {watchdog.dut.read('vehicle speed')}/Average: {average_speed}/{max_speed}    ", end="\r")
                sleep(0.5)

                test_duration = (datetime.now() - startTime).total_seconds()
                if test_duration > TEST_TIMEOUT:
                    print(f"TIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                    return

            print(f"\nRPM reached")
        except KeyboardInterrupt:
            print("Skipping pedal test...")
            return

        # Check if speed control responds to change
        max_speed -= 5
        print(f"Increase max speed to {max_speed} kph")
        watchdog.dut.write("Vehicle maximum speed (Race mode PAS max speed)", max_speed)
        input("Press Enter to start Pedal tests...")
        print("Pedaling...")

        startTime = datetime.now()
        running_average = []
        average_window = 5
        average_speed = 0
        try:
            while average_speed < max_speed * 0.95:
                running_average.append(watchdog.dut.read("vehicle speed"))
                if len(running_average) > average_window:
                    running_average.pop(0)
                    average_speed = sum(running_average) / len(running_average)
                print(f"Speed: {watchdog.dut.read('vehicle speed')}/Average: {average_speed}/{max_speed}    ", end="\r")
                sleep(0.5)

                test_duration = (datetime.now() - startTime).total_seconds()
                if test_duration > TEST_TIMEOUT:
                    print(f"TIMEOUT: Current test is taking longer than {TEST_TIMEOUT} seconds")
                    return
        except KeyboardInterrupt:
            print("Skipping pedal test...")
        else:
            print(f"\nRPM reached")
            print("Pedal test passed!")
            RESULTS["Torque Speed Pedal tests"] = True
        finally:
            watchdog.dut.write("Vehicle maximum speed (Race mode PAS max speed)", 25)
            sleep(3)

        # Remote test case
        print("Remote test...")
        torque_command = 5  # % of max torque
        p = {"Fault clear": 1,
             "Control command source": 0}  # using remote throttle voltage
        watchdog.update_params(**p)
        print(f"Remote torque command set to {torque_command}")
        watchdog.dut.remote_speed_torque_mode(speed=0.25 * rated_rpm, torque=torque_command, motoring_current=100)
        sleep(2)

        vehicle_speed = watchdog.dut.get_rpm()
        print("Increasing torque command...")
        watchdog.dut.remote_speed_torque_mode(speed=0.75 * rated_rpm, torque=torque_command * 2, motoring_current=100)
        sleep(3)
        if watchdog.dut.get_rpm() > vehicle_speed:
            print("Remote test passed!")
            RESULTS["Torque Speed Remote tests"] = True
        else:
            print("Remote test failed")

        watchdog.dut.stop_remote_motor()


if __name__ == "__main__":
    # init for TC 10.6.1
    parameters = {"Fault clear": 1,
                  "Control command source": 1,
                  "Speed regulator mode": 0,
                  "Throttle sensor source": 5,  # using remote throttle voltage
                  "Remote Throttle Voltage": THROTTLE_MIN,
                  "Assist mode source": 0}
    # Init Watchdog
    dog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    # dog = Watchdog(port=PORT, baud=BAUD_RATE, mb_address=MB_ADDRESS, params=parameters, pvalues=values, j1939=True)
    # dog.dut.load_run_params("Parameter Files/Run parameters for ASI controller TC 10.6 6021.csv")

    # TC 10.6.1 Speed Control
    control_test(dog, 0)

    # TC 10.6.2 Torque Control
    control_test(dog, 1)

    # TC 10.6.3 Torque Control w/ Speed Limit
    control_test(dog, 2)

    print("tests Results:")
    for key, result in RESULTS.items():
        print(f"{key}: {result}")
