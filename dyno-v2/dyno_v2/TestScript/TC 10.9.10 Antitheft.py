# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime

# COM & Motor parameters for TC 10.9.7 Simultaneous Throttle Speed Pedal Torque Mode
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

if __name__ == "__main__":
    parameters = {"Features4": 0,
                  "Wheel Lock/Antitheft disable source": 3,  # remote
                  "Features": 1 << 2}  # antitheft
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()

    print("Initialization successful!")

    def end_of_test():
        # End of test
        watchdog.restore_parameters()
        watchdog.dut.save_to_flash()


    # Enables antitheft
    print("Enabling antitheft")
    remote_digital_commands = int(watchdog.dut.read("Remote Digital Commands"))
    if (remote_digital_commands & (1 << 14)) >> 14 == 1:
        watchdog.dut.write("Remote Digital Commands", remote_digital_commands - 1 << 14)

    # Check Antitheft status
    start_time = datetime.now()
    while (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT on enabling antitheft")
            end_of_test()
            exit()

    if (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 1:
        print("PASSED: Antitheft enabled\n")
    else:
        print("FAILED: Antitheft not engaged")
        end_of_test()
        exit()

    # Check saving to flash
    print("Checking save to flash has been disabled")
    watchdog.dut.save_to_flash()
    input("Power cycle and press Enter to continue")
    if watchdog.dut.read("Wheel Lock/Antitheft disable source") == 0:
        print("PASSED: Save to flash disabled")
    else:
        print("FAILED: Save to flash still enabled")
        end_of_test()
        exit()

    # Check bootloading
    watchdog.update_params(**parameters)

    # Restart TTL port for BACDoor bootloading
    watchdog.dut.modbus.modbus.serial.close()
    input("Bootload from BACDoor\nPress Enter after the process finishes")
    watchdog.dut.modbus.modbus.serial.open()

    # Check firmware change
    if watchdog.dut.firmware == watchdog.dut.read("software revision level"):
        print("PASSED: Bootloading is disabled")
    else:
        print("FAILED: Bootloading still enabled")
        end_of_test()
        exit()

    end_of_test()
    print("PASSED: Antitheft disabling save to flash and bootloading Test Finished")