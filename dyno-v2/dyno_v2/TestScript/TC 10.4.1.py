# IMPORTS
from dyno_v2.Module.asi_controller import ASIController
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep


# COM & Motor parameters for TC 10.1.2
PORT = "COM25"       # "PCAN_USBBUS1"
BAUD_RATE = 115200  # 250000
MB_ADDRESS = 1      # 42
parameters = ["software revision level",
              "application CRC32 high word",
              "application CRC32 low word",
              "test build",
              "boot loader software revision",
              "bootloader CRC32 high word",
              "bootloader CRC32 low word",
              "parameter CRC32 high word",
              "parameter CRC32 low word"]

if __name__ == "__main__":
    pv = {"Speed regulator mode": 2}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **pv)
    print("Controller initiated!")
    print("Revision info:")
    for parameter in parameters:
        value = watchdog.dut.read(parameter)
        if "revision" in parameter:
            print(parameter + ": " + str(value))
        elif parameter == "test build":
            print(parameter + ": " + str(int(value)))
        # elif parameter == "bootloader CRC32 low word" and value == 0:
        #     print(parameter + ": 0000")
        else:
            if value < 0:
                print(f"{parameter}: {int(value + 65536):04X}")
            else:
                print(f"{parameter}: {int(value):04X}")

    parameters = parameters[-2:]  # only checks parameter CRC32 high & low
    change = "Speed regulator mode"
    watchdog.dut.write(change, 0)
    print(change + " is changed!")
    watchdog.dut.save_to_flash(0x7FFF)
    watchdog.dut.power_cycle()

    for parameter in parameters:
        value = watchdog.dut.read(parameter)
        if value < 0:
            print(f"{parameter}: {int(value + 65536):04X}")
        else:
            print(f"{parameter}: {int(value):04X}")


