# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep


# COM & Motor parameters for TC 10.9.4 Hot battery foldback
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1
START_TEMP = "Hot battery foldback starting temperature"
END_TEMP = "Hot battery foldback ending temperature"
LIMIT = "positive battery limit"
WARNING = "warnings2"
BIT = 8

if __name__ == "__main__":
    tests = [False, False, False]
    parameters = {"Control command source": 0,
                  START_TEMP: 0,
                  END_TEMP: 0,
                  "Speed regulator mode": 0,
                  "Remote state command": 0,
                  "Remote Speed Command in RPM": 100,
                  "Remote maximum motoring current": 10}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Initialization successful!")

    # Test 1
    print('Test 1')
    room_temp = watchdog.dut.read('battery temperature')
    print(f"Current battery temperature: {room_temp}")
    print(f'Writing {room_temp - 15} to "{START_TEMP}"')
    watchdog.dut.write(START_TEMP, room_temp - 15)
    print(f'Writing {room_temp - 5} to "{END_TEMP}"')
    watchdog.dut.write(END_TEMP, room_temp - 5)
    sleep(2)

    limit = watchdog.dut.read(LIMIT)
    print(f"{LIMIT}: {limit}")
    if limit == 0:
        print(f'{LIMIT} GOOD!')
    else:
        print(f'{LIMIT} BAD')
        exit()

    warning = (int(watchdog.dut.read(WARNING)) & (1 << BIT)) >> BIT
    print(f"Hot Battery Foldback: {'True' if warning == 1 else 'False'}")
    if warning == 1:
        print(f'Controller in Hot Battery Foldback!')
    else:
        print(f'Controller not in Hot Battery Foldback!')
        exit()

    watchdog.dut.start_remote_motor()
    sleep(1)
    if watchdog.dut.get_rpm() < 20:
        print("Foldback is working")
    else:
        print("Foldback is not working")
        watchdog.dut.stop_remote_motor()
        exit()

    print('Test 1 Passed\n')

    # Test 2
    print("Test 2")
    print(f'Writing {0} to "{START_TEMP}"')
    watchdog.dut.write(START_TEMP, 0)
    print(f'Writing {0} to "{END_TEMP}"')
    watchdog.dut.write(END_TEMP, 0)
    sleep(2)

    limit = watchdog.dut.read(LIMIT)
    print(f"{LIMIT}: {limit}")
    if limit == 1:
        print(f'{LIMIT} GOOD!')
    else:
        print(f'{LIMIT} BAD')
        exit()

    warning = (int(watchdog.dut.read(WARNING)) & (1 << BIT)) >> BIT
    print(f"Hot Battery Foldback: {'True' if warning == 1 else 'False'}")
    if warning == 1:
        print(f'Controller in Hot Battery Foldback!')
        exit()
    else:
        print(f'Controller not in Hot Battery Foldback!')

    sleep(1)
    if watchdog.dut.get_rpm() > 90:
        print("Foldback is working")
    else:
        print("Foldback is not working")
        exit()

    watchdog.dut.stop_remote_motor()
    print('Test 2 Passed\n')

    # Test 3
    print("Test 3")
    print(f'Writing {room_temp - 10} to "{START_TEMP}"')
    watchdog.dut.write(START_TEMP, room_temp - 10)
    print(f'Writing {room_temp + 10} to "{END_TEMP}"')
    watchdog.dut.write(END_TEMP, room_temp + 10)
    sleep(2)

    limit = watchdog.dut.read(LIMIT)
    print(f"{LIMIT}: {limit}")
    if 0.49 <= limit <= 0.51:
        print(f'{LIMIT} GOOD!')
    else:
        print(f'{LIMIT} BAD')
        exit()

    warning = (int(watchdog.dut.read(WARNING)) & (1 << BIT)) >> BIT
    print(f"Hot Battery Foldback: {'True' if warning == 1 else 'False'}")
    if warning == 1:
        print(f'Controller in Hot Battery Foldback!')
    else:
        print(f'Controller not in Hot Battery Foldback!')
        exit()

    print('Test 3 Passed\n')

    # Test 4
    print("Test 4")
    print(f'Writing {0} to "{START_TEMP}"')
    watchdog.dut.write(START_TEMP, 0)
    sleep(2)

    limit = watchdog.dut.read(LIMIT)
    print(f"{LIMIT}: {limit}")
    if limit == 1:
        print(f'{LIMIT} GOOD!')
    else:
        print(f'{LIMIT} BAD')
        exit()

    warning = (int(watchdog.dut.read(WARNING)) & (1 << BIT)) >> BIT
    print(f"Hot Battery Foldback: {'True' if warning == 1 else 'False'}")
    if warning == 1:
        print(f'Controller in Hot Battery Foldback!')
        exit()
    else:
        print(f'Controller not in Hot Battery Foldback!')

    print('Test 4 Passed')
    print("TC 10.9.4 Hot battery foldback passed\n")
    print(f'Writing {0} to "{START_TEMP}"')
    watchdog.dut.write(START_TEMP, 0)
    print(f'Writing {0} to "{END_TEMP}"')
    watchdog.dut.write(END_TEMP, 0)