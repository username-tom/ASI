"""DynoModule version of TC 10.5.4"""
# ASI Includes
from dyno_v2.Module.ASIDynoModule import *

from time import sleep
from datetime import datetime

if __name__ == "__main__":
    # instruments on their addresses:
    # Yoko：
    yoko = Yokogawa_WT1806("192.168.1.79")
    brake = ASIController("COM5", 115200, 1, "")
    dut = ASIController("COM12", 115200, 1, "")

    # BAC2BAC：
    # dut = ASIController("COM8", 115200, 1, "")
    # brake  = ASIController("COM6", 115200, 1, "")

    # init dyno, set timing params, and start logging
    sleep(1)
    dyno = ASIDynoModule(config='default',
                         log_folder="C:/DynoResults/TC 10.5.4/")

    # init variables
    REMOTE_SPEED_COMMAND = 50  # Remote speed command (490)
    REMOTE_MOTORING_CURRENT = 100  # Remote motoring current (491)
    REMOTE_BRAKING_CURRENT = 100  # Remote braking current (492)

    dyno.devices[1].stop_remote_motor()
    dyno.devices[1].clear_faults()
    dyno.devices[1].turn_off_communication_timeout()

    ################### Test Start ######################
    print("TC 10.3.3 tests starting!")
    # Logging start!
    dyno.start_logging(1)
    print("Logging start!")
    startTime = dyno.start_time
    print("tests Started at " + str(startTime.time().isoformat()))

    # Starting motor to reach steady state
    dyno.devices[1].remote_speed_mode(speed_command=50)

    start_time = datetime.now()
    while dyno.devices[1].get_rpm() <= 0.8 * 0.5 * dyno.devices[1].read("Rated motor speed"):
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before motor reaching target speed!")
            dyno.stop_test()
            dyno.stop_logging()
            exit()

    dyno.int_event.wait(5)
    dyno.test_outputs["Test Result"] = {1: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        2: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        3: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        4: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        5: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        6: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        7: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        8: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        9: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        10: {"Phase Current": False,
                                            "DUT Reading": False,
                                            "Motor Current": False},
                                        }

    # check current readings at no load
    for i in range(1, 6):
        # check phase currents
        phase_rms = {1: dyno.current_csv_line["Phase RMS Current 1"],
                     2: dyno.current_csv_line["Phase RMS Current 2"],
                     3: dyno.current_csv_line["Phase RMS Current 3"]}
        avg_phase_true = (phase_rms[1] + phase_rms[2] + phase_rms[3]) / 3
        print(f"Average Phase RMS Current: {avg_phase_true}")
        max_diff = 0
        for phase in phase_rms:
            diff = abs(phase_rms[phase] - avg_phase_true) / avg_phase_true * 100
            if diff > max_diff:
                max_diff = diff
        print(f"Maximum difference: {max_diff}%")
        if max_diff < 10:
            print(f"Check {i}: PASS!\n")
            dyno.test_outputs['Test Result'][i]["Phase Current"] = True
        else:
            print(f"Check {i}: FAIL!\n")

        # check controller readings
        max_peak_phase = 1.4142 * avg_phase_true * 1.2
        max_rms = avg_phase_true * 1.1
        if "DUT phase A current" in dyno.current_csv_line.keys():
            prefix = True
        else:
            prefix = False
        dut_phase = {1: dyno.current_csv_line[f"{'DUT ' if prefix else ''}phase A current"],
                     2: dyno.current_csv_line[f"{'DUT ' if prefix else ''}phase B current"],
                     3: dyno.current_csv_line[f"{'DUT ' if prefix else ''}phase C current"]}
        dut_phase_result = None
        dut_rms = {1: dyno.current_csv_line[f"{'DUT ' if prefix else ''}Ia_rms"],
                   3: dyno.current_csv_line[f"{'DUT ' if prefix else ''}Ic_rms"]}
        dut_rms_result = None
        print("Check phase current readings...")
        for phase in dut_phase:
            if abs(dut_phase[phase]) > max_peak_phase:
                dut_phase_result = False
        if dut_phase_result is None:
            print(f"Check {i}: PASS!\n")
            dut_phase_result = True
        else:
            if not dut_phase_result:
                print(f"Check {i}: FAIL!\n")

        print("Check DUT RMS currents...")
        for phase in dut_rms:
            if dut_rms[phase] > max_rms:
                dut_rms_result = False
        if dut_rms_result is None:
            print(f"Check {i}: PASS!\n")
            dut_rms_result = True
        else:
            if not dut_rms_result:
                print(f"Check {i}: FAIL!\n")

        if dut_phase_result and dut_rms_result:
            dyno.test_outputs["Test Result"][i]["DUT Reading"] = True

        # check motor current
        max_motor_current = 1.4142 * avg_phase_true * 1.05
        print("Check motor current...")
        if dyno.current_csv_line[f"{'DUT ' if prefix else ''}motor current"] <= max_motor_current:
            print(f"Check {i}: PASS!\n")
            dyno.test_outputs['Test Result'][i]["Motor Current"] = True
        else:
            print(f"Check {i}: FAIL!\n")

        dyno.int_event.wait(2)

    # check current readings with load
    dyno.devices[2].start()
    dyno.devices[2].set_torque(5)

    # wait for steady state
    start_time = datetime.now()
    while dyno.devices[1].get_rpm() <= 0.8 * 0.5 * dyno.devices[1].read("Rated motor speed"):
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before motor reaching target speed!")
            dyno.stop_test()
            dyno.stop_logging()
            exit()

    for i in range(6, 11):
        # check phase currents
        phase_rms = {1: dyno.current_csv_line["Phase RMS Current 1"],
                     2: dyno.current_csv_line["Phase RMS Current 2"],
                     3: dyno.current_csv_line["Phase RMS Current 3"]}
        avg_phase_true = (phase_rms[1] + phase_rms[2] + phase_rms[3]) / 3
        print(f"Average Phase RMS Current: {avg_phase_true}")
        max_diff = 0
        for phase in phase_rms:
            diff = abs(phase_rms[phase] - avg_phase_true) / avg_phase_true * 100
            if diff > max_diff:
                max_diff = diff
        print(f"Maximum difference: {max_diff}%")
        if max_diff < 10:
            print(f"Check {i}: PASS!\n")
            dyno.test_outputs['Test Result'][i]["Phase Current"] = True
        else:
            print(f"Check {i}: FAIL!\n")

        # check controller readings
        max_peak_phase = 1.4142 * avg_phase_true * 1.2
        max_rms = avg_phase_true * 1.1
        if "DUT phase A current" in dyno.current_csv_line.keys():
            prefix = True
        else:
            prefix = False
        dut_phase = {1: dyno.current_csv_line[f"{'DUT ' if prefix else ''}phase A current"],
                     2: dyno.current_csv_line[f"{'DUT ' if prefix else ''}phase B current"],
                     3: dyno.current_csv_line[f"{'DUT ' if prefix else ''}phase C current"]}
        dut_phase_result = None
        dut_rms = {1: dyno.current_csv_line[f"{'DUT ' if prefix else ''}Ia_rms"],
                   3: dyno.current_csv_line[f"{'DUT ' if prefix else ''}Ic_rms"]}
        dut_rms_result = None
        print("Check phase current readings...")
        for phase in dut_phase:
            if abs(dut_phase[phase]) > max_peak_phase:
                dut_phase_result = False
        if dut_phase_result is None:
            print(f"Check {i}: PASS!\n")
            dut_phase_result = True
        else:
            if not dut_phase_result:
                print(f"Check {i}: FAIL!\n")

        print("Check DUT RMS currents...")
        for phase in dut_rms:
            if dut_rms[phase] > max_rms:
                dut_rms_result = False
        if dut_rms_result is None:
            print(f"Check {i}: PASS!\n")
            dut_rms_result = True
        else:
            if not dut_rms_result:
                print(f"Check {i}: FAIL!\n")

        if dut_phase_result and dut_rms_result:
            dyno.test_outputs["Test Result"][i]["DUT Reading"] = True

        # check motor current
        max_motor_current = 1.4142 * avg_phase_true * 1.05
        print("Check motor current...")
        if dyno.current_csv_line[f"{'DUT ' if prefix else ''}motor current"] <= max_motor_current:
            print(f"Check {i}: PASS!\n")
            dyno.test_outputs['Test Result'][i]["Motor Current"] = True
        else:
            print(f"Check {i}: FAIL!\n")

        dyno.int_event.wait(2)

    dyno.test_outputs['Tests'] = {}
    for test in dyno.test_outputs['Test Result']:
        dyno.test_outputs['Tests'][test] = False
        passes = 0
        for result in dyno.test_outputs['Test Result'][test]:
            if dyno.test_outputs['Test Result'][test][result]:
                print(f"Test {test} - {result}: PASS!")
                passes += 1
            else:
                print(f"Test {test} - {result}: FAIL!")
        if passes == 3:
            dyno.test_outputs['Tests'][test] = True
    print()
    passes = 0
    for test in dyno.test_outputs['Tests']:
        if dyno.test_outputs['Tests'][test]:
            passes += 1
        else:
            break
    if passes == 10:
        print("TC 10.3.3 PASSED!")
    else:
        print("TC 10.3.3 FAILED!")

    dyno.stop_test()
    dyno.int_event.wait(3)
    dyno.stop_logging()


    ################### Test End ######################
    sleep(1)
    endTime = datetime.now()
    delta = endTime - startTime
    print("TC 10.3.3 test duration: " + str(delta.total_seconds()) + " seconds")
