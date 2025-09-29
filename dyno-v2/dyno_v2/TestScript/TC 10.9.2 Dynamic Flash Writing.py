# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime
from threading import Thread


# COM & Motor parameters for TC 10.9.2 Dynamic Flash Writing
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

def wait_for(time):
    wait_start = datetime.now()
    waiting = True
    while waiting:
        if (datetime.now() - wait_start).total_seconds() < time:
            sleep(1)
        else:
            waiting = False


if __name__ == "__main__":
    parameters = {"Control command source": 1,  # Throttle
                  "Speed regulator mode": 0,  # Speed
                  "Throttle sensor source": 5,  # Network
                  "Remote Throttle Voltage": 1,
                  "Throttle off voltage": 1,
                  "Throttle full voltage": 4,
                  "Dynamic Flash Write Interval (seconds)": 30}  # seconds
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.clear_faults()

    # Reset if device already have dynamic flash feature enabled
    if (int(watchdog.dut.read("Level 1 Features")) & (1 << 3)) >> 3 == 1:
        print("Resetting parameters")
        watchdog.dut.set_access_level(1)
        watchdog.dut.write("Level 1 Features", 0)
        watchdog.dut.save_to_flash()
        input("Power cycle and press Enter to continue")
        watchdog.dut.write("Remote Throttle Voltage", 1)
        watchdog.dut.clear_faults()

    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.set_access_level(1)
    watchdog.dut.write("Level 1 Features", 1 << 3)
    watchdog.dut.save_to_flash()
    input("Power cycle and press Enter to continue")
    watchdog.dut.write("Remote Throttle Voltage", 1)

    def end_of_test():
        # End of test
        watchdog.dut.set_access_level(1)
        watchdog.restore_parameters()
        watchdog.dut.save_to_flash()

    print("Initialization successful!")

    # store current values for dynamic flash writing related parameters
    print("Test Started\nStoring current values")
    motor_on_time_low = watchdog.dut.read('motor on time low')
    motor_on_time_high = watchdog.dut.read('motor on time high')
    odometer_low = watchdog.dut.read('odometer low')
    odometer_high = watchdog.dut.read('odometer high')
    packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    boot_counter = watchdog.dut.read('boot counter')

    input("Power cycle and press Enter to continue")

    # Check packet count
    print("Checking packet count")
    if packet_count > 0:
        print(f"PASSED: Packet count {packet_count}\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {packet_count} did not increase on start!")
        end_of_test()
        exit()

    # Check boot counter
    print("Checking boot counter")
    if watchdog.dut.read('boot counter') > boot_counter:
        print("PASSED: boot counter incremented on start!\n")
    else:
        print(f"FAILED: boot counter {boot_counter} did not increase on start!")
        end_of_test()
        exit()

    # Check Dynamic Flash write Interval
    print("Waiting for 30 seconds")
    wait_thread = Thread(target=wait_for, args=[30])
    wait_thread.start()
    wait_thread.join()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count >= packet_count + 1:
        packet_count = current_packet_count
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} did not increment!")
        end_of_test()
        exit()

    # Check boot counter
    input("Power cycle and press Enter to continue")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)
    print("Checking boot counter")
    current_boot_counter = watchdog.dut.read('boot counter')
    if current_boot_counter >= boot_counter + 1:
        boot_counter = current_boot_counter
        print("PASSED: boot counter incremented on start!\n")
    else:
        print(f"FAILED: boot counter {current_boot_counter} did not increase on start!")
        end_of_test()
        exit()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count >= packet_count + 1:
        packet_count = current_packet_count
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} did not increment!")
        end_of_test()
        exit()

    # Run motor
    print('Testing Running motor pauses dynamic flash writing')
    print("Setting Remote Throttle Voltage to 2\nDynamic Flash Packet Count should still increment")
    watchdog.dut.write("Remote Throttle Voltage", 2)
    sleep(0.5)

    # Check Dynamic Flash write Interval
    print("Waiting for 40 seconds")
    wait_thread = Thread(target=wait_for, args=[40])
    wait_thread.start()
    wait_thread.join()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count >= packet_count:
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} did not increment!")
        end_of_test()
        exit()

    # Check on time
    print("Checking motor on time low")
    current_motor_on_time_low = watchdog.dut.read('motor on time low')
    if motor_on_time_low + 0.008 <= current_motor_on_time_low <= motor_on_time_low + 0.009:
        motor_on_time_low = current_motor_on_time_low
        print(f"PASSED: motor on time {current_motor_on_time_low} in range\n")
    else:
        print(f"FAILED: Motor on time low {current_motor_on_time_low} did not increase!")
        end_of_test()
        exit()

    # Check odometer
    print("Checking odometer low")
    current_odometer_low = watchdog.dut.read('odometer low')
    if 0.015 <= current_odometer_low <= odometer_low + 0.025:
        odometer_low = current_odometer_low
        print(f"PASSED: odometer {current_odometer_low} in range\n")
    else:
        print(f"FAILED: Odometer low {current_odometer_low} did not increase!")
        end_of_test()
        exit()

    # Throttle back to off
    print("Setting Remote Throttle Voltage to 1")
    watchdog.dut.write("Remote Throttle Voltage", 1)

    # Check Dynamic Flash write Interval
    print("Waiting for 10 seconds")
    wait_thread = Thread(target=wait_for, args=[10])
    wait_thread.start()
    wait_thread.join()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count >= packet_count + 1:
        packet_count = current_packet_count
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} did not increment!")
        end_of_test()
        exit()

    # Run motor
    print('Testing power cycle while motor is running')
    print("Setting Remote Throttle Voltage to 2\nDynamic Flash Packet Count should be paused")
    watchdog.dut.write("Remote Throttle Voltage", 2)
    sleep(0.5)

    # Power cycle
    input("Power cycle and press Enter to continue")
    watchdog.dut.write("Remote Throttle Voltage", 1)

    # Check Dynamic Flash write Interval
    print("Waiting for 5 seconds")
    wait_thread = Thread(target=wait_for, args=[5])
    wait_thread.start()
    wait_thread.join()

    # Check on time
    print("Checking motor on time low")
    current_motor_on_time_low = watchdog.dut.read('motor on time low')
    if current_motor_on_time_low == motor_on_time_low:
        print("PASSED: motor on time in range\n")
    else:
        print(f"FAILED: Motor on time low {motor_on_time_low} -> {current_motor_on_time_low} increased!")
        end_of_test()
        exit()

    # Check odometer
    print("Checking odometer low")
    current_odometer_low = watchdog.dut.read('odometer low')
    if 0.015 <= current_odometer_low <= 0.035:
        odometer_low = current_odometer_low
        print(f"PASSED: odometer {current_odometer_low} in range\n")
    else:
        print(f"FAILED: Odometer low {current_odometer_low} out of range!")
        end_of_test()
        exit()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count == packet_count + 1:
        packet_count = current_packet_count
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} did not increment!")
        end_of_test()
        exit()

    # Check boot counter
    print("Checking boot counter")
    current_boot_counter = watchdog.dut.read('boot counter')
    if current_boot_counter >= boot_counter + 1:
        boot_counter = current_boot_counter
        print("PASSED: boot counter incremented on start!\n")
    else:
        print(f"FAILED: boot counter {current_boot_counter} did not increase on start!")
        end_of_test()
        exit()

    # Check dynamic flash write interval to 60 seconds
    print("Checking different interval")
    watchdog.dut.write("Dynamic Flash Write Interval (seconds)", 60)
    if watchdog.dut.read("Dynamic Flash Write Interval (seconds)") != 60:
        end_of_test()
        exit()
    watchdog.dut.save_to_flash()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count >= packet_count + 1:
        packet_count = current_packet_count
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} did not increment!")
        end_of_test()
        exit()

    # Check boot counter
    input("Power cycle and press Enter to continue")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)
    print("Checking boot counter")
    current_boot_counter = watchdog.dut.read('boot counter')
    if current_boot_counter >= boot_counter + 1:
        boot_counter = current_boot_counter
        print("PASSED: boot counter incremented on start!\n")
    else:
        print(f"FAILED: boot counter {current_boot_counter} did not increase on start!")
        end_of_test()
        exit()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count >= packet_count + 1:
        packet_count = current_packet_count
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} did not increment!")
        end_of_test()
        exit()

    # Check Dynamic Flash write Interval
    print("Waiting for 60 seconds")
    wait_thread = Thread(target=wait_for, args=[60])
    wait_thread.start()
    wait_thread.join()

    # Check packet count
    print("Checking Dynamic Flash Packet Count")
    current_packet_count = watchdog.dut.read('Dynamic Flash Packet Count')
    if current_packet_count >= packet_count + 1:
        packet_count = current_packet_count
        print("PASSED: packet count incremented!\n")
    else:
        print(f"FAILED: Dynamic Flash Packet Count {current_packet_count} | Interval change did not work")
        end_of_test()
        exit()

    end_of_test()
    print("PASSED: Dynamic Flash Writing Test Finished\nPower cycle to reset parameters")