# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.7 Simultaneous Throttle Speed Pedal Torque Mode
PORT = "COM5"
BAUD_RATE = 115200
MB_ADDRESS = 1
ENCODER_PARAMETERS = [
    'Encoder analog noise threshold',
    'Encoder Cos V Source',
    'Encoder Cos High Voltage',
    'Encoder Cos Low Voltage',
    'Encoder Cos Fault Range',
    'Encoder Noise Frequency Threshold',
    'Encoder offset',
    'Encoder Sine V Source',
    'Encoder Sine High Voltage',
    'Encoder Sine Low Voltage',
    'Encoder Sin Fault Range'
]

def wait_for(time):
    wait_start = datetime.now()
    waiting = True
    while waiting:
        if (datetime.now() - wait_start).total_seconds() < time:
            sleep(1)
        else:
            waiting = False


if __name__ == "__main__":
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS)
    watchdog.dut.turn_off_communication_timeout()
    print("Storing existing encoder parameters")
    encoder_parameters = {}
    for p in ENCODER_PARAMETERS:
        encoder_parameters[p] = watchdog.dut.read(p)


    def end_of_test():
        # End of test
        for p in ENCODER_PARAMETERS:
            watchdog.dut.write(p, encoder_parameters[p])


    if watchdog.dut.read('Switching frequency') != 10000:
        watchdog.dut.set_access_level(1)
        watchdog.dut.write('Switching frequency', 10000)
        watchdog.dut.set_access_level(0)
        watchdog.dut.save_to_flash()
        input("Power cycle and press Enter to continue")

    print("Initialization successful!")

    # Run Motor discovery 5
    watchdog.dut.write("Motor discover mode", 5)

    # Wait for motor steady state
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()

    while watchdog.dut.get_rpm() > 0:
        sleep(1)

    # Check autotune offset error
    offset_error = watchdog.dut.read("autotune_offset_error")
    print(f'autotune offset error: {offset_error}')
    if offset_error < 3:
        print('PASSED: Autotune offset error less than 3\u00B0')
    else:
        print("FAILED: Autotune offset error more than 3\u00B0")
        end_of_test()
        exit()

    # Check sin cos source can be automatically flipped
    print("Check motor discovery can flip cos/sin source\nFlipping cos/sin source")
    print(f'Origianl cos source: {encoder_parameters["Encoder Cos V Source"]}')
    print(f'Origianl sin source: {encoder_parameters["Encoder Sine V Source"]}')
    watchdog.dut.write('Encoder Cos V Source', encoder_parameters['Encoder Sine V Source'])
    watchdog.dut.write('Encoder Sine V Source', encoder_parameters['Encoder Cos V Source'])
    print(f'New cos source: {watchdog.dut.read("Encoder Cos V Source")}')
    print(f'New sin source: {watchdog.dut.read("Encoder Sine V Source")}')

    # Run Motor discovery 5
    watchdog.dut.write("Motor discover mode", 5)

    # Wait for motor steady state
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()

    while watchdog.dut.get_rpm() > 0:
        sleep(1)

    # Check cos/sin sources
    if watchdog.dut.read('Encoder Cos V Source') == encoder_parameters['Encoder Cos V Source']:
        print('PASSED: Encoder Cos V Source flipped')
    else:
        print('FAILED: Encoder Cos V Source not flipped')
        end_of_test()
        exit()

    if watchdog.dut.read('Encoder Sine V Source') == encoder_parameters['Encoder Sine V Source']:
        print('PASSED: Encoder Sine V Source flipped')
    else:
        print('FAILED: Encoder Sine V Source not flipped')
        end_of_test()
        exit()

    # Check parameters are within reasonable range
    change_list = ['Encoder Sine High Voltage',
                   'Encoder Sine Low Voltage',
                   'Encoder Cos High Voltage',
                   'Encoder Cos Low Voltage']
    for p in change_list:
        watchdog.dut.write(p, 0)

    # Run Motor discovery 5
    watchdog.dut.write("Motor discover mode", 5)

    # Wait for motor steady state
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()

    while watchdog.dut.get_rpm() > 0:
        sleep(1)

    # Check parameters
    for p in change_list:
        if encoder_parameters[p] - 0.5 <= watchdog.dut.read(p) <= encoder_parameters[p] + 0.5:
            print(f"PASSED: {p} within range")
        else:
            print(f"FAILED: {p} out of range")
            end_of_test()
            exit()
    print('PASSED: All parameters are within range')

    end_of_test()
    print("PASSED: Common Wheel Speed/Motor Temperature Input Feature Test Finished")