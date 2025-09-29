# ASI Includes
from dyno_v2.Module.ASIDynoModule import ASIDynoModule
from tkinter import *
from tkinter import messagebox, simpledialog
from time import sleep
from datetime import datetime, timedelta
from dyno_v2.Module.TestABC import TestABC
from math import floor

param_file = "Parameter Files/LineReactor.xml"
log_header = ["Result Time", "Label ID", "Manufacturer Code",
              "Top Level Hardware", "Hardware", "Firmware",
              "Parameter", "Revision", "Serial Number",
              "Pre-test Bridge Check Passed",
              "Pre-test POST Static Phase U Open Voltage",
              "Pre-test POST Static Phase V Open Voltage",
              "Pre-test POST Static Phase W Open Voltage",
              "Pre-test POST Dynamic Phase U Hi Voltage",
              "Pre-test POST Dynamic Phase V Hi Voltage",
              "Pre-test POST Dynamic Phase W Hi Voltage",
              "Pre-test POST Dynamic Phase U Lo Voltage",
              "Pre-test POST Dynamic Phase V Lo Voltage",
              "Pre-test POST Dynamic Phase W Lo Voltage",
              "Pre-test faults", "Pre-test warnings", "Pre-test faults2", "Pre-test warnings2",
              "Pre-test Rs", "Pre-test Ls", "Initial Temperature",
              "Time to Foldback", "Final Temperature",
              "Post-test faults", "Post-test warnings", "Post-test faults2", "Post-test warnings2",
              "Post-test Rs", "Post-test Ls",
              "Post-test Bridge Check Passed",
              "Post-test POST Static Phase U Open Voltage",
              "Post-test POST Static Phase V Open Voltage",
              "Post-test POST Static Phase W Open Voltage",
              "Post-test POST Dynamic Phase U Hi Voltage",
              "Post-test POST Dynamic Phase V Hi Voltage",
              "Post-test POST Dynamic Phase W Hi Voltage",
              "Post-test POST Dynamic Phase U Lo Voltage",
              "Post-test POST Dynamic Phase V Lo Voltage",
              "Post-test POST Dynamic Phase W Lo Voltage",
              "End of tests faults", "End of tests warnings", "End of tests faults2", "End of tests warnings2",
              "Average YOKO RMS U", "Average YOKO RMS V", "Average YOKO RMS W",
              "Average DUT RMS U", "Average DUT RMS V", "Average DUT RMS W", "Average DUT Motor Current"]


def msg_box(title, msg):
    messagebox.showinfo(title, msg)


def input_box(title, msg):
    answer = simpledialog.askstring(title, msg)
    return answer


class LineReactorTest(TestABC):

    def __init__(self, dyno, use_barcode=False, motor_type=None, barcode=None, sn=None):
        super().__init__(dyno, use_barcode, motor_type, barcode, sn)
        # self.dyno = dyno
        # self.use_barcode = use_barcode
        # self.motor_type = motor_type
        # self.barcode = barcode
        # self.sn = sn
        # self.testing = True
        self.averages = [0] * 7
        self.pre_test_faults = 0
        self.pre_test_warnings = 0
        self.pre_test_faults2 = 0
        self.pre_test_warnings2 = 0
        self.post_test_faults = 0
        self.post_test_warnings = 0
        self.post_test_faults2 = 0
        self.post_test_warnings2 = 0

    # Line Reactor Mode, TW August 2022
    def line_reactor_mode(self, current=10., freq=100., start_temperature=25,
                          stop_at=0):  # 0 - tests time; 1 - Foldback; other - Delta temperature
        print("Initiating line reactor...")
        # self.dyno.BRK = None
        # if self.dyno.DUT is None:
        # port = str(input_box("User input", "Driver is NoneType, please enter COM port for driver (COM#)... "))
        # self.dyno.DUT = ASIController(port.upper(), 115200, 1, "")
        # if self.dyno.PA is None:
        # ip = str(input_box("User input", "Yokogawa is NoneType, please enter IP address (192.168.1.###)... "))
        # self.dyno.PA = Yokogawa_WT1806(ip.strip())

        self.logging_setup()
        print("Establishing initial steady state...")
        # Count down to start due to potential high current test condition
        # Also provides data points for initial state
        count_down = 5
        while count_down >= 0:
            print(f"Line reactor test starting in {count_down} seconds...")
            count_down -= 1
            sleep(1)
        print("Start Open Loop Current Mode!")

        time_end = datetime.now() + timedelta(minutes=self.dyno.TestTime)
        time_ss = datetime.now() + timedelta(minutes=self.dyno.SSTime)
        startTime = datetime.now()
        self.dyno.DUT.current_mode(motoring_current=100, current=current, frequency=freq)
        counter = 1
        while (datetime.now() < time_end and
               datetime.now() < time_ss and self.testing and
               len(self.dyno.DUT.check_faults()) == 0 and
               not self.dyno.DUT.in_foldback()):
            if counter % 13 != 0:  # roughly 10 seconds
                pass
            else:
                temp = [0] * 7
                temp[0] = self.dyno.PA.getMeasurement("Phase RMS Current 1") + self.averages[0]
                temp[1] = self.dyno.PA.getMeasurement("Phase RMS Current 2") + self.averages[1]
                temp[2] = self.dyno.PA.getMeasurement("Phase RMS Current 3") + self.averages[2]
                temp[3] = self.dyno.DUT.read("phase A current") + self.averages[3]
                temp[4] = self.dyno.DUT.read("phase B current") + self.averages[4]
                temp[5] = self.dyno.DUT.read("phase C current") + self.averages[5]
                temp[6] = self.dyno.DUT.read("motor current") + self.averages[6]
                self.averages = temp
                print(self.averages)
            counter += 1
            print(f"Driver Status: Motor Current: {self.dyno.DUT.read('motor current'):.2f}/{current} | "
                  f"Elapsed: {(datetime.now() - startTime).total_seconds():.1f}s | "
                  f"Foldback: {self.dyno.DUT.in_foldback()}")
            sleep(self.dyno.tPID)
        for i, average in enumerate(self.averages):
            average /= floor(counter / 13)
            self.averages[i] = average

        faults = self.dyno.DUT.check_faults()
        if (len(faults) == 1 and "ContrlTempFLDBK" not in str(faults)) or len(faults) > 1:
            self.post_test_faults = self.dyno.DUT.read("faults")
            self.post_test_warnings = self.dyno.DUT.read("warnings")
            self.post_test_faults2 = self.dyno.DUT.read("faults2")
            self.post_test_warnings2 = self.dyno.DUT.read("warnings2")
        self.dyno.stop_test()
        delta = datetime.now() - startTime
        print(f"\nFoldback after {delta.total_seconds():.2f} seconds")
        while self.dyno.DUT.get_rpm() > 0:
            continue

        # Returns controller temperature at end of test time and elapsed time [float], [deltatime]
        if stop_at == 0:
            self.dyno.stop_logging()
            return self.dyno.DUT.read("controller temperature"), delta
        elif stop_at == 1:
            while datetime.now() < time_end and datetime.now() < time_ss:
                continue
            self.dyno.stop_logging()
            return self.dyno.DUT.read("controller temperature"), datetime.now() - startTime
        else:
            while self.dyno.DUT.read("controller temperature") > start_temperature + stop_at:
                continue
            self.dyno.stop_logging()
            return self.dyno.DUT.read("controller temperature"), datetime.now() - startTime

    def line_reactor_test(self):
        self.dyno.update(self.dyno.config["basic_sstime"], self.dyno.config["basic_sstol"], self.dyno.config["basic_rpmtol"],
                         self.dyno.config["basic_testtime"], self.dyno.config["basic_tpid"])
        # openCurrent = float(simpledialog.askstring("User input", "Open loop current: "))  # Amp
        # openFrequency = float(simpledialog.askstring("User input", "Open loop frequency: "))  # Hz
        openCurrent = 400  # Amp
        openFrequency = 200  # Hz
        # openMotoring = float(input("Open loop motoring current: "))  # %
        # if openMotoring > 100:
        #     openMotoring = 100
        # elif openMotoring < 0:
        #     openMotoring = 0
        self.dyno.DUT.logParam = f"{self.dyno.DUT.root_dir if self.dyno.DUT.root_dir else ''}/Parameters to log/controller_line_reactor.csv"
        if not self.testing:
            return
        print("Line Reactor tests")
        # log_file = simpledialog.askstring("User input", f"Please enter test summary log file name ({self.dyno.logpath}): ")
        log_file = f"Summary"
        sleep(0.1)
        self.dyno.extra_logging(log_file, log_header, same_folder=False)
        if not self.testing:
            return
        # print(f"Please enter Line Reactor tests stop condition...\n"
        # f"  0 - (Default) Stop at controller foldback\n"
        # f"  1 - Stop after preset timer\n"
        # f" >1 - Stop after controller temperature drops below (starting room temperature + #)")
        # stop = simpledialog.askstring("User input", "Line Reactor tests stop condition: ")
        stop = 0
        try:
            stop = int(stop)
        except TypeError:
            stop = 0
        if not self.testing:
            return
        # num_tests = int(simpledialog.askstring("User input", "Please input # of tests to perform... "))
        num_tests = 1
        for i in range(num_tests):
            sleep(1)
            # if not self.dyno.DUT.barcode_scanned():
            # print(f"Fatal error: Can't read from barcode...\nTerminating program...")
            # exit(1)
            if not self.testing:
                return
            startTemp = 25  # Assumed default room temperature
            try:
                startTemp = self.dyno.DUT.read('controller temperature')
            except (OSError, ValueError) as e:
                print(f"{e}\n"
                      f"Error reading from controller...\n"
                      f"Line Reactor tests {i + 1}/{num_tests} aborted!\n"
                      f"Exiting program...")
                exit(1)
            else:
                print(f"Controller Temperature: {startTemp}")

            self.dyno.DUT.write("Motor position sensor type", 2)
            self.dyno.DUT.clear_faults()
            if not self.testing:
                return
            print(f"Line Reactor tests {i + 1}/{num_tests}\nLoading parameter files...")
            self.dyno.DUT.load_parameters(param_file)
            msg_box("tests paused", "Disconnect Line Reactor phase cables and press Enter... ")
            print("Running Pre-test Bridge checks...")
            if not self.testing:
                return
            # Pre-test Bridge check
            pre_bridge, pre_openCct, pre_Hi, pre_Lo = self.dyno.DUT.bridge_check()
            print(f"Pre-test Bridge Check: {pre_bridge}")
            sleep(1)
            self.pre_test_faults = self.dyno.DUT.read("faults")
            self.pre_test_warnings = self.dyno.DUT.read("warnings")
            self.pre_test_faults2 = self.dyno.DUT.read("faults2")
            self.pre_test_warnings2 = self.dyno.DUT.read("warnings2")
            if not self.testing:
                return
            msg_box("tests paused", "Please connect Line Reactor phase cables and press Enter... ")
            print("Running Pre-test Motor discovery...")
            if not self.testing:
                return
            # Pre-test Motor discovery
            pre_rs, pre_ls = self.dyno.DUT.motor_discovery(1)
            print(f"Pre-test Rs: {pre_rs} | Ls: {pre_ls}")
            if not self.testing:
                return
            msg_box("tests paused", f"Press Enter to start Line Reactor tests {i + 1}/{num_tests}... ")

            final_temp, elapsed_time = self.line_reactor_mode(current=openCurrent, freq=openFrequency,
                                                              start_temperature=startTemp, stop_at=stop)
            print(f"Line Reactor tests {i + 1}/{num_tests} finished...\n"
                  f"Elapsed time: {elapsed_time}\n"
                  f"Controller Temperature at end of test: {final_temp}")
            if not self.testing:
                return
            print("Running Post-test Motor discovery...")

            # Post-test Motor discovery
            post_rs, post_ls = self.dyno.DUT.motor_discovery(1)
            print(f"Pre-test Rs: {post_rs} | Ls: {post_ls}")
            sleep(1)
            if not self.testing:
                return
            msg_box("tests paused", "Disconnect Line Reactor phase cables and press Enter... ")
            print("Running Post-test Bridge checks...")
            if not self.testing:
                return
            # Post-test Bridge check
            post_bridge, post_openCct, post_Hi, post_Lo = self.dyno.DUT.bridge_check()

            print(f"Post-test Bridge Check: {post_bridge}")
            end_faults = self.dyno.DUT.read("faults")
            end_warnings = self.dyno.DUT.read("warnings")
            end_faults2 = self.dyno.DUT.read("faults2")
            end_warnings2 = self.dyno.DUT.read("warnings2")

            if not self.testing:
                return
            # Log detailed results
            result = [datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f'), self.dyno.DUT.barcode["label_id"],
                      self.dyno.DUT.barcode["mfg_code"], self.dyno.DUT.barcode["part_num"],
                      self.dyno.DUT.barcode["hardware"], self.dyno.DUT.barcode["firmware"],
                      self.dyno.DUT.barcode["parameter"], self.dyno.DUT.barcode["revision"],
                      self.dyno.DUT.barcode["serial_num"], pre_bridge, pre_openCct[0], pre_openCct[1], pre_openCct[2],
                      pre_Hi[0], pre_Hi[1], pre_Hi[2], pre_Lo[0], pre_Lo[1], pre_Lo[2],
                      self.pre_test_faults, self.pre_test_warnings, self.pre_test_faults2, self.pre_test_warnings2,
                      pre_rs, pre_ls, startTemp, elapsed_time, final_temp,
                      self.post_test_faults, self.post_test_warnings, self.post_test_faults2, self.post_test_warnings2,
                      post_rs, post_ls, post_bridge, post_openCct[0], post_openCct[1], post_openCct[2],
                      post_Hi[0], post_Hi[1], post_Hi[2], post_Lo[0], post_Lo[1], post_Lo[2],
                      end_faults, end_warnings, end_faults2, end_warnings2]
            result.extend(self.averages)
            self.dyno.extra_line(log_file, custom=True, data=result, same_folder=False)
            if not self.testing:
                return
            print(f"Line Reactor tests {i + 1}/{num_tests}: Results logged")
            if i + 1 < num_tests:
                msg_box("tests paused", f"Please switch controller...\n"
                                       f"Press Enter to start Line Reactor tests {i + 2}/{num_tests}")

    def interrupt(self):
        self.testing = False

    def logging_setup(self):
        print(f"\nStart logging!")
        output = f"0000-00000"
        if self.use_barcode:
            output = self.barcode['serial_num']
        # self.dyno.DUT.log_params = "Parameters to log/controller_line_reactor.csv"
        self.dyno.start_logging(1, run_down=f"{output} LineReactor")

    def log_result(self, cycle=None, i=None, start=None):
        pass


if __name__ == "__main__":
    root = Tk()
    root.withdraw()
    root.mainloop()

    dyno = ASIDynoModule(config="HiSpeed-LineReactor", log_folder="C:/LineReactorResults/")

    try:
        test = LineReactorTest(dyno)
        test.line_reactor_test()
    except KeyboardInterrupt:
        print(f"\nInterrupted!")
        dyno.stop_test()
        dyno.stop_logging()

    # dyno.stop_logging()
