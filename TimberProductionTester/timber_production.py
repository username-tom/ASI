"""timber_production: Timber Production Tester GUI"""

__version__ = '0.1'

import serial.tools.list_ports
from tkinter import *
from tkinter import ttk
from tkinter import messagebox, font
from Module.ASIDynoModule import *
from GUI.tooltip import ToolTip
from GUI.icons import ASIIcons
from datetime import datetime
import pandas as pd
from time import sleep
from threading import Thread



def _com_ports():
    return [port for port, _, _ in serial.tools.list_ports.comports()]


def log_result(file_name="", data=None):
    csv_name = f"{file_name.replace('.csv', '')}.csv"
    backup_location = f"{BACKUP_DESTINATION}\\Timber Production Result\\{csv_name}"
    datafile = f"{SAVE_DESTINATION}\\Timber Production Result\\{csv_name}"

    try:
        with open(file=datafile, mode='a', newline='') as csvfile:
            csv.writer(csvfile).writerow(data)
    except PermissionError:
        with open(file=backup_location, mode='a', newline='') as csvfile:
            csv.writer(csvfile).writerow(data)

        return


def create_summary(file_name="", header=None):
    csv_name = f"{file_name.replace('.csv', '')}.csv"

    try:
        makedirs(f"{SAVE_DESTINATION}/Timber Production Result/", exist_ok=True)
    except (PermissionError, FileNotFoundError):
        messagebox.showinfo("Attention",
                            f"Error when accessing {SAVE_DESTINATION}\n"
                            f"Saving to backup directory {BACKUP_DESTINATION}")
        makedirs(BACKUP_DESTINATION, exist_ok=True)
        datafile = f"{BACKUP_DESTINATION}/Timber Production Result/{csv_name}"
        # self.testing = False
        # return
    else:
        datafile = f"{SAVE_DESTINATION}/Timber Production Result/{csv_name}"

    try:
        with open(file=datafile, mode='x', newline='') as csvfile:
            csv.writer(csvfile).writerow(header)
    except FileExistsError as e:
        logging.info("Attention: File already exists, only appending new lines! ")


class TimberProductionTester:
    """GUI Runner for Line Reactor Test"""

    def __init__(self, root):
        self.root = root
        self.root.title("Timber Production Tester")
        self.root.geometry(GEOMETRY)
        self.root.resizable(False, False)
        self.root.iconbitmap('ASI Logo.ico')
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root['background'] = 'white'
        default_font = font.nametofont('TkDefaultFont')
        default_font.config(size=FONT_SIZE)
        self.dut_port = StringVar(value="")
        self.brk_port = StringVar(value="")
        self.baud_rate = 115200
        self.mb_id = 1
        self.status = StringVar(value=f"DISCONNECTED")
        self.dyno = None
        self.loop_interval = 1
        self.start_time = None
        self.barcode = StringVar(value='')
        self.barcode.trace('w', self.barcode_tracer)
        self.test_note = ''
        self.startTemp = -99
        self.test_logged = False
        self._reset_result()
        self.checks = []
        self.live_rpm = StringVar(value='0')
        self.live_current = StringVar(value='0')
        self.live_temperature = StringVar(value='0')
        self.live_brk = StringVar(value='0')
        self.live_thread = None
        self.live_status = False
        self.test_stopping = False

        self.output_container = None
        self.mainframe = self.build_mainframe()
        self.mainframe.grid(column=0, row=1, sticky='news', columnspan=3)
        self.root.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        Label(self.root, name="barcode_label", text="Barcode:", background='white').grid(column=0, row=0, sticky='e')
        Entry(self.root, name="barcode_entry", textvariable=self.barcode, background='white').grid(
            column=1, row=0, sticky='we', columnspan=3, padx=15)
        self.root.children['barcode_entry'].focus_set()

        self.root.option_add('*tearOff', FALSE)

        self.menu = Menu(self.root)
        self.root['menu'] = self.menu

        self.advanced_menu = Menu(self.menu)

        self.menu.add_cascade(menu=self.advanced_menu, label='Advanced')

        self.advanced_menu.add_command(label='Restore Parameters', command=self.restore_parameters,
                                       font=f'TkDefaultFont 12')

    def build_mainframe(self):
        mainframe = Frame(self.root, padx=10, pady=10, background='white', relief='sunken')

        Label(mainframe, name="condition_status", text="STATUS:", background='white').grid(column=0, row=1, sticky='e')
        Label(mainframe, name="condition_value", textvariable=self.status, background='white', width=20).grid(
            column=1, row=1, columnspan=3, sticky='news')

        Label(mainframe, name="dut_com_label", text="DUT", background='white').grid(column=0, row=2, sticky='e')
        ttk.Combobox(mainframe, name="dut_com_entry", textvariable=self.dut_port, background='white', width=10,
                     font=f'TkDefaultFont {FONT_SIZE}').grid(
            column=1, row=2, columnspan=3)

        Label(mainframe, name="brk_com_label", text="BRK", background='white').grid(column=0, row=3, sticky='e')
        ttk.Combobox(mainframe, name="brk_com_entry", textvariable=self.brk_port, background='white', width=10,
                     font=f'TkDefaultFont {FONT_SIZE}').grid(
            column=1, row=3, columnspan=3)

        def combo_events_ports(evt):
            if int(evt.type) == 4:
                w = evt.widget
                try:
                    mainframe.children['dut_com_entry']['values'] = _com_ports()
                    mainframe.children['brk_com_entry']['values'] = _com_ports()
                except IndexError:
                    pass
                w.event_generate('<Down>', when="head")


        ports = _com_ports()
        mainframe.children['dut_com_entry'].bind('<Button-1>', combo_events_ports)
        mainframe.children['dut_com_entry']['values'] = ports
        mainframe.children['brk_com_entry'].bind('<Button-1>', combo_events_ports)
        mainframe.children['brk_com_entry']['values'] = ports
        self.dut_port.set(DUT_COM_PORT)
        self.brk_port.set(BRK_COM_PORT)
        ToolTip(mainframe.children['dut_com_label'], msg="DUT COM port #", delay=0.5)
        ToolTip(mainframe.children['brk_com_label'], msg="Brake COM port #", delay=0.5)

        Button(mainframe, name="start_btn", text="Start", command=self._test_start, width=25,
               background='green', activebackground='green').grid(column=0, row=18, columnspan=5, pady=2)
        ToolTip(mainframe.children['start_btn'],
                msg="Connects to DUT and starts Timber Production Test", delay=0.5)
        mainframe.children['start_btn']['state'] = DISABLED
        Button(mainframe, name="stop_btn", text="Stop", command=self._test_stop, width=25,
               background='red', activebackground='red').grid(column=0, row=19, columnspan=5, pady=2)
        ToolTip(mainframe.children['stop_btn'],
                msg="Stops the test and disconnects DUT", delay=0.5)


        temp_widget = Label(mainframe, name='help', text="?", justify='left', font='Arial 10 bold')
        temp_widget.grid(column=0, row=30, sticky='se', pady=10, columnspan=5)
        ToolTip(temp_widget, msg=HELP_TEXT, delay=0.5, y_offset=-40)

        status_container = LabelFrame(mainframe, background='white', text='Live Status')
        status_container.grid(column=0, row=40, sticky='we', columnspan=5)

        temp_widget = Label(status_container, background='white', text='DUT Motor RPM')
        temp_widget.grid(column=0, row=0, sticky='e')
        temp_widget = Label(status_container, background='white', textvariable=self.live_rpm)
        temp_widget.grid(column=1, row=0, sticky='w')
        temp_widget = Label(status_container, background='white', text='DUT Motor Current')
        temp_widget.grid(column=0, row=1, sticky='e')
        temp_widget = Label(status_container, background='white', textvariable=self.live_current)
        temp_widget.grid(column=1, row=1, sticky='w')
        temp_widget = Label(status_container, background='white', text='DUT Motor Temperature')
        temp_widget.grid(column=0, row=2, sticky='e')
        temp_widget = Label(status_container, background='white', textvariable=self.live_temperature)
        temp_widget.grid(column=1, row=2, sticky='w')
        temp_widget = Label(status_container, background='white', text='BRK Torque command')
        temp_widget.grid(column=0, row=3, sticky='e')
        temp_widget = Label(status_container, background='white', textvariable=self.live_brk)
        temp_widget.grid(column=1, row=3, sticky='w')

        self.build_out_frame()

        return mainframe

    def build_out_frame(self):
        """Constructing output frame"""
        output_container = Frame(self.root, relief='flat',
                                 background='white', name='output_frame')
        output_container.grid(column=3, row=1, sticky='news')

        for i in [2, 4, 6, 8, 10, 12, 14]:
            output_container.grid_rowconfigure(i, weight=1)
        output_container.grid_columnconfigure((0, 1), weight=1, minsize=250)

        out_frame = Frame(self.root.children['output_frame'], relief='flat',
                          background='white', name='output_frame')
        out_frame.grid(column=0, row=1, sticky='news', columnspan=2)
        out_frame.columnconfigure((0, 1), weight=1)

        self.out_frame = out_frame

        self._init_out()

        Text(self.root.children['output_frame'], name='note_text',
             undo=True, width=50,
             height=4, font=f'TkDefaultFont {FONT_SIZE}').grid(
            column=0, row=2, columnspan=2, pady=10, sticky='ns')

        return output_container

    def live(self):
        while self.live_status:
            if self.dyno:
                if (datetime.now() - self.dyno.start_time).total_seconds() > TEST_DURATION * 60:
                    self._add_note("Test Timed Out!")
                    self._test_stop()
                    break

                self.live_rpm.set(
                    self.dyno.devices[self.dyno.driver].get_rpm())
                self.live_current.set(
                    f'{self.dyno.devices[self.dyno.driver].read("motor current"):.3f}')
                self.live_temperature.set(
                    self.dyno.devices[self.dyno.driver].read("motor temperature"))
                self.live_brk.set(
                    f'{self.dyno.devices[3 - self.dyno.driver].read("Remote torque command"):.3f}')
                self.dyno.int_event.wait(1)

    def start_live(self):
        self.live_status = True
        self.live_thread = Thread(target=self.live)
        self.live_thread.start()

    def end_live(self):
        self.live_status = False
        self.live_thread = None

    def restore_parameters(self):
        def action():
            self._on_connect()

            if self.dyno:
                if self.dyno.devices[self.dyno.driver]:
                    self.dyno.devices[self.dyno.driver].raise_access_level()
                    self.dyno.devices[self.dyno.driver].load_parameters("Parameter Files/DUT.xml",
                                                                        master=self.root,
                                                                        indicator="Restoring DUT...")
                    self.dyno.devices[self.dyno.driver].reset_access_level()
                    self.dyno.devices[self.dyno.driver].save_to_flash()
                if self.dyno.devices[3 - self.dyno.driver]:
                    self.dyno.devices[3 - self.dyno.driver].raise_access_level()
                    self.dyno.devices[3 - self.dyno.driver].load_parameters("Parameter Files/BRK.xml",
                                                                            master=self.root,
                                                                            indicator="Restoring BRK...")
                    self.dyno.devices[3 - self.dyno.driver].reset_access_level()
                    self.dyno.devices[3 - self.dyno.driver].save_to_flash()
                self._on_connect()

        Thread(target=action).start()

    def barcode_tracer(self, *args):
        if self.barcode.get() == "":
            self.mainframe.children['start_btn']['state'] = DISABLED
        else:
            self.mainframe.children['start_btn']['state'] = NORMAL

    def get_sn(self):
        segments = self.barcode.get().split('~')
        for segment in segments:
            pieces = segment.split('-')
            if (len(pieces) == 2 and
                    len(pieces[0]) == 4 and
                    len(pieces[1]) == 5):
                return segment

    def _on_connect(self):
        if self.status.get() in ["DISCONNECTED", 'CONNECTING']:
            self.status.set("CONNECTING...")
            try:
                dut = ASIController(com_port=self.dut_port.get())
            except CommError:
                self._test_stop()
                return
            try:
                brk = ASIController(com_port=self.brk_port.get())
            except CommError:
                self._test_stop()
                return

            if hasattr(dut, 'modbus') and hasattr(dut.modbus, 'modbus') and \
                    hasattr(brk, 'modbus') and hasattr(brk.modbus, 'modbus'):
                self.status.set("CONNECTED")
                self.dyno = ASIDynoModule(dut, brk, log_folder=SAVE_DESTINATION)
            else:
                messagebox.showinfo("Bad Connection",
                                    "Error: Bad Connection with controllers! Please retry!")
                self.status.set("DISCONNECTED")
                return False

            if self.dyno.devices[1].read("Speed regulator mode") == 1 and \
                self.dyno.devices[2].read("Speed regulator mode") == 0:
                self.dyno.driver = 2
                config.set('default', 'dut_com_port', self.brk_port.get())
                config.set('default', 'brk_com_port', self.dut_port.get())
                self.dut_port.set(config.get('default', 'dut_com_port'))
                self.brk_port.set(config.get('default', 'brk_com_port'))
            elif self.dyno.devices[1].read("Speed regulator mode") == 0 and \
                self.dyno.devices[2].read("Speed regulator mode") == 1:
                self.dyno.driver = 1
                config.set('default', 'dut_com_port', self.dut_port.get())
                config.set('default', 'brk_com_port', self.brk_port.get())

            self.start_live()

        elif self.status.get() in ["CONNECTED", "TESTING", "CONNECTING..."]:
            self.status.set("DISCONNECTING...")
            self.end_live()

            try:
                self.dyno.__del__()
            except (ValueError, AttributeError, OSError):
                pass
            finally:
                self.dyno = None
                self.status.set("DISCONNECTED")

    def _test_start(self):
        def action():
            self._reset_variables()

            self.status.set('CONNECTING')
            self.mainframe.children['dut_com_entry']['values'] = _com_ports()
            self.mainframe.children['brk_com_entry']['values'] = _com_ports()
            if self.barcode.get() == '':
                messagebox.showinfo("Error", "Empty Barcode! Please retry!")
                return

            self.mainframe.children['start_btn']['state'] = DISABLED
            self.mainframe.children['stop_btn']['state'] = NORMAL
            self.result[index("Result Time")] = datetime.now().strftime('%m/%d/%Y %H:%M')
            self.result[index('Serial Number')] = self.get_sn()
            self.result[index("Barcode")] = self.barcode.get()

            sleep(1)

            self._on_connect()
            if self.status.get() == "CONNECTED":
                self._update_output("Connection",
                                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'check', 'green')
            else:
                self._update_output("Connection",
                                    "Failed",
                                    'cross', 'red')
                return

            self.status.set('TESTING')
            self.dyno.testing = True

            create_summary(header=log_header,
                           file_name=f"Timber Production Summary "
                                     f"{datetime.now().strftime('%Y-%m-%d')}")
            self.test_thread = Thread(target=self.test)
            self.test_thread.start()

            self.out_frame.children['frame_test_result'].children[
                'test_result_status'].config(text='Testing')

        temp = Thread(target=action)
        temp.start()

    def _test_stop(self):
        if not self.test_stopping:
            def action():
                self.test_stopping = True
                self.mainframe.children['dut_com_entry']['values'] = _com_ports()
                self.mainframe.children['brk_com_entry']['values'] = _com_ports()
                if self.dyno:
                    self.dyno.testing = False
                    self.dyno.interrupt_motor_discovery()
                    self.dyno.int_event.set()
                    self.dyno.stop_test()
                    self.dyno.int_event.clear()
                if not self.test_logged:
                    self._log_failure()
                self.test_thread = None
                self.status.set('CONNECTED')
                self._on_connect()

                try:
                    # self.root.children["barcode_entry"]['state'] = NORMAL
                    self.barcode.set('')
                    self.root.children['barcode_entry'].focus_set()
                except KeyError:
                    pass
                self.test_stopping = False

            temp = Thread(target=action)
            temp.start()

    def _on_closing(self):
        if self.dyno and self.dyno.testing:
            self._test_stop()
        if (self.status.get() == "CONNECTED"
              or self.status.get() == "TESTING"
              or self.status.get() == "CONNECTING..."):
            self._on_connect()

        self.root.update()

        # by default geometry ignores menu bar
        geometry = f'{self.root.geometry()}'
        geometry_prefix = int(geometry.split("x")[0]) + X_OFFSET
        geometry_affix = "+".join(geometry.split("+")[1:])
        parsed_geometry = int(geometry.split("+")[0].split("x")[1]) + Y_OFFSET
        config.set('default', 'geometry', f'{geometry_prefix}x{parsed_geometry}+{geometry_affix}')
        with open('config.ini', 'w') as file:
            config.write(file)
        self.root.destroy()

    def test(self):
        """
        Timber Production Test Procedure
        """
        self._pre_test()
        self.dyno.clear_faults()

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        self.dyno.int_event.wait(3)

        self.result[index("Pre-test Faults")] = self.dyno.devices[self.dyno.driver].check_faults()

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        # pre-test motor discovery 1
        pre_md = [False] * 5
        original_rs = self.dyno.devices[self.dyno.driver].read("Rs")
        original_ls = self.dyno.devices[self.dyno.driver].read("Ls")
        try:
            pre_rs, pre_ls = self.dyno.motor_discovery(1)
        except AttributeError:
            self._test_stop()
            return
        else:
            self.result[index('Pre-test Rs')] = pre_rs
            self.result[index('Pre-test Ls')] = pre_ls

        if abs(pre_rs) - PRE_RS <= original_rs <= abs(pre_rs) + PRE_RS:
            pre_md[0] = True
            self._update_output("Pre-test Rs", pre_rs, 'check', 'green')
        else:
            self._update_output("Pre-test Rs", pre_rs, 'cross', 'red')
            self._add_note("Pre-test Rs Out of Range")

        if abs(pre_ls) - PRE_LS <= original_ls <= abs(pre_ls) + PRE_LS:
            pre_md[1] = True
            self._update_output("Pre-test Ls", pre_ls, 'check', 'green')
        else:
            self._update_output("Pre-test Ls", pre_ls, 'cross', 'red')
            self._add_note("Pre-test Ls Out of Range")

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        # pre-test motor discovery 2
        original_rpm = self.dyno.devices[self.dyno.driver].read("Rated motor speed")
        original_offset = self.dyno.devices[self.dyno.driver].read("Hall offset")
        original_halls = []
        for i in range(8):
            original_halls.append(self.dyno.devices[self.dyno.driver].read(f"Hall sector[{i}]"))

        try:
            pre_rpm, pre_offset, pre_halls = self.dyno.motor_discovery(2)
        except AttributeError:
            self._test_stop()
            return
        else:
            self.result[index('Pre-test Rated RPM')] = pre_rpm
            self.result[index('Pre-test Hall Offset')] = pre_offset
            self.result[index('Pre-test Hall Sectors')] = pre_halls

        if pre_halls == original_halls:
            pre_md[2] = True
            self._update_output("Pre-test Hall Sectors", pre_halls, 'check', 'green')
        else:
            self._update_output("Pre-test Hall Sectors", pre_halls, 'cross', 'red')
            self._add_note("Pre-test Hall Sectors Different from Default")

        if pre_rpm - PRE_RPM <= original_rpm <= pre_rpm + PRE_RPM:
            pre_md[3] = True

        if pre_offset - PRE_OFFSET <= original_offset <= pre_offset + PRE_OFFSET:
            pre_md[4] = True

        if [True] * 5 == pre_md:
            self._update_output("Pre-test Motor Discovery", 'Passed', 'check', 'green')
        else:
            self._update_output("Pre-test Motor Discovery", 'Failed', 'cross', 'red')
            self._add_note("Pre-test Motor Discovery Failed")

        # unloaded test
        self.dyno.int_event.wait(3)

        for i in range(4):
            if not self.dyno or not self.dyno.testing:
                self._test_stop()
                return
            else:
                self.dyno.devices[self.dyno.driver].remote_speed_mode(speed_command=UNLOADED_SPEED * (i + 1) / 4)
                sleep(2)

        self.dyno.devices[self.dyno.driver].remote_speed_mode(speed_command=UNLOADED_SPEED)
        self.dyno.int_event.wait(UNLOADED_DURATION)

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        unloaded_result = self._check_unloaded_data()
        if unloaded_result == [True] * 3:
            self._update_output("Unloaded Run", "Passed", "check", "green")
            self.result[index("Unloaded Result")] = "Passed"
        else:
            self._update_output("Unloaded Run", "Failed", "cross", "red")
            self.result[index("Unloaded Result")] = "Failed"
            self._add_note("Unloaded Run Failed")

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        # rundown
        self.dyno.devices[self.dyno.driver].remote_speed_mode(speed_command=LOADED_SPEED,)
        self.dyno.devices[3 - self.dyno.driver].start()
        self.dyno.devices[3 - self.dyno.driver].set_torque(0)
        self.dyno.int_event.wait(2)

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        self.dyno.babying(speed_command=LOADED_SPEED)

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        self.dyno.int_event.wait(2)

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        self.dyno.rundown(minTorque=LOADED_MIN,
                          maxTorque=LOADED_MAX,
                          torqueStep=LOADED_STEP,
                          settleTime=LOADED_DURATION)

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        rundown_result = self._check_rundown_data()
        if rundown_result == [True] * 2:
            self._update_output("Rundown", "Passed", "check", "green")
            self.result[index("Rundown Result")] = "Passed"
        else:
            self._update_output("Rundown", "Failed", "cross", "red")
            self._add_note("Rundown Failed")

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        self.dyno.wait_till_stopped(self.dyno.driver)

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        self.dyno.int_event.wait(3)
        self.result[index("Post-test Faults")] = self.dyno.devices[self.dyno.driver].check_faults()

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        # post-test motor discovery 1
        post_md = [False] * 5
        try:
            post_rs, post_ls = self.dyno.motor_discovery(1)
        except AttributeError:
            self._test_stop()
            return
        else:
            self.result[index('Post-test Rs')] = post_rs
            self.result[index('Post-test Ls')] = post_ls

        if abs(post_rs) - POST_RS <= original_rs <= abs(post_rs) + POST_RS:
            post_md[0] = True
            self._update_output("Post-test Rs", post_rs, 'check', 'green')
        else:
            self._update_output("Post-test Rs", post_rs, 'cross', 'red')
            self._add_note("Post-test Rs Out of Range")

        if abs(post_ls) - POST_LS <= original_ls <= abs(post_ls) + POST_LS:
            post_md[1] = True
            self._update_output("Post-test Ls", post_ls, 'check', 'green')
        else:
            self._update_output("Post-test Ls", post_ls, 'cross', 'red')
            self._add_note("Post-test Ls Out of Range")

        if not self.dyno or not self.dyno.testing:
            self._test_stop()
            return

        # post-test motor discovery 2
        try:
            post_rpm, post_offset, post_halls = self.dyno.motor_discovery(2)
        except AttributeError:
            self._test_stop()
            return
        else:
            self.result[index('Post-test Rated RPM')] = post_rpm
            self.result[index('Post-test Hall Offset')] = post_offset
            self.result[index('Post-test Hall Sectors')] = post_halls

        if post_halls == original_halls:
            post_md[2] = True
            self._update_output("Post-test Hall Sectors", post_halls, 'check', 'green')
        else:
            self._update_output("Post-test Hall Sectors", post_halls, 'cross', 'red')
            self._add_note("Post-test Hall Sectors Different from Default")

        if post_rpm - POST_RPM <= original_rpm <= post_rpm + POST_RPM:
            post_md[3] = True

        if post_offset - POST_OFFSET <= original_offset <= post_offset + POST_OFFSET:
            post_md[4] = True

        if [True] * 5 == post_md:
            self._update_output("Post-test Motor Discovery", 'Passed', 'check', 'green')
        else:
            self._update_output("Post-test Motor Discovery", 'Failed', 'cross', 'red')
            self._add_note("Post-test Motor Discovery Failed")

        self._post_test()

    def _pre_test(self):
        # Pre-test
        try:
            self.startTemp = self.dyno.devices[self.dyno.driver].read('motor temperature')
        except (OSError, ValueError, AttributeError):
            self._test_stop()
            return
        else:
            self.result[index("Initial Motor Temperature")] = self.startTemp

        self.dyno.devices[1].clear_faults()
        self.dyno.devices[2].clear_faults()
        self.dyno.start_logging(1, run_down=self.get_sn())

    def _post_test(self):
        if self._check_test_result():
            self.result[index('Test Result')] = "PASSED"
            self._update_output("Test Result", "Passed", 'check', 'green')
        else:
            self.result[index('Test Result')] = "FAILED"
            self._update_output("Test Result", "Failed", 'cross', 'red')

        self.dyno.stop_logging()

        log_result(file_name=f"Timber Production Summary "
                             f"{datetime.now().strftime('%Y-%m-%d')}",
                   data=self.result)
        self.test_logged = True

        self.root.children['barcode_entry'].focus_set()
        self._test_stop()

    def _check_test_result(self):
        return (self.output_result["Pre-test Motor Discovery"] == "Passed" and
                self.output_result["Unloaded Run"] == "Passed" and
                self.output_result['Rundown'] == "Passed" and
                self.output_result['Post-test Motor Discovery'] == "Passed")

    def _add_note(self, text):
        self.test_note = f"{text}; {self.test_note}"

    def _show_note(self):
        self.root.children['output_frame'].children['note_text'].insert('1.0', self.test_note)

    def _log_failure(self):
        if self.result[index('Test Result')] == '':
            self.result[index('Test Result')] = "Interrupted"
            self._add_note('Interrupted')
            self._update_output("Test Result", 'Interrupted', 'cross', 'yellow')
        else:
            self.out_frame.children['frame_test_result'].children[
                'test_result_status'].config(text='Failed', background='red')
            self._add_note('Failed')

        self.result[index('Note')] = f"{self.test_note}"
        log_result(file_name=f"Timber Production Summary "
                             f"{datetime.now().strftime('%Y-%m-%d')}",
                   data=self.result)
        self._show_note()
        self.test_logged = True

    def _reset_variables(self):
        self.root.children['output_frame'].children['note_text'].delete('1.0', END)
        self.startTemp = -99
        self.test_logged = False
        self.test_note = ''
        self._reset_result()
        temp = Thread(target=self._reset_out)
        temp.start()
        temp.join()

    def _reset_result(self):
        self.result = [""] * len(log_header)

    def _init_out(self):
        self.output_result = OUTPUT_RESULTS.copy()
        for i, result in enumerate(self.output_result):
            temp_container = Frame(self.out_frame, relief='flat', background='white',
                                   name=f'frame_{"_".join(result.lower().split(" "))}')
            temp_container.grid_rowconfigure(0, minsize=35, weight=1)
            temp_container.grid(column=0, row=i, sticky='news')
            temp_container.grid_columnconfigure((1, 2), weight=1, minsize=240)

            temp_widget = ASIIcons(temp_container, size=30, item='check',
                                   width=1.5, foreground='grey')
            temp_widget.canvas.grid(column=0, row=0)
            self.checks.append(temp_widget)

            temp_widget = Label(temp_container, text=result, background='white')
            temp_widget.grid(column=1, row=0, sticky='w')
            temp = Label(temp_container, text=self.output_result[result], background='gray',
                         name=f"{'_'.join(result.lower().split(' '))}_status")
            temp.grid(column=2, row=0, sticky='we')

    def _reset_out(self):
        for result in self.output_result:
            self.output_result[result] = None
        self.output_result['Test Result'] = "Not Started"
        for i, result in enumerate(self.output_result):
            temp_container = self.out_frame.children[f'frame_{"_".join(result.lower().split(" "))}']

            temp = self.checks[i]
            temp.reset(item='check', foreground='grey', background='white')

            temp = temp_container.children[f"{'_'.join(result.lower().split(' '))}_status"]
            temp.config(background='gray', text="" if not self.output_result[result] else self.output_result[result])

    def _update_output(self, output, text, check, foreground):
        self.output_result[output] = text
        temp = self.checks[check_index(output)]
        temp.reset(item=check, foreground=foreground, background='white')
        temp = self.out_frame.children[
            f"frame_{'_'.join(output.lower().split(' '))}"].children[
            f"{'_'.join(output.lower().split(' '))}_status"]
        temp.config(background=foreground, text=text)

    def _check_unloaded_data(self):
        df = pd.read_csv(self.dyno.log_file())
        unloaded_result = [False] * 3
        ia = df['DUT Ia_rms'].loc[(df['DUT Remote state command'] == 2) &
                                  (df['BRK Remote state command'] == 0) &
                                  (df['DUT motor rpm'] > 0.8 * UNLOADED_SPEED / 100 * self.dyno.devices[
                                      self.dyno.driver].read("Rated motor speed"))]
        ia_avg = ia.mean()
        ia_max = ia.max()
        ia_min = ia.min()
        self.result[index("Unloaded Ia RMS Avg")] = ia_avg
        self.result[index("Unloaded Ia RMS Max")] = ia_max
        self.result[index("Unloaded Ia RMS Min")] = ia_min

        if UNLOADED_IA[0] <= ia_min <= ia_avg <= ia_max <= UNLOADED_IA[1]:
            unloaded_result[0] = True
        else:
            self._add_note("Unloaded Ia_rms Out of Range")

        ic = df['DUT Ic_rms'].loc[(df['DUT Remote state command'] == 2) &
                                  (df['BRK Remote state command'] == 0) &
                                  (df['DUT motor rpm'] > 0.8 * UNLOADED_SPEED / 100 * self.dyno.devices[
                                      self.dyno.driver].read("Rated motor speed"))]
        ic_avg = ic.mean()
        ic_max = ic.max()
        ic_min = ic.min()
        self.result[index("Unloaded Ic RMS Avg")] = ic_avg
        self.result[index("Unloaded Ic RMS Max")] = ic_max
        self.result[index("Unloaded Ic RMS Min")] = ic_min

        if UNLOADED_IC[0] <= ic_min <= ic_avg <= ic_max <= UNLOADED_IC[1]:
            unloaded_result[1] = True
        else:
            self._add_note("Unloaded Ic_rms Out of Range")

        motor_current = df['DUT motor current'].loc[(df['DUT Remote state command'] == 2) &
                                                    (df['BRK Remote state command'] == 0) &
                                                    (df['DUT motor rpm'] > 0.8 * UNLOADED_SPEED / 100 * self.dyno.devices[
                                                        self.dyno.driver].read("Rated motor speed"))]
        motor_current_avg = motor_current.mean()
        self.result[index("Unloaded Motor Current")] = motor_current_avg

        if UNLOADED_MOTOR_CURRENT[0] <= motor_current_avg <= UNLOADED_MOTOR_CURRENT[1]:
            unloaded_result[2] = True
        else:
            self._add_note('Unloaded Motor Current Out of Range')

        return unloaded_result

    def _check_rundown_data(self):
        rundown_result = [False] * 2
        self.result[index('Rundown Max Torque')] = self.dyno.test_outputs['max_torque']
        if self.dyno.test_outputs['max_torque'] >= LOADED_TARGET:
            rundown_result[0] = True
            self._update_output("Max Torque",
                                self.dyno.test_outputs['max_torque'],
                                'check', 'green')
        else:
            self._update_output("Max Torque",
                                self.dyno.test_outputs['max_torque'],
                                'cross', 'red')
            self._add_note("Target Torque NOT Reached")

        self.result[index('Rundown Max Temperature')] = self.dyno.test_outputs['max_temp']
        if self.dyno.test_outputs['max_temp'] <= LOADED_TEMP:
            rundown_result[1] = True

        return rundown_result


if __name__ == "__main__":
    gui = Tk()
    TimberProductionTester(gui)
    gui.mainloop()
