"""dyno_controller: GUI Controller for ASI DynoModule"""

__version__ = '0.7.2'

import tkinter.font

# Imports

from dyno_v2.Module.gui_parameters import *
import shutil
import sys
sys.path.insert(0, f'{ROOT_DIR}/dyno_v2/TestScript')
sys.path.insert(0, f'{ROOT_DIR}')

import numpy as np

def count_log_files(folder):
    """Counts existing log files"""

    def extract_digits(filename):
        s = ''
        for char in filename:
            if char.isdigit():
                s += char
        return int(s)

    try:
        logs = [extract_digits(f) for f in os.listdir(folder) if f.endswith('.log')]
    except FileNotFoundError:
        return 0
    else:
        if not logs:
            return 0
        else:
            latest_file_number = max(logs)
            if latest_file_number >= 9:
                largest_file_name = f'logs/std-0.log'
                os.remove(largest_file_name)
                for i in range(9):
                    name1 = f'logs/std-{i + 1}.log'
                    name2 = f'logs/std-{i}.log'
                    try:
                        os.rename(name1, name2)
                    except FileNotFoundError:
                        shutil.copy(f'logs/std-{i - 1}.log', name2)
                return 9
            return latest_file_number + 1

# rolling log: https://stackoverflow.com/questions/56195040/how-to-create-rolling-logger-in-python
import logging

class NoParsingFilter(logging.Handler):
    def handle(self, record):
        if 'Bus error:' in str(record.getMessage()):
            raise CommLossError

if sys.platform.startswith("win"):
    os.makedirs(f'{ROOT_DIR}/logs', exist_ok=True)
    logging.basicConfig(filename=f'logs/std-{count_log_files(f"{ROOT_DIR}/logs/")}.log',
                        datefmt='%Y/%m/%d %I:%M:%S %p', filemode='w',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    # logging.getLogger('can.pcan').addHandler(NoParsingFilter())
# pylint: disable=wrong-import-position
import warnings
import lxml.etree as ET
from tkinter import ttk, font, messagebox, filedialog
import serial.tools.list_ports
# pylint: disable=import-error
from dyno_v2.Module.yokogawa_WT1806 import *
from dyno_v2.Module.can_interface import CANInterface
from dyno_v2.TestScript.controller_thermal_max import ControllerThermalMax
from dyno_v2.TestScript.rundown_test import RundownTest
from dyno_v2.TestScript.LineReactorTest import LineReactorTest
from dyno_v2.TestScript.for_debug import ForDebug
from dyno_v2.TestScript.production_validation import ProductionValidation
from dyno_v2.TestScript.debug_dyno_start_stop import DebugStartStop
from dyno_v2.TestScript.cyclic_test_jason import CyclicTest
from dyno_v2.TestScript.efficiency_map import EfficiencyMapTest
from dyno_v2.TestScript.cyclic_open_loop import CyclicOpenLoopTest
from dyno_v2.Module.script_runner import *
from dyno_v2.GUI.ScrollableFrame import ScrollableFrame
from dyno_v2.GUI.output_bubble import OutputBubble
from dyno_v2.GUI.main_elements import *
from dyno_v2.GUI.dyno_plot import *

warnings.filterwarnings("ignore")
logging.info("Libraries imported")


class RedirectText:
    """Redirects stdout/stderr to tkinter text"""

    def __init__(self, text_ctrl: Text, logger, log_level=logging.INFO):
        """Constructor"""
        self.output = text_ctrl
        self.logger = logger
        self.level = log_level

    def write(self, string: str):
        """Overwrites stdout/stderr write"""
        try:
            self.output['state'] = NORMAL
            if string.startswith("\33[") and string.endswith("A"):
                num = int(string.strip("\33[").strip("A"))
                self.output.mark_set(INSERT, f"{int(self.output.index(INSERT).split('.')[0]) - num}.{0}")
                self.output.delete(self.output.index(INSERT), END)
            else:
                self.output.insert(END, string, "standard")
        except TclError:
            pass
        finally:
            self.output.update()
            self.output.see(END)
            self.output['state'] = DISABLED
        for line in string.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        """Overwrites stdout/stderr flush"""
        try:
            self.output.update()
            self.output.see(END)
        except TclError:
            pass

class RedirectError:
    """Redirects stderr to logging"""

    def __init__(self, logger, log_level=logging.INFO):
        """Constructor"""
        self.logger = logger
        self.level = log_level

    def write(self, string: str):
        """Overwrites stderr write"""
        for line in string.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())


def browse_files():
    """browse_files: static method for loading parameter .xml files"""
    return filedialog.askopenfilename(initialdir="/", title="Select a File",
                                      filetypes=(("ASI files", "*.xml* *.ehx*"), ("all files", "*.*")))

def styling(mode):
    """styling: static method for setting up tkinter style"""
    # https://stackoverflow.com/questions/22389198/ttk-styling-tnotebook-tab-background-and-borderwidth-not-working
    styler = ttk.Style()
    # Import the Notebook.tab element from the default theme
    try:
        styler.element_create('Plain.Notebook.tab', "from", 'default')
        styler.element_create('home_dut.TNotebook', "from", 'default')
        styler.element_create('home_brk.TNotebook', "from", 'default')
        styler.element_create('live.TNotebook', "from", 'default')
        styler.element_create('dut.TLabelframe', 'from', 'default')
        styler.element_create('brk.TLabelframe', 'from', 'default')
        styler.element_create('yoko.TLabelframe', 'from', 'default')
        styler.element_create('dut.TLabel', 'from', 'default')
        styler.element_create('brk.TLabel', 'from', 'default')
        styler.element_create('brk.TCheckbutton', 'from', 'default')
        styler.element_create('yoko.TLabel', 'from', 'default')
        styler.element_create('maintitle.TLabel', 'from', 'default')
    except TclError:
        pass
    # Redefine the TNotebook Tab layout to use the new element
    styler.layout("TNotebook.Tab",
                  [('Plain.Notebook.tab',
                    {'children': [('Notebook.padding',
                                   {'children': [('Notebook.focus',
                                                  {'children': [('Notebook.label',
                                                                 {'sticky': 'news'})],
                                                   'sticky': 'nswe'})],
                                    'sticky': 'nswe'})],
                     'sticky': 'nswe'})])
    styler.configure("TNotebook", background='white' if mode else "#26242f", borderwidth=-1, tabposition='sw')
    styler.configure("TNotebook.Tab", background='white' if mode else "#26242f", foreground="#5DA01D",
                     borderwidth=0, width=15, anchor='center', padding=[0, 0, 0, 2])
    styler.map("TNotebook.Tab", background=[("selected", "#5DA01D")], foreground=[("selected", 'white' if mode else "#26242f")])
    styler.configure("live.TNotebook", background='white' if mode else "#26242f", borderwidth=0, tabposition='ne', tabmargins=0)
    styler.layout("live.TNotebook", [])
    styler.layout("live.TNotebook.Tab", [])
    styler.map("live.TNotebook.Tab", background=[("selected", "#5DA01D")], foreground=[("selected", 'white' if mode else "#26242f")])

    styler.configure("home_dut.TNotebook", background='#ccccff' if mode else "#26242f", borderwidth=-1, tabposition='nw')
    styler.map("home_dut.TNotebook.Tab", background=[("selected", "#5DA01D")], foreground=[("selected", 'white' if mode else "#26242f")])
    styler.configure("home_dut.TNotebook.Tab", background='#ccccff' if mode else "#26242f",
                     borderwidth=0, width=15, anchor='center', padding=0)

    styler.configure("home_brk.TNotebook", background='#ccffcc' if mode else "#26242f", borderwidth=-1, tabposition='nw')
    styler.map("home_dut.TNotebook.Tab", background=[("selected", "#5DA01D")], foreground=[("selected", 'white' if mode else "#26242f")])
    styler.configure("home_brk.TNotebook.Tab", background='#ccffcc' if mode else "#26242f",
                     borderwidth=0, width=15, anchor='center', padding=0)
    styler.configure("TFrame", background='white' if mode else "#26242f", foreground='black' if mode else 'white', borderwidth=0)
    styler.configure("TButton", background='#d9d9d9' if mode else "#26242f", foreground='black' if mode else 'white', borderwidth=0)
    styler.map('TButton', background=[('active', '#d9d9d9' if mode else "#26242f")])
    styler.configure("TLabel", background='white' if mode else "#26242f", foreground='black' if mode else 'white', borderwidth=0)
    styler.configure("TLabelframe", background='white' if mode else "#26242f", foreground='black' if mode else 'white', borderwidth=0)
    styler.configure("TLabelframe.Label", background='white' if mode else "#26242f", foerground='black' if mode else 'white', borderwidth=0)
    styler.configure("TLabelframe.Text", background='white' if mode else "#26242f", foerground='black' if mode else 'white', borderwidth=0)
    styler.configure("TText", background='white' if mode else "#26242f", borderwidth=0)
    styler.configure("TCheckbutton", background='white' if mode else "#26242f", foerground='black' if mode else 'white',
                     borderwidth=0, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
    styler.configure('filter.TCheckbutton', font=f'{OPTION_FONT_NAME} 8')
    styler.configure('dut.TLabelframe', background='#ccccff' if mode else "#26242f")
    styler.configure('brk.TLabelframe', background='#ccffcc' if mode else "#26242f")
    styler.configure('yoko.TLabelframe', background='#ffffcc' if mode else "#26242f")
    styler.configure('dut.TLabel', background='#ccccff' if mode else "#26242f")
    styler.configure('brk.TLabel', background='#ccffcc' if mode else "#26242f")
    styler.configure('brk.TCheckbutton', background='#ccffcc' if mode else "#26242f")
    styler.configure('yoko.TLabel', background='#ffffcc' if mode else "#26242f")
    styler.configure(".", font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
    styler.configure('maintitle.TLabel', font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE + 2}')
    logging.info("Finished setting up styles")

def _com_ports():
    ports = []
    for port, desc, hwid in serial.tools.list_ports.comports():
        ports.append(port)
    ports.append('CAN')
    return ports


def _param_value_handler(value, scale=None):
    if scale != 'hex':
        if len(value) == 16 and '.' not in value:
            return float(int(value, 2))
    else:
        return int(value, 16)
    return float(value)


# pylint: disable=too-many-instance-attributes, too-many-lines
# pylint: disable=unused-argument, unused-variable
# pylint: disable=too-many-statements, too-many-branches


def _equal_config_value(value, config_value):
    if pd.isna(value) and pd.isna(config_value):
        return True
    elif pd.isna(value) and not pd.isna(config_value):
        return False
    elif not pd.isna(value) and pd.isna(config_value):
        return False
    elif not pd.isna(value) and not pd.isna(config_value):
        if value == config_value:
            return True
        else:
            return False

    return False


class DynoConnector:
    """DynoConnector: dyno-v2 GUI class"""

    def __init__(self, root):
        """
        Initiates GUI

        root: Tk()
        """
        logging.info("Initiation started")
        self.root = root
        self.root.title("ASI DynoModule Controller")
        self.width = IntVar(value=LAST_WIDTH)
        self.height = IntVar(value=LAST_HEIGHT)
        self.root.geometry(LAST_GEOMETRY)
        self.root.resizable(True, True)
        self.root.minsize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.root.iconbitmap(f'{ROOT_DIR}/dyno_v2/ASI Logo grayscale.ico')
        self.root['background'] = 'white'
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.tk.call('tk', 'scaling', 1.25)
        self.configs = config_reader()
        # self.configs_template = template_reader()
        self.dut_port = StringVar(value=self.configs.loc['default']['dut_port'])
        self.dut_rate = IntVar(value=int(self.configs.loc['default']['dut_baud']))
        self.dut_id = IntVar(value=int(self.configs.loc['default']['dut_id']))
        self.brk_port = StringVar(value=self.configs.loc['default']['brk_port'])
        temp = (0 if pd.isna(self.configs.loc['default']['brk_baud']) else int(self.configs.loc['default']['brk_baud']))
        self.brk_rate = IntVar(value=temp)
        temp = (0 if pd.isna(self.configs.loc['default']['brk_id']) else int(self.configs.loc['default']['brk_id']))
        self.brk_id = IntVar(value=temp)
        self.abb = BooleanVar(value=(True if self.configs.loc['default']['brk_controller'] == 'ABB' else False))
        self.abb_auto = BooleanVar(value=True)
        self.yoko_ip = IntVar(value=int(self.configs.loc['default']['yoko_ip']))
        self.config_list = None  # config list at test tab
        self.config_popup = None  # config pop up at home tab
        self.show_config = False
        self.config_value = StringVar(value='default')
        self.test = StringVar(value='Production/Rundown')
        self.connection_condition = StringVar()
        self.dut_var = BooleanVar(value=True)
        self.brk_var = BooleanVar(value=True)
        self.yoko_var = BooleanVar(value=True)
        self.connection_status = [BooleanVar(value=False), BooleanVar(value=False), BooleanVar(value=False)]
        self.dyno = None
        self.dut_frame = None
        self.dut_extra_frame = None
        self.dut_extra_frame_1 = None
        # self.dut_header = None
        self.brk_frame = None
        self.brk_extra_frame = None
        self.brk_extra_frame_1 = None
        # self.brk_header = None
        self.log_interval = IntVar(value=1)
        self.extra_file = StringVar(value="extra logging")
        self.same_folder = BooleanVar(value=True)
        self.plot_display = StringVar(value="save")
        self.error_display = StringVar(value="save")
        self.error2display = StringVar(value="DUT warnings")
        self.result_destination = StringVar(value="C:/DynoResults")
        self.controller_params = {"DUT": [], "BRK": [], "ABB": []}
        self.controller_params_raw = parse_etree(f"{ROOT_DIR}/GUI Controller.xml")
        self.test_start_time = datetime.now()
        self.test_duration = (datetime.now() - self.test_start_time).total_seconds()
        self.status_params = {"DUT": {},
                              "BRK": {},
                              "ABB": {},
                              'YOKO': {},
                              'TEST': {'Start Time': StringVar(value=f"{self.test_start_time.strftime('%H:%M:%S')}"),
                                       'Duration': StringVar(value=f'{self.test_duration:.1f}'),
                                       'Steps': StringVar(value='0/0'),
                                       'Cycles': StringVar(value='0/0'),
                                       'Est. Test Time': StringVar(value='0'),}}
        self.speed_limit_frame = None
        self.dut_status_frame = None
        self.brk_status_frame = None
        self.yoko_status_frame = None
        self.test_status_frame = None
        self.status_thread = None
        self.updating = False
        self.limit_timeout_id = None
        self.brk_torque_timeout_id = None
        self.speed_limit_upper = IntVar(value=5000)
        self.speed_limit_upper.trace_add('write', self._limit_changed)
        self.speed_limit_lower = IntVar(value=-5000)
        self.speed_limit_lower.trace_add('write', self._limit_changed)
        self.torque_limit = DoubleVar(value=float(self.configs.loc['default']['max_torque']))
        self.torque_limit.trace_add('write', self._limit_changed)
        self.graph_params = []
        self.ramp_target = DoubleVar(value=0)
        self.ramp_step = IntVar(value=5)
        self.ramp_duration = DoubleVar(value=0.1)
        self.run_duration_h = IntVar(value=0)
        self.run_duration_m = IntVar(value=0)
        self.run_duration_s = IntVar(value=0)
        self.run_timer_status = BooleanVar(value=False)
        self.calc_torque = DoubleVar(value=0)
        self.countdown_thread = None
        self.graphs = {}
        self.x_combo_var = StringVar()
        self.y_params_var = StringVar()
        self.motor_type = StringVar()
        self.text = None
        self.error_text = None
        self.edit_popup = StringVar(value="Edit")
        self.test_note = StringVar(value='Motor Type: ')
        self.current_motor = StringVar()
        self.testing = False
        self.cyclic = False
        self.config_filter = {}
        self.test_handler = None
        self.test_thread = None
        self.stopping = False
        self.with_barcode = BooleanVar(value=True)
        self.notify_progress = BooleanVar(value=False)
        self.rundown_zoom = BooleanVar(value=False)
        self.notify = BooleanVar(value=False)
        self.serial_num = StringVar(value="####-000##")
        self.serial_num_1 = StringVar(value="####-000##")
        self.barcode_var = StringVar()
        self.barcode_2_var = StringVar()
        self._graphing_thread = None
        self.can_interface = None
        self.enable_email = BooleanVar(value=False)
        self.enable_int_email = BooleanVar(value=False)
        self.main_parameters = {}
        self.main_elements = {}
        logging.info("Finished loading variables ")

        self.dark_mode = StringVar(value='Enable')
        self.output_toggle = StringVar(value='Hide')
        self.bac_2_bac = StringVar(value='Enable')
        self.font_size = IntVar(value=OPTION_FONT_SIZE)
        styling(True)
        self.root.option_add('*TCombobox*Listbox*Font', tkinter.font.Font(size=OPTION_FONT_SIZE))

        self.build_home_menu()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.notebook = ttk.Notebook(self.root, width=750, height=550, padding="5 5 0 0", style='TNotebook')
        self.notebook.columnconfigure(0, weight=1)
        self.notebook.rowconfigure(0, weight=1)
        self.notebook.grid(column=0, row=1, sticky='news')
        logging.info('Creating test home_screen section')
        self.home_screen = self.build_main_gui(self.notebook)
        logging.info("Creating connector section ")
        self.connector_tab = self.build_mainframe(self.notebook)
        # self.notebook.bind('<<NotebookTabChanged>>', self._update_ports)
        logging.info("Creating controller section ")
        self.controller_tab = self.build_controlframe(self.notebook)
        logging.info("Creating test script section ")
        self.test_tab = self.build_testframe(self.notebook)
        self._populate_config_list()
        logging.info("Creating live graphing section ")
        self.graph_tab = self.build_graphframe(self.notebook)
        # logging.info("Creating advanced section ")
        # self.advanced_tab = self.build_advanced_frame(self.notebook)
        # logging.info("Creating option section ")
        # self.option_tab = self.build_option_frame(self.notebook)

        self.status_bar = None

        logging.info("Binding hotkeys ")
        self.test_tab.children['config_desc_text'].bind('<KeyRelease>', self._update_description)
        # self.root.bind('<Escape>', self._dyno_stop)
        self.root.bind('<Escape>', self._e_stop)
        self.root.bind('<F1>', lambda e: self.notebook.select(0))
        self.root.bind('<F2>', lambda e: self.notebook.select(1))
        self.root.bind('<F3>', lambda e: self.notebook.select(2))
        self.root.bind('<F4>', lambda e: self.notebook.select(3))
        self.root.bind('<F5>', lambda e: self.notebook.select(4))
        # self.root.bind('<F6>', lambda e: self.notebook.select(5))
        # self.root.bind('<F7>', lambda e: self.notebook.select(6))
        self.root.bind('<Configure>', self._resize)

        logging.info("Creating output section")
        out_level = Toplevel(self.root)
        out_level.geometry(OUT_GEOMETRY)
        out_level.resizable(True, True)
        out_level.columnconfigure(1, weight=1)
        out_level.rowconfigure(1, weight=1)
        out_level.iconbitmap(f'{ROOT_DIR}/dyno_v2/ASI Logo grayscale.ico')
        out_level.protocol("WM_DELETE_WINDOW", lambda :None)
        self.n_out = ttk.Notebook(out_level, width=550, height=550, padding="0")
        self.n_out.grid(column=1, row=1, sticky='news')
        self.out_level = out_level
        self.build_out_menu()

        self.output_container = self.build_out_frame(self.n_out)
        self.error_container = self.build_out_error_frame(self.n_out)
        # out_level.iconify()
        # self.build_out_bubble()
        # self.redirect_error_2_log()

        self.bac_2_bac.set('Enable')
        self._bac_2_bac()

        # self.root.state('zoomed')

        # version indicator
        temp = ttk.Frame(self.root, width=50, height=20)
        temp.place(relx=0.88, rely=0.999, anchor='se')
        temp.columnconfigure((0, 1), weight=1)
        ttk.Label(temp, text='Version: ').grid(column=0, row=0, sticky='we')
        ttk.Label(temp, text=__version__).grid(column=1, row=0, sticky='w')

        # window size indicator
        temp = ttk.Frame(self.root, width=50, height=20)
        temp.place(relx=0.98, rely=0.999, anchor='se')
        temp.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(temp, textvariable=self.width).grid(column=0, row=0, sticky='e')
        ttk.Label(temp, text='x').grid(column=1, row=0, sticky='we')
        ttk.Label(temp, textvariable=self.height).grid(column=2, row=0, sticky='w')

        logging.info("Loading finished")
        print(f"Welcome to DynoController v{__version__}")
        print("Good luck with your tests!")

    def build_out_bubble(self):
        """
        GUI front end element
        Constructing output bubble
        Attempt to create AutoCAD style output
        On hold - not used anywhere
        """
        mainframe = Frame(self.root, bg='')
        mainframe.place(relx=0.5, rely=0.9, anchor='s')

        output = OutputBubble(mainframe, logger=logging.getLogger('STDOUT'))

        return mainframe


    def build_out_frame(self, root: ttk.Notebook):
        """
        GUI front end elements
        Constructing output frame
        """
        output_container = ttk.Frame(root, relief='flat')
        root.add(output_container, text="Output")

        default_font = font.nametofont(OPTION_FONT_NAME)
        default_font.config(size=OPTION_FONT_SIZE)
        self.text = Text(output_container, font=OPTION_FONT_NAME, background='black', foreground='white', relief='flat')
        self.text.grid(column=0, row=0, sticky='news')
        text_vsb = Scrollbar(output_container, orient="vertical", command=self.text.yview)
        text_vsb.grid(column=1, row=0, sticky="ns")
        text_hsb = Scrollbar(output_container, orient="horizontal", command=self.text.xview)
        text_hsb.grid(column=0, row=1, sticky="we")
        self.text.configure(yscrollcommand=text_vsb.set, xscrollcommand=text_hsb.set)
        output_container.grid_rowconfigure(0, weight=1)
        output_container.grid_columnconfigure(0, weight=1)
        output_container.grid_rowconfigure(1, weight=0)
        output_container.grid_columnconfigure(1, weight=0)
        # ttk.Button(output_container, text="Clear Output", command=self._clear_output).grid(column=0, row=2)

        logging.info("Redirecting output")
        # redirect stdout
        redirector = RedirectText(self.text, logging.getLogger('STDOUT'))
        sys.stdout = redirector

        return output_container

    def redirect_error_2_log(self):
        """
        GUI backend funtion
        Redirect stderr to logging
        """
        logging.info("Redirecting error")
        # redirect stderr
        redirector = RedirectError(logging.getLogger('STDERR'))
        sys.stderr = redirector

    def redirect_error(self):
        """
        GUI backend function
        Redirect strerr to GUI text output
        """
        logging.info("Redirecting error")
        # redirect stderr
        redirector = RedirectText(self.error_text, logging.getLogger('STDERR'))
        sys.stderr = redirector

    def build_out_error_frame(self, root: ttk.Notebook):
        """
        GUI front end element
        Constructing Error Frame
        """
        output_container = ttk.Frame(root, relief='flat')
        root.add(output_container, text="Error")

        default_font = font.nametofont(ERROR_FONT_NAME)
        default_font.config(size=OPTION_FONT_SIZE)
        self.error_text = Text(output_container, font=ERROR_FONT_NAME,
                               background='black', foreground='white')
        self.error_text.grid(column=0, row=0, sticky='news')
        text_vsb = Scrollbar(output_container, orient="vertical", command=self.error_text.yview)
        text_vsb.grid(column=1, row=0, sticky="ns")
        text_hsb = Scrollbar(output_container, orient="horizontal", command=self.error_text.xview)
        text_hsb.grid(column=0, row=1, sticky="we")
        self.error_text.configure(yscrollcommand=text_vsb.set, xscrollcommand=text_hsb.set)
        output_container.grid_rowconfigure(0, weight=1)
        output_container.grid_columnconfigure(0, weight=1)
        output_container.grid_rowconfigure(1, weight=0)
        output_container.grid_columnconfigure(1, weight=0)
        # ttk.Button(output_container, text="Clear Error", command=self._clear_error).grid(column=0, row=2)

        self.redirect_error()

        return output_container

    def build_main_gui(self, root: ttk.Notebook):
        """
        GUI front end element
        Constructing home page
        """
        mainframe = ttk.Frame(root, relief='flat')
        root.add(mainframe, text="Home [F1]")
        # for i in (0, 1, 2):
        #     mainframe.columnconfigure(i, weight=1)
        # for i in (2, 3):
        #     mainframe.rowconfigure(i, weight=1)

        # container = ttk.Frame(mainframe, relief='flat', name='dyno_set_container')
        # container.grid(column=1, row=1, columnspan=2, sticky='news')
        # container.place(relx=0.5, rely=0.1, anchor='s')

        self.main_elements['column_1'] = ttk.Frame(mainframe, relief='flat')
        self.main_elements['column_1'].grid(column=1, row=1, sticky='news')
        self.main_elements['column_2'] = ttk.Frame(mainframe, relief='flat')
        self.main_elements['column_2'].grid(column=2, row=1, sticky='news')
        self.main_elements['column_3'] = ttk.Frame(mainframe, relief='flat')
        self.main_elements['column_3'].grid(column=3, row=1, sticky='news')

        self.main_elements['column_1'].columnconfigure(0, weight=1)
        self.main_elements['column_2'].columnconfigure(0, weight=1)
        self.main_elements['column_3'].columnconfigure(0, weight=1)
        self.main_elements['column_1'].rowconfigure((0, 1, 2), weight=1)
        self.main_elements['column_2'].rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.main_elements['column_3'].rowconfigure((0, 1), weight=1, minsize=MIN_HEIGHT * 0.5)

        mainframe.columnconfigure((1, 2, 3), weight=1)
        mainframe.columnconfigure((0, 4), minsize=30)

        container = ttk.Frame(self.main_elements['column_2'], relief='flat')
        container.grid(column=0, row=0)

        self.main_parameters['dyno_set'] = StringVar(value=DYNO_SET)
        temp = ttk.Combobox(container, textvariable=self.main_parameters['dyno_set'],
                            name='dyno_set', font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        temp.grid(column=0, row=0, padx=20)
        # temp.place(relx=0.5, y=20, anchor='e')
        temp['values'] = [DYNO_SET, 'BAC2BAC']
        temp.bind('<<ComboboxSelected>>', self.update_main_set)

        temp = ttk.Button(container, textvariable=self.connection_condition,
                          command=self._main_connect, name='connect_btn', width=15)
        temp.grid(column=1, row=0, padx=20)
        # temp.place(relx=0.595, y=20, anchor='e')

        temp = ttk.Button(container, text='+',
                          command=lambda: self.notebook.select(1),
                          name='more_connect_btn', width=3)
        temp.grid(column=2, row=0, padx=20)
        # temp.place(relx=0.6, y=20, anchor='w')

        # self.main_parameters['big_dyno_brk'] = StringVar(value='ABB')
        # temp = ttk.Combobox(mainframe, textvariable=self.main_parameters['big_dyno_brk'], name='big_dyno_brk')
        # temp['values'] = ['ABB', 'ASI', 'Line Reactor', 'N/A']
        # temp.place(relx=0.7, y=20, anchor='center')
        # if DYNO_SET == 'BIG DYNO':
        #     # temp.grid(column=2, row=0, sticky='w')
        #     temp['state'] = DISABLED

        container = ttk.Frame(self.main_elements['column_2'], relief='flat')
        container.grid(column=0, row=2)

        self.main_canvas = Canvas(container, width=400, height=200, background='white',
                                  bd=0, highlightthickness=0, relief='ridge')
        self.main_canvas.grid(column=0, row=1)
        # self.main_canvas.place(relx=0.5, rely=0.1, anchor='n')

        self.dyno_gui = DynoSet(self.main_canvas,
                                dut=''
                                    if pd.isna(self.configs.loc['default']['dut_controller'])
                                    else self.configs.loc['default']['dut_controller'],
                                brk=''
                                    if pd.isna(self.configs.loc['default']['brk_controller'])
                                    else self.configs.loc['default']['brk_controller'])

        self.main_parameters['dut_controller'] = StringVar(value=self.configs.loc['default']['dut_controller'])
        self.main_parameters['brk_controller'] = StringVar(value=self.configs.loc['default']['brk_controller'])
        self.main_parameters['dut_motor'] = StringVar(value=self.configs.loc['default']['dut_motor'])
        self.main_parameters['brk_motor'] = StringVar(value=self.configs.loc['default']['brk_motor'])

        container = ttk.Frame(self.main_elements['column_2'], relief='flat')
        container.grid(column=0, row=1)
        container.columnconfigure((0, 1, 2), weight=1)

        temp_widget = ttk.Checkbutton(container, variable=self.dut_var, onvalue=True,
                                      name='main_dut_check', takefocus=False)
        temp_widget.grid(column=0, row=0, padx=50)
        # temp_widget.place(relx=0.41, rely=0.06, anchor='n')
        self.main_elements['dut_check'] = temp_widget
        temp_widget = ttk.Checkbutton(container, variable=self.brk_var, onvalue=True,
                                      name='main_brk_check', takefocus=False)
        temp_widget.grid(column=2, row=0, padx=50)
        # temp_widget.place(relx=0.6, rely=0.06, anchor='n')
        self.main_elements['brk_check'] = temp_widget
        temp_widget = ttk.Checkbutton(container, variable=self.yoko_var, onvalue=True,
                                      name='main_yoko_check', takefocus=False, command=self.toggle_yoko)
        temp_widget.grid(column=1, row=0, padx=50)
        # temp_widget.place(relx=0.5, rely=0.06, anchor='n')
        self.main_elements['yoko_check'] = temp_widget

        def make_dut_section():
            """
            GUI front end
            Building DUT section on home screen
            """
            container = ttk.Frame(self.main_elements['column_1'], relief='flat')
            container.grid(column=0, row=0)

            label = Label(container, text='DUT', font=('Comic Sans', 15), background='#ccccff')
            temp = ttk.LabelFrame(container, width=MIN_WIDTH * 0.3, height=MIN_HEIGHT * 0.55,
                                  labelanchor='n', labelwidget=label, style='dut.TLabelframe')
            temp.grid(column=0, row=0)
            # temp.place(relx=0.35, rely=0.49, anchor='se')

            # motor controller selection
            temp_container = Frame(temp, background="#ccccff", relief='flat')
            temp_container.grid(column=0, row=0)

            temp_widget = Label(temp_container, text="Motor:", background='#ccccff')
            # temp_widget.place(relx=0.02, rely=0.05, anchor='sw')
            temp_widget.grid(column=0, row=0, padx=10)

            temp_widget = ttk.Combobox(temp_container, textvariable=self.main_parameters['dut_motor'],
                                       name='main_dut_motor_cb', width=10,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.15, rely=0.05, anchor='sw')
            temp_widget.grid(column=1, row=0, padx=10)
            temp_widget['values'] = DUT_MOTOR_SELECTION
            temp_widget.bind('<<ComboboxSelected>>', self.update_main)

            temp_widget = ASIStatusIndicator(temp_container, 'DUT')
            # temp_widget.canvas.place(relx=0.97, rely=0.01, anchor='center')
            temp_widget.canvas.grid(column=4, row=0, sticky='e', padx='30 0')
            self.main_elements['dut_indicator'] = temp_widget

            temp_widget = Label(temp_container, text="Controller:", background='#ccccff')
            # temp_widget.place(relx=0.5, rely=0.05, anchor='sw')
            temp_widget.grid(column=2, row=0, sticky='e', padx=10)

            temp_widget = ttk.Combobox(temp_container, textvariable=self.main_parameters['dut_controller'],
                                       name='main_dut_controller_cb', width=10,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.7, rely=0.05, anchor='sw')
            temp_widget.grid(column=3, row=0, sticky='e', padx=10)
            temp_widget['values'] = DUT_CONTROLLER_SELECTION
            temp_widget.bind('<<ComboboxSelected>>', self.update_main)

            # parameter/status notebook
            temp_note = ttk.Notebook(temp, style='home_dut.TNotebook', width=int(MIN_WIDTH * 0.29),
                                     height=int(MIN_HEIGHT * 0.22))
            # temp_note.place(relx=0.02, rely=0.07, anchor='nw')
            temp_note.grid(column=0, row=1, padx='10', pady='5', sticky='news')
            temp_note_frame = Frame(temp_note, background='#ccccff',
                                    width=MIN_WIDTH * 0.29, height=MIN_HEIGHT * 0.2)
            temp_note_frame.columnconfigure((0, 1), weight=1)
            temp_note.add(temp_note_frame, text='Parameters')

            # Motor spec. parameters
            temp_container = Frame(temp_note_frame, name="dut_motor_params",
                                   background='#ccccff', width=MIN_WIDTH * 0.17)
            self.main_elements['dut_motor_params'] = temp_container
            # temp_container.place(relx=0.02, rely=0.07, anchor='nw')
            temp_container.grid(column=0, row=0)
            s_frame = ScrollableFrame(temp_container, width=MIN_WIDTH * 0.17,
                                      height=MIN_HEIGHT * 0.2, background='#ccccff')
            s_frame.pack(fill='both')
            # s_frame.grid()
            self.main_elements['dut_motor_param_frame'] = s_frame.scrollable_frame
            for i in (0, 1, 2):
                self.main_elements['dut_motor_param_frame'].columnconfigure(i, weight=1)

            for i, p in enumerate(MOTOR_MAIN_PARAMETERS):
                Label(self.main_elements['dut_motor_param_frame'] , text=p[0],
                      name=f"main_dut_param_{p[0]}",
                      background="#ccccff", pady=2,
                      justify='right', anchor='e').grid(column=0,
                                                        row=1 + i,
                                                        sticky='e')
                self.main_elements['dut_motor_param_frame'].children[
                    f"main_dut_param_{p[0]}"].bind('<MouseWheel>',
                                                   self.main_elements['dut_motor_param_frame'].master.master.on_mousewheel)
                self.main_parameters[f'dut_{p[0]}'] = StringVar(value='0')
                Entry(self.main_elements['dut_motor_param_frame'],
                      textvariable=self.main_parameters[f'dut_{p[0]}'], width=8,
                      name=f"main_dut_param_{p[0]}_value",
                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=1,
                                                                row=1 + i, sticky='we')
                self.main_elements['dut_motor_param_frame'].children[
                    f"main_dut_param_{p[0]}_value"].bind('<Return>', self._upload_main)
                self.main_elements['dut_motor_param_frame'].children[
                    f"main_dut_param_{p[0]}_value"].bind('<FocusIn>',
                                                         lambda e: e.widget.select_range(0, END))
                self.main_elements['dut_motor_param_frame'].children[
                    f"main_dut_param_{p[0]}_value"].bind('<Button-1>',
                                                         lambda e: e.widget.select_range(0, END))
                self.main_elements['dut_motor_param_frame'].children[
                    f"main_dut_param_{p[0]}_value"].bind('<MouseWheel>',
                                                         self.main_elements[
                                                             'dut_motor_param_frame'].master.master.on_mousewheel)
                Label(self.main_elements['dut_motor_param_frame'],
                      text=p[1],
                      name=f"main_dut_param_{p[0]}_unit",
                      background="#ccccff", pady=2).grid(column=2,
                                                         row=1 + i, sticky='w')
                self.main_elements['dut_motor_param_frame'].children[
                    f"main_dut_param_{p[0]}_unit"].bind('<MouseWheel>',
                                                         self.main_elements[
                                                             'dut_motor_param_frame'].master.master.on_mousewheel)

            temp_container = Frame(temp_note_frame, name="dut_motor_halls",
                                   background='#ccccff', width=MIN_WIDTH * 0.1)
            self.main_elements['dut_motor_halls'] = temp_container
            # temp_container.place(relx=0.98, rely=0.07, anchor='ne')
            temp_container.grid(column=1, row=0)
            s_frame = ScrollableFrame(temp_container, width=MIN_WIDTH * 0.09,
                                      height=MIN_HEIGHT * 0.2, background='#ccccff')
            s_frame.pack(fill='both')
            self.main_elements['dut_motor_halls_frame'] = s_frame.scrollable_frame
            for i in (0, 1):
                self.main_elements['dut_motor_halls_frame'].columnconfigure(i, weight=1)

            for i, p in enumerate(MOTOR_HALLS):
                Label(self.main_elements['dut_motor_halls_frame'], text=p,
                      name=f"main_dut_param_{p}",
                      background="#ccccff", pady=2,
                      justify='right', anchor='e').grid(column=0,
                                                        row=1 + i,
                                                        sticky='e')
                self.main_elements['dut_motor_halls_frame'].children[
                    f"main_dut_param_{p}"].bind('<MouseWheel>',
                                                self.main_elements[
                                                    'dut_motor_halls_frame'].master.master.on_mousewheel)
                self.main_parameters[f'dut_{p}'] = StringVar(value='0')
                Entry(self.main_elements['dut_motor_halls_frame'],
                      textvariable=self.main_parameters[f'dut_{p}'], width=6,
                      name=f"main_dut_param_{p}_value",
                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=1, row=1 + i, sticky='e')
                self.main_elements['dut_motor_halls_frame'].children[
                    f"main_dut_param_{p}_value"].bind('<Return>', self._upload_main)
                self.main_elements['dut_motor_halls_frame'].children[
                    f"main_dut_param_{p}_value"].bind('<FocusIn>',
                                                      lambda e: e.widget.select_range(0, END))
                self.main_elements['dut_motor_halls_frame'].children[
                    f"main_dut_param_{p}_value"].bind('<Button-1>',
                                                      lambda e: e.widget.select_range(0, END))
                self.main_elements['dut_motor_halls_frame'].children[
                    f"main_dut_param_{p}_value"].bind('<MouseWheel>',
                                                      self.main_elements[
                                                          'dut_motor_halls_frame'].master.master.on_mousewheel)

            # status
            temp_container = ttk.Frame(temp_note, relief='flat',
                                       width=MIN_WIDTH * 0.29, height=MIN_HEIGHT * 0.22)
            temp_note.add(temp_container, text='Status')
            temp_container.columnconfigure(0, weight=1)

            s_frame = ScrollableFrame(temp_container,
                                      width=MIN_WIDTH * 0.28,
                                      height=MIN_HEIGHT * 0.22,
                                      background='#ccccff')
            s_frame.grid(column=0, row=0, sticky='news')
            s_frame.columnconfigure(0, weight=1)
            # s_frame.pack(fill='both')
            self.main_elements['live_param_frame'] = s_frame.scrollable_frame
            for i in (0, 1):
                self.main_elements['live_param_frame'].columnconfigure(i, weight=1)

            self.main_parameters['live_list_parameters'] = {}
            self.main_parameters['live_list_params'] = parse_etree(f"{ROOT_DIR}/status_parameters.xml")
            for controller in ['DUT']:
                for element in self.main_parameters['live_list_params'].findall(f"{controller}/Name"):
                    self.main_parameters['live_list_parameters'][f'{controller} {element.text}'] = DoubleVar(value=0)

            for i, p in enumerate(self.main_parameters['live_list_parameters']):
                Label(self.main_elements['live_param_frame'], text=p, background='#ccccff',
                      name=f"main_live_list_param_{p}_{i}", font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}',
                      pady=2, justify='center', anchor='center').grid(
                    column=(i % 2), row=int(i / 2) * 2, sticky='we')
                self.main_elements['live_param_frame'].children[
                    f"main_live_list_param_{p}_{i}"].bind('<MouseWheel>',
                                                          self.main_elements[
                                                              'live_param_frame'].master.master.on_mousewheel)
                self.main_parameters[f'live_list_param_{p}_{i}'] = StringVar(value='0')
                Label(self.main_elements['live_param_frame'],
                      textvariable=self.main_parameters[f'live_list_param_{p}_{i}'],
                      width=6, name=f"main_live_list_param_{p}_{i}_value",
                      font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}', background='#ccccff', pady=2).grid(
                    column=(i % 2), row=int(i / 2) * 2 + 1, sticky='we')
                self.main_elements['live_param_frame'].children[
                    f"main_live_list_param_{p}_{i}_value"].bind(
                    '<MouseWheel>',
                    self.main_elements['live_param_frame'].master.master.on_mousewheel)

            # DUT custom spin
            self.main_parameters['dut_main_spin_mode'] = StringVar(value='Speed')
            self.main_parameters['dut_main_speed_rpm'] = DoubleVar(value=0)
            self.main_parameters['dut_main_motoring'] = DoubleVar(value=0)
            self.main_parameters['dut_main_braking'] = DoubleVar(value=0)
            self.main_parameters['dut_main_speed_command'] = DoubleVar(value=0)
            self.main_parameters['dut_main_torque'] = DoubleVar(value=0)
            self.main_parameters['dut_main_modulation'] = DoubleVar(value=0)
            self.main_parameters['dut_main_current'] = DoubleVar(value=0)
            self.main_parameters['dut_main_frequency'] = DoubleVar(value=0)
            self.main_parameters['dut_main_angle'] = DoubleVar(value=0)

            temp_main_container = LabelFrame(temp, name="dut_motor_spin",
                                             background='#ccccff', text='A Quick Spin',
                                             width=MIN_WIDTH * 0.29, height=MIN_HEIGHT * 0.14)
            self.main_elements['dut_main_spin'] = temp_main_container
            # temp_main_container.place(relx=0.02, rely=0.55, anchor='nw')
            temp_main_container.grid(column=0, row=2, padx='10', sticky='news')
            temp_main_container.columnconfigure((0, 1, 2, 3, 4), weight=1)

            temp_widget = Label(temp_main_container, text="Speed Regulator Mode:", background='#ccccff')
            # temp_widget.place(relx=0.02, rely=0.02, anchor='nw')
            temp_widget.grid(column=0, row=0, columnspan=2)

            temp_widget = ttk.Combobox(temp_main_container,
                                       textvariable=self.main_parameters['dut_main_spin_mode'],
                                       name='main_dut_spin_mode', width=20,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.4, rely=0.02, anchor='nw')
            temp_widget.grid(column=2, row=0, columnspan=2)
            temp_widget['values'] = MAIN_SPIN_MODE
            temp_widget.bind('<<ComboboxSelected>>', self._update_main_spin)

            temp_widget = Button(temp_main_container, text='Run', command=self._run_main_spin,
                                 bg='green', activebackground='green',
                                 fg='white', activeforeground='white')
            # temp_widget.place(relx=0.98, rely=0, anchor='ne')
            temp_widget.grid(column=4, row=0, rowspan=3, sticky='news')

            # Spin RPM
            temp_widget = Label(temp_main_container, text="RPM:", background='#ccccff')
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_speed_rpm_label'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_speed_rpm_label'][1], anchor='nw')
            temp_widget.grid(column=0, row=1)
            self.main_elements['dut_main_speed_rpm_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_speed_rpm'], width=10)
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_speed_rpm'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_speed_rpm'][1], anchor='nw')
            temp_widget.grid(column=1, row=1)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_speed_rpm'] = temp_widget
            # Spin Speed
            temp_widget = Label(temp_main_container, text="Speed Command:", background='#ccccff')
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_speed_command_label'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_speed_command_label'][1], anchor='nw')
            temp_widget.grid(column=2, row=1)
            self.main_elements['dut_main_speed_command_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_speed_command'], width=10)
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_speed_command'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_speed_command'][1], anchor='nw')
            temp_widget.grid(column=3, row=1)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_speed_command'] = temp_widget
            # Spin torque
            temp_widget = Label(temp_main_container, text="Torque:", background='#ccccff')
            self.main_elements['dut_main_torque_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_torque'], width=10)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_torque'] = temp_widget
            # Spin motoring
            temp_widget = Label(temp_main_container, text="Motoring:", background='#ccccff')
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_motoring_label'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_motoring_label'][1], anchor='nw')
            temp_widget.grid(column=0, row=2)
            self.main_elements['dut_main_motoring_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_motoring'], width=10)
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_motoring'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_motoring'][1], anchor='nw')
            temp_widget.grid(column=1, row=2)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_motoring'] = temp_widget
            # Spin braking
            temp_widget = Label(temp_main_container, text="Braking:", background='#ccccff')
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_braking_label'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_braking_label'][1], anchor='nw')
            temp_widget.grid(column=2, row=2)
            self.main_elements['dut_main_braking_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_braking'], width=10)
            # temp_widget.place(relx=MAIN_SPIN_PLACE['dut_main_braking'][0],
            #                   rely=MAIN_SPIN_PLACE['dut_main_braking'][1], anchor='nw')
            temp_widget.grid(column=3, row=2)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_braking'] = temp_widget
            # Spin open loop current
            temp_widget = Label(temp_main_container, text="Current:", background='#ccccff')
            self.main_elements['dut_main_current_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_current'], width=10)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_current'] = temp_widget
            # Spin open loop modulation
            temp_widget = Label(temp_main_container, text="Modulation:", background='#ccccff')
            self.main_elements['dut_main_modulation_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_modulation'], width=10)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_modulation'] = temp_widget
            # Spin open loop frequency
            temp_widget = Label(temp_main_container, text="Frequency:", background='#ccccff')
            self.main_elements['dut_main_frequency_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_frequency'], width=10)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_frequency'] = temp_widget
            # Spin open loop angle
            temp_widget = Label(temp_main_container, text="Angle:", background='#ccccff')
            self.main_elements['dut_main_angle_label'] = temp_widget
            temp_widget = Entry(temp_main_container, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                                textvariable=self.main_parameters['dut_main_angle'], width=10)
            temp_widget.bind('<Return>', self._run_main_spin)
            temp_widget.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
            temp_widget.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
            self.main_elements['dut_main_angle'] = temp_widget

            # DUT buttons
            temp_main_container = Frame(temp, background="#ccccff", relief='flat')
            temp_main_container.grid(column=0, row=5, sticky='w', padx='10', pady='5')

            # DUT control buttons
            temp_container = Frame(temp_main_container, width=200, height=20,
                                   background="#ccccff", relief='flat')
            # temp_container.place(relx=0.02, rely=0.91, anchor='sw')
            temp_container.grid(column=0, row=0, pady=2)

            temp_widget = Label(temp_container, text="Remote state command:", background='#ccccff')
            # temp_widget.place(relx=0.02, rely=0.89, anchor='sw')
            temp_widget.grid(column=0, row=0, padx='0 10')

            # Remote State Command - 0
            temp_widget = Button(temp_container, text="0", command=self._dut_stop,
                                 name='stop_btn', width=4, pady=0,
                                 foreground='white', activeforeground='white',
                                 background='red', activebackground='red')
            # temp_widget.place(relx=0.33, rely=0.90, anchor='sw')
            temp_widget.grid(column=1, row=0)
            self.main_elements['brk_start_btn'] = temp_widget
            temp_widget = ToolTip(temp_container.children['stop_btn'], delay=TOOLTIP_DELAY,
                                  msg="write 0 to Remote state command")
            self.main_elements['brk_start_tt'] = temp_widget

            # Remote State Command - 1
            temp_widget = Button(temp_container, text="1", command=self._dut_idle,
                                 name='idle_btn', width=4, pady=0,
                                 background='yellow', activebackground='yellow')
            # temp_widget.place(relx=0.41, rely=0.90, anchor='sw')
            temp_widget.grid(column=2, row=0)
            self.main_elements['dut_idle_btn'] = temp_widget
            temp_widget = ToolTip(temp_container.children['idle_btn'], delay=TOOLTIP_DELAY,
                                msg="write 1 to Remote state command")
            self.main_elements['dut_idle_tt'] = temp_widget

            # Remote State Command - 2
            temp_widget = Button(temp_container, text="2", command=self._dut_start,
                                 name='start_btn', width=4, pady=0,
                                 foreground='white', activeforeground='white',
                                 background='green', activebackground='green')
            # temp_widget.place(relx=0.49, rely=0.90, anchor='sw')
            temp_widget.grid(column=3, row=0)
            self.main_elements['dut_start_btn'] = temp_widget
            temp_widget = ToolTip(temp_container.children['start_btn'], delay=TOOLTIP_DELAY,
                                msg="write 2 to Remote state command")
            self.main_elements['dut_start_tt'] = temp_widget

            # Motor discovery
            temp_container = Frame(temp_main_container, width=100, height=20,
                                   background="#ccccff", relief='flat')
            # temp_container.place(relx=0.6, rely=0.91, anchor='sw')
            temp_container.grid(column=1, row=0, padx='20 5', pady=2)

            temp_widget = Label(temp_container, text="Motor Discovery", background='#ccccff')
            # temp_widget.place(relx=0.6, rely=0.89, anchor='sw')
            temp_widget.grid(column=0, row=0)

            # Motor Discovery - 1
            temp_widget = Button(temp_container, text="1", command=lambda: self._gui_motor_discovery(1, 1),
                                     name='dut_motor_discovery_btn_1', width=2, pady=0)
            # temp_widget.place(relx=0.85, rely=0.9, anchor='sw')
            temp_widget.grid(column=1, row=0, sticky='e')
            self.main_elements['dut_motor_disc_1'] = temp_widget
            # Motor Discovery - 1
            temp_widget = Button(temp_container, text="2", command=lambda: self._gui_motor_discovery(1, 2),
                       name='dut_motor_discovery_btn_2', width=2, pady=0)
            # temp_widget.place(relx=0.9, rely=0.9, anchor='sw')
            temp_widget.grid(column=2, row=0)
            self.main_elements['dut_motor_disc_2'] = temp_widget

            # Save to flash
            temp_container = Frame(temp_main_container, width=100, height=20,
                                   background="#ccccff", relief='flat')
            # temp_container.place(relx=0.7, rely=0.98, anchor='sw')
            temp_container.grid(column=1, row=1, pady=2)

            temp_widget = Button(temp_container, text="Save to Flash", pady=0,
                                     command=self._flash_dut, name='dut_save2flash_btn')
            # temp_widget.place(relx=0.7, rely=0.98, anchor='sw')
            temp_widget.grid()
            ToolTip(temp_container.children['dut_save2flash_btn'],
                    delay=TOOLTIP_DELAY, msg="Driver save to flash")

            # parameter file
            temp_container = Frame(temp_main_container, width=100, height=20,
                                   background="#ccccff", relief='flat')
            # temp_container.place(relx=0.02, rely=0.98, anchor='sw')
            temp_container.grid(column=0, row=1, sticky='w', pady=2)

            temp_widget = Label(temp_container, text="Parameter File", background='#ccccff')
            # temp_widget.place(relx=0.02, rely=0.97, anchor='sw')
            temp_widget.grid(column=0, row=0)
            # Load parameter file
            temp_widget = Button(temp_container, text="Load", command=self._file_load_dut,
                                     name='dut_load_param_btn', width=5, pady=0)
            # temp_widget.place(relx=0.22, rely=0.98, anchor='sw')
            temp_widget.grid(column=1, row=0)
            ToolTip(temp_container.children['dut_load_param_btn'],
                    delay=TOOLTIP_DELAY, msg="Driver load parameter file")
            # Save parameter to file
            temp_widget = Button(temp_container, text="Save", pady=0,
                                     command=self._file_save_dut, name='dut_save_param_btn', width=5)
            # temp_widget.place(relx=0.32, rely=0.98, anchor='sw')
            temp_widget.grid(column=2, row=0)
            ToolTip(temp_container.children['dut_save_param_btn'],
                    delay=TOOLTIP_DELAY, msg="Driver save parameters to file")

            # temp = Button(temp, text='+',
            #               command=lambda: self.notebook.select(2),
            #               name='more_control_btn', width=1)
            # temp.place(relx=.99, rely=.99, anchor='se')
            temp_widget = ASIIcons(temp, size=25, item='list', background='#ccccff')
            temp_widget.canvas.bind("<Button-1>", lambda x: self.notebook.select(2))
            temp_widget.canvas.place(relx=.99, rely=.99, anchor='se')

        def make_brk_section():
            """
            GUI front end
            Building BRK section on home screen
            """
            container = ttk.Frame(self.main_elements['column_3'], relief='flat')
            container.grid(column=0, row=0, sticky='n')

            label = Label(container, text='BRK', font=('Comic Sans', 15), background='#ccffcc')
            temp = ttk.LabelFrame(container, width=MIN_WIDTH * 0.3, height=MIN_HEIGHT * 0.55,
                                  labelanchor='n', labelwidget=label, style='brk.TLabelframe')
            temp.grid(column=0, row=0, sticky='news')
            # temp.place(relx=0.65, rely=0.49, anchor='sw')

            # motor controller selection
            temp_container = Frame(temp, background="#ccffcc", relief='flat')
            temp_container.grid(column=0, row=0)

            temp_widget = Label(temp_container, text="Motor:", background='#ccffcc')
            # temp_widget.place(relx=0.02, rely=0.05, anchor='sw')
            temp_widget.grid(column=0, row=0, padx=10)

            temp_widget = ttk.Combobox(temp_container,
                                       textvariable=self.main_parameters['brk_motor'],
                                       name='main_brk_motor_cb', width=10,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.15, rely=0.05, anchor='sw')
            temp_widget.grid(column=1, row=0, padx=10)
            temp_widget['values'] = BRK_MOTOR_SELECTION
            temp_widget.bind('<<ComboboxSelected>>', self.update_main)

            temp_widget = Label(temp_container, text="Controller:", background='#ccffcc')
            # temp_widget.place(relx=0.5, rely=0.05, anchor='sw')
            temp_widget.grid(column=2, row=0, padx=10)

            temp_widget = ttk.Combobox(temp_container, textvariable=self.main_parameters['brk_controller'],
                                       name='main_brk_controller_cb', width=10,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.7, rely=0.05, anchor='sw')
            temp_widget.grid(column=3, row=0, padx=10)
            temp_widget['values'] = BRK_CONTROLLER_SELECTION
            temp_widget.bind('<<ComboboxSelected>>', self.update_main)

            temp_widget = ASIStatusIndicator(temp_container, 'BRK')
            # temp_widget.canvas.place(relx=0.97, rely=0.01, anchor='center')
            temp_widget.canvas.grid(column=4, row=0, sticky='e', padx='30 0')
            self.main_elements['brk_indicator'] = temp_widget

            temp_note = ttk.Notebook(temp, style='home_brk.TNotebook', width=int(MIN_WIDTH * 0.29),
                                     height=int(MIN_HEIGHT * 0.22))
            # temp_note.place(relx=0.02, rely=0.07, anchor='nw')
            temp_note.grid(column=0, row=1, padx='10', pady='5')
            temp_note_frame = Frame(temp_note, background='#ccffcc',
                                    width=MIN_WIDTH * 0.29, height=MIN_HEIGHT * 0.2)
            temp_note_frame.columnconfigure((0, 1), weight=1)
            temp_note.add(temp_note_frame, text='Parameters')

            # Motor spec. parameters
            temp_container = Frame(temp_note_frame, name="brk_motor_params",
                                   background='#ccffcc', width=MIN_WIDTH * 0.17)
            self.main_elements['brk_motor_params'] = temp_container
            # temp_container.place(relx=0.02, rely=0.07, anchor='nw')
            temp_container.grid(column=0, row=0)
            s_frame = ScrollableFrame(temp_container,
                                      width=MIN_WIDTH * 0.17,
                                      height=MIN_HEIGHT * 0.2,
                                      background='#ccffcc')
            s_frame.pack(fill='both')
            self.main_elements['brk_motor_param_frame'] = s_frame.scrollable_frame
            for i in (0, 1, 2):
                self.main_elements['brk_motor_param_frame'].columnconfigure(i, weight=1)

            for i, p in enumerate(MOTOR_MAIN_PARAMETERS):
                Label(self.main_elements['brk_motor_param_frame'], text=p[0],
                      name=f"main_brk_param_{p[0]}",
                      background="#ccffcc", pady=2, justify='right',
                      anchor='e').grid(column=0, row=1 + i, sticky='e')
                self.main_elements['brk_motor_param_frame'].children[
                    f"main_brk_param_{p[0]}"].bind('<MouseWheel>',
                                                   self.main_elements[
                                                       'brk_motor_param_frame'].master.master.on_mousewheel)
                self.main_parameters[f'brk_{p[0]}'] = StringVar(value='0')
                Entry(self.main_elements['brk_motor_param_frame'], font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                      textvariable=self.main_parameters[f'brk_{p[0]}'], width=8,
                      name=f"main_brk_param_{p[0]}_value").grid(column=1, row=1 + i, sticky='we')
                self.main_elements['brk_motor_param_frame'].children[
                    f"main_brk_param_{p[0]}_value"].bind('<Return>', self._upload_main)
                self.main_elements['brk_motor_param_frame'].children[
                    f"main_brk_param_{p[0]}_value"].bind('<FocusIn>',
                                                         lambda e: e.widget.select_range(0, END))
                self.main_elements['brk_motor_param_frame'].children[
                    f"main_brk_param_{p[0]}_value"].bind('<Button-1>',
                                                         lambda e: e.widget.select_range(0, END))
                self.main_elements['brk_motor_param_frame'].children[
                    f"main_brk_param_{p[0]}_value"].bind('<MouseWheel>',
                                                         self.main_elements[
                                                             'brk_motor_param_frame'].master.master.on_mousewheel)
                Label(self.main_elements['brk_motor_param_frame'],
                      text=p[1],
                      name=f"main_brk_param_{p[0]}_unit",
                      background="#ccffcc", pady=2).grid(
                    column=2, row=1 + i, sticky='e')
                self.main_elements['brk_motor_param_frame'].children[
                    f"main_brk_param_{p[0]}_unit"].bind('<MouseWheel>',
                                                         self.main_elements[
                                                             'brk_motor_param_frame'].master.master.on_mousewheel)

            temp_container = Frame(temp_note_frame, name="brk_motor_halls",
                                   background='#ccffcc', width=MIN_WIDTH * 0.09)
            self.main_elements['brk_motor_halls'] = temp_container
            # temp_container.place(relx=0.98, rely=0.07, anchor='ne')
            temp_container.grid(column=1, row=0)
            s_frame = ScrollableFrame(temp_container,
                                      width=MIN_WIDTH * 0.09, height=MIN_HEIGHT * 0.2,
                                      background='#ccffcc')
            s_frame.pack(fill='both')
            self.main_elements['brk_motor_halls_frame'] = s_frame.scrollable_frame
            for i in (0, 1):
                self.main_elements['brk_motor_halls_frame'].columnconfigure(i, weight=1)

            for i, p in enumerate(MOTOR_HALLS):
                Label(self.main_elements['brk_motor_halls_frame'], text=p,
                      name=f"main_brk_param_{p}",
                      background="#ccffcc", pady=2,
                      justify='right', anchor='e').grid(
                    column=0, row=1 + i, sticky='e')
                self.main_elements['brk_motor_halls_frame'].children[
                    f"main_brk_param_{p}"].bind('<MouseWheel>',
                                                self.main_elements[
                                                    'brk_motor_halls_frame'].master.master.on_mousewheel)
                self.main_parameters[f'brk_{p}'] = StringVar(value='0')
                Entry(self.main_elements['brk_motor_halls_frame'], font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
                      textvariable=self.main_parameters[f'brk_{p}'], width=6,
                      name=f"main_brk_param_{p}_value").grid(column=1, row=1 + i, sticky='e')
                self.main_elements['brk_motor_halls_frame'].children[
                    f"main_brk_param_{p}_value"].bind('<Return>', self._upload_main)
                self.main_elements['brk_motor_halls_frame'].children[
                    f"main_brk_param_{p}_value"].bind('<FocusIn>',
                                                      lambda e: e.widget.select_range(0, END))
                self.main_elements['brk_motor_halls_frame'].children[
                    f"main_brk_param_{p}_value"].bind('<Button-1>',
                                                      lambda e: e.widget.select_range(0, END))
                self.main_elements['brk_motor_halls_frame'].children[
                    f"main_brk_param_{p}_value"].bind('<MouseWheel>',
                                                      self.main_elements[
                                                          'brk_motor_halls_frame'].master.master.on_mousewheel)

            # status
            temp_container = ttk.Frame(temp_note, relief='flat',
                                       width=MIN_WIDTH * 0.29, height=MIN_HEIGHT * 0.22)
            temp_note.add(temp_container, text='Status')
            temp_container.columnconfigure(0, weight=1)

            s_frame = ScrollableFrame(temp_container,
                                      width=MIN_WIDTH * 0.28,
                                      height=MIN_HEIGHT * 0.22,
                                      background='#ccffcc')
            s_frame.grid(column=0, row=0, sticky='news')
            s_frame.columnconfigure(0, weight=1)
            # s_frame.pack(fill='both')
            self.main_elements['live_param_frame'] = s_frame.scrollable_frame
            for i in (0, 1):
                self.main_elements['live_param_frame'].columnconfigure(i, weight=1)

            # self.main_parameters['live_list_parameters'] = {}
            # self.main_parameters['live_list_params'] = parse_etree(f"{ROOT_DIR}/status_parameters.xml")
            i = len(self.main_parameters['live_list_parameters'])
            j = 0
            for controller in ['BRK']:
                for element in self.main_parameters['live_list_params'].findall(f"{controller}/Name"):
                    self.main_parameters['live_list_parameters'][f'{controller} {element.text}'] = DoubleVar(value=0)

            for p in self.main_parameters['live_list_parameters']:
                if p.split(' ')[0] == 'DUT':
                    continue
                Label(self.main_elements['live_param_frame'], text=p, background='#ccffcc',
                      name=f"main_live_list_param_{p}_{i}", font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}',
                      pady=2, justify='center', anchor='center').grid(
                    column=(j % 2), row=int(j / 2) * 2, sticky='we')
                self.main_elements['live_param_frame'].children[
                    f"main_live_list_param_{p}_{i}"].bind('<MouseWheel>',
                                                          self.main_elements[
                                                              'live_param_frame'].master.master.on_mousewheel)
                self.main_parameters[f'live_list_param_{p}_{i}'] = StringVar(value='0')
                Label(self.main_elements['live_param_frame'],
                      textvariable=self.main_parameters[f'live_list_param_{p}_{i}'],
                      width=6, name=f"main_live_list_param_{p}_{i}_value",
                      font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}', background='#ccffcc', pady=2).grid(
                    column=(j % 2), row=int(j / 2) * 2 + 1, sticky='we')
                self.main_elements['live_param_frame'].children[
                    f"main_live_list_param_{p}_{i}_value"].bind(
                    '<MouseWheel>',
                    self.main_elements['live_param_frame'].master.master.on_mousewheel)
                i += 1
                j += 1

            # BRK buttons
            temp_main_container = Frame(temp, background="#ccffcc", relief='flat')
            temp_main_container.grid(column=0, row=5, padx='10', pady='5')

            temp_container = Frame(temp_main_container, width=100, height=20,
                                   background="#ccffcc", relief='flat')
            temp_container.grid(column=0, row=0, padx=5, pady=2, sticky='w')

            temp_widget = Label(temp_container, text="Mode:", background='#ccffcc')
            # temp_widget.place(relx=0.02, rely=0.57, anchor='nw')
            temp_widget.grid(column=0, row=0, padx='0 5')
            self.main_elements['abb_mode_label'] = temp_widget

            self.main_parameters['abb_mode'] = StringVar(value='Remote')
            # temp_widget = Label(temp_container, textvariable=self.main_parameters['abb_mode'], background='#ccffcc')
            # # temp_widget.place(relx=0.12, rely=0.57, anchor='nw')
            # temp_widget.grid(column=1, row=0, padx='5')
            # self.main_elements['abb_mode'] = temp_widget

            temp_widget = Button(temp_container,
                                 textvariable=self.main_parameters['abb_mode'],
                                 command=self._toggle_abb,
                                 state=DISABLED, name='abb_toggle_btn')
            # temp_widget.place(relx=0.25, rely=0.57, anchor='nw')
            temp_widget.grid(column=1, row=0, padx='5')
            self.main_elements['abb_local_toggle'] = temp_widget

            self.main_parameters['abb_speed_torque'] = StringVar(value='Torque')
            temp_widget = Button(temp_container,
                                 textvariable=self.main_parameters['abb_speed_torque'],
                                 command=self._toggle_abb_speed_torque,
                                 state=DISABLED, name='abb_speed_torque_toggle_btn')
            # temp_widget.place(relx=0.25, rely=0.57, anchor='nw')
            temp_widget.grid(column=2, row=0, padx='5')
            self.main_elements['abb_speed_torque_toggle'] = temp_widget

            temp_widget = Label(temp_container, text="Direction:", background='#ccffcc')
            # temp_widget.place(relx=0.02, rely=0.57, anchor='nw')
            temp_widget.grid(column=3, row=0, padx='10 5')
            self.main_elements['abb_dir_label'] = temp_widget

            self.main_parameters['abb_dir'] = StringVar(value='FORWARD')
            temp_widget = ttk.Combobox(temp_container,
                                       textvariable=self.main_parameters['abb_dir'],
                                       name='main_brk_abb_dir', width=10,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.15, rely=0.05, anchor='sw')
            temp_widget.grid(column=4, row=0, padx='5 10')
            temp_widget['values'] = ['FORWARD', 'REVERSE', 'REQUEST']
            temp_widget.bind('<<ComboboxSelected>>', self._update_abb_direction)
            self.main_elements['abb_dir'] = temp_widget

            temp_widget = Label(temp_container, text="Limits:", background='#ccffcc')
            # temp_widget.place(relx=0.02, rely=0.57, anchor='nw')
            temp_widget.grid(column=6, row=0, padx='10 5')
            self.main_elements['abb_limit_label'] = temp_widget

            self.main_parameters['abb_limit'] = StringVar(value='REVERSE')
            temp_widget = ttk.Combobox(temp_container,
                                       textvariable=self.main_parameters['abb_limit'],
                                       name='main_brk_abb_limit', width=10,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.15, rely=0.05, anchor='sw')
            temp_widget.grid(column=7, row=0, padx='5 10')
            temp_widget['values'] = ['FORWARD', 'REVERSE', 'BOTH']
            temp_widget.bind('<<ComboboxSelected>>', self._update_abb_limits)
            self.main_elements['abb_limit'] = temp_widget

            buttonframe = Frame(temp_main_container, name='btn_frame',
                                background='#ccffcc')
            # buttonframe.place(relx=0.02, rely=0.64, anchor='nw')
            buttonframe.grid(column=0, row=1, padx=5, sticky='w')

            temp_widget = Button(buttonframe, text="BRK Ramp",
                                 command=self._brk_ramp, name="ctrl_ramp_btn")
            temp_widget.grid(column=0, row=1, padx='0 10')
            self.main_elements['main_brk_ramp_btn'] = temp_widget
            ToolTip(buttonframe.children['ctrl_ramp_btn'],
                    msg="Ramp brake torque to target % level within the time and total_steps indicated.\n"
                        "+ to Brake | - to Boost",
                    delay=TOOLTIP_DELAY)
            ttk.Label(buttonframe, text="To", background='#ccffcc').grid(column=1, row=1)
            Entry(buttonframe, textvariable=self.ramp_target,
                  width=4, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=2, row=1)
            ttk.Label(buttonframe, text="% in", background='#ccffcc').grid(column=3, row=1)
            Entry(buttonframe, textvariable=self.ramp_step,
                  width=4, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=4, row=1)
            ttk.Label(buttonframe, text="steps over", background='#ccffcc').grid(column=5, row=1)
            Entry(buttonframe, textvariable=self.ramp_duration,
                  width=4, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=6, row=1)
            ttk.Label(buttonframe, text="second(s)", background='#ccffcc').grid(column=7, row=1)

            temp_container = Frame(temp_main_container, background="#ccffcc", relief='flat')
            temp_container.grid(column=0, row=2, padx=5, pady=2, sticky='w')

            temp_inner = Frame(temp_container, background="#ccffcc", relief='flat')
            temp_inner.grid(column=0, row=0, padx='0 5')

            temp_widget = Button(temp_inner, text="Save to Flash",
                                     command=self._flash_brk, name='brk_save2flash_btn')
            # temp_widget.place(relx=0.02, rely=0.8, anchor='sw')
            temp_widget.grid(column=0, row=0, padx='0 5')
            ToolTip(temp_inner.children['brk_save2flash_btn'], delay=TOOLTIP_DELAY,
                    msg="Brake save to flash. Only works with ASI Controller")
            self.main_elements['brk_save2flash_btn'] = temp_widget

            temp_widget = Label(temp_inner, text='Parameter File', background='#ccffcc')
            # temp_widget.place(relx=0.25, rely=0.79, anchor='sw')
            temp_widget.grid(column=1, row=0, padx='10 5')
            temp_widget = Button(temp_inner, text="Load", command=self._file_load_brk,
                                     name='brk_load_param_btn', width=5)
            # temp_widget.place(relx=0.45, rely=0.8, anchor='sw')
            temp_widget.grid(column=2, row=0)
            ToolTip(temp_inner.children['brk_load_param_btn'], delay=TOOLTIP_DELAY,
                    msg="Brake load parameter file. Only works with ASI Controller")
            self.main_elements['brk_load_param_btn'] = temp_widget
            temp_widget = Button(temp_inner, text="Save", command=self._file_save_brk,
                                     name='brk_save_param_btn', width=5)
            # temp_widget.place(relx=0.55, rely=0.8, anchor='sw')
            temp_widget.grid(column=3, row=0)
            ToolTip(temp_inner.children['brk_save_param_btn'], delay=TOOLTIP_DELAY,
                    msg="Brake save parameters to file. Only works with ASI Controller")
            self.main_elements['brk_save_param_btn'] = temp_widget

            temp_widget = Label(temp_inner, text="Motor Discovery", background='#ccffcc')
            # temp_widget.place(relx=0.67, rely=0.79, anchor='sw')
            temp_widget.grid(column=4, row=0, padx='20 5')
            temp_widget = Button(temp_inner, text="1", command=lambda: self._gui_motor_discovery(2, 1),
                       name='brk_motor_discovery_btn_1', width=2)
            # temp_widget.place(relx=0.93, rely=0.8, anchor='se')
            temp_widget.grid(column=5, row=0)
            self.main_elements['brk_motor_discovery_btn_1'] = temp_widget
            temp_widget = Button(temp_inner, text="2", command=lambda: self._gui_motor_discovery(2, 2),
                       name='brk_motor_discovery_btn_2', width=2)
            # temp_widget.place(relx=0.99, rely=0.8, anchor='se')
            temp_widget.grid(column=6, row=0)
            self.main_elements['brk_motor_discovery_btn_2'] = temp_widget

            temp_container = Frame(temp_main_container, background="#ccffcc", relief='flat')
            temp_container.grid(column=0, row=3, padx=5, pady=2, sticky='w')

            temp_inner = Frame(temp_container, background="#ccffcc", relief='flat')
            temp_inner.grid(column=0, row=0, padx='0 5')

            temp_widget = Button(temp_inner, text="START", width=12,
                                 background='green', activebackground='green',
                                 foreground='white', activeforeground='white',
                                 command=self._brk_start, name='brk_start_btn')
            # temp_widget.place(relx=0.02, rely=0.90, anchor='sw')
            temp_widget.grid(column=0, row=0, padx='0 10', sticky='we')
            self.main_elements['brk_start_btn'] = temp_widget
            temp_widget = ToolTip(temp_inner.children['brk_start_btn'], delay=TOOLTIP_DELAY,
                                  msg="ASI Controller: Starts in Torque mode with 0% torque command. "
                                      "Determines brake torque direction\nABB: Starts Brake")
            self.main_elements['brk_start_tt'] = temp_widget

            temp_widget = Button(temp_inner, text="STOP", width=12,
                                 background='red', activebackground='red',
                                 foreground='white', activeforeground='white',
                                 command=self._brk_stop, name='brk_stop_btn')
            # temp_widget.place(relx=0.02, rely=0.98, anchor='sw')
            temp_widget.grid(column=0, row=1, padx='0 10', sticky='we')
            self.main_elements['brk_stop_btn'] = temp_widget
            temp_widget = ToolTip(temp_inner.children['brk_stop_btn'], delay=TOOLTIP_DELAY,
                                  msg="ASI Controller: write 0 to Remote state command\nABB: Stops Brake")
            self.main_elements['brk_stop_tt'] = temp_widget

            # Brake torque ASI spinbox
            self.main_parameters['brk_torque'] = DoubleVar(value=0.0)
            temp_widget = ASISpinBox(temp_inner, self.main_parameters['brk_torque'], width=40,
                                     background='#ccffcc', foreground='black')
            # temp_widget.container.place(relx=0.27, rely=0.98, anchor='sw')
            temp_widget.container.grid(column=1, row=0, rowspan=2, padx='10')
            self.main_elements['brk_torque'] = temp_widget

            # Reset brake direction button
            temp_widget = Button(temp_inner, text='Reset\nBRK Dir',
                                     command=self._set_brk_dir, name='set_dir_btn', width=7)
            # temp_widget.place(relx=0.88, rely=0.965, anchor='se')
            temp_widget.grid(column=2, row=0, rowspan=2, padx='10')
            self.main_elements['set_dir_btn'] = temp_widget
            temp_widget = ToolTip(temp_inner.children['set_dir_btn'],
                                  msg='Reset BRK Direction\nUse when BRK spinning',
                                  delay=TOOLTIP_DELAY)
            self.main_elements['set_dir_tt'] = temp_widget

            # temp = Button(temp, text='+', command=lambda: self.notebook.select(2),
            #                   name='more_control_btn', width=1)
            # temp.place(relx=0.99, rely=0.99, anchor='se')

            temp_widget = ASIIcons(temp, size=25, item='list', background='#ccffcc')
            temp_widget.canvas.bind("<Button-1>", lambda x: self.notebook.select(2))
            temp_widget.canvas.place(relx=.99, rely=.99, anchor='se')

            self.update_main()

        def make_yoko_section():
            """
            GUI front end
            Building YOKOGAWA section on home screen
            """
            container = ttk.Frame(self.main_elements['column_2'], relief='flat')
            container.grid(column=0, row=3, sticky='ns')
            container.columnconfigure(0, weight=1)

            label = Label(container, text='YOKOGAWA', font=('Comic Sans', 15), background='#ffffcc')
            temp = ttk.LabelFrame(container, width=MIN_WIDTH * 0.3, height=MIN_HEIGHT * 0.5,
                                  labelanchor='n', labelwidget=label, style='yoko.TLabelframe')
            temp.grid(column=0, row=0, pady=5)
            # temp.place(relx=0.5, rely=0.4, anchor='n')

            temp_widget = ASIStatusIndicator(temp, 'YOKO')
            temp_widget.canvas.grid(column=0, row=0, sticky='e', padx=5)
            # temp_widget.canvas.place(relx=0.97, rely=0.01, anchor='center')
            self.main_elements['yoko_indicator'] = temp_widget

            # Yoko parameters
            temp_container = Frame(temp, name="brk_motor_params", background='#ffffcc', width=MIN_WIDTH * 0.28)
            self.main_elements['yoko_params'] = temp_container
            temp_container.grid(column=0, row=1, padx=5, pady=5)
            temp_container.columnconfigure(0, weight=1)
            temp_container.rowconfigure(0, weight=1)
            # temp_container.place(relx=0.02, rely=0.05, anchor='nw')
            s_frame = ScrollableFrame(temp_container,
                                      width=MIN_WIDTH * 0.28, height=MIN_HEIGHT * 0.4,
                                      background='#ffffcc')
            s_frame.grid(column=0, row=0)
            # s_frame.pack(fill='both')
            self.main_elements['yoko_param_frame'] = s_frame.scrollable_frame
            for i in (0, 1, 2, 3, 4, 5):
                self.main_elements['yoko_param_frame'].columnconfigure(i, weight=1)
                
            params = pd.read_csv(YOKO_PARAMETER_FILE)
            self.yoko_params = params

            for i in range(len(params)):
                Label(self.main_elements['yoko_param_frame'],
                      text=params.loc[i]['Name'], width=22,
                      name=f"main_yoko_param_{params.loc[i]['Shortened Name']}_{i}",
                      font=f'{OPTION_FONT_NAME} {YOKO_FONT_SIZE}',
                      background="#ffffcc", pady=2, justify='right', anchor='e').grid(
                    column=(i % 2) * 3, row=int(1 + i / 2), sticky='e')
                self.main_elements['yoko_param_frame'].children[
                    f"main_yoko_param_{params.loc[i]['Shortened Name']}_{i}"].bind(
                    '<MouseWheel>',
                    self.main_elements['yoko_param_frame'].master.master.on_mousewheel)
                self.main_parameters[f'yoko_param_{params.loc[i]["Shortened Name"]}_{i}'] = StringVar(value='0')
                Label(self.main_elements['yoko_param_frame'],
                      textvariable=self.main_parameters[f'yoko_param_{params.loc[i]["Shortened Name"]}_{i}'],
                      width=6, name=f"main_yoko_param_{params.loc[i]['Shortened Name']}_{i}_value",
                      font=f'{OPTION_FONT_NAME} {YOKO_FONT_SIZE}',
                      background="#ffffcc", pady=2).grid(
                    column=(i % 2) * 3 + 1, row=int(1 + i / 2), sticky='we')
                self.main_elements['yoko_param_frame'].children[
                    f"main_yoko_param_{params.loc[i]['Shortened Name']}_{i}_value"].bind(
                    '<MouseWheel>',
                    self.main_elements['yoko_param_frame'].master.master.on_mousewheel)
                Label(self.main_elements['yoko_param_frame'], text=params.loc[i]["Units"], width=3,
                      name=f"main_yoko_param_{params.loc[i]['Shortened Name']}_{i}_unit",
                      font=f'{OPTION_FONT_NAME} {YOKO_FONT_SIZE}',
                      background="#ffffcc", pady=2).grid(
                    column=(i % 2) * 3 + 2, row=int(1 + i / 2), sticky='e')
                self.main_elements['yoko_param_frame'].children[
                    f"main_yoko_param_{params.loc[i]['Shortened Name']}_{i}_unit"].bind(
                    '<MouseWheel>',
                    self.main_elements[
                        'yoko_param_frame'].master.master.on_mousewheel)

        def make_log_section():
            """
            GUI front end
            Building logging section on home screen
            """
            container = ttk.Frame(self.main_elements['column_1'], relief='flat')
            container.grid(column=0, row=1, sticky='ns', )

            label = Label(container, text='Logging', font=('Comic Sans', 15), background='white')
            temp = ttk.LabelFrame(container, width=MIN_WIDTH * 0.3, height=MIN_HEIGHT * 0.24,
                                  labelanchor='n', labelwidget=label)
            temp.grid(column=0, row=0, sticky='news')
            # temp.place(relx=0.35, rely=0.5, anchor='ne')

            # logging directory
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=0, sticky='ws', padx='10', pady=2)

            temp_widget = ttk.Label(temp_container, text="Logging to: ")
            # temp_widget.place(relx=0.02, rely=0.02, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')
            temp_widget = Entry(temp_container, textvariable=self.result_destination,
                                name='result_entry', width=25,
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.2, rely=0.02, anchor='nw')
            temp_widget.grid(column=1, row=0)
            ToolTip(temp_container.children['result_entry'], delay=TOOLTIP_DELAY,
                    msg="Please don't leave this field empty when starting a test script")
            temp_widget = ttk.Label(temp_container, text="/")
            # temp_widget.place(relx=0.6, rely=0.02, anchor='nw')
            temp_widget.grid(column=2, row=0)
            self.main_parameters['result_dir'] = StringVar(value='placeholder')
            self.main_parameters['previous_result_dir'] = StringVar(value='')
            temp_widget = ttk.Label(temp_container, textvariable=self.main_parameters['result_dir'],
                                    name='result_dir', width=20)
            # temp_widget.place(relx=0.63, rely=0.02, anchor='nw')
            temp_widget.grid(column=3, row=0)
            temp_widget = Button(temp_container, text="...", command=self._result_destination,
                                 name='test_browse_btn', width=3)
            # temp_widget.place(relx=0.98, rely=0.02, anchor='ne')
            temp_widget.grid(column=4, row=0, sticky='e')

            self.main_parameters['log_note_var'] = StringVar(value='')
            temp_widget = ttk.Label(temp_container, text='Custom Note: ')
            # temp_widget.place(relx=0.02, rely=0.2)
            temp_widget.grid(column=0, row=1, sticky='w')
            temp_widget = Entry(temp_container, textvariable=self.main_parameters['log_note_var'],
                                name='note_entry', width=40,
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.2, rely=0.2, anchor='nw')
            temp_widget.grid(column=1, row=1, columnspan=4, sticky='news')
            ToolTip(temp_container.children['note_entry'], delay=TOOLTIP_DELAY,
                    msg="Custom notes for logging folder")
            self.main_elements['note_entry'] = temp_widget

            # logging control
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=1, sticky='ws', padx='10', pady=2)

            temp_widget = Button(temp_container, text="Start", command=self._start_logging,
                                 state=DISABLED, name='start_log_btn', width=12,
                                 bg='green', activebackground='green',
                                 fg='white', activeforeground='white')
            # temp_widget.place(relx=0.02, rely=0.4, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')
            self.main_elements['start_logging'] = temp_widget
            ToolTip(temp_container.children['start_log_btn'], delay=TOOLTIP_DELAY,
                    msg="Starts logging at chosen interval. "
                        "Allows extra logging and live graphing. Default to C:/DynoResults")

            temp_widget = Button(temp_container, text="Stop", command=self._stop_logging,
                                 state=DISABLED, name="stop_log_btn", width=12,
                                 bg='red', activebackground='red',
                                 fg='white', activeforeground='white')
            # temp_widget.place(relx=0.25, rely=0.4, anchor='nw')
            temp_widget.grid(column=1, row=0, sticky='w', padx=5)
            self.main_elements['stop_logging'] = temp_widget
            ToolTip(temp_container.children['stop_log_btn'], delay=TOOLTIP_DELAY,
                    msg="Stops logging. Disabling extra logging and live graphing")

            temp_widget = ttk.Label(temp_container, text="Interval")
            # temp_widget.place(relx=0.55, rely=0.4, anchor='nw')
            temp_widget.grid(column=2, row=0, sticky='e', padx='40 0')
            temp_widget = Entry(temp_container, textvariable=self.log_interval,
                                width=5, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.65, rely=0.4, anchor='nw')
            temp_widget.grid(column=3, row=0, sticky='we')
            temp_widget = ttk.Label(temp_container, text="s")
            # temp_widget.place(relx=0.75, rely=0.4, anchor='nw')
            temp_widget.grid(column=4, row=0, sticky='w', padx='0 5')

            temp_widget = Button(temp_container, text="Update", command=self._update_log_interval,
                                     state=DISABLED, name='update_log_btn')
            # temp_widget.place(relx=0.98, rely=0.4, anchor='ne')
            temp_widget.grid(column=5, row=0, sticky='e')
            self.main_elements['update_log'] = temp_widget
            ToolTip(temp_container.children['update_log_btn'], delay=TOOLTIP_DELAY,
                    msg="Updates logging interval. ")

            temp_widget = ASIIcons(temp_container, size=25, item='folder')
            temp_widget.canvas.bind("<Button-1>", self._open_result_folder)
            # temp_widget = Button(temp_container, text="Open Result Folder",
            #                          command=self._open_result_folder,
            #                          state=DISABLED, name='open_results')
            # temp_widget.place(relx=0.98, rely=0.8, anchor='ne')
            temp_widget.canvas.grid(column=6, row=0, sticky='e', padx='20 5')
            self.main_elements['open_results'] = temp_widget

            # additional logging
            temp_main_container = LabelFrame(temp, name="logging_additional",
                                             background='white', text='Additional Logging')
            self.main_elements['additional_logging_frame'] = temp_main_container
            temp_main_container.grid(column=0, row=2, padx='10', sticky='news', pady='0 5')

            temp_container = Frame(temp_main_container, background="white", relief='flat')
            temp_container.grid(column=0, row=2, sticky='ws', padx='5', pady=2)

            # temp_widget = ttk.Label(temp_container, text="Additional Logging")
            # temp_widget.place(relx=0.02, rely=0.6, anchor='nw')
            # temp_widget.grid(column=0, row=0, sticky='w')
            temp_widget = Button(temp_container, text="Create", command=self._extra_logging,
                                     state=DISABLED, name="extra_log_btn", width=8)
            # temp_widget.place(relx=0.3, rely=0.6, anchor='nw')
            temp_widget.grid(column=0, row=0, padx=10)
            self.main_elements['create_extra_log'] = temp_widget
            ToolTip(temp_container.children['extra_log_btn'], delay=TOOLTIP_DELAY,
                    msg="Starts a new CSV file for separate logging. Only enabled when DynoModule is logging. "
                        "Can create and write to multiple different files")

            temp_widget = Button(temp_container, text="Log", command=self._extra_line,
                                     state=DISABLED, name='extra_line_btn', width=8)
            # temp_widget.place(relx=0.98, rely=0.6, anchor='ne')
            temp_widget.grid(column=1, row=0, sticky='e', padx='10 0')
            self.main_elements['extra_log'] = temp_widget
            ToolTip(temp_container.children['extra_line_btn'], delay=TOOLTIP_DELAY,
                    msg="Add a new row of data to the extra logging file indicated above. "
                        "Make sure file name is correct!")

            temp_widget = ttk.Checkbutton(temp_container, text="Same folder", onvalue=True,
                                          variable=self.same_folder, name='same_folder_btn')
            # temp_widget.place(relx=0.44, rely=0.61, anchor='nw')
            temp_widget.grid(column=2, row=0, padx='40 10')
            ToolTip(temp_container.children['same_folder_btn'], delay=TOOLTIP_DELAY,
                    msg="Save the extra logging files under the same folder as general logging. "
                        "Uncheck to save 1 level above")

            temp_widget = ttk.Checkbutton(temp_container, text="Level above", onvalue=False,
                                          variable=self.same_folder, name='level_above_btn')
            # temp_widget.place(relx=0.65, rely=0.61, anchor='nw')
            temp_widget.grid(column=3, row=0, padx=10)

            # additional logging lower
            temp_container = Frame(temp_main_container, background="white", relief='flat')
            temp_container.grid(column=0, row=3, sticky='ws', padx='5', pady='2 5')
            temp_container.columnconfigure(1, weight=1)

            temp_widget = ttk.Label(temp_container, text="File name")
            # temp_widget.place(relx=0.02, rely=0.8, anchor='nw')
            temp_widget.grid(column=0, row=1, sticky='w')
            temp_widget = Entry(temp_container, textvariable=self.extra_file,
                                width=40, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.25, rely=0.8, anchor='nw')
            temp_widget.grid(column=1, row=1, padx=10)

        def make_test_section():
            """
            GUI front end
            Building test section on home screen
            """
            container = ttk.Frame(self.main_elements['column_1'], relief='flat')
            container.grid(column=0, row=2)

            label = Label(container, text='Test', font=('Comic Sans', 15), background='white')
            temp = ttk.LabelFrame(container, width=MIN_WIDTH * 0.3, height=MIN_HEIGHT * 0.3,
                                  labelanchor='n', labelwidget=label)
            temp.grid(column=0, row=0, sticky='news')
            # temp.place(relx=0.35, rely=0.71, anchor='ne')

            # test selector
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=0, sticky='ws', padx='10', pady=5)

            temp_widget = ttk.Label(temp_container, text="Test:")
            # temp_widget.place(relx=0.02, rely=0.02, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')

            temp_widget = ttk.Combobox(temp_container, textvariable=self.test, width=25,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.15, rely=0.02, anchor='nw')
            temp_widget.grid(column=1, row=0, sticky='w', padx=10)
            temp_widget['values'] = TEST_SCRIPTS
            temp_widget.bind('<<ComboboxSelected>>', self.test_inputs)
            ToolTip(temp_widget, delay=TOOLTIP_DELAY, msg="Which test are we running?")
            temp_widget = ttk.Checkbutton(temp_container, text="with barcode", variable=self.with_barcode,
                                          command=self._barcode2sn, name='barcode_check')
            # temp_widget.place(relx=0.5, rely=0.02, anchor='nw')
            temp_widget.grid(column=2, row=0, sticky='w', padx=10)

            temp_widget = Button(temp_container, text="RUN", command=self._start_test_thread,
                                 name='test_run_btn', fg='white', activeforeground='white',
                                 bg='green', activebackground='green', width=10)
            # temp_widget.place(relx=0.98, rely=0, anchor='ne')
            temp_widget.grid(column=3, row=0, sticky='e', padx='10 0')

            # preset selector
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=1, sticky='ws', padx='10', pady=5)

            temp_widget = ttk.Combobox(temp_container, textvariable=self.config_value,
                                       name='config_combo', width=57,
                                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.02, rely=0.18, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')
            temp_widget['values'] = self.configs.index.to_list()
            temp_widget.bind('<<ComboboxSelected>>', self._populate_config_list)
            self.main_elements['main_test_preset'] = temp_widget

            temp_widget = ToolTip(temp_widget, delay=TOOLTIP_DELAY,
                                  msg=self.config_value.get())
            self.main_elements['main_test_preset_tt'] = temp_widget

            # temp_widget = ttk.Button(temp, text='Toggle List', name='toggle_config_btn', command=self._popup_config_list)
            temp_widget = ASIIcons(temp_container, size=25, item='popout')
            temp_widget.canvas.bind("<Button-1>", self._popup_config_list)
            # temp_widget.canvas.place(relx=0.98, rely=0.18, anchor='ne')
            temp_widget.canvas.grid(column=1, row=0, sticky='w')

            # temp_widget = Button(temp, text="STOP", command=self.sigint_handler, name='stop_btn', bg='red', fg='white',
            #                      activebackground='red')
            # temp_widget.place(relx=0.85, rely=0, anchor='nw')

            # motor type/notes
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=2, sticky='ws', padx='10', pady=5)

            temp_widget = ttk.Label(temp_container, textvariable=self.test_note)
            # temp_widget.place(relx=0.02, rely=0.32, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')
            temp_widget = Entry(temp_container, textvariable=self.motor_type,
                                name='type_entry', font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.2, rely=0.32, anchor='nw')
            temp_widget.grid(column=1, row=0, sticky='w', padx=10)
            ToolTip(temp_container.children['type_entry'], msg="Any text allowed")

            # serial numbers
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=3, sticky='ws', padx='10', pady=5)

            temp_widget = ttk.Label(temp_container, text="S/N")
            # temp_widget.place(relx=0.02, rely=0.47, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')
            temp_widget = Entry(temp_container, textvariable=self.serial_num, width=15, name='sn_entry',
                                state=DISABLED, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.15, rely=0.47, anchor='nw')
            temp_widget.grid(column=1, row=0, sticky='w', padx=10)
            ToolTip(temp_container.children['sn_entry'], msg="Default to 0000-00000 (Keep in 'number dash number' format)")
            self.main_elements['main_sn_entry'] = temp_widget

            temp_widget = ttk.Label(temp_container, text="S/N 2", name='sn_label_2')
            self.main_elements['main_sn_2_label'] = temp_widget
            temp_widget = Entry(temp_container, textvariable=self.serial_num_1, width=15, name='sn_entry_2',
                                state=DISABLED, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            ToolTip(temp_container.children['sn_entry_2'], msg="Default to 0000-00000 (Keep in 'number dash number' format)")
            self.main_elements['main_sn_2_entry'] = temp_widget

            # barcodes
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=4, sticky='ws', padx='10', pady=5)

            temp_widget = ttk.Label(temp_container, text="Barcode: ")
            # temp_widget.place(relx=0.02, rely=0.62, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')
            temp_widget = Entry(temp_container, textvariable=self.barcode_var, name='barcode_entry',
                                width=48, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.18, rely=0.62, anchor='nw')
            temp_widget.grid(column=1, row=0, sticky='w')
            temp_container.children['barcode_entry'].bind('<FocusIn>', self._select_all)
            self.main_elements['main_barcode_entry'] = temp_widget

            temp_widget = ttk.Label(temp_container, text="Barcode B: ", name='barcode_2_label')
            self.main_elements['main_barcode_2_label'] = temp_widget
            temp_widget = Entry(temp_container, textvariable=self.barcode_2_var, name='barcode_2_entry',
                                width=48, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            temp_container.children['barcode_2_entry'].bind('<FocusIn>', self._select_all_2)
            self.main_elements['main_barcode_2_entry'] = temp_widget

            # zoom in
            temp_container = Frame(temp, background="white", relief='flat')
            temp_container.grid(column=0, row=5, sticky='ws', padx='10', pady=5)
            self.main_elements['main_test_zoom_frame'] = temp_container

            temp_widget = ttk.Checkbutton(temp_container, text="Zoom in mode",
                                          variable=self.rundown_zoom, name='zoom_check')
            # temp_widget.place(relx=0.02, rely=0.77, anchor='nw')
            temp_widget.grid(column=0, row=0, sticky='w')
            self.main_elements['main_test_zoom'] = temp_widget
            temp_widget = Entry(temp_container, name='zoom_lo_entry', width=10,
                                justify='right', font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.3, rely=0.77, anchor='nw')
            temp_widget.grid(column=1, row=0, sticky='w', padx='50 0')
            self.main_elements['main_test_zoom_lo'] = temp_widget
            temp_widget = ttk.Label(temp_container, text="Nm -", name='zoom_label', justify='center')
            # temp_widget.place(relx=0.45, rely=0.77, anchor='nw')
            temp_widget.grid(column=2, row=0, sticky='w')
            self.main_elements['main_test_zoom_lo_unit'] = temp_widget
            temp_widget = Entry(temp_container, name='zoom_hi_entry', width=10,
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            # temp_widget.place(relx=0.55, rely=0.77, anchor='nw')
            temp_widget.grid(column=3, row=0, sticky='w')
            self.main_elements['main_test_zoom_hi'] = temp_widget
            temp_widget = ttk.Label(temp_container, text="Nm", name='zoom_label1')
            # temp_widget.place(relx=0.7, rely=0.77, anchor='nw')
            temp_widget.grid(column=4, row=0, sticky='w')
            self.main_elements['main_test_zoom_hi_unit'] = temp_widget

            # efficiency map
            temp_container = Frame(temp, background="white", relief='flat')
            # temp_container.grid(column=0, row=6, sticky='ws', padx='10', pady=2)
            self.main_elements['main_test_efficiency_map'] = temp_container

            self.main_parameters['effi_target'] = BooleanVar(value=False)
            temp_widget = ttk.Label(temp_container, text="Efficiency Map Target:",
                                          name='effi_target')
            temp_widget.grid(column=0, row=0, sticky='w')
            self.main_elements['effi_target_label'] = temp_widget
            temp_widget = ttk.Checkbutton(temp_container, name='effi_motor_check', onvalue=True, text='Motor',
                                          variable=self.main_parameters['effi_target'])
            temp_widget.grid(column=1, row=0, sticky='w')
            self.main_elements['effi_motor_check'] = temp_widget
            temp_widget = ttk.Checkbutton(temp_container, name='effi_controller_check', onvalue=False, text='Controller',
                                          variable=self.main_parameters['effi_target'])
            temp_widget.grid(column=2, row=0, sticky='w')
            self.main_elements['effi_controller_check'] = temp_widget

            # temp = ttk.Button(temp, text='+',
            #                   command=lambda: self.notebook.select(3),
            #                   name='more_test_btn', width=3)
            # temp.place(relx=0.98, rely=0.5, anchor='se')
            temp_widget = ASIIcons(temp, size=25, item='list')
            temp_widget.canvas.bind("<Button-1>", lambda: self.notebook.select(3))
            temp_widget.canvas.place(relx=0.99, rely=0.99, anchor='se')

        def make_control_section():
            """
            GUI front end
            Building controller section on home screen
            """
            container = ttk.Frame(self.main_elements['column_2'], relief='flat')
            container.grid(column=0, row=4, sticky='ns')
            # container.columnconfigure(0, weight=1)

            label = Label(container, text='Controller', font=('Comic Sans', 15), background='white')
            temp = ttk.LabelFrame(container, labelanchor='n', labelwidget=label)
            temp.grid(column=0, row=0, sticky='news')
            temp.columnconfigure((0, 1, 2, 3, 4), weight=1)
            # temp.place(relx=0.5, rely=0.75, anchor='n')

            temp_widget = Button(temp, text="DYNO START", command=self._dyno_start,
                                 fg='white', relief='groove', width=12,
                                 name='dyno_start_btn', bg='green',
                                 activebackground='green', activeforeground='white')
            temp_widget.grid(column=0, row=0, pady=5, padx=5)
            # temp_widget.place(relx=0.02, rely=0.02, anchor='nw')
            self.main_elements['dyno_start_btn'] = temp_widget
            temp_widget = ToolTip(temp.children['dyno_start_btn'], delay=TOOLTIP_DELAY,
                                  msg="Dyno Start Sequence: start logging -> wait 2s -> write 2 to Remote state command")
            self.main_elements['dyno_start_tt'] = temp_widget

            # controller limits
            self.speed_limit_frame = ttk.LabelFrame(temp, text="Safety Limits", labelanchor='n', padding=5)
            self.speed_limit_frame.grid(column=2, row=0, rowspan=3, padx=20, pady=5)
            # self.speed_limit_frame.place(relx=0.5, rely=0, anchor='nw')
            Entry(self.speed_limit_frame, textvariable=self.speed_limit_upper,
                  width=8, name="upper_limit", foreground='red',
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=0, row=2, sticky='news', columnspan=2)
            ToolTip(self.speed_limit_frame.children['upper_limit'], msg='Upper speed limit', delay=TOOLTIP_DELAY)
            ttk.Label(self.speed_limit_frame, text='RPM').grid(column=2, row=2, sticky='news', pady="2px")

            Entry(self.speed_limit_frame, textvariable=self.speed_limit_lower,
                  width=8, name="lower_limit", foreground='red',
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=0, row=3, sticky='news', pady="2px", columnspan=2)
            ToolTip(self.speed_limit_frame.children['lower_limit'], msg='Lower speed limit', delay=TOOLTIP_DELAY)
            ttk.Label(self.speed_limit_frame, text='RPM').grid(column=2, row=3, sticky='news', pady="2px")

            Entry(self.speed_limit_frame, textvariable=self.torque_limit,
                  width=5, name="torque_limit", foreground='red',
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=0, row=4, sticky='news', pady="2px")
            ToolTip(self.speed_limit_frame.children['torque_limit'], msg='Torque limit', delay=TOOLTIP_DELAY)
            ttk.Label(self.speed_limit_frame, text='Nm').grid(column=1, row=4, sticky='news', pady="2px")

            # same as control frame
            buttonframe = ttk.Frame(temp, name='btn_frame', width=MIN_WIDTH * 0.15, height=MIN_HEIGHT * 0.1)
            buttonframe.grid(column=0, row=4, columnspan=3, sticky='w', pady=5, padx=5)
            # buttonframe.place(relx=0.02, rely=0.98, anchor='sw')
            # buttonframe.columnconfigure(0, weight=1)
            for i in (0, 1):
                buttonframe.rowconfigure(i, weight=1)

            def build_buttonframe():
                # Button(buttonframe, text="BRK Ramp", command=self._brk_ramp, name="ctrl_ramp_btn",
                #        relief='groove', bg=DEFAULT_GREY).grid(column=0, row=1, sticky='news', padx='0 10')
                # ToolTip(buttonframe.children['ctrl_ramp_btn'],
                #         msg="Ramp brake torque to target % level within the time and total_steps indicated.\n+ to Brake | - to Boost",
                #         delay=TOOLTIP_DELAY)
                # ttk.Label(buttonframe, text="To").grid(column=1, row=1)
                # Entry(buttonframe, textvariable=self.ramp_target, width=4).grid(column=2, row=1)
                # ttk.Label(buttonframe, text="% in").grid(column=3, row=1)
                # Entry(buttonframe, textvariable=self.ramp_step, width=4).grid(column=4, row=1)
                # ttk.Label(buttonframe, text="total_steps for").grid(column=5, row=1)
                # Entry(buttonframe, textvariable=self.ramp_duration, width=4).grid(column=6, row=1)
                # ttk.Label(buttonframe, text="second(s)").grid(column=7, row=1)

                Button(buttonframe, text="DYNO Stop Timer", command=self._run_for,
                       name="ctrl_timer_btn").grid(column=0, row=0, sticky='news', padx='0 10')
                ToolTip(buttonframe.children['ctrl_timer_btn'], delay=TOOLTIP_DELAY,
                        msg="Stops DynoModule (both driver and brake) at the end of the countdown.\n"
                            "Toggle to start/stop.\nMax 999:59:59")
                Entry(buttonframe, textvariable=self.run_duration_h, width=4,
                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                    column=1, row=0)
                ttk.Label(buttonframe, text=":").grid(column=2, row=0)
                Entry(buttonframe, textvariable=self.run_duration_m, width=4,
                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                    column=3, row=0)
                ttk.Label(buttonframe, text=":").grid(column=4, row=0)
                Entry(buttonframe, textvariable=self.run_duration_s, width=4,
                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                    column=5, row=0)

            build_buttonframe()

            temp_widget = ASIStopButton(temp, name='dyno_stop_btn', size=130)
            temp_widget.canvas.grid(column=4, row=0, rowspan=5, padx=5)
            # temp_widget.canvas.place(relx=0.98, rely=0.02, anchor='ne')
            temp_widget.canvas.bind('<Button-1>', self._e_stop)
            self.main_elements['dyno_stop_btn'] = temp_widget
            temp_widget = ToolTip(temp.children['dyno_stop_btn'], delay=TOOLTIP_DELAY,
                    msg="Dyno Stop Sequence! Does not stop logging")
            self.main_elements['dyno_stop_tt'] = temp_widget

            temp_widget = Button(temp, text="Fault Clear", command=self._fault_clear,
                                 name='ctrl_fault_clear_btn')
            temp_widget.grid(column=0, row=1, sticky='news', pady=5, padx=5)
            # temp_widget.place(relx=0.02, rely=0.22, anchor='nw')
            self.main_elements['fault_clear_btn'] = temp_widget
            temp_widget = ToolTip(temp.children['ctrl_fault_clear_btn'], msg="Clears fault for both driver and brake",
                                  delay=TOOLTIP_DELAY)
            self.main_elements['fault_clear_tt'] = temp_widget

            temp_widget = Button(temp, text="Check Faults",
                                     command=self._check_fault, name='ctrl_check_faults_btn')
            temp_widget.grid(column=0, row=2, sticky='news', pady=5, padx=5)
            # temp_widget.place(relx=0.02, rely=0.4, anchor='nw')
            self.main_elements['check_faults_btn'] = temp_widget
            temp_widget = ToolTip(temp.children['ctrl_check_faults_btn'],
                                  msg="Checks fault for both driver and brake",
                                  delay=TOOLTIP_DELAY)
            self.main_elements['check_faults_tt'] = temp_widget

            temp_widget = Button(temp, text="Read", command=self._update_main,
                                 name='main_read', width=12)
            temp_widget.grid(column=1, row=0, sticky='news', pady=5, padx=5)
            # temp_widget.place(relx=0.25, rely=0.02, anchor='nw')
            self.main_elements['main_read_btn'] = temp_widget
            temp_widget = ToolTip(temp.children['main_read'],
                                  msg="read parameters from DUT & BRK",
                                  delay=TOOLTIP_DELAY)
            self.main_elements['main_read_btn_tt'] = temp_widget

            temp_widget = Button(temp, text="Write", command=self._upload_main,
                                 name='main_write', width=12)
            temp_widget.grid(column=1, row=1, sticky='news', pady=5, padx=5)
            # temp_widget.place(relx=0.25, rely=0.22, anchor='nw')
            self.main_elements['main_write_btn'] = temp_widget
            temp_widget = ToolTip(temp.children['main_write'],
                                  msg="read parameters from DUT & BRK",
                                  delay=TOOLTIP_DELAY)
            self.main_elements['main_write_btn_tt'] = temp_widget

        def make_live_section():
            """
            GUI front end
            Building live status section on home screen
            """
            container = ttk.Frame(self.main_elements['column_3'], relief='flat')
            container.grid(column=0, row=1, sticky='n')
            container.columnconfigure(0, weight=1)
            container.rowconfigure(0, weight=1)

            label = Label(container, text='Status', font=('Comic Sans', 15), background='white')
            temp = ttk.LabelFrame(container, width=MIN_WIDTH * 0.3, height=MIN_HEIGHT * 0.5,
                                  labelanchor='n', labelwidget=label)
            temp.grid(column=0, row=0, sticky='news')
            temp.columnconfigure(0, weight=1)
            temp.rowconfigure(0, weight=1)
            # temp.place(relx=0.65, rely=0.5, anchor='nw')

            # status notebook
            self.status_notebook = ttk.Notebook(temp,
                                                width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4),
                                                style='live.TNotebook')
            self.status_notebook.grid(column=0, row=0, sticky='news', padx=5)
            # self.status_notebook.columnconfigure(0, weight=1)
            # self.status_notebook.rowconfigure((0, 1, 2), weight=1)
            # self.status_notebook.place(relx=0.01, rely=0.01, anchor='nw')

            tabs = Frame(temp, relief='flat',
                         width=MIN_WIDTH * 0.1, height=MIN_HEIGHT * 0.05,
                         background="white")
            tabs.grid(column=0, row=3, sticky='s', pady=5)
            # tabs.place(relx=0.02, rely=0.88, anchor='nw')

            # graph
            temp_widget = ASIIcons(tabs, size=30, item='graph',
                                   background="white", foreground='#5DA01D')
            temp_widget.canvas.grid(column=0, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.1, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._live_tab_change(0))
            self.main_elements['live_graph_tab'] = temp_widget

            # list parameters
            # temp_widget = ASIIcons(tabs, size=30, item='list',
            #                        background="white", foreground='black')
            # temp_widget.canvas.grid(column=1, row=0, padx=5)
            # # temp_widget.canvas.place(relx=0.3, rely=0.5, anchor='w')
            # temp_widget.canvas.bind('<Button-1>', lambda x: self._live_tab_change(1))
            # self.main_elements['live_list_tab'] = temp_widget

            # warnings and faults
            temp_widget = ASIIcons(tabs, size=30, item='faults',
                                   background="white", foreground='black')
            temp_widget.canvas.grid(column=2, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.5, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._live_tab_change(1))
            self.main_elements['live_faults_tab'] = temp_widget

            # test parameters
            temp_widget = ASIIcons(tabs, size=30, item='test',
                                   background="white", foreground='black')
            temp_widget.canvas.grid(column=3, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.7, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._live_tab_change(2))
            self.main_elements['live_test_tab'] = temp_widget

            # graph notebook
            temp_widget = ttk.Frame(self.status_notebook)
            temp_widget.columnconfigure(0, weight=1)
            temp_widget.rowconfigure(0, weight=1)
            self.graph_notebook = ttk.Notebook(temp_widget,
                                               width=int(MIN_WIDTH * 0.28), height=int(MIN_HEIGHT * 0.3),
                                               style='live.TNotebook')
            self.graph_notebook.grid(column=0, row=0, sticky='news')
            self.graph_notebook.columnconfigure(0, weight=1)
            # self.graph_notebook.rowconfigure(0, weight=1)
            # self.graph_notebook.place(relx=0.01, rely=0.01, anchor='nw')
            self.status_notebook.add(temp_widget)

            # graph notebook tabs
            tabs = Frame(temp_widget, relief='flat',
                         width=MIN_WIDTH * 0.2, height=MIN_HEIGHT * 0.05,
                         background="white")
            tabs.grid(column=0, row=2, sticky='s', pady=5)

            # tabs.place(relx=0.02, rely=0.85, anchor='nw')

            # basic graph RPM & Torque
            temp_widget = ASIIcons(tabs, size=25, item='RPMTorque',
                                   background="white", foreground='#5DA01D')
            temp_widget.canvas.grid(column=0, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.01, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._graph_tab_change(0))
            self.main_elements['graph_basic_tab'] = temp_widget

            # temperature graph
            temp_widget = ASIIcons(tabs, size=25, item='temp',
                                   background="white", foreground='black')
            temp_widget.canvas.grid(column=1, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.1, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._graph_tab_change(1))
            self.main_elements['graph_temp_tab'] = temp_widget

            # mechanical graph
            temp_widget = ASIIcons(tabs, size=25, item='nut',
                                   background="white", foreground='black')
            temp_widget.canvas.grid(column=2, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.2, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._graph_tab_change(2))
            self.main_elements['graph_mech_tab'] = temp_widget

            # electrical graph
            temp_widget = ASIIcons(tabs, size=25, item='lightning bolt',
                                   background="white", foreground='black')
            temp_widget.canvas.grid(column=3, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.3, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._graph_tab_change(3))
            self.main_elements['graph_elec_tab'] = temp_widget

            # efficiency graph
            temp_widget = ASIIcons(tabs, size=25, item='eta',
                                   background="white", foreground='black')
            temp_widget.canvas.grid(column=4, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.4, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._graph_tab_change(4))
            self.main_elements['graph_effi_tab'] = temp_widget

            # motoring & braking current graph
            temp_widget = ASIIcons(tabs, size=25, item='tblimit',
                                   background="white", foreground='black')
            temp_widget.canvas.grid(column=5, row=0, padx=5)
            # temp_widget.canvas.place(relx=0.5, rely=0.5, anchor='w')
            temp_widget.canvas.bind('<Button-1>', lambda x: self._graph_tab_change(5))
            self.main_elements['graph_mb_tab'] = temp_widget

            self.main_parameters['graphing'] = False
            self.main_parameters['graphing_interval'] = 13
            self.main_parameters['graphing_data'] = pd.DataFrame(columns=self.graph_params)

            # RPM Torque
            temp_container = ttk.Frame(self.graph_notebook, relief='flat',
                                       width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # temp_container.grid(column=0, row=0, sticky='news')
            # temp_container.pack(fill='both')
            self.graph_notebook.add(temp_container)
            self.main_elements['graph_basic_frame'] = temp_container

            self.main_elements['dyno_plots'] = DynoPlotHandler()

            self.graphs['RPMTorque'] = self.main_elements['dyno_plots'].add_plot(
                temp_container, 5.5, 3, 'single', 1, True, 'grid', self.dyno,
                self.main_parameters['graphing_data'], graph_params=self.graph_params,
                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
                title="RPM & Torque", graph='RPMTorque')
            # self.graphs['RPMTorque'] = DynoPlot(temp_container, 5.5, 3, 'single', 1, True, 'grid', self.dyno,
            #                                     self.main_parameters['graphing_data'], graph_params=self.graph_params,
            #                                     status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
            #                                     title="RPM & Torque", graph='RPMTorque')

            # Temperature
            temp_container = ttk.Frame(self.graph_notebook, relief='flat',
                                       width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # temp_container.grid(column=0, row=0, sticky='news')
            # temp_container.pack(fill='both')
            self.graph_notebook.add(temp_container)
            self.main_elements['graph_temp_frame'] = temp_container

            self.graphs['temp'] = self.main_elements['dyno_plots'].add_plot(
                temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
                self.main_parameters['graphing_data'], graph_params=self.graph_params,
                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
                dut_controller=self.configs.loc['default']['dut_controller'],
                yoko_ip=self.configs.loc['default']['yoko_ip'],
                brk_controller=self.main_parameters['brk_controller'].get(),
                title="Temperature", graph='temp')
            # self.graphs['temp'] = DynoPlot(temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
            #                                self.main_parameters['graphing_data'], graph_params=self.graph_params,
            #                                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
            #                                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
            #                                dut_controller=self.configs.loc['default']['dut_controller'],
            #                                yoko_ip=self.configs.loc['default']['yoko_ip'],
            #                                brk_controller=self.main_parameters['brk_controller'].get(),
            #                                title="Temperature", graph='temp')

            # Mechanical
            temp_container = ttk.Frame(self.graph_notebook, relief='flat',
                                       width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # temp_container.grid(column=0, row=0, sticky='news')
            # temp_container.pack(fill='both')
            self.graph_notebook.add(temp_container)
            self.main_elements['graph_mech_frame'] = temp_container

            self.graphs['mech'] = self.main_elements['dyno_plots'].add_plot(
                temp_container, 5.5, 3, 'single', 1, True, 'grid', self.dyno,
                self.main_parameters['graphing_data'], graph_params=self.graph_params,
                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
                title="Mechanical Power", graph='mech')
            # self.graphs['mech'] = DynoPlot(temp_container, 5.5, 3, 'single', 1, True, 'grid', self.dyno,
            #                                self.main_parameters['graphing_data'], graph_params=self.graph_params,
            #                                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
            #                                title="Mechanical Power", graph='mech')

            # Electrical
            temp_container = ttk.Frame(self.graph_notebook, relief='flat',
                                       width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # temp_container.grid(column=0, row=0, sticky='news')
            # temp_container.pack(fill='both')
            self.graph_notebook.add(temp_container)
            self.main_elements['graph_elec_frame'] = temp_container

            self.graphs['elec'] = self.main_elements['dyno_plots'].add_plot(
                temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
                self.main_parameters['graphing_data'], graph_params=self.graph_params,
                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
                dut_controller=self.configs.loc['default']['dut_controller'],
                yoko_ip=self.configs.loc['default']['yoko_ip'],
                brk_controller=self.main_parameters['brk_controller'].get(),
                title="Electrical", graph='elec')
            # self.graphs['elec'] = DynoPlot(temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
            #                                self.main_parameters['graphing_data'], graph_params=self.graph_params,
            #                                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
            #                                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
            #                                dut_controller=self.configs.loc['default']['dut_controller'],
            #                                yoko_ip=self.configs.loc['default']['yoko_ip'],
            #                                brk_controller=self.main_parameters['brk_controller'].get(),
            #                                title="Electrical", graph='elec')

            # Efficiency
            temp_container = ttk.Frame(self.graph_notebook, relief='flat',
                                       width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # temp_container.grid(column=0, row=0, sticky='news')
            # temp_container.pack(fill='both')
            self.graph_notebook.add(temp_container)
            self.main_elements['graph_effi_frame'] = temp_container

            self.graphs['effi'] = self.main_elements['dyno_plots'].add_plot(
                temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
                self.main_parameters['graphing_data'], graph_params=self.graph_params,
                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
                dut_controller=self.configs.loc['default']['dut_controller'],
                yoko_ip=self.configs.loc['default']['yoko_ip'],
                brk_controller=self.main_parameters['brk_controller'].get(),
                title="Efficiency", graph='effi')
            # self.graphs['effi'] = DynoPlot(temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
            #                                self.main_parameters['graphing_data'], graph_params=self.graph_params,
            #                                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
            #                                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
            #                                dut_controller=self.configs.loc['default']['dut_controller'],
            #                                yoko_ip=self.configs.loc['default']['yoko_ip'],
            #                                brk_controller=self.main_parameters['brk_controller'].get(),
            #                                title="Efficiency", graph='effi')

            # motoring & braking
            temp_container = ttk.Frame(self.graph_notebook, relief='flat',
                                       width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # temp_container.grid(column=0, row=0, sticky='news')
            # temp_container.pack(fill='both')
            self.graph_notebook.add(temp_container)
            self.main_elements['graph_mb_frame'] = temp_container

            self.graphs['mb'] = self.main_elements['dyno_plots'].add_plot(
                temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
                self.main_parameters['graphing_data'], graph_params=self.graph_params,
                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
                dut_controller=self.configs.loc['default']['dut_controller'],
                yoko_ip=self.configs.loc['default']['yoko_ip'],
                brk_controller=self.main_parameters['brk_controller'].get(),
                title="Motoring & Braking", graph='mb')
            # self.graphs['mb'] = DynoPlot(temp_container, 5.5, 3, 'grid', 1, True, 'grid', self.dyno,
            #                                self.main_parameters['graphing_data'], graph_params=self.graph_params,
            #                                plot_count=0, grid_parameters={}, container_height=MIN_HEIGHT * 0.3,
            #                                status_params=parse_etree(f"{ROOT_DIR}/live_parameters.xml"),
            #                                dut_controller=self.configs.loc['default']['dut_controller'],
            #                                yoko_ip=self.configs.loc['default']['yoko_ip'],
            #                                brk_controller=self.main_parameters['brk_controller'].get(),
            #                                title="Motoring & Braking", graph='mb')

            # List
            # temp_container = ttk.Frame(temp, relief='flat',
            #                            width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # # temp_container.grid(column=0, row=0, sticky='news')
            # # temp_container.pack(fill='both')
            # self.status_notebook.add(temp_container)
            # temp_container.columnconfigure(0, weight=1)
            #
            # s_frame = ScrollableFrame(temp_container,
            #                           width=MIN_WIDTH * 0.28,
            #                           height=MIN_HEIGHT * 0.4,
            #                           background='white')
            # s_frame.grid(column=0, row=0, sticky='news')
            # s_frame.columnconfigure(0, weight=1)
            # # s_frame.pack(fill='both')
            # self.main_elements['live_param_frame'] = s_frame.scrollable_frame
            # for i in (0, 1):
            #     self.main_elements['live_param_frame'].columnconfigure(i, weight=1)
            #
            # # self.main_parameters['live_list_parameters'] = {}
            # self.main_parameters['live_list_params'] = parse_etree(f"{ROOT_DIR}/status_parameters.xml")
            # for controller in ['DUT', 'BRK', 'ABB']:
            #     if controller == 'DUT' and pd.isna(self.configs.loc['default']['dut_controller']):
            #         continue
            #
            #     if controller == 'BRK' and self.configs.loc['default']['brk_controller'] not in ASI_CONTROLLERS:
            #         continue
            #
            #     if controller == 'ABB' and self.configs.loc['default']['brk_controller'] != 'ABB':
            #         continue
            #
            #     for element in self.main_parameters['live_list_params'].findall(f"{controller}/Name"):
            #         if f'{controller} {element.text}' not in self.main_parameters['live_list_parameters'].keys():
            #             self.main_parameters['live_list_parameters'][f'{controller} {element.text}'] = DoubleVar(value=0)
            #
            # for i, p in enumerate(self.main_parameters['live_list_parameters']):
            #     Label(self.main_elements['live_param_frame'], text=p, background='white',
            #           name=f"main_live_list_param_{p}_{i}", font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}',
            #           pady=2, justify='center', anchor='center').grid(
            #         column=(i % 2), row=int(i / 2) * 2, sticky='we')
            #     self.main_elements['live_param_frame'].children[
            #         f"main_live_list_param_{p}_{i}"].bind('<MouseWheel>',
            #                                               self.main_elements[
            #                                                   'live_param_frame'].master.master.on_mousewheel)
            #     # self.main_parameters[f'live_list_param_{p}_{i}'] = StringVar(value='0')
            #     Label(self.main_elements['live_param_frame'],
            #           textvariable=self.main_parameters[f'live_list_param_{p}_{i}'],
            #           width=6, name=f"main_live_list_param_{p}_{i}_value",
            #           font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}', background='white', pady=2).grid(
            #         column=(i % 2), row=int(i / 2) * 2 + 1, sticky='we')
            #     self.main_elements['live_param_frame'].children[
            #         f"main_live_list_param_{p}_{i}_value"].bind(
            #         '<MouseWheel>',
            #         self.main_elements['live_param_frame'].master.master.on_mousewheel)
            #     # Label(self.main_elements['live_param_frame'], text=params.loc[i]["Units"], width=3,
            #     #       name=f"main_live_list_param_{params.loc[i]['Shortened Name']}_{i}_unit", font=f'{OPTION_FONT_NAME} 8',
            #     #       background='#ccccff' if p.split(' ')[0] == 'DUT' else '#ccffcc', pady=2).grid(
            #     #     column=(i % 2) * 3 + 2, row=int(1 + i / 2), sticky='e')
            #     # self.main_elements['live_param_frame'].children[f"main_live_list_param_{params.loc[i]['Shortened Name']}_{i}_unit"].bind(
            #     #     '<MouseWheel>',
            #     #     self.main_elements[
            #     #         'live_param_frame'].master.master.on_mousewheel)

            # warnings & faults
            temp_container = ttk.Frame(temp, relief='flat',
                                       width=int(MIN_WIDTH * 0.29),
                                       height=int(MIN_HEIGHT * 0.4))
            # temp_container.grid(column=0, row=0, sticky='news')
            # temp_container.pack(fill='both')
            self.status_notebook.add(temp_container)
            self.main_elements['live_faults_frame'] = temp_container

            self.main_parameters['live_faults'] = {}
            self.main_parameters['live_faults_tree'] = parse_etree(f"{ROOT_DIR}/dyno_v2/ASIObjectDictionary.xml")
            for controller in ['DUT', 'BRK']:
                if controller == 'DUT' and \
                        self.configs.loc['default']['dut_controller'] not in ASI_CONTROLLERS:
                    continue

                if controller == 'BRK' and \
                        self.configs.loc['default']['brk_controller'] not in ASI_CONTROLLERS:
                    continue

                temp_widget = Canvas(temp_container, width=MIN_WIDTH * 0.29, height=MIN_HEIGHT * 0.2,
                                     background='#ccffcc' if controller == 'BRK' else '#ccccff')
                temp_widget.grid(column=0, row=0 if controller == 'DUT' else 1)
                # temp_widget.place(relx=0, rely=0.5 if controller == 'BRK' else 0, anchor='nw')
                temp_widget.create_text(MIN_WIDTH * 0.01, MIN_HEIGHT * 0.1, text=controller, angle=90)
                for i in range(16):
                    temp_widget.create_text(MIN_WIDTH * 0.064 + i * 26, MIN_HEIGHT * 0.02, text=15 - i)
                for i, f in enumerate(['faults', 'faults2', 'warnings', 'warnings2']):
                    temp_widget.create_text(MIN_WIDTH * 0.04,
                                            MIN_HEIGHT * (0.055 + i * 0.035),
                                            text=f, font=f'{OPTION_FONT_NAME} 9')
                    self.main_parameters['live_faults'][f'{controller} {f}'] = IntVar(value=0)
                    temp_indicator = ASIFaultsIndicator(temp_container,
                                                        self.main_parameters['live_faults'][f'{controller} {f}'],
                                                        self.main_parameters['live_faults_tree'],
                                                        f, width=MIN_WIDTH * 0.2)
                    temp_indicator.container.place(relx=0.2,
                                                   rely=(0.1 if controller == 'DUT' else 0.6) + i * 0.08, anchor='nw')
                    self.main_elements[f'live_faults_indicator_{controller}_{f}'] = temp_indicator

            # test status
            self.test_status_frame = ttk.Frame(temp, relief='flat',
                                       width=int(MIN_WIDTH * 0.29), height=int(MIN_HEIGHT * 0.4))
            # self.test_status_frame.grid(column=0, row=0, sticky='news')
            # self.test_status_frame.pack(fill='both')
            self.status_notebook.add(self.test_status_frame)

            for i in (0, 1):
                self.test_status_frame.columnconfigure(i, weight=1)

            for i, param in enumerate(self.status_params['TEST']):
                temp_widget = Label(self.test_status_frame, text=f"{param}",
                                    name=f"status_test_name_{i}", font=f'{OPTION_FONT_NAME} 12',
                                    pady=2, justify='center', anchor='center', background='white')
                temp_widget.grid(column=(i % 2), row=int(i / 2) * 2)
                temp_widget = Label(self.test_status_frame, textvariable=self.status_params['TEST'][param],
                                    name=f"status_test_value_{i}", font=f'{OPTION_FONT_NAME} 12', pady=2,
                                    justify='center', anchor='center', background='white')
                temp_widget.grid(column=(i % 2), row=int(i / 2) * 2 + 1)


            # temp_widget = ttk.Button(temp, text='+',
            #                          command=lambda: self.notebook.select(4),
            #                          name='more_live_btn', width=3)
            # temp_widget.place(relx=0.98, rely=0.98, anchor='se')


        make_dut_section()
        make_brk_section()
        make_yoko_section()
        make_log_section()
        make_test_section()
        make_control_section()
        make_live_section()

        return mainframe

    def build_mainframe(self, root: ttk.Notebook):
        """
        GUI front end
        Constructing connector frame - old GUI
        """
        mainframe = ttk.Frame(root, relief='flat')
        root.add(mainframe, text="Connector [F2]")
        for i in (0, 1, 2, 3, 4, 5, 6, 7, 8):
            mainframe.columnconfigure(i, weight=1)
        for i in (6, 11, 12, 13, 14):
            mainframe.rowconfigure(i, weight=1)

        def combo_events_ports(evt):
            if int(evt.type) == 4:
                w = evt.widget
                try:
                    self._update_ports()
                except IndexError:
                    pass
                w.event_generate('<Down>', when="head")

        def combo_events_baud(evt):
            if int(evt.type) == 4:
                w = evt.widget
                try:
                    self._update_baud()
                except IndexError:
                    pass
                w.event_generate('<Down>', when="head")

        temp = ttk.Button(mainframe, text='Back', command=lambda: self.notebook.select(0), name='more_connect_btn', width=10)
        temp.place(x=5, y=5, anchor='nw')

        # ttk.Button(mainframe, text="\nUpdate COM Ports\n", command=self._update_ports, name='update_port_btn').grid(
        #     columnspan=4, column=5, rowspan=3, row=3, pady=5, sticky='news')
        # ToolTip(mainframe.children['main_default_btn'], msg="Default communication settings!", delay=TOOLTIP_DELAY)
        ttk.Label(mainframe, text='Device', style='maintitle.TLabel').grid(column=2, row=6)
        ttk.Label(mainframe, text='Port', style='maintitle.TLabel').grid(column=3, row=6)
        ttk.Label(mainframe, text='Baudrate', style='maintitle.TLabel').grid(column=4, row=6)
        ttk.Label(mainframe, text='ID', style='maintitle.TLabel').grid(column=5, row=6)
        ttk.Label(mainframe, text='ABB options', style='maintitle.TLabel').grid(column=6, row=6, columnspan=2)

        ttk.Checkbutton(mainframe, variable=self.dut_var, onvalue=True, name='main_dut_check', takefocus=False).grid(
            column=1, row=7, sticky='e')
        ttk.Checkbutton(mainframe, variable=self.brk_var, onvalue=True,  name='main_brk_check', takefocus=False).grid(
            column=1, row=8, sticky='e')
        ttk.Checkbutton(mainframe, variable=self.yoko_var, onvalue=True, name='main_yoko_check', takefocus=False).grid(
            column=1, row=9, sticky='e')
        ToolTip(mainframe.children['main_dut_check'], msg="Include driver when connecting?", delay=TOOLTIP_DELAY)
        ToolTip(mainframe.children['main_brk_check'], msg="Include brake when connecting?", delay=TOOLTIP_DELAY)
        ToolTip(mainframe.children['main_yoko_check'], msg="Include YOKOGAWA when connecting?", delay=TOOLTIP_DELAY)

        ttk.Label(mainframe, text="DUT").grid(column=2, row=7, pady=5)
        ttk.Label(mainframe, text="BRK").grid(column=2, row=8, pady=5)
        ttk.Label(mainframe, text="Yokogawa").grid(column=2, row=9, pady=5)

        ttk.Combobox(mainframe, textvariable=self.dut_port,
                     width=6, name='dut_port_combo',
                     font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=3, row=7, sticky='we')
        mainframe.children['dut_port_combo']['values'] = _com_ports()
        mainframe.children['dut_port_combo'].bind('<Button-1>', combo_events_ports)
        ttk.Combobox(mainframe, textvariable=self.dut_rate,
                     width=6, name='dut_baud_combo',
                     font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=4, row=7, sticky='we')
        mainframe.children['dut_baud_combo']['values'] = COM_BAUD_RATE
        mainframe.children['dut_baud_combo'].bind('<Button-1>', combo_events_baud)
        Entry(mainframe, textvariable=self.dut_id, width=4,
              font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=5, row=7, sticky='we')
        ttk.Combobox(mainframe, textvariable=self.brk_port,
                     width=6, name='brk_port_combo',
                     font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=3, row=8, sticky='we')
        mainframe.children['brk_port_combo']['values'] = _com_ports()
        mainframe.children['brk_port_combo'].bind('<Button-1>', combo_events_ports)
        ttk.Combobox(mainframe, textvariable=self.brk_rate,
                     width=6, name='brk_baud_combo',
                     font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=4, row=8, sticky='we')
        mainframe.children['brk_baud_combo']['values'] = COM_BAUD_RATE
        mainframe.children['brk_baud_combo'].bind('<Button-1>', combo_events_baud)
        Entry(mainframe, textvariable=self.brk_id, width=4,
              font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=5, row=8, sticky='we')
        ttk.Checkbutton(mainframe, text="Remote Mode", variable=self.abb_auto,
                        onvalue=True, name='main_auto_check', takefocus=False).grid(
            column=7, row=8)
        ToolTip(mainframe.children['main_auto_check'],
                msg="ABB brake in auto/manual mode", delay=TOOLTIP_DELAY)
        ttk.Checkbutton(mainframe, text="ABB", variable=self.abb,
                        onvalue=True, name='main_abb_check', takefocus=False).grid(
            column=6, row=8)
        ToolTip(mainframe.children['main_abb_check'],
                msg="Brake controller: ABB or ASI Controller", delay=TOOLTIP_DELAY)
        ttk.Label(mainframe, text="192.168.1.").grid(
            column=3, row=9, sticky='e')
        Entry(mainframe, textvariable=self.yoko_ip, width=5,
              name='yoko_ip_entry',
              font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=4, row=9, sticky='w')
        ToolTip(mainframe.children['yoko_ip_entry'],
                msg='Leave as 0 to ignore YOKOGAWA', delay=TOOLTIP_DELAY)

        self._update_connection_status(mainframe)

        self.connection_condition.set("CONNECT")
        ttk.Button(mainframe, textvariable=self.connection_condition, padding='0 10 0 10',
                   width=50, command=self._main_connect, name='connect_btn')
        mainframe.children['connect_btn'].grid(column=0, row=11, columnspan=8, pady=5, sticky='ns')
        ToolTip(mainframe.children['connect_btn'], delay=TOOLTIP_DELAY,
                msg="Connecting to Dyno with the instruments selected above.\n"
                    "Make sure controllers are turned on and connected\n"
                    "Reconnect to change instruments")
        ttk.Button(mainframe, text="Toggle ABB auto <-> manual", command=self._toggle_abb,
                   width=50, state=DISABLED, name='abb_toggle_btn')
        mainframe.children['abb_toggle_btn'].grid(column=0, row=12, columnspan=8, pady=5, sticky='ns')
        ToolTip(mainframe.children['abb_toggle_btn'], delay=TOOLTIP_DELAY,
                msg="Toggles between auto and manual mode when connected to ABB.\nCheck keypad for \"LOC/REM\" status")
        ttk.Button(mainframe, text="DEFAULT", command=self._connect_default, width=50, name='main_default_btn').grid(
            columnspan=8, column=0, row=13, sticky='ns')
        ToolTip(mainframe.children['main_default_btn'], msg="Default communication settings!", delay=TOOLTIP_DELAY)

        ttk.LabelFrame(mainframe, text="Help", name='helper_frame').grid(
            column=0, row=14, columnspan=8)
        ToolTip(mainframe.children['helper_frame'], msg="Helper information", delay=2)
        ttk.Label(mainframe.children['helper_frame'], text=HELP_TEXT, width=90).grid(
            column=0, row=0, padx=5, pady=5, sticky='we')

        return mainframe

    def build_controlframe(self, root: ttk.Notebook):
        """
        GUI front end
        Constructing controller frame - old GUI
        """
        mainframe = ttk.Frame(root, relief='flat')
        root.add(mainframe, text="Controller [F3]")
        for i in (0, 1, 2, 3):
            mainframe.columnconfigure(i, weight=1)
        for i in [2]:
            mainframe.rowconfigure(i, weight=1)

        # param_frame = ttk.Panedwindow(mainframe, orient=HORIZONTAL)
        param_frame = ttk.Frame(mainframe, name='param_frame')
        param_frame.grid(columnspan=4, column=0, row=2, sticky='news')
        for i in range(2):
            param_frame.columnconfigure(i, weight=1)
        param_frame.rowconfigure((0, 1), weight=1)

        temp = ttk.Button(mainframe, text='Back',
                          command=lambda: self.notebook.select(0),
                          name='more_connect_btn', width=10)
        temp.grid(column=0, row=0 ,sticky='nw')

        # DUT main frame
        dut_label = Label(mainframe, text='DUT', font=('Comic Sans', 15), background='#ccccff')
        self.dut_frame = ttk.LabelFrame(param_frame, name="dut_label_frame_0", labelanchor='n',
                                        labelwidget=dut_label, style='dut.TLabelframe')
        # self.dut_header = ttk.Panedwindow(self.dut_frame, orient=HORIZONTAL)
        # self.dut_header.add(ttk.Label(self.dut_header, text="Name"))
        # self.dut_header.add(ttk.Label(self.dut_header, text="Value"))
        # self.dut_header.add(ttk.Label(self.dut_header, text="Unit"))
        # self.dut_header.add(ttk.Frame(self.dut_header))
        # self.dut_header.grid(column=0, row=0, sticky="we")

        self.dut_frame.grid(column=0, row=0, rowspan=2 ,sticky='news', padx=2)
        # param_frame.add(self.dut_frame)
        s_frame = ScrollableFrame(self.dut_frame, width=340, height=850, background='#ccccff')
        # s_frame.grid(column=0, row=1, sticky='news')
        s_frame.pack(fill='both')
        self.dut_frame = s_frame.scrollable_frame
        for i in (0, 1, 2):
            self.dut_frame.columnconfigure(i, weight=1)

        # DUT extra frame
        dut_label = Label(mainframe, text='DUT', font=('Comic Sans', 15), background='#ccccff')
        self.dut_extra_frame = ttk.LabelFrame(param_frame, name="dut_label_frame_1", style='dut.TLabelframe',
                                              labelanchor='n', labelwidget=dut_label)
        s_frame = ScrollableFrame(self.dut_extra_frame, width=340, height=500, background='#ccccff')
        # s_frame.grid(column=0, row=1, sticky='news')
        self.dut_extra_frame = s_frame.scrollable_frame
        for i in (0, 1, 2):
            self.dut_extra_frame.columnconfigure(i, weight=1)

        # DUT extra frame 1
        dut_label = Label(mainframe, text='DUT', font=('Comic Sans', 15), background='#ccccff')
        self.dut_extra_frame_1 = ttk.LabelFrame(param_frame, name="dut_label_frame_2", style='dut.TLabelframe',
                                              labelanchor='n', labelwidget=dut_label)
        s_frame = ScrollableFrame(self.dut_extra_frame_1, width=340, height=500, background='#ccccff')
        # s_frame.grid(column=0, row=1, sticky='news')
        self.dut_extra_frame_1 = s_frame.scrollable_frame
        for i in (0, 1, 2):
            self.dut_extra_frame_1.columnconfigure(i, weight=1)

        # BRK main frame
        brk_label = Label(mainframe, text='BRK', font=('Comic Sans', 15), background='#ccffcc')
        self.brk_frame = ttk.LabelFrame(param_frame, name="brk_label_frame_0", labelanchor='n', labelwidget=brk_label, style='brk.TLabelframe')

        # self.brk_header = ttk.Panedwindow(self.brk_frame, orient=HORIZONTAL)
        # self.brk_header.add(ttk.Label(self.brk_header, text="Name"))
        # self.brk_header.add(ttk.Label(self.brk_header, text="Value"))
        # self.brk_header.add(ttk.Label(self.brk_header, text="Unit"))
        # self.brk_header.add(ttk.Frame(self.brk_header))
        # self.brk_header.grid(column=0, row=0, sticky="we")

        self.brk_frame.grid(column=1, row=0, rowspan=2, sticky='news', padx=2)
        # param_frame.add(self.brk_frame)
        s_frame = ScrollableFrame(self.brk_frame, width=340, height=850, background='#ccffcc')
        # s_frame.grid(column=0, row=1, sticky='news')
        s_frame.pack(fill='both')
        self.brk_frame = s_frame.scrollable_frame
        for i in (0, 1, 2):
            self.brk_frame.columnconfigure(i, weight=1)

        # BRK extra frame
        brk_label = Label(mainframe, text='BRK', font=('Comic Sans', 15), background='#ccffcc')
        self.brk_extra_frame = ttk.LabelFrame(param_frame, name="brk_label_frame_1", style='brk.TLabelframe',
                                              labelanchor='n', labelwidget=brk_label)
        s_frame = ScrollableFrame(self.brk_extra_frame, width=340, height=500, background='#ccffcc')
        self.brk_extra_frame = s_frame.scrollable_frame
        for i in (0, 1, 2):
            self.brk_extra_frame.columnconfigure(i, weight=1)

        # BRK extra frame 1
        brk_label = Label(mainframe, text='BRK', font=('Comic Sans', 15), background='#ccffcc')
        self.brk_extra_frame_1 = ttk.LabelFrame(param_frame, name="brk_label_frame_2", style='brk.TLabelframe',
                                              labelanchor='n', labelwidget=brk_label)
        s_frame = ScrollableFrame(self.brk_extra_frame_1, width=340, height=500, background='#ccffcc')
        self.brk_extra_frame_1 = s_frame.scrollable_frame
        for i in (0, 1, 2):
            self.brk_extra_frame_1.columnconfigure(i, weight=1)

        # self.controller_params_operation([self.dut_frame, self.brk_frame], ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}"],
        #                                  mode=CONTROL_PARAM_INIT)

        ttk.Button(mainframe, text="DUT START", command=self._dut_start, name='start_btn').grid(
            column=0, row=10, sticky='news', padx=10)
        ToolTip(mainframe.children['start_btn'], delay=TOOLTIP_DELAY,
                msg="write 2 to Remote state command")

        ttk.Button(mainframe, text="DUT STOP", command=self._dut_stop, name='stop_btn').grid(
            column=1, row=10, sticky='news', padx=10)
        ToolTip(mainframe.children['stop_btn'], delay=TOOLTIP_DELAY,
                msg="write 0 to Remote state command")

        ttk.Button(mainframe, text="BRK START", command=self._brk_start, name='brk_start_btn').grid(
            column=2, row=10, sticky='news', padx=10)
        ToolTip(mainframe.children['brk_start_btn'], delay=TOOLTIP_DELAY,
                msg="ASI Controller: Starts in Torque mode with 0% torque command. "
                    "Determines brake torque direction\n"
                    "ABB: Starts Brake")

        ttk.Button(mainframe, text="BRK STOP", command=self._brk_stop, name='brk_stop_btn').grid(
            column=3, row=10, sticky='news', padx=10)
        ToolTip(mainframe.children['brk_stop_btn'], delay=TOOLTIP_DELAY,
                msg="ASI Controller: write 0 to Remote state command\nABB: Stops Brake")

        Button(mainframe, text="DYNO START", command=self._dyno_start, fg='white', relief='groove',
               name='dyno_start_btn', bg='green', activebackground='green', activeforeground='white').grid(
            column=0, row=12, sticky='news', padx=10)
        ToolTip(mainframe.children['dyno_start_btn'], delay=TOOLTIP_DELAY,
                msg="Dyno Start Sequence: start logging -> wait 2s -> write 2 to Remote state command")

        Button(mainframe, text="DYNO STOP", command=lambda: self._dyno_stop(1), fg='white', relief='groove',
               name='dyno_stop_btn', bg='red', activebackground='red', activeforeground='white').grid(
            column=1, row=12, sticky='news', padx=10)
        ToolTip(mainframe.children['dyno_stop_btn'], delay=TOOLTIP_DELAY,
                msg="Dyno Stop Sequence! Does not stop logging")

        ttk.Button(mainframe, text="Fault Clear", command=self._fault_clear, name='ctrl_fault_clear_btn').grid(
            column=2, row=12, sticky='news', padx=10)
        ToolTip(mainframe.children['ctrl_fault_clear_btn'], msg="Clears fault for both driver and brake", delay=TOOLTIP_DELAY)

        ttk.Button(mainframe, text="Check Fault",
                   command=self._check_fault, name='ctrl_check_fault_btn').grid(
            column=3, row=12, sticky='news', padx=10)
        ToolTip(mainframe.children['ctrl_check_fault_btn'], delay=TOOLTIP_DELAY,
                msg="Checks fault for DUT (and BRK, if BRK is also ASI controller)")
        # Entry(mainframe, textvariable=self.motor_discovery_brk_mode, width=2).grid(
        #     column=3, row=13)

        ttk.Separator(mainframe, orient='horizontal').grid(column=0, row=14, columnspan=4, sticky='we')

        # buttonframe = ttk.Frame(mainframe, name='btn_frame')
        # buttonframe.grid(column=0, row=15, columnspan=2, sticky='news')
        # buttonframe.columnconfigure(0, weight=1)
        # for i in (0, 1):
        #     buttonframe.rowconfigure(i, weight=1)

        # def build_buttonframe():
        #     Button(buttonframe, text="BRK Ramp", command=self._brk_ramp, name="ctrl_ramp_btn",
        #            relief='groove', bg=DEFAULT_GREY).grid(
        #         column=0, row=0, sticky='news', padx=10)
        #     ToolTip(buttonframe.children['ctrl_ramp_btn'],
        #             msg="Ramp brake torque to target % level within the time and total_steps indicated.\n+ to Brake | - to Boost",
        #             delay=TOOLTIP_DELAY)
        #     ttk.Label(buttonframe, text="To").grid(column=1, row=0)
        #     Entry(buttonframe, textvariable=self.ramp_target, width=4,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=2, row=0)
        #     ttk.Label(buttonframe, text="% in").grid(column=3, row=0)
        #     Entry(buttonframe, textvariable=self.ramp_step, width=4,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=4, row=0)
        #     ttk.Label(buttonframe, text="total_steps for").grid(column=5, row=0)
        #     Entry(buttonframe, textvariable=self.ramp_duration, width=4,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(column=6, row=0)
        #     ttk.Label(buttonframe, text="second(s)").grid(column=7, row=0)
        #
        #     # ttk.Separator(buttonframe, orient='horizontal').grid(columnspan=8, column=0, row=1, sticky='we')
        #
        #     Button(buttonframe, text="DYNO Stop Timer", command=self._run_for, name="ctrl_timer_btn",
        #            relief='groove', bg=DEFAULT_GREY).grid(
        #         column=0, row=2, sticky='news', padx=10)
        #     ToolTip(buttonframe.children['ctrl_timer_btn'], delay=TOOLTIP_DELAY,
        #             msg="Stops DynoModule (both driver and brake) at the end of the countdown.\n"
        #                 "Toggle to start/stop.\nMax 999:59:59")
        #     Entry(buttonframe, textvariable=self.run_duration_h, width=4,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=1, row=2)
        #     ttk.Label(buttonframe, text=":").grid(column=2, row=2)
        #     Entry(buttonframe, textvariable=self.run_duration_m, width=4,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=3, row=2)
        #     ttk.Label(buttonframe, text=":").grid(column=4, row=2)
        #     Entry(buttonframe, textvariable=self.run_duration_s, width=4,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=5, row=2)

        # build_buttonframe()

        # def build_buttonframe_2():
        # container = ttk.Frame(mainframe, name='btn_frame_1')
        # container.grid(column=2, row=15, padx=20, sticky='news')

        ttk.Button(mainframe, text='Reset BRK Direction',
                   command=self._set_brk_dir, name='set_dir_btn').grid(
            column=2, row=15, padx=10, sticky='news')
        ToolTip(mainframe.children['set_dir_btn'],
                msg='Only works with ASI controller\nUse when BRK is spinning',
                delay=TOOLTIP_DELAY)

        # ttk.Separator(container, orient='horizontal').grid(columnspan=3, column=0, row=1, sticky='we')
        container = Frame(mainframe, name='btn_frame_2', background='white', relief='flat')
        container.grid(column=3, row=15, padx=10)

        ttk.Label(container, text='Calculated BRK Torque:').grid(column=0, row=2)
        Entry(container, textvariable=self.calc_torque, name='set_torque_entry',
              font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}', width=5).grid(
            column=1, row=2)
        ttk.Label(container, text='%', width=2).grid(column=2, row=2)
        container.children['set_torque_entry'].bind('<Return>', self._set_torque)
        ToolTip(container.children['set_torque_entry'],
                msg='Only works with ASI controller\n+ Braking | - Boosting',
                delay=TOOLTIP_DELAY)

        # build_buttonframe_2()
        # ttk.Separator(mainframe, orient='horizontal').grid(column=0, row=16, columnspan=4, sticky='we')

        # restframe = ttk.Frame(mainframe, name='rest_frame')
        # restframe.grid(column=0, row=17, columnspan=4, sticky='news')
        # for i in (0, 1, 2, 3, 4, 5):
        #     restframe.columnconfigure(i, weight=1)
        # for i in (14, 16, 18, 19):
        #     restframe.rowconfigure(i, weight=1)

        # def build_restframe():
        #     ttk.Button(restframe, text="Start Logging", command=self._start_logging,
        #                state=DISABLED, name='start_log_btn').grid(
        #         column=0, row=14, sticky='news', padx=10)
        #     # ToolTip(restframe.children['start_log_btn'], delay=TOOLTIP_DELAY,
        #     #         msg="Starts logging at chosen interval. "
        #     #             "Allows extra logging and live graphing. Logs are saved at C:/DynoResults")
        #
        #     ttk.Button(restframe, text="Update Interval", command=self._update_log_interval,
        #                state=DISABLED, name='update_log_btn').grid(
        #         column=1, row=14, sticky='news', padx=10)
        #     # ToolTip(restframe.children['update_log_btn'], delay=TOOLTIP_DELAY, msg="Updates logging interval. ")
        #
        #     ttk.Label(restframe, text="Interval").grid(column=2, row=14, sticky='e')
        #     Entry(restframe, textvariable=self.log_interval, width=5,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=3, row=14, sticky='we', padx=10)
        #     ttk.Label(restframe, text="s").grid(column=4, row=14, sticky='w')
        #     ttk.Button(restframe, text="Stop Logging", command=self._stop_logging,
        #                state=DISABLED, name="stop_log_btn").grid(
        #         column=5, row=14, sticky='news', padx=10)
        #     # ToolTip(restframe.children['stop_log_btn'], delay=TOOLTIP_DELAY, msg="Stops logging. Disabling extra logging and live graphing")
        #
        #     ttk.Separator(restframe, orient='horizontal').grid(column=0, row=15, columnspan=6, sticky='we')
        #
        #     ttk.Button(restframe, text="Create Extra Log File", command=self._extra_logging,
        #                state=DISABLED, name="extra_log_btn").grid(
        #         column=0, row=16, sticky='news', padx=10)
        #     ToolTip(restframe.children['extra_log_btn'], delay=TOOLTIP_DELAY,
        #             msg="Starts a new CSV file for separate logging. Only enabled when DynoModule is logging. "
        #                 "Can create and write to multiple different files")
        #     ttk.Checkbutton(restframe, text="Same folder", onvalue=True,
        #                     variable=self.same_folder, name='ctrl_same_folder_btn').grid(
        #         column=1, row=16, sticky='w')
        #     ToolTip(restframe.children['ctrl_same_folder_btn'], delay=TOOLTIP_DELAY,
        #             msg="Save the extra logging files under the same folder as general logging. "
        #                 "Uncheck to save 1 level above")
        #     ttk.Label(restframe, text="File name").grid(column=2, row=16, sticky='e')
        #     Entry(restframe, textvariable=self.extra_file, width=20,
        #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=3, row=16, sticky='we', padx=10)
        #     ttk.Button(restframe, text="Log to Extra File", command=self._extra_line,
        #                state=DISABLED, name='extra_line_btn').grid(
        #         column=5, row=16, sticky='news', padx=10)
        #     ToolTip(restframe.children['extra_line_btn'], delay=TOOLTIP_DELAY,
        #             msg="Add a new row of data to the extra logging file indicated above. "
        #                 "Make sure file name is correct!")
        #
        #     ttk.Separator(restframe, orient='horizontal').grid(
        #         column=0, row=17, columnspan=6, sticky='we')
        #
        #     ttk.Button(restframe, text="Basic Graph",
        #                command=self._basic_plot, name='basic_plot_btn').grid(
        #         column=0, row=18, sticky='news', padx=10)
        #     ToolTip(restframe.children['basic_plot_btn'], delay=TOOLTIP_DELAY,
        #             msg="Create a predefined basic plot. Can be displayed, saved or both. "
        #                 "Only functional at the end of test when logging is stopped")
        #     ttk.Label(restframe, text="Display").grid(column=2, row=18, sticky='e')
        #     ttk.Combobox(restframe, textvariable=self.plot_display,
        #                  width=8, name='basic_plot_combo',
        #                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=3, row=18, sticky='we')
        #     restframe.children['basic_plot_combo']['values'] = ["display", "save", "both"]
        #
        #     ttk.Separator(restframe, orient='horizontal').grid(column=0, row=19, columnspan=6, sticky='we')
        #
        #     ttk.Button(restframe, text="Error Graph", command=self._plot_errors, name='error_plot_btn').grid(
        #         column=0, row=20, sticky='news', padx=10)
        #     ToolTip(restframe.children['error_plot_btn'], delay=TOOLTIP_DELAY,
        #             msg="Create an error plot over time from data logged. Can be displayed, saved or both. "
        #                 "Only functional at the end of test when logging is stopped")
        #     # ttk.Label(restframe, text="Error").grid(column=1, row=19, sticky=E)
        #     ttk.Combobox(restframe, textvariable=self.error2display,
        #                  width=15, name='error_plot_combo',
        #                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=1, row=20, sticky='we')
        #     restframe.children['error_plot_combo']['values'] = ["DUT warnings", "DUT faults", "BRK warnings", "BRK faults"]
        #     ttk.Label(restframe, text="Display").grid(column=2, row=20, sticky='e')
        #     ttk.Combobox(restframe, textvariable=self.error_display,
        #                  width=8, name='error_plot_display_combo',
        #                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
        #         column=3, row=20, sticky='we')
        #     restframe.children['error_plot_display_combo']['values'] = ["display", "save", "both"]

        # build_restframe()

        ttk.Button(mainframe, text="DUT Motor Disco. Mode 1", command=lambda: self._gui_motor_discovery(1, 1),
                   name='dut_motor_discovery_btn_1').grid(
            column=0, row=20, padx=10, sticky='news')
        ttk.Button(mainframe, text="DUT Motor Disco. Mode 2", command=lambda: self._gui_motor_discovery(1, 2),
                   name='dut_motor_discovery_btn_2').grid(
            column=1, row=20, padx=10, sticky='news')
        # Entry(mainframe, textvariable=self.motor_discovery_dut_mode, width=2).grid(
        #     column=1, row=13)
        ttk.Button(mainframe, text="BRK Motor Disco. Mode 1", command=lambda: self._gui_motor_discovery(2, 1),
                   name='brk_motor_discovery_btn_1').grid(
            column=2, row=20, padx=10, sticky='news')
        ttk.Button(mainframe, text="BRK Motor Disco. Mode 2", command=lambda: self._gui_motor_discovery(2, 2),
                   name='brk_motor_discovery_btn_2').grid(
            column=3, row=20, padx=10, sticky='news')

        # ttk.Button(mainframe, text="DUT Save to Flash", command=self._flash_dut, name='dut_save2flash_btn').grid(
        #     column=0, row=21, padx=10, sticky='news')
        # ToolTip(mainframe.children['dut_save2flash_btn'], delay=TOOLTIP_DELAY, msg="Driver save to flash")
        # ttk.Button(mainframe, text="BRK Save to Flash", command=self._flash_brk, name='brk_save2flash_btn').grid(
        #     column=0, row=22, padx=10, sticky='news')
        # ToolTip(mainframe.children['brk_save2flash_btn'], delay=TOOLTIP_DELAY, msg="Brake save to flash. Only works with ASI Controller")
        # ttk.Button(mainframe, text="DUT Load Parameters", command=self._file_load_dut, name='dut_load_param_btn').grid(
        #     column=2, row=21, padx=10, sticky='news')
        # ToolTip(mainframe.children['dut_load_param_btn'], delay=TOOLTIP_DELAY, msg="Driver load parameter file")
        # ttk.Button(mainframe, text="BRK Load Parameters", command=self._file_load_brk, name='brk_load_param_btn').grid(
        #     column=2, row=22, padx=10, sticky='news')
        # ToolTip(mainframe.children['brk_load_param_btn'], delay=TOOLTIP_DELAY, msg="Brake load parameter file. Only works with ASI Controller")
        # ttk.Button(mainframe, text="DUT Save Parameters", command=self._file_save_dut, name='dut_save_param_btn').grid(
        #     column=1, row=21, padx=10, sticky='news')
        # ToolTip(mainframe.children['dut_save_param_btn'], delay=TOOLTIP_DELAY, msg="Driver save parameters to file")
        # ttk.Button(mainframe, text="BRK Save Parameters", command=self._file_save_brk, name='brk_save_param_btn').grid(
        #     column=1, row=22, padx=10, sticky='news')
        # ToolTip(mainframe.children['brk_save_param_btn'], delay=TOOLTIP_DELAY, msg="Brake save parameters to file. Only works with ASI Controller")
        ttk.Button(mainframe, text="Read", command=self._update_main, name='read_param_btn').grid(
            column=0, row=15, padx=10, sticky='news')
        ToolTip(mainframe.children['read_param_btn'], delay=TOOLTIP_DELAY,
                msg="Read all parameters above from connected instruments")
        ttk.Button(mainframe, text="Write", command=self._upload_main, name='write_param_btn').grid(
            column=1, row=15, padx=10, sticky='news')
        ToolTip(mainframe.children['write_param_btn'], delay=TOOLTIP_DELAY,
                msg="Write all parameters above to connected instruments")

        return mainframe

    def build_testframe(self, root: ttk.Notebook):
        """
        GUI front end
        Constructing Tester frame - old GUI
        """
        # container = ttk.Notebook(root, style='TNotebook')
        container = ttk.Frame(root, relief='flat')
        mainframe = ttk.Frame(container, relief='flat')
        mainframe.grid(column=0, row=0, sticky='news')
        container.columnconfigure((0, 1), weight=1)
        container.rowconfigure(0, weight=1)
        root.add(container, text="Tester [F4]")

        def build_preset():
            # mainframe = ttk.Frame(container, relief='flat', name='test_preset')
            # container.add(mainframe, text='Preset')
            for i in (0, 1, 2, 3, 4, 5, 6, 7):
                mainframe.columnconfigure(i, weight=1)
            for i in (2, 3, 5):
                mainframe.rowconfigure(i, weight=1)
            mainframe.rowconfigure(5, weight=2)

            # label_title = ttk.Label(mainframe, text="ASI DynoModule Tester", background='#5DA01D', anchor='center')
            # label_title.grid(column=0, row=0, columnspan=8, sticky='news')
            # ttk.Separator(mainframe).grid(columnspan=8, column=0, row=1, sticky='we', pady=2)

            temp = ttk.Button(mainframe, text='Back',
                              command=lambda: self.notebook.select(0),
                              name='more_connect_btn', width=10)
            temp.place(x=5, y=5, anchor='nw')

            btn_frame = ttk.Frame(mainframe, name='test_btn_frame', padding='5')
            btn_frame.grid(column=0, row=3, columnspan=8, sticky='we')
            for i in (0, 1, 2, 3, 4, 5, 6, 7):
                btn_frame.columnconfigure(i, weight=1)
            for i in (0, 3, 8, 9, 10, 11):
                btn_frame.rowconfigure(i, weight=1)

            ttk.Label(btn_frame, text="Preset: ").grid(column=0, row=3)
            ttk.Combobox(btn_frame, textvariable=self.config_value,
                         name='config_combo',
                         font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=1, row=3, columnspan=6, sticky='we', padx=15)
            btn_frame.children['config_combo']['values'] = self.configs.index.to_list()
            ToolTip(btn_frame.children['config_combo'], delay=TOOLTIP_DELAY,
                    msg="Select a preset for connection and test configurations")
            btn_frame.children['config_combo'].bind('<<ComboboxSelected>>',
                                                    self._populate_config_list)

            ttk.Button(btn_frame, text='Filter',
                       name='filter_config_btn', command=self._popup_filter).grid(
                column=7, row=3, sticky='we')
            # ttk.Button(btn_frame, text='Toggle List', name='toggle_config_btn', command=self._popup_config_list).grid(
            #     column=7, row=3, sticky='we')

            ttk.Label(btn_frame, text="Test").grid(column=0, row=8)
            tests = ttk.Combobox(btn_frame, textvariable=self.test,
                                 font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            tests.grid(column=1, row=8, columnspan=3, sticky='we')
            tests['values'] = TEST_SCRIPTS
            tests.bind('<<ComboboxSelected>>', self.test_inputs)
            ToolTip(tests, delay=TOOLTIP_DELAY, msg="Which test are we running?")

            ttk.Label(btn_frame, text="Save results to: ").grid(column=0, row=9, pady=10)
            Entry(btn_frame, textvariable=self.result_destination,
                  name='result_entry', font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=1, row=9, sticky='we', columnspan=6)
            ToolTip(btn_frame.children['result_entry'], delay=TOOLTIP_DELAY,
                    msg="Please don't leave this field empty when starting a test script")
            ttk.Button(btn_frame, text="Browse",
                       command=self._result_destination, name='test_browse_btn').grid(
                column=7, row=9, sticky='we')

            Button(btn_frame, text="RUN", command=self._start_test_thread,
                   name='test_run_btn', fg='white',
                   bg='green', activebackground='green').grid(
                column=5, row=8, sticky='we')
            ttk.Checkbutton(btn_frame, text="with barcode", variable=self.with_barcode,
                            command=self._barcode2sn, name='barcode_check').grid(
                column=4, row=8)
            Button(btn_frame, text="STOP", command=self._e_stop, name='stop_btn',
                   bg='red', fg='white', activebackground='red').grid(
                column=6, row=8, sticky='we')
            ttk.Button(btn_frame, text="CEDAR GUIDE",
                       command=self._open_cedar_guide, name='guide_btn').grid(
                column=7, row=8, sticky='we')
            ToolTip(btn_frame.children['guide_btn'], msg="Opens CEDAR TESTING GUIDE")

            ttk.Label(btn_frame, textvariable=self.test_note).grid(column=0, row=10)
            Entry(btn_frame, textvariable=self.motor_type, name='type_entry',
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=1, row=10, columnspan=3, sticky='we')
            ToolTip(btn_frame.children['type_entry'],
                    msg="Any text allowed")

            ttk.Label(btn_frame, text="S/N").grid(column=4, row=10)
            Entry(btn_frame, textvariable=self.serial_num, width=15, name='sn_entry',
                  state=DISABLED, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=5, row=10, sticky='we')
            ToolTip(btn_frame.children['sn_entry'],
                    msg="Default to 0000-00000 (Keep in 'number dash number' format)")

            ttk.Label(btn_frame, text="S/N 2", name='sn_label_2')
            Entry(btn_frame, textvariable=self.serial_num_1, width=15, name='sn_entry_2',
                  state=DISABLED, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            ToolTip(btn_frame.children['sn_entry_2'],
                    msg="Default to 0000-00000 (Keep in 'number dash number' format)")

            ttk.Label(btn_frame, text="Barcode: ").grid(column=0, row=11)
            Entry(btn_frame, textvariable=self.barcode_var, name='barcode_entry',
                  width=90, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=1, row=11, columnspan=8, sticky='we', pady=5)
            btn_frame.children['barcode_entry'].bind('<FocusIn>', self._select_all)

            ttk.Label(btn_frame, text="Barcode B: ", name='barcode_2_label')
            Entry(btn_frame, textvariable=self.barcode_2_var, name='barcode_2_entry',
                  width=90, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            btn_frame.children['barcode_2_entry'].bind('<FocusIn>', self._select_all_2)

            ttk.Checkbutton(btn_frame, text="Notify via email when done",
                            variable=self.notify, name='notify_check').grid(
                column=0, row=13, columnspan=4, sticky='e')
            Entry(btn_frame, name='email_entry', width=35, justify='right',
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=4, row=13, sticky='e', pady=5, columnspan=2)
            ttk.Label(btn_frame, text="@acceleratedsystems.com").grid(
                column=6, row=13, columnspan=2, sticky='w')

            ttk.Checkbutton(btn_frame, text="Notify progress via email",
                            variable=self.notify_progress, name='progress_check')
            Entry(btn_frame, name='email_progress_entry', width=35, justify='right',
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
            ttk.Label(btn_frame, text="@acceleratedsystems.com", name='progress_label')

            ttk.Checkbutton(btn_frame, text="Zoom in mode", variable=self.rundown_zoom,
                            name='zoom_check', onvalue=True).grid(
                column=0, row=14, columnspan=4, sticky='e')
            Entry(btn_frame, name='zoom_lo_entry', width=10, justify='right',
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=4, row=14, sticky='e', pady=5)
            ttk.Label(btn_frame, text="Nm -", name='zoom_label', justify='center').grid(
                column=5, row=14)
            Entry(btn_frame, name='zoom_hi_entry', width=10,
                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
                column=6, row=14, sticky='we')
            ttk.Label(btn_frame, text="Nm", name='zoom_label1').grid(
                column=7, row=14, sticky='w')

            ttk.Label(btn_frame, text="Efficiency Map Target:",
                      name='effi_target_label')
            ttk.Checkbutton(btn_frame, name='effi_motor_check', onvalue=True, text='Motor',
                            variable=self.main_parameters['effi_target'])
            ttk.Checkbutton(btn_frame, name='effi_controller_check', onvalue=False, text='Controller',
                            variable=self.main_parameters['effi_target'])

            # ttk.Button(mainframe, textvariable=self.edit_popup, command=self._bind_edit, name='edit_config_btn')
            # ToolTip(mainframe.children['edit_config_btn'], delay=TOOLTIP_DELAY,
            #         msg="Toggle configuration items between editable and read-only. Double click to edit")
            ttk.Button(mainframe, text="Save to file", command=self._save_config_list, name="save_config_btn")
            ToolTip(mainframe.children['save_config_btn'], delay=TOOLTIP_DELAY,
                    msg="Save onboard configurations to file (persist after restart)")
            ttk.Button(mainframe, text="New preset", command=self._new_config, name="new_config_btn").grid(
                column=4, row=13, columnspan=2, sticky='news')
            ToolTip(mainframe.children['new_config_btn'], delay=TOOLTIP_DELAY,
                    msg="Create a new configuration from current preset. Save to file to keep the changes")
            ttk.Button(mainframe, text="Delete preset", command=self._del_config, name='del_config_btn').grid(
                column=6, row=13, columnspan=2, sticky='news')

            ToolTip(mainframe.children['del_config_btn'], delay=TOOLTIP_DELAY,
                    msg="Delete the currently selected configuration. Save to file to keep the changes")
            mainframe.children['save_config_btn'].grid(column=2, row=13, columnspan=2, sticky='news')

            # self._build_config_popup(mainframe)

            config_list_container = ttk.Frame(container, relief='flat')
            config_list_container.grid(column=1, row=0, sticky='news', pady=10, padx=10)
            self.config_list = ScrollableFrame(config_list_container,
                                               width=MIN_WIDTH * 0.4, height=MIN_HEIGHT,
                                               background='white')
            self.config_list.pack(fill='both')

            Text(mainframe, name='config_desc_text', font=OPTION_FONT_NAME,
                 undo=True, width=70, height=4).grid(
                column=0, row=5, columnspan=8, rowspan=4, pady=10, sticky='ns')

            self.init_config_list(mainframe)

            # Reminder Label Frame
            helper_container = ttk.LabelFrame(mainframe, text="Reminder")
            helper_container.grid(column=0, row=2, columnspan=8)
            ToolTip(helper_container, msg="Helper information", delay=2)
            ttk.Label(helper_container, text=REMINDER_TEXT, width=90).grid(
                column=0, row=0, padx=5, pady=5, sticky='we')

        build_preset()

        return mainframe

    def build_graphframe(self, root: ttk.Notebook):
        """
        GUI front end
        Constructing graphing frame - old GUI
        """
        mainframe = ttk.Frame(root, padding="10 10", relief='flat')
        root.add(mainframe, text="Graphing [F5]")
        # for i in range(12):
        #     mainframe.columnconfigure(i, weight=1)
        # for i in (1, 8):
        #     mainframe.rowconfigure(i, weight=1)
        mainframe.rowconfigure(8, weight=1)

        temp = ttk.Button(mainframe, text='Back', command=lambda: self.notebook.select(0),
                          name='more_connect_btn', width=10)
        temp.grid(column=0, row=0 ,sticky='nw')

        # self.graphs['adv'] = self.main_elements['dyno_plots'].add_plot(
        #     mainframe, 6.2, 3.2, 'adv',
        #     2, True, 'grid', self.dyno,
        #     x_combo=self.x_combo_var,
        #     y_0=self.y_params_var,
        #     y_1=self.y_params_var,
        #     graph_params=self.graph_params,
        #     graph='adv'
        # )
        self.graphs['adv'] = DynoPlot(mainframe, 6.2, 3.2, 'adv',
                                      2, True, 'grid', self.dyno,
                                      x_combo=self.x_combo_var,
                                      y_0=self.y_params_var,
                                      y_1=self.y_params_var,
                                      graph_params=self.graph_params)

        return mainframe

    # def build_advanced_frame(self, root: ttk.Notebook):
    #     """
    #     GUI front end
    #     Constructing advanced option tab - old GUI
    #     """
    #     mainframe = ttk.Frame(root, padding="400 10", relief='flat')
    #     root.add(mainframe, text="Advanced [F6]")
    #     for i in (1, 2, 3):
    #         mainframe.columnconfigure(i, weight=1)
    #
    #     # label_title = ttk.Label(mainframe, text="ASI DynoModule Advanced Options", background='#5DA01D', anchor='center')
    #     # label_title.grid(column=0, row=0, columnspan=5, sticky='news')
    #     # ttk.Separator(mainframe).grid(columnspan=5, column=0, row=1, sticky='we', pady=5)
    #
    #     temp = ttk.Button(mainframe, text='Back', command=lambda: self.notebook.select(0),
    #                       name='more_connect_btn', width=10)
    #     temp.place(x=5, y=5, anchor='nw')
    #
    #     ttk.Label(mainframe, text='Load Firmware:').grid(column=1, row=2, sticky='e', padx=10)
    #     ttk.Button(mainframe, text='DUT', command=self._load_firmware_dut, name='dut_firmware_btn').grid(
    #         column=2, row=2, sticky='we')
    #     ttk.Button(mainframe, text='BRK', command=self._load_firmware_brk, name='brk_firmware_btn').grid(
    #         column=3, row=2, sticky='we')
    #
    #     ttk.Label(mainframe, text='Clear Text:').grid(column=1, row=4, sticky='e', padx=10)
    #     ttk.Button(mainframe, text='Output', command=self._clear_output, name='clear_output_btn').grid(
    #         column=2, row=4, sticky='we')
    #     ttk.Button(mainframe, text='Error', command=self._clear_error, name='clear_error_btn').grid(
    #         column=3, row=4, sticky='we')
    #
    #     ttk.Label(mainframe, text='Motor Discovery:').grid(column=1, row=5, sticky='e', padx=10)
    #     ttk.Button(mainframe, text="DUT Motor Disco. Mode 9", command=lambda: self._dut_motor_discovery(9),
    #                name='dut_motor_discovery_btn_3').grid(
    #         column=2, row=5, sticky='we')
    #     ttk.Button(mainframe, text="BRK Motor Disco. Mode 9", command=lambda: self._brk_motor_discovery(9),
    #                name='brk_motor_discovery_btn_3').grid(
    #         column=3, row=5, sticky='we')
    #
    #     ttk.Label(mainframe, text='Reset Configuration List from File:').grid(column=1, row=6, sticky='e', padx=10)
    #     ttk.Button(mainframe, text="Reset from File", command=self._reset_configs, name='reset_configs_btn').grid(
    #         column=2, row=6, sticky='we')
    #
    #     ttk.Label(mainframe, text='CAN Interface (beta)').grid(column=1, row=7, sticky='e', padx=10)
    #     ttk.Button(mainframe, text="Launch", command=self._can_interface, name='can_interface_btn').grid(
    #         column=2, row=7, sticky='we')
    #
    #     ttk.Label(mainframe, text='BACDoor Mode').grid(column=1, row=8, sticky='e', padx=10)
    #     ttk.Button(mainframe, textvariable=self.bac_2_bac, command=self._bac_2_bac, name='bac2bac_btn').grid(
    #         column=2, row=8, sticky='we')
    #
    #     ttk.Label(mainframe, text='Status Bar').grid(column=1, row=9, sticky='e', padx=10)
    #     ttk.Button(mainframe, text='Toggle', command=self.toggle_status_bar, name='status_bar_btn').grid(
    #         column=2, row=9, sticky='we')
    #
    #     ttk.Label(mainframe, text='Access Level').grid(column=1, row=10, sticky='e', padx=10)
    #     temp_frame = Frame(mainframe, relief='flat', background='gray')
    #     temp_frame.grid(column=2, row=10, sticky='w')
    #     temp = ttk.Button(temp_frame, text=0, width=5,
    #                       command=lambda : self._advanced_access_level(0))
    #     temp.grid(column=0, row=0)
    #     temp = ttk.Button(temp_frame, text=1, width=5,
    #                       command=lambda : self._advanced_access_level(1))
    #     temp.grid(column=1, row=0)
    #     temp = ttk.Button(temp_frame, text=2, width=5,
    #                       command=lambda : self._advanced_access_level(2))
    #     temp.grid(column=2, row=0)
    #     temp = ttk.Button(temp_frame, text=3, width=5,
    #                       command=lambda : self._advanced_access_level(3))
    #     temp.grid(column=3, row=0)
    #     temp = ttk.Button(temp_frame, text=4, width=5,
    #                       command=lambda : self._advanced_access_level(4))
    #     temp.grid(column=4, row=0)
    #
    #     ttk.Label(mainframe, text='Reset Can Move:').grid(column=1, row=11, sticky='e', padx=10)
    #     ttk.Button(mainframe, text='DUT', command=lambda: self._reset_can_move(1), name='dut_can_move_btn').grid(
    #         column=2, row=11, sticky='we')
    #     ttk.Button(mainframe, text='BRK', command=lambda: self._reset_can_move(2), name='brk_can_move_btn').grid(
    #         column=3, row=11, sticky='we')
    #
    #     return mainframe
    #
    # def build_option_frame(self, root: ttk.Notebook):
    #     """
    #     GUI front end
    #     Constructing options tab - old GUI
    #     """
    #     mainframe = ttk.Frame(root, padding="400 10", relief='flat')
    #     root.add(mainframe, text="Option [F7]")
    #     for i in (1, 2, 3):
    #         mainframe.columnconfigure(i, weight=1)
    #
    #     # label_title = ttk.Label(mainframe, text="ASI DynoModule Options", background='#5DA01D', anchor='center')
    #     # label_title.grid(column=0, row=0, columnspan=4, sticky='news')
    #     # ttk.Separator(mainframe).grid(columnspan=4, column=0, row=1, sticky='we', pady=5)
    #
    #     temp = ttk.Button(mainframe, text='Back',
    #                       command=lambda: self.notebook.select(0),
    #                       name='more_connect_btn', width=10)
    #     temp.place(x=5, y=5, anchor='nw')
    #
    #     ttk.Label(mainframe, text='DynoController Firmware:').grid(
    #         column=1, row=2, sticky='e', padx=10)
    #     ttk.Label(mainframe, text=__version__).grid(column=2, row=2, sticky='w')
    #
    #     ttk.Label(mainframe, text='Dark Mode').grid(column=1, row=3, sticky='e', padx=10)
    #     ttk.Button(mainframe, textvariable=self.dark_mode,
    #                command=self._dark_light_mode, name='dark_mode_btn').grid(
    #         column=2, row=3, sticky='w')
    #
    #     ttk.Label(mainframe, text='Font Size').grid(column=1, row=4, sticky='e', padx=10)
    #     Entry(mainframe, textvariable=self.font_size, name='font_size_entry',
    #           font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
    #         column=2, row=4, sticky='we')
    #     mainframe.children['font_size_entry'].bind('<Return>', self._update_font_size)
    #     ToolTip(mainframe.children['font_size_entry'], msg='Resize status bar element to update', delay=TOOLTIP_DELAY)
    #
    #     ttk.Label(mainframe, text='Show/Hide Outputs').grid(column=1, row=5, sticky='e', padx=10)
    #     ttk.Button(mainframe, textvariable=self.output_toggle, command=self._output_toggle, name='output_toggle_btn').grid(
    #         column=2, row=5, sticky='w')
    #
    #     ttk.Label(mainframe, text='Enable Email Notification').grid(column=1, row=6, sticky='e', padx=10)
    #     ttk.Checkbutton(mainframe, variable=self.enable_email, onvalue=True, name='enable_email_check').grid(
    #         column=2, row=6, sticky='w')
    #
    #     ttk.Label(mainframe, text='Enable Email Notification for Interrupts').grid(column=1, row=7, sticky='e', padx=10)
    #     ttk.Checkbutton(mainframe, variable=self.enable_int_email, onvalue=True, name='enable_int_email_check').grid(
    #         column=2, row=7, sticky='w')
    #
    #     ttk.Label(mainframe, text='Resize').grid(column=1, row=8, sticky='e', padx=10)
    #     ttk.Button(mainframe, text='Set', command=lambda : self.root.geometry('1920x1017'),
    #                name='resize_root_btn').grid(
    #         column=2, row=8, sticky='w')
    #
    #     return mainframe

    def build_home_menu(self):
        self.root.option_add('*tearOff', FALSE)

        self.main_elements['home_menu'] = Menu(self.root)
        self.root['menu'] = self.main_elements['home_menu']

        option_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_option'] = option_menu
        advanced_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_advanced'] = advanced_menu
        motor_discovery_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_motor_discovery'] = motor_discovery_menu
        access_level_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_access_level'] = access_level_menu
        dut_md_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_motor_discovery_dut'] = access_level_menu
        brk_md_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_motor_discovery_brk'] = access_level_menu
        can_move_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_can_move'] = can_move_menu
        bootload_menu = Menu(self.main_elements['home_menu'])
        self.main_elements['menu_bootload'] = bootload_menu

        self.main_elements['home_menu'].add_cascade(menu=option_menu, label='Options',
                                                    font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        # Options
        option_menu.add_command(label='Dark Mode', command=self._dark_light_mode,
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        option_menu.add_command(label='Resize', command=self._resize_hd,
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        option_menu.add_checkbutton(label='Enable Email Notification',
                                    variable=self.enable_email, onvalue=True, offvalue=False,
                                    font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        option_menu.add_checkbutton(label='Enable Email Notification for Interrupts',
                                    variable=self.enable_int_email, onvalue=True, offvalue=False,
                                    font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        # Advanced
        self.main_elements['home_menu'].add_cascade(menu=advanced_menu, label='Advanced',
                                                    font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        advanced_menu.add_command(label='Reset Config List', command=self._reset_configs,
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        advanced_menu.add_command(label='CAN Interface (beta)', command=self._can_interface,
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        advanced_menu.add_command(label='Toggle Status Bar', command=self.toggle_status_bar,
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        # Motor discovery
        advanced_menu.add_cascade(menu=motor_discovery_menu, label='Motor Discovery',
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        motor_discovery_menu.add_cascade(menu=dut_md_menu, label='DUT',
                                         font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        motor_discovery_menu.add_cascade(menu=brk_md_menu, label='BRK',
                                         font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        dut_md_menu.add_command(label='1', command=lambda: self._gui_motor_discovery(1, 1),
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        dut_md_menu.add_command(label='2', command=lambda: self._gui_motor_discovery(1, 2),
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        dut_md_menu.add_command(label='9', command=lambda: self._gui_motor_discovery(1, 9),
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        brk_md_menu.add_command(label='1', command=lambda: self._gui_motor_discovery(2, 1),
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        brk_md_menu.add_command(label='2', command=lambda: self._gui_motor_discovery(2, 2),
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        brk_md_menu.add_command(label='9', command=lambda: self._gui_motor_discovery(2, 9),
                                font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        # Access level
        advanced_menu.add_cascade(menu=access_level_menu, label='Access Level',
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        access_level_menu.add_command(label='0', command=lambda : self._advanced_access_level(0),
                                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        access_level_menu.add_command(label='1', command=lambda : self._advanced_access_level(1),
                                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        access_level_menu.add_command(label='2', command=lambda : self._advanced_access_level(2),
                                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        access_level_menu.add_command(label='3', command=lambda : self._advanced_access_level(3),
                                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        access_level_menu.add_command(label='4', command=lambda : self._advanced_access_level(4),
                                      font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        # Reset can move
        advanced_menu.add_cascade(menu=can_move_menu, label='Reset can move',
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        can_move_menu.add_command(label='DUT', command=lambda: self._reset_can_move(1),
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        can_move_menu.add_command(label='BRK', command=lambda: self._reset_can_move(2),
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        # Bootload
        advanced_menu.add_cascade(menu=bootload_menu, label='Bootloader',
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        bootload_menu.add_command(label="DUT", command=self._load_firmware_dut,
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        bootload_menu.add_command(label="BRK", command=self._load_firmware_brk,
                                  font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

    def build_out_menu(self):

        self.main_elements['out_menu'] = Menu(self.root)
        self.out_level['menu'] = self.main_elements['out_menu']

        clear_menu = Menu(self.main_elements['out_menu'])
        self.main_elements['menu_clear_text'] = clear_menu
        self.main_elements['out_menu'].add_cascade(menu=clear_menu, label='Clear Text',
                                                   font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

        # Clear text
        clear_menu.add_command(label='Output', command=self._clear_output,
                               font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        clear_menu.add_command(label='Error', command=self._clear_error,
                               font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')

    def build_status_bar(self):
        """
        GUI front end 
        Constructing status bar
        """
        logging.info("Creating status bar")
        status_level = Toplevel(self.root)
        status_level.geometry(f'{self.width.get()}x150+10+10')
        status_level.resizable(True, True)
        status_level.columnconfigure(0, weight=1)
        status_level.rowconfigure(2, weight=1)
        status_level.protocol("WM_DELETE_WINDOW", self.toggle_status_bar)

        mainframe = Frame(status_level, relief='flat', height=150)
        paned_status = PanedWindow(mainframe, borderwidth=5, background="#5DA01D", name='status_pane', handlesize=5)
        paned_status.pack(fill='both', expand=True)

        dut_label = Label(mainframe, text='DUT', background='#ccccff')
        self.dut_status_frame = ttk.LabelFrame(paned_status, padding=2, labelwidget=dut_label, labelanchor='n', style='dut.TLabelframe')
        for i in range(10):
            self.dut_status_frame.columnconfigure(i, weight=1)

        brk_label = Label(mainframe, text="BRK", background='#ccffcc')
        self.brk_status_frame = ttk.LabelFrame(paned_status, labelwidget=brk_label, padding=2, labelanchor='n', style='brk.TLabelframe')
        for i in range(10):
            self.brk_status_frame.columnconfigure(i, weight=1)

        yoko_label = Label(mainframe, text="Yokogawa", background='#ffffcc')
        self.yoko_status_frame = ttk.LabelFrame(paned_status, padding=2, labelwidget=yoko_label, labelanchor='n', style='yoko.TLabelframe')
        for i in range(10):
            self.yoko_status_frame.columnconfigure(i, weight=1)

        # self.test_status_frame = ttk.LabelFrame(paned_status, padding=2, text="Test", labelanchor='n')
        # paned_status.add(self.test_status_frame)

        self.status_bar = mainframe
        self._init_status_bar()
        self.status_bar.grid(column=0, row=2, sticky='news', columnspan=6)
        if self.dyno:
            self._start_status_thread()
        # return mainframe

    def _init_status_bar(self):
        """
        GUI front end
        Initializing status bar content
        """
        status_params = parse_etree(f"{ROOT_DIR}/status_parameters.xml")
        for controller in ['DUT', 'BRK', 'ABB', 'YOKO']:
            # temp = []
            # for element in status_params.findall(f"{controller}/Name"):
            #     temp.append(element.text)
            new_dict = {}
            for element in status_params.findall(f"{controller}/Name"):
                new_dict[element.text] = DoubleVar(value=0)
            # for key in temp:
            #     new_dict[key] = DoubleVar(value=0)
            self.status_params[controller] = new_dict
        # Driver status
        self._orphan(self.dut_status_frame.winfo_children())
        if self.dut_var.get():
            self.status_bar.children['status_pane'].add(self.dut_status_frame)
            self.status_bar.children['status_pane'].paneconfig(self.dut_status_frame, minsize=STATUS_MINSIZE_DUT)
            for i, param in enumerate(self.status_params['DUT']):
                temp = ttk.Label(self.dut_status_frame, text=f"{param}", name=f"status_dut_name_{i}", style='dut.TLabel')
                temp.grid(column=int(i / 2), row=2 + (i % 2) * 2)
                temp.bind('<Button-3>', self._status_menu)
                temp = ttk.Label(self.dut_status_frame, textvariable=self.status_params['DUT'][param], name=f"status_dut_value_{i}",
                                 style='dut.TLabel')
                temp.grid(column=int(i / 2), row=2 + (i % 2) * 2 + 1)
                temp.bind('<Button-3>', self._status_menu)
        else:
            self.status_bar.children['status_pane'].remove(self.dut_status_frame)

        # Brake status
        self._orphan(self.brk_status_frame.winfo_children())
        if self.brk_var.get():
            self.status_bar.children['status_pane'].add(self.brk_status_frame)
            if self.abb.get():
                self.status_bar.children['status_pane'].paneconfig(self.brk_status_frame, minsize=STATUS_MINSIZE_ABB)
                for i, param in enumerate(self.status_params['ABB']):
                    temp = ttk.Label(self.brk_status_frame, text=f"{param}", name=f"status_abb_name_{i}", style='brk.TLabel')
                    temp.grid(column=int(i / 2), row=2 + (i % 2) * 2)
                    # temp.bind('<Button-3>', self._param_menu)
                    temp = ttk.Label(self.brk_status_frame, textvariable=self.status_params['ABB'][param],
                                     name=f"status_abb_value_{i}", style='brk.TLabel')
                    temp.grid(column=int(i / 2), row=2 + (i % 2) * 2 + 1)
                    # temp.bind('<Button-3>', self._param_menu)
            else:
                self.status_bar.children['status_pane'].paneconfig(self.brk_status_frame, minsize=STATUS_MINSIZE_BRK)
                for i, param in enumerate(self.status_params['BRK']):
                    temp = ttk.Label(self.brk_status_frame, text=f"{param}", name=f"status_brk_name_{i}", style='brk.TLabel')
                    temp.grid(column=int(i / 2), row=2 + (i % 2) * 2)
                    temp.bind('<Button-3>', self._status_menu)
                    temp = ttk.Label(self.brk_status_frame, textvariable=self.status_params['BRK'][param],
                                     name=f"status_brk_value_{i}", style='brk.TLabel')
                    temp.grid(column=int(i / 2), row=2 + (i % 2) * 2 + 1)
                    temp.bind('<Button-3>', self._status_menu)
        else:
            self.status_bar.children['status_pane'].remove(self.brk_status_frame)

        # YOKO status
        self._orphan(self.yoko_status_frame.winfo_children())
        if self.yoko_var.get():
            self.status_bar.children['status_pane'].add(self.yoko_status_frame)
            self.status_bar.children['status_pane'].paneconfig(self.yoko_status_frame, minsize=STATUS_MINSIZE_YOKO)
            for i, param in enumerate(self.status_params['YOKO']):
                temp = ttk.Label(self.yoko_status_frame, text=f"{param}", name=f"status_yoko_name_{i}", style='yoko.TLabel')
                temp.grid(column=int(i / 2), row=2 + (i % 2) * 2)
                temp.bind('<Button-3>', self._status_menu)
                temp = ttk.Label(self.yoko_status_frame, textvariable=self.status_params['YOKO'][param],
                                 name=f"status_yoko_value_{i}", style='yoko.TLabel')
                temp.grid(column=int(i / 2), row=2 + (i % 2) * 2 + 1)
                temp.bind('<Button-3>', self._status_menu)
        else:
            self.status_bar.children['status_pane'].remove(self.yoko_status_frame)

        # TEST status
        # self._orphan(self.test_status_frame.winfo_children())
        # self.status_bar.children['status_pane'].paneconfig(self.test_status_frame, minsize=STATUS_MINSIZE_TEST)
        # for i, param in enumerate(self.status_params['TEST']):
        #     temp = ttk.Label(self.test_status_frame, text=f"{param}", name=f"status_test_name_{i}")
        #     temp.grid(column=int(i / 2), row=2 + (i % 2) * 2)
        #     # temp.bind('<Button-3>', self._status_menu)
        #     temp = ttk.Label(self.test_status_frame, textvariable=self.status_params['TEST'][param], name=f"status_test_value_{i}")
        #     temp.grid(column=int(i / 2), row=2 + (i % 2) * 2 + 1)
        #     # temp.bind('<Button-3>', self._status_menu)

    def _start_status_thread(self):
        """
        GUI back end 
        Starting thread for status bar
        """
        if self.status_bar:
            self._init_status_bar()
            self.updating = True
            self.status_thread = Thread(target=self._update_status)
            self.status_thread.start()
            logging.info("Status thread started")

    def _stop_status_thread(self):
        """
        GUI back end 
        Stopping thread for status bar
        """
        if self.updating:
            self.updating = False
            # self.status_thread.join()
            self.status_thread = None
            logging.info("Status thread stopped")

    def _connection_check(self, device):
        """
        GUI backend + Dyno conditions
        Checks Dyno devices' connection
        """
        if device == 'dut':  # DUT connection check
            if self.dyno and self.dyno.devices[1].connected:
                return True
            else:
                self.connection_status[0].set(False)
                print("Error: Bad Connection with driver!")
                # logging.info("DUT Connection lost")
                self._main_connect()
                return False
        elif device == 'abb':  # ABB connection check
            if not self.dyno.devices[2].connected:
                print("Error: Bad Connection with brake (ABB)!")
                # logging.info("BRK Connection lost (ABB)")
                self._main_connect()
                return False
            else:
                return True
        elif device == 'brk':  # BRK connection check
            if not self.dyno.devices[2].connected:
                print("Error: Bad Connection with brake!")
                # logging.info("BRK Connection lost")
                self._main_connect()
                return False
            else:
                return True
        elif device == 'yoko':  # Yokogawa connection check
            if not hasattr(self.dyno.devices[PA], 'device'):
                print("Error: Bad Connection with YOKOGAWA! Please retry!")
                # logging.info("YOKOGAWA Connection lost")
                self._main_connect()
                return False
            else:
                return True

    def _update_status(self):
        """
        GUI back end + Dyno data grabbing
        Thread target
        Target method for status bar thread
        Speed check moved to live_thread_faults
        """
        while self.updating:
            sleep(1)
            # DUT status

            if self.connection_status[0].get() and self.updating:
                # self._connection_check('dut')  # Check connection
                # # Speed check
                # try:
                #     if self.dyno.devices[1].get_rpm() > self.speed_limit_upper.get():
                #         logging.warning("DUT over Upper Speed Limit")
                #         self.speed_limit_frame.children['upper_limit'].config(background='red', foreground='white')
                #         if self.enable_email.get() and self.enable_int_email.get():
                #             over_speed_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")
                #         if self.testing:
                #             self.sigint_handler()
                #         else:
                #             self._dyno_stop()
                #     elif self.dyno.devices[1].get_rpm() < self.speed_limit_lower.get():
                #         logging.warning("DUT under Lower Speed Limit")
                #         self.speed_limit_frame.children['lower_limit'].config(background='red', foreground='white')
                #         if self.enable_email.get() and self.enable_int_email.get():
                #             over_speed_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")
                #         if self.testing:
                #             self.sigint_handler()
                #         else:
                #             self._dyno_stop()
                #     else:
                #         self.speed_limit_frame.children['upper_limit'].config(background='white', foreground='red')
                #         self.speed_limit_frame.children['lower_limit'].config(background='white', foreground='red')
                # except (AttributeError, TypeError, CommLossError):
                #     pass


                # update status
                for param in self.status_params['DUT']:
                    try:
                        self._connection_check('dut')
                        self.status_params['DUT'][param].set(self.dyno.devices[1].log_params[param].Value)
                        # if self.dyno.is_logging_enabled():
                        #     self.status_params['DUT'][param].set(self.dyno.devices[1].log_params[param].Value)
                        # else:
                        #     self.status_params['DUT'][param].set(self.dyno.devices[1].read(param))
                    except (AttributeError, CommLossError):
                        pass
            # BRK status
            if self.connection_status[1].get() and self.updating:
                if self.abb.get():
                    # self._connection_check('abb')
                    for param in self.status_params['ABB']:
                        try:
                            self._connection_check('abb')
                            self.status_params['ABB'][param].set(f'{self.dyno.devices[2].read(param):.2f}')
                        except AttributeError:
                            pass
                else:
                    # self._connection_check('brk')
                    for param in self.status_params['BRK']:
                        try:
                            self._connection_check('brk')
                            self.status_params['BRK'][param].set(self.dyno.devices[2].log_params[param].Value)
                            # if self.dyno.is_logging_enabled():
                            #     self.status_params['BRK'][param].set(self.dyno.devices[2].log_params[param].Value)
                            # else:
                            #     self.status_params['BRK'][param].set(self.dyno.devices[2].read(param))
                        except (AttributeError, CommLossError):
                            pass
            # YOKO Status
            if self.connection_status[2].get() and self.updating:
                # check connection
                # self._connection_check('yoko')

                # try:
                #     if self.dyno.devices[PA].getMeasurement('Motor Speed') > self.speed_limit_upper.get():
                #         logging.warning("YOKO RPM out of range")
                #         self.speed_limit_frame.children['upper_limit'].config(background='red', foreground='white')
                #         if self.enable_email.get() and self.enable_int_email.get():
                #             over_speed_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")
                #         if self.testing:
                #             self.sigint_handler()
                #         else:
                #             self._dyno_stop()
                #     else:
                #         self.speed_limit_frame.children['upper_limit'].config(background='white', foreground='red')
                # except (AttributeError, TypeError):
                #     pass
                for param in self.status_params['YOKO']:
                    try:
                        self._connection_check('yoko')
                        self.status_params['YOKO'][param].set(self.dyno.devices[PA].getMeasurement(param))
                    except AttributeError:
                        pass
                        

        logging.info('End of status_update')

    def _status_menu(self, event=None):
        """
        GUI front end
        Build right click menu for +/- parameter on status bar
        """
        if self.connection_condition.get() == "\nCONNECT\n":
            return
        m = Menu(self.root, tearoff=0)
        m.add_command(label='Add', command=lambda: self._popup_add_status(event))
        m.add_command(label='Delete', command=lambda: self._del_status(event))

        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _popup_add_status(self, event=None):
        """
        GUI front end 
        Build pop up window for status bar
        """
        top = Toplevel(self.root)
        popup = Frame(top)
        popup.grid(column=0, row=0)
        param_list = Listbox(popup, width=50, height=20, exportselection=False, selectmode='multiple')
        temp = []
        index = int(str(event.widget).split(".")[-1].split("_")[-1])
        if event.widget.master == self.dut_status_frame:
            if hasattr(self, 'dyno') and self.dyno.devices[1] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_status(top, index, param_list.curselection(),
                                                                           'DUT')).grid(column=0, row=2)
            for param in self.dyno.devices[1].log_params:
                temp.append(self.dyno.devices[1].log_params[param].Name)
        elif event.widget.master == self.brk_status_frame:
            if hasattr(self, 'dyno') and self.dyno.devices[2] is None:
                top.destroy()
                return
            if not self.abb.get():
                ttk.Button(popup, text='Add', command=lambda: self._add_status(top, index, param_list.curselection(),
                                                                               'BRK')).grid(column=0, row=2)
            for param in self.dyno.devices[2].log_params:
                temp.append(self.dyno.devices[2].log_params[param].Name)
        elif event.widget.master == self.yoko_status_frame:
            if hasattr(self, 'dyno') and self.dyno.devices[PA] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_status(top, index, param_list.curselection(),
                                                                           'YOKO')).grid(column=0, row=2)
            for param in self.dyno.devices[PA].log_params:
                temp.append(self.dyno.devices[PA].log_params[param].Name)
        names = StringVar(value=temp)
        param_list.configure(listvariable=names)
        param_list.grid(column=0, row=1, columnspan=2, sticky='news')
        ttk.Button(popup, text='Cancel', command=top.destroy).grid(column=1, row=2)

    def _add_status(self, top, index, names, controller):
        """
        GUI backend
        Add parameter to parameter list
        """
        if self.dyno is not None:
            if controller == "DUT":
                params_to_add = []
                for i in names:
                    for j, name in enumerate(self.dyno.devices[1].log_params):
                        if i == j:
                            params_to_add.append(self.dyno.devices[1].log_params[name].Name)
            elif controller == "BRK" and isinstance(self.dyno.devices[2], ASIController):
                params_to_add = []
                for i in names:
                    for j, name in enumerate(self.dyno.devices[2].log_params):
                        if i == j:
                            params_to_add.append(self.dyno.devices[2].log_params[name].Name)
            elif controller == 'YOKO':
                params_to_add = []
                for i in names:
                    for j, name in enumerate(self.dyno.devices[PA].log_params):
                        if i == j:
                            params_to_add.append(self.dyno.devices[PA].log_params[name].Name)
            old_tree = ET.parse(f"{ROOT_DIR}/status_parameters.xml").getroot()
            old = {}
            for temp in ['DUT', 'BRK', 'YOKO', 'ABB']:
                old[temp] = old_tree.find(temp)
            new_tree = ET.Element('Parameters')
            for c in ['DUT', 'BRK', 'YOKO', 'ABB']:
                temp = ET.SubElement(new_tree, c)
                for i, param in enumerate(old[c].findall('Name')):
                    if i == index and controller == c:
                        for name in params_to_add:
                            ET.SubElement(temp, 'Name').text = name
                    ET.SubElement(temp, 'Name').text = param.text
            indent(new_tree)
            new_tree = ET.ElementTree(new_tree)
            new_tree.write(f"{ROOT_DIR}/status_parameters.xml")
            logging.info(f"\'{params_to_add}\' added to DUT status bar")
            self._init_status_bar()
            top.destroy()

    def _del_status(self, event=None):
        """
        GUI backend 
        Delete parameter from parameter list
        """
        if self.dyno is not None:
            index = int(str(event.widget).split(".")[-1].split("_")[-1])
            c = str(event.widget).split('.')[-1].split('_')[1]
            old_tree = ET.parse(f"{ROOT_DIR}/status_parameters.xml").getroot()
            old = {}
            for temp in ['DUT', 'BRK', 'YOKO', 'ABB']:
                old[temp] = old_tree.find(temp)
            new_tree = ET.Element('Parameters')
            for controller in ['DUT', 'BRK', 'YOKO', 'ABB']:
                temp = ET.SubElement(new_tree, controller)
                for i, param in enumerate(old[controller].findall('Name')):
                    if i == index and controller.lower() == c:
                        continue
                    ET.SubElement(temp, 'Name').text = param.text
            temp = ET.SubElement(new_tree, 'ABB')
            ET.SubElement(temp, 'Name').text = 'Torque'

            indent(new_tree)
            new_tree = ET.ElementTree(new_tree)
            new_tree.write(f"{ROOT_DIR}/status_parameters.xml")
            logging.info('Delete complete')
            self._init_status_bar()

    def test_inputs(self, event=None):
        """
        GUI front end
        Change custom inputs based on chosen test
        """
        if self.test.get() == "Production/Rundown" or self.test.get() == "Validation":
            self.test_note.set("Motor: ")
            self.test_tab.children['test_btn_frame'].children['guide_btn'].grid(
                column=7, row=8, sticky='we')
            self.test_tab.children['test_btn_frame'].children['zoom_check'].grid(
                column=0, row=14, columnspan=4, sticky='e')
            self.test_tab.children['test_btn_frame'].children['zoom_lo_entry'].grid(
                column=4, row=14, sticky='e', pady=5)
            self.test_tab.children['test_btn_frame'].children['zoom_label'].grid(
                column=5, row=14)
            self.test_tab.children['test_btn_frame'].children['zoom_hi_entry'].grid(
                column=6, row=14, sticky='we')
            self.test_tab.children['test_btn_frame'].children['zoom_label1'].grid(
                column=7, row=14, sticky='w')

            self.test_tab.children['test_btn_frame'].children['effi_target_label'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['effi_motor_check'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['effi_controller_check'].grid_remove()

            # main
            self.main_elements['main_test_zoom_frame'].grid(column=0, row=5, sticky='ws',
                                                            padx='10', pady=5)
            self.main_elements['main_test_efficiency_map'].grid_forget()
            # self.main_elements['main_test_zoom'].place(relx=0.02, rely=0.77, anchor='nw')
            # self.main_elements['main_test_zoom_lo'].place(relx=0.3, rely=0.77, anchor='nw')
            # self.main_elements['main_test_zoom_lo_unit'].place(relx=0.45, rely=0.77, anchor='nw')
            # self.main_elements['main_test_zoom_hi'].place(relx=0.55, rely=0.77, anchor='nw')
            # self.main_elements['main_test_zoom_hi_unit'].place(relx=0.7, rely=0.77, anchor='nw')77, anchor='nw')
            # self.main_elements['effi_target_label'].place_forget()
            # self.main_elements['effi_motor_check'].place_forget()
            # self.main_elements['effi_controller_check'].place_forget()

        elif self.test.get() == 'Efficiency Map':
            self.test_note.set("Motor: ")

            self.test_tab.children['test_btn_frame'].children['effi_target_label'].grid(
                column=0, row=14, columnspan=4, sticky='e')
            self.test_tab.children['test_btn_frame'].children['effi_motor_check'].grid(
                column=4, row=14, sticky='e', pady=5)
            self.test_tab.children['test_btn_frame'].children['effi_controller_check'].grid(
                column=5, row=14, sticky='e', pady=5)

            self.test_tab.children['test_btn_frame'].children['guide_btn'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_check'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_lo_entry'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_label'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_hi_entry'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_label1'].grid_remove()

            # main

            self.main_elements['main_test_zoom_frame'].grid_forget()
            self.main_elements['main_test_efficiency_map'].grid(column=0, row=6, sticky='ws',
                                                                padx='10', pady=5)
            # self.main_elements['main_test_zoom'].place_forget()
            # self.main_elements['main_test_zoom_lo'].place_forget()
            # self.main_elements['main_test_zoom_lo_unit'].place_forget()
            # self.main_elements['main_test_zoom_hi'].place_forget()
            # self.main_elements['main_test_zoom_hi_unit'].place_forget()
            #
            # self.main_elements['effi_target_label'].place(relx=0.02, rely=0.77, anchor='nw')
            # self.main_elements['effi_motor_check'].place(relx=0.35, rely=0.77, anchor='nw')
            # self.main_elements['effi_controller_check'].place(relx=0.55, rely=0.77, anchor='nw')

        else:
            self.test_note.set("Test Note: ")
            self.test_tab.children['test_btn_frame'].children['guide_btn'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_check'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_lo_entry'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_label'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_hi_entry'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['zoom_label1'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['effi_target_label'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['effi_motor_check'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['effi_controller_check'].grid_remove()

            # main
            self.main_elements['main_test_zoom_frame'].grid_forget()
            self.main_elements['main_test_efficiency_map'].grid_forget()
            # self.main_elements['main_test_zoom'].place_forget()
            # self.main_elements['main_test_zoom_lo'].place_forget()
            # self.main_elements['main_test_zoom_lo_unit'].place_forget()
            # self.main_elements['main_test_zoom_hi'].place_forget()
            # self.main_elements['main_test_zoom_hi_unit'].place_forget()
            # self.main_elements['effi_target_label'].place_forget()
            # self.main_elements['effi_motor_check'].place_forget()
            # self.main_elements['effi_controller_check'].place_forget()

        if self.test.get() == "Life Test/Cyclic Test":
            self.test_tab.children['test_btn_frame'].children['sn_label_2'].grid(
                column=6, row=10)
            self.test_tab.children['test_btn_frame'].children['sn_entry_2'].grid(
                column=7, row=10)
            self.test_tab.children['test_btn_frame'].children['barcode_2_label'].grid(
                column=0, row=12)
            self.test_tab.children['test_btn_frame'].children['barcode_2_entry'].grid(
                column=1, row=12, columnspan=8, sticky='we')
            self.test_tab.children['test_btn_frame'].children['progress_check'].grid(
                column=0, row=14, columnspan=4, sticky='e')
            self.test_tab.children['test_btn_frame'].children['email_progress_entry'].grid(
                column=4, row=14, sticky='e', pady=5, columnspan=2)
            self.test_tab.children['test_btn_frame'].children['progress_label'].grid(
                column=6, row=14, columnspan=2, sticky='w')

            # main
            self.main_elements['main_sn_2_label'].grid(column=2, row=0, sticky='w')
            self.main_elements['main_sn_2_entry'].grid(column=3, row=0, sticky='w', padx='50 10')
            self.main_elements['main_barcode_2_label'].grid(column=0, row=1, sticky='w', pady=5)
            self.main_elements['main_barcode_2_entry'].grid(column=1, row=1, sticky='w', padx=10, pady=5)
            # self.main_elements['main_sn_2_label'].place(relx=0.5, rely=0.47, anchor='nw')
            # self.main_elements['main_sn_2_entry'].place(relx=0.62, rely=0.47, anchor='nw')
            # self.main_elements['main_barcode_2_label'].place(relx=0.02, rely=0.77, anchor='nw')
            # self.main_elements['main_barcode_2_entry'].place(relx=0.18, rely=0.77, anchor='nw')

        else:
            self.test_tab.children['test_btn_frame'].children['sn_label_2'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['sn_entry_2'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['barcode_2_label'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['barcode_2_entry'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['progress_check'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['email_progress_entry'].grid_remove()
            self.test_tab.children['test_btn_frame'].children['progress_label'].grid_remove()

            # main
            self.main_elements['main_sn_2_label'].grid_forget()
            self.main_elements['main_sn_2_entry'].grid_forget()
            self.main_elements['main_barcode_2_label'].grid_forget()
            self.main_elements['main_barcode_2_entry'].grid_forget()
            # self.main_elements['main_sn_2_label'].place_forget()
            # self.main_elements['main_sn_2_entry'].place_forget()
            # self.main_elements['main_barcode_2_label'].place_forget()
            # self.main_elements['main_barcode_2_entry'].place_forget()

        self._populate_config_list()

    def controller_params_operation(self, frames, controllers, mode, widget=None):
        """
        GUI backend + Dyno data manipulation
        All-in-one function for controller tab BACDoor
        Manipulates Controller parameters - init/update/upload
        """
        if mode == CONTROL_PARAM_UPDATE:  # Update values
            for controller in controllers:
                for i in range(len(self.controller_params_raw.findall(f"{controller}/Name"))):
                    # if self.dyno.devices[1] is None and self.dyno.devices[2] is None:
                    #     break
                    try:
                        name = self.controller_params_raw.findall(f"{controller}/Name")[i].text
                        if controller in ["DUT", "DUT_EXT", "DUT_EXT_EXT"] and \
                                self.dyno and isinstance(self.dyno.devices[1], ASIController):
                            ans = self.dyno.devices[1].read(name)
                            ans = self._value_format(name, controller, ans)
                            if isinstance(ans, str):
                                self.controller_params[controller][name].set(ans)
                            elif f"{ans:.2f}".endswith('.00'):
                                self.controller_params[controller][name].set(f"{int(ans)}")
                            else:
                                self.controller_params[controller][name].set(f"{ans:.2f}")
                        elif (controller in ["BRK", "BRK_EXT", "BRK_EXT_EXT"] and
                              self.dyno and isinstance(self.dyno.devices[2], ASIController)) or \
                                (controller == "ABB" and isinstance(self.dyno.devices[2], AbbAcs800)):
                            ans = self.dyno.devices[2].read(name)
                            ans = self._value_format(name, controller, ans)
                            if f"{ans:.2f}".endswith('.00'):
                                self.controller_params[controller][name].set(f"{int(ans)}")
                            else:
                                self.controller_params[controller][name].set(f"{ans:.2f}")
                    except (KeyError, TypeError):
                        pass
        elif mode == CONTROL_PARAM_UPLOAD:  # Upload value
            if widget is None:   # from button, uploads all
                for controller in controllers:
                    if controller == "ABB" and self.dyno.devices[2] is not None:
                        if self.dyno.devices[2].mode == 'torque':
                            self.dyno.devices[2].set_torque(
                                _param_value_handler(self.controller_params[controller]["Torque"].get()))
                        elif self.dyno.devices[2].mode == 'speed':
                            self.dyno.devices[2].set_rpm(
                                _param_value_handler(self.controller_params[controller]["Speed"].get()))
                        continue
                        # if int(self.controller_params[controller]['Speed'].get()) == 0:
                        #     self.dyno.devices[2].torque_mode()
                        #     self.dyno.devices[2].set_torque(_param_value_handler(self.controller_params[controller]["Torque"].get()))
                        #     continue
                        # else:
                        #     self.dyno.devices[2].set_torque(0)
                        # if int(self.controller_params[controller]['Torque'].get()) == 0:
                        #     self.dyno.devices[2].speed_mode()
                        #     self.dyno.devices[2].set_rpm(_param_value_handler(self.controller_params[controller]['Speed'].get()))
                        #     continue
                        # else:
                        #     self.dyno.devices[2].set_rpm(0)
                    for i in range(len(self.controller_params_raw.findall(f"{controller}/Name"))):
                        try:
                            name = self.controller_params_raw.findall(f"{controller}/Name")[i].text
                            if controller in ["DUT", "DUT_EXT", "DUT_EXT_EXT"] and self.dyno.devices[1] is not None:
                                self.dyno.devices[1].write(name,
                                                    _param_value_handler(self.controller_params[controller][name].get(),
                                                                         self.dyno.devices[1].run_parameters[name].Scale))
                                # print(name)
                            elif self.dyno.devices[2] is not None:
                                if controller in ["BRK", "BRK_EXT", "BRK_EXT_EXT"]:
                                    self.dyno.devices[2].write(name,
                                                        _param_value_handler(self.controller_params[controller][name].get(),
                                                                             self.dyno.devices[2].run_parameters[name].Scale))
                        except (AttributeError, KeyError):
                            pass
            else:   # from 'Return' button, uploads only one value
                logging.info("Writing to %s", widget[0].cget("text"))
                if frames[0] in [self.dut_frame, self.dut_extra_frame, self.dut_extra_frame_1] and \
                        self.dyno.devices[1] is not None:  # DUT
                    try:
                        int(self.dyno.devices[1].run_parameters[widget[0].cget("text")].AccessLevel)
                    except TypeError:
                        self.dyno.devices[1].write(widget[0].cget("text"), float(widget[1].get()))
                    else:
                        if int(self.dyno.devices[1].run_parameters[widget[0].cget("text")].AccessLevel) > 2:
                            ans = messagebox.askokcancel("High Access Level",
                                                         "Parameter to write has greater access level than 2")
                            if not ans:
                                widget[1].delete(0, END)
                                widget[1].insert(0, self._value_format(widget[0].cget("text"), "DUT",
                                                                       self.dyno.devices[1].read(widget[0].cget("text"))))
                                return
                        if 'Parameter access code' not in widget[0].cget("text"):
                            self.dyno.devices[1].set_access_level(
                                int(self.dyno.devices[1].run_parameters[widget[0].cget("text")].AccessLevel))
                            self.dyno.devices[1].write(widget[0].cget("text"),
                                                _param_value_handler(widget[1].get(),
                                                                     self.dyno.devices[1].run_parameters[widget[0].cget("text")].Scale))
                            self.dyno.devices[1].set_access_level(0)
                        else:
                            self.dyno.devices[1].write(widget[0].cget("text"),
                                                _param_value_handler(widget[1].get(),
                                                                     self.dyno.devices[1].run_parameters[widget[0].cget("text")].Scale))
                        if frames[0] == self.dut_frame:
                            self.controller_params["DUT"][widget[0].cget("text")].set(widget[1].get())
                        elif frames[0] == self.dut_extra_frame:
                            self.controller_params["DUT_EXT"][widget[0].cget("text")].set(widget[1].get())
                        elif frames[0] == self.dut_extra_frame_1:
                            self.controller_params["DUT_EXT_EXT"][widget[0].cget("text")].set(widget[1].get())

                elif frames[0] in [self.brk_frame, self.brk_extra_frame, self.brk_extra_frame_1] and \
                        self.dyno.devices[2] is not None and \
                        isinstance(self.dyno.devices[2], ASIController):  # BRK
                    try:
                        int(self.dyno.devices[2].run_parameters[widget[0].cget("text")].AccessLevel)
                    except TypeError:
                        self.dyno.devices[2].write(widget[0].cget("text"), float(widget[1].get()))
                    else:
                        if int(self.dyno.devices[2].run_parameters[widget[0].cget("text")].AccessLevel) > 2:
                            ans = messagebox.askokcancel("High Access Level", "Parameter to write has greater access level than 2")
                            if not ans:
                                widget[1].delete(0, END)
                                widget[1].insert(0, f'{self.dyno.devices[2].read(widget[0].cget("text")):.2f}')
                                return
                        if 'Parameter access code' not in widget[0].cget("text"):
                            self.dyno.devices[2].set_access_level(int(self.dyno.devices[2].run_parameters[widget[0].cget("text")].AccessLevel))
                            self.dyno.devices[2].write(widget[0].cget("text"),
                                                _param_value_handler(widget[1].get(),
                                                                     self.dyno.devices[2].run_parameters[widget[0].cget("text")].Scale))
                            self.dyno.devices[2].set_access_level(0)
                        else:
                            self.dyno.devices[2].write(widget[0].cget("text"),
                                                _param_value_handler(widget[1].get(),
                                                                     self.dyno.devices[2].run_parameters[widget[0].cget("text")].Scale))
                        if frames[0] == self.brk_frame:
                            self.controller_params["BRK"][widget[0].cget("text")].set(widget[1].get())
                        elif frames[0] == self.brk_extra_frame:
                            self.controller_params["BRK_EXT"][widget[0].cget("text")].set(widget[1].get())
                        elif frames[0] == self.brk_extra_frame_1:
                            self.controller_params["BRK_EXT_EXT"][widget[0].cget("text")].set(widget[1].get())
        elif mode == CONTROL_PARAM_INIT:
            self.controller_params = {"DUT": {}, "BRK": {}, "ABB": {}, "DUT_EXT": {},
                                      "BRK_EXT": {}, "DUT_EXT_EXT": {}, "BRK_EXT_EXT": {}}
            for frame, controller in zip(frames, controllers):
                self._orphan(frame.winfo_children())
                temp = []
                for element in self.controller_params_raw.findall(f"{controller}/Name"):
                    temp.append(element.text)
                processed = []
                for name in temp:
                    if controller in ["DUT", "DUT_EXT", "DUT_EXT_EXT"] and \
                            self.dyno.devices[1] is not None and \
                            isinstance(self.dyno.devices[1], ASIController):
                        processed.append(self.dyno.devices[1].etree.find(f"//ParameterDescription[Name='%s']" % name))
                        self.dyno.devices[1].add_run_parameter(name)
                    elif controller in ["BRK", "BRK_EXT", "BRK_EXT_EXT"] and \
                            self.dyno.devices[2] is not None and \
                            isinstance(self.dyno.devices[2], ASIController):
                        processed.append(self.dyno.devices[2].etree.find(f"//ParameterDescription[Name='%s']" % name))
                        self.dyno.devices[2].add_run_parameter(name)
                    elif controller == "ABB" and \
                            self.dyno.devices[2] is not None and \
                            isinstance(self.dyno.devices[2], AbbAcs800):
                        processed.append(self.dyno.devices[2].etree.find("/ABB/ParameterDescription[Name='%s']" % name))
                for i in range(len(processed)):
                    # in case parameter names mismatch among different dictionaries
                    try:
                        name = processed[i].find('Name').text
                        try:
                            frame.children[f"ctrl_param_{controller}_{i}"]
                        except KeyError:
                            Label(frame, text=f"{name}", width=34,
                                  name=f"ctrl_param_{controller}_{i}", justify='right',
                                  font=f'{OPTION_FONT_NAME} 10',
                                  background=f'{"#ccccff" if "dut" in controller.lower() else "#ccffcc"}', pady=2).grid(
                                column=0, row=1 + i, sticky='we')
                            frame.children[f"ctrl_param_{controller}_{i}"].bind('<Button-3>', self._param_menu)
                            frame.children[f"ctrl_param_{controller}_{i}"].bind('<MouseWheel>', frame.master.master.on_mousewheel)
                            # frame.children[f"ctrl_param_{controller}_{i}"].bind("<B1-Motion>", self._drag_handler)
                            # frame.children[f"ctrl_param_{controller}_{i}"].bind("<ButtonRelease-1>", self._drop_handler)
                        # self.controller_params[controller].append(StringVar(value='0'))
                        try:
                            self.controller_params[controller][name]
                        except KeyError:
                            self.controller_params[controller][name] = StringVar(value='0')
                        try:
                            frame.children[f'ctrl_param_{controller}_{i}'].children[f'ctrl_param_{controller}_tt_{i}']
                        except KeyError:
                            pass
                            ToolTip(frame.children[f'ctrl_param_{controller}_{i}'],
                                    msg=processed[i].find('Description').text, delay=TOOLTIP_DELAY,
                                    name=f'ctrl_param_{controller}_tt_{i}', follow=False)
                        try:
                            frame.children[f"ctrl_param_{controller}_{i}_entry"]
                        except KeyError:
                            entry = Entry(frame, textvariable=self.controller_params[controller][name],
                                          width=16, name=f"ctrl_param_{controller}_{i}_entry",
                                          font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
                            entry.grid(column=1, row=1 + i, ipady=1)
                            entry.bind('<Return>', lambda e: self._controller_write(e))
                            entry.bind('<FocusIn>', lambda e: e.widget.select_range(0, END))
                            entry.bind('<Button-1>', lambda e: e.widget.select_range(0, END))
                        try:
                            frame.children[f"ctrl_param_{controller}_{i}_unit"]
                        except KeyError:
                            unit = processed[i].find('Units').text
                            Label(frame, text=unit, anchor='w',
                                  name=f"ctrl_param_{controller}_{i}_unit", pady=2,
                                  font=f'{OPTION_FONT_NAME} 10',
                                  background=f'{"#ccccff" if "dut" in controller.lower() else "#ccffcc"}').grid(
                                column=2, row=1 + i, sticky='w')
                            frame.children[f"ctrl_param_{controller}_{i}_unit"].bind('<MouseWheel>',
                                                                                     frame.master.master.on_mousewheel)
                            
                        
                    except (AttributeError, IndexError):
                        pass

    def _update_main(self, event=None):
        """
        GUI backend + dyno data read
        Update DUT/BRK parameters for home screen
        """
        if self.dyno and isinstance(self.dyno.devices[1], ASIController):
            for p in MOTOR_MAIN_PARAMETERS:
                self.main_parameters[f'dut_{p[0]}'].set(self.dyno.devices[1].read(p[0]))
            for p in MOTOR_HALLS:
                self.main_parameters[f'dut_{p}'].set(f'{self.dyno.devices[1].read(p):.1f}')

        if self.dyno and isinstance(self.dyno.devices[2], ASIController):
            for p in MOTOR_MAIN_PARAMETERS:
                self.main_parameters[f'brk_{p[0]}'].set(self.dyno.devices[2].read(p[0]))
            for p in MOTOR_HALLS:
                self.main_parameters[f'brk_{p}'].set(f'{self.dyno.devices[2].read(p):.1f}')

            self.main_parameters['brk_torque'].set(self.dyno.devices[2].read("Remote torque command"))

        if self.dyno and isinstance(self.dyno.devices[2], AbbAcs800):
            self.main_parameters['brk_torque'].set(self.dyno.devices[2].read("Torque"))

        self._controller_read()


    def _upload_main(self, event=None):
        """
        GUI backend + dyno data write
        Upload DUT/BRK parameters for home screen 
        """
        if self.dyno and isinstance(self.dyno.devices[1], ASIController):
            for p in MOTOR_MAIN_PARAMETERS:
                self.dyno.devices[1].write(p[0], float(self.main_parameters[f'dut_{p[0]}'].get()))
            for p in MOTOR_HALLS:
                self.dyno.devices[1].write(p, float(self.main_parameters[f'dut_{p}'].get()))

        if self.dyno and isinstance(self.dyno.devices[2], ASIController):
            for p in MOTOR_MAIN_PARAMETERS:
                self.dyno.devices[2].write(p[0], float(self.main_parameters[f'brk_{p[0]}'].get()))
            for p in MOTOR_HALLS:
                self.dyno.devices[2].write(p, float(self.main_parameters[f'brk_{p}'].get()))

        self._controller_read()
        self._update_main()

    def _update_main_yoko(self, event=None):
        """
        GUI backend + yoko polling
        Update Yokogawa parameters for home screen
        """
        if self.dyno and self.dyno.devices[PA]:
            for i in range(len(self.yoko_params)):
                name = self.yoko_params.loc[i]['Name']
                temp = self.main_parameters[f'yoko_param_{self.yoko_params.loc[i]["Shortened Name"]}_{i}']
                if self.dyno.is_logging_enabled():
                    temp.set(self.dyno.devices[PA].log_params[name].Value)
                else:
                    value = self.dyno.devices[PA].query(":numeric:normal:value? " + str(self.dyno.devices[PA].log_params[name].Address))
                    if isfinite(float(value)):
                        temp.set(value)
                    else:
                        temp.set('0')

    def _update_main_spin(self, event=None):
        """
        GUI backend
        Updates front end for DUT quick spin
        """
        if self.main_parameters['dut_main_spin_mode'].get() == 'Speed':
            # self.main_elements['dut_main_speed_rpm_label'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_rpm_label'][0],
            #                                                      rely=MAIN_SPIN_PLACE['dut_main_speed_rpm_label'][1], anchor='nw')
            # self.main_elements['dut_main_speed_rpm'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_rpm'][0],
            #                                                rely=MAIN_SPIN_PLACE['dut_main_speed_rpm'][1], anchor='nw')
            # self.main_elements['dut_main_speed_command_label'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_command_label'][0],
            #                                                          rely=MAIN_SPIN_PLACE['dut_main_speed_command_label'][1], anchor='nw')
            # self.main_elements['dut_main_speed_command'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_command'][0],
            #                                                    rely=MAIN_SPIN_PLACE['dut_main_speed_command'][1], anchor='nw')
            # self.main_elements['dut_main_motoring_label'].place(relx=MAIN_SPIN_PLACE['dut_main_motoring_label'][0],
            #                                                     rely=MAIN_SPIN_PLACE['dut_main_motoring_label'][1], anchor='nw')
            # self.main_elements['dut_main_motoring'].place(relx=MAIN_SPIN_PLACE['dut_main_motoring'][0],
            #                                               rely=MAIN_SPIN_PLACE['dut_main_motoring'][1], anchor='nw')
            # self.main_elements['dut_main_braking_label'].place(relx=MAIN_SPIN_PLACE['dut_main_braking_label'][0],
            #                                                    rely=MAIN_SPIN_PLACE['dut_main_braking_label'][1], anchor='nw')
            # self.main_elements['dut_main_braking'].place(relx=MAIN_SPIN_PLACE['dut_main_braking'][0],
            #                                              rely=MAIN_SPIN_PLACE['dut_main_braking'][1], anchor='nw')
            self.main_elements['dut_main_speed_rpm_label'].grid(column=0, row=1)
            self.main_elements['dut_main_speed_rpm'].grid(column=1, row=1)
            self.main_elements['dut_main_speed_command_label'].grid(column=2, row=1)
            self.main_elements['dut_main_speed_command'].grid(column=3, row=1)
            self.main_elements['dut_main_motoring_label'].grid(column=0, row=2)
            self.main_elements['dut_main_motoring'].grid(column=1, row=2)
            self.main_elements['dut_main_braking_label'].grid(column=2, row=2)
            self.main_elements['dut_main_braking'].grid(column=3, row=2)

            # self.main_elements['dut_main_torque_label'].place_forget()
            # self.main_elements['dut_main_torque'].place_forget()
            # self.main_elements['dut_main_current_label'].place_forget()
            # self.main_elements['dut_main_current'].place_forget()
            # self.main_elements['dut_main_modulation_label'].place_forget()
            # self.main_elements['dut_main_modulation'].place_forget()
            # self.main_elements['dut_main_frequency_label'].place_forget()
            # self.main_elements['dut_main_frequency'].place_forget()
            # self.main_elements['dut_main_angle_label'].place_forget()
            # self.main_elements['dut_main_angle'].place_forget()
            self.main_elements['dut_main_torque_label'].grid_forget()
            self.main_elements['dut_main_torque'].grid_forget()
            self.main_elements['dut_main_current_label'].grid_forget()
            self.main_elements['dut_main_current'].grid_forget()
            self.main_elements['dut_main_modulation_label'].grid_forget()
            self.main_elements['dut_main_modulation'].grid_forget()
            self.main_elements['dut_main_frequency_label'].grid_forget()
            self.main_elements['dut_main_frequency'].grid_forget()
            self.main_elements['dut_main_angle_label'].grid_forget()
            self.main_elements['dut_main_angle'].grid_forget()

        elif self.main_parameters['dut_main_spin_mode'].get() == 'Torque':
            # self.main_elements['dut_main_torque_label'].place(relx=MAIN_SPIN_PLACE['dut_main_torque_label'][0],
            #                                                   rely=MAIN_SPIN_PLACE['dut_main_torque_label'][1], anchor='nw')
            # self.main_elements['dut_main_torque'].place(relx=MAIN_SPIN_PLACE['dut_main_torque'][0],
            #                                             rely=MAIN_SPIN_PLACE['dut_main_torque'][1], anchor='nw')
            self.main_elements['dut_main_torque_label'].grid(column=0, row=1)
            self.main_elements['dut_main_torque'].grid(column=1, row=1)
            self.main_elements['dut_main_motoring_label'].grid(column=0, row=2)
            self.main_elements['dut_main_motoring'].grid(column=1, row=2)
            self.main_elements['dut_main_braking_label'].grid(column=2, row=2)
            self.main_elements['dut_main_braking'].grid(column=3, row=2)

            # self.main_elements['dut_main_speed_rpm_label'].place_forget()
            # self.main_elements['dut_main_speed_rpm'].place_forget()
            # self.main_elements['dut_main_speed_command_label'].place_forget()
            # self.main_elements['dut_main_speed_command'].place_forget()
            # self.main_elements['dut_main_motoring_label'].place_forget()
            # self.main_elements['dut_main_motoring'].place_forget()
            # self.main_elements['dut_main_braking_label'].place_forget()
            # self.main_elements['dut_main_braking'].place_forget()
            # self.main_elements['dut_main_speed_rpm_label'].place_forget()
            # self.main_elements['dut_main_speed_rpm'].place_forget()
            # self.main_elements['dut_main_current_label'].place_forget()
            # self.main_elements['dut_main_current'].place_forget()
            # self.main_elements['dut_main_modulation_label'].place_forget()
            # self.main_elements['dut_main_modulation'].place_forget()
            # self.main_elements['dut_main_frequency_label'].place_forget()
            # self.main_elements['dut_main_frequency'].place_forget()
            # self.main_elements['dut_main_angle_label'].place_forget()
            # self.main_elements['dut_main_angle'].place_forget()
            self.main_elements['dut_main_speed_rpm_label'].grid_forget()
            self.main_elements['dut_main_speed_rpm'].grid_forget()
            self.main_elements['dut_main_speed_command_label'].grid_forget()
            self.main_elements['dut_main_speed_command'].grid_forget()
            # self.main_elements['dut_main_motoring_label'].grid_forget()
            # self.main_elements['dut_main_motoring'].grid_forget()
            # self.main_elements['dut_main_braking_label'].grid_forget()
            # self.main_elements['dut_main_braking'].grid_forget()
            self.main_elements['dut_main_speed_rpm_label'].grid_forget()
            self.main_elements['dut_main_speed_rpm'].grid_forget()
            self.main_elements['dut_main_current_label'].grid_forget()
            self.main_elements['dut_main_current'].grid_forget()
            self.main_elements['dut_main_modulation_label'].grid_forget()
            self.main_elements['dut_main_modulation'].grid_forget()
            self.main_elements['dut_main_frequency_label'].grid_forget()
            self.main_elements['dut_main_frequency'].grid_forget()
            self.main_elements['dut_main_angle_label'].grid_forget()
            self.main_elements['dut_main_angle'].grid_forget()

        elif self.main_parameters['dut_main_spin_mode'].get() == 'Torque with speed limit':
            # self.main_elements['dut_main_speed_rpm_label'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_rpm_label'][0],
            #                                                      rely=MAIN_SPIN_PLACE['dut_main_speed_rpm_label'][1], anchor='nw')
            # self.main_elements['dut_main_speed_rpm'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_rpm'][0],
            #                                                rely=MAIN_SPIN_PLACE['dut_main_speed_rpm'][1], anchor='nw')
            # self.main_elements['dut_main_speed_command_label'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_command_label'][0],
            #                                                          rely=MAIN_SPIN_PLACE['dut_main_speed_command_label'][1], anchor='nw')
            # self.main_elements['dut_main_speed_command'].place(relx=MAIN_SPIN_PLACE['dut_main_speed_command'][0],
            #                                                    rely=MAIN_SPIN_PLACE['dut_main_speed_command'][1], anchor='nw')
            # self.main_elements['dut_main_motoring_label'].place(relx=MAIN_SPIN_PLACE['dut_main_motoring_label'][0],
            #                                                     rely=MAIN_SPIN_PLACE['dut_main_motoring_label'][1], anchor='nw')
            # self.main_elements['dut_main_motoring'].place(relx=MAIN_SPIN_PLACE['dut_main_motoring'][0],
            #                                               rely=MAIN_SPIN_PLACE['dut_main_motoring'][1], anchor='nw')
            # self.main_elements['dut_main_torque_label'].place(relx=MAIN_SPIN_PLACE['dut_main_braking_label'][0],
            #                                                    rely=MAIN_SPIN_PLACE['dut_main_braking_label'][1], anchor='nw')
            # self.main_elements['dut_main_torque'].place(relx=MAIN_SPIN_PLACE['dut_main_braking'][0],
            #                                              rely=MAIN_SPIN_PLACE['dut_main_braking'][1], anchor='nw')
            self.main_elements['dut_main_speed_rpm_label'].grid(column=0, row=1)
            self.main_elements['dut_main_speed_rpm'].grid(column=1, row=1)
            self.main_elements['dut_main_speed_command_label'].grid(column=2, row=1)
            self.main_elements['dut_main_speed_command'].grid(column=3, row=1)
            self.main_elements['dut_main_motoring_label'].grid(column=0, row=2)
            self.main_elements['dut_main_motoring'].grid(column=1, row=2)
            self.main_elements['dut_main_torque_label'].grid(column=2, row=2)
            self.main_elements['dut_main_torque'].grid(column=3, row=2)

            # self.main_elements['dut_main_braking_label'].place_forget()
            # self.main_elements['dut_main_braking'].place_forget()
            # self.main_elements['dut_main_current_label'].place_forget()
            # self.main_elements['dut_main_current'].place_forget()
            # self.main_elements['dut_main_modulation_label'].place_forget()
            # self.main_elements['dut_main_modulation'].place_forget()
            # self.main_elements['dut_main_frequency_label'].place_forget()
            # self.main_elements['dut_main_frequency'].place_forget()
            # self.main_elements['dut_main_angle_label'].place_forget()
            # self.main_elements['dut_main_angle'].place_forget()
            self.main_elements['dut_main_braking_label'].grid_forget()
            self.main_elements['dut_main_braking'].grid_forget()
            self.main_elements['dut_main_current_label'].grid_forget()
            self.main_elements['dut_main_current'].grid_forget()
            self.main_elements['dut_main_modulation_label'].grid_forget()
            self.main_elements['dut_main_modulation'].grid_forget()
            self.main_elements['dut_main_frequency_label'].grid_forget()
            self.main_elements['dut_main_frequency'].grid_forget()
            self.main_elements['dut_main_angle_label'].grid_forget()
            self.main_elements['dut_main_angle'].grid_forget()

        elif self.main_parameters['dut_main_spin_mode'].get() == 'Open loop current':
            # self.main_elements['dut_main_current_label'].place(relx=MAIN_SPIN_PLACE['dut_main_current_label'][0],
            #                                                    rely=MAIN_SPIN_PLACE['dut_main_current_label'][1], anchor='nw')
            # self.main_elements['dut_main_current'].place(relx=MAIN_SPIN_PLACE['dut_main_current'][0],
            #                                              rely=MAIN_SPIN_PLACE['dut_main_current'][1], anchor='nw')
            # self.main_elements['dut_main_frequency_label'].place(relx=MAIN_SPIN_PLACE['dut_main_frequency_label'][0],
            #                                                      rely=MAIN_SPIN_PLACE['dut_main_frequency_label'][1], anchor='nw')
            # self.main_elements['dut_main_frequency'].place(relx=MAIN_SPIN_PLACE['dut_main_frequency'][0],
            #                                                rely=MAIN_SPIN_PLACE['dut_main_frequency'][1], anchor='nw')
            # self.main_elements['dut_main_angle_label'].place(relx=MAIN_SPIN_PLACE['dut_main_angle_label'][0],
            #                                                  rely=MAIN_SPIN_PLACE['dut_main_angle_label'][1], anchor='nw')
            # self.main_elements['dut_main_angle'].place(relx=MAIN_SPIN_PLACE['dut_main_angle'][0],
            #                                            rely=MAIN_SPIN_PLACE['dut_main_angle'][1], anchor='nw')
            # self.main_elements['dut_main_motoring_label'].place(relx=MAIN_SPIN_PLACE['dut_main_braking_label'][0],
            #                                                     rely=MAIN_SPIN_PLACE['dut_main_braking_label'][1], anchor='nw')
            # self.main_elements['dut_main_motoring'].place(relx=MAIN_SPIN_PLACE['dut_main_braking'][0],
            #                                               rely=MAIN_SPIN_PLACE['dut_main_braking'][1], anchor='nw')
            self.main_elements['dut_main_current_label'].grid(column=0, row=1)
            self.main_elements['dut_main_current'].grid(column=1, row=1)
            self.main_elements['dut_main_frequency_label'].grid(column=2, row=1)
            self.main_elements['dut_main_frequency'].grid(column=3, row=1)
            self.main_elements['dut_main_angle_label'].grid(column=0, row=2)
            self.main_elements['dut_main_angle'].grid(column=1, row=2)
            self.main_elements['dut_main_motoring_label'].grid(column=2, row=2)
            self.main_elements['dut_main_motoring'].grid(column=3, row=2)

            # self.main_elements['dut_main_torque_label'].place_forget()
            # self.main_elements['dut_main_torque'].place_forget()
            # self.main_elements['dut_main_speed_rpm_label'].place_forget()
            # self.main_elements['dut_main_speed_rpm'].place_forget()
            # self.main_elements['dut_main_speed_command_label'].place_forget()
            # self.main_elements['dut_main_speed_command'].place_forget()
            # self.main_elements['dut_main_braking_label'].place_forget()
            # self.main_elements['dut_main_braking'].place_forget()
            # self.main_elements['dut_main_speed_rpm_label'].place_forget()
            # self.main_elements['dut_main_speed_rpm'].place_forget()
            # self.main_elements['dut_main_modulation_label'].place_forget()
            # self.main_elements['dut_main_modulation'].place_forget()
            self.main_elements['dut_main_torque_label'].grid_forget()
            self.main_elements['dut_main_torque'].grid_forget()
            self.main_elements['dut_main_speed_rpm_label'].grid_forget()
            self.main_elements['dut_main_speed_rpm'].grid_forget()
            self.main_elements['dut_main_speed_command_label'].grid_forget()
            self.main_elements['dut_main_speed_command'].grid_forget()
            self.main_elements['dut_main_braking_label'].grid_forget()
            self.main_elements['dut_main_braking'].grid_forget()
            self.main_elements['dut_main_speed_rpm_label'].grid_forget()
            self.main_elements['dut_main_speed_rpm'].grid_forget()
            self.main_elements['dut_main_modulation_label'].grid_forget()
            self.main_elements['dut_main_modulation'].grid_forget()

        elif self.main_parameters['dut_main_spin_mode'].get() == 'Open loop voltage':
            # self.main_elements['dut_main_modulation_label'].place(relx=MAIN_SPIN_PLACE['dut_main_modulation_label'][0],
            #                                                    rely=MAIN_SPIN_PLACE['dut_main_modulation_label'][1], anchor='nw')
            # self.main_elements['dut_main_modulation'].place(relx=MAIN_SPIN_PLACE['dut_main_modulation'][0],
            #                                              rely=MAIN_SPIN_PLACE['dut_main_modulation'][1], anchor='nw')
            # self.main_elements['dut_main_frequency_label'].place(relx=MAIN_SPIN_PLACE['dut_main_frequency_label'][0],
            #                                                      rely=MAIN_SPIN_PLACE['dut_main_frequency_label'][1], anchor='nw')
            # self.main_elements['dut_main_frequency'].place(relx=MAIN_SPIN_PLACE['dut_main_frequency'][0],
            #                                                rely=MAIN_SPIN_PLACE['dut_main_frequency'][1], anchor='nw')
            # self.main_elements['dut_main_angle_label'].place(relx=MAIN_SPIN_PLACE['dut_main_angle_label'][0],
            #                                                  rely=MAIN_SPIN_PLACE['dut_main_angle_label'][1], anchor='nw')
            # self.main_elements['dut_main_angle'].place(relx=MAIN_SPIN_PLACE['dut_main_angle'][0],
            #                                            rely=MAIN_SPIN_PLACE['dut_main_angle'][1], anchor='nw')
            # self.main_elements['dut_main_motoring_label'].place(relx=MAIN_SPIN_PLACE['dut_main_braking_label'][0],
            #                                                     rely=MAIN_SPIN_PLACE['dut_main_braking_label'][1], anchor='nw')
            # self.main_elements['dut_main_motoring'].place(relx=MAIN_SPIN_PLACE['dut_main_braking'][0],
            #                                               rely=MAIN_SPIN_PLACE['dut_main_braking'][1], anchor='nw')
            self.main_elements['dut_main_modulation_label'].grid(column=0, row=1)
            self.main_elements['dut_main_modulation'].grid(column=1, row=1)
            self.main_elements['dut_main_frequency_label'].grid(column=2, row=1)
            self.main_elements['dut_main_frequency'].grid(column=3, row=1)
            self.main_elements['dut_main_angle_label'].grid(column=0, row=2)
            self.main_elements['dut_main_angle'].grid(column=1, row=2)
            self.main_elements['dut_main_motoring_label'].grid(column=2, row=2)
            self.main_elements['dut_main_motoring'].grid(column=3, row=2)

            # self.main_elements['dut_main_torque_label'].place_forget()
            # self.main_elements['dut_main_torque'].place_forget()
            # self.main_elements['dut_main_speed_rpm_label'].place_forget()
            # self.main_elements['dut_main_speed_rpm'].place_forget()
            # self.main_elements['dut_main_speed_command_label'].place_forget()
            # self.main_elements['dut_main_speed_command'].place_forget()
            # self.main_elements['dut_main_braking_label'].place_forget()
            # self.main_elements['dut_main_braking'].place_forget()
            # self.main_elements['dut_main_speed_rpm_label'].place_forget()
            # self.main_elements['dut_main_speed_rpm'].place_forget()
            # self.main_elements['dut_main_current_label'].place_forget()
            # self.main_elements['dut_main_current'].place_forget()
            self.main_elements['dut_main_torque_label'].grid_forget()
            self.main_elements['dut_main_torque'].grid_forget()
            self.main_elements['dut_main_speed_rpm_label'].grid_forget()
            self.main_elements['dut_main_speed_rpm'].grid_forget()
            self.main_elements['dut_main_speed_command_label'].grid_forget()
            self.main_elements['dut_main_speed_command'].grid_forget()
            self.main_elements['dut_main_braking_label'].grid_forget()
            self.main_elements['dut_main_braking'].grid_forget()
            self.main_elements['dut_main_speed_rpm_label'].grid_forget()
            self.main_elements['dut_main_speed_rpm'].grid_forget()
            self.main_elements['dut_main_current_label'].grid_forget()
            self.main_elements['dut_main_current'].grid_forget()

        # self.main_parameters['dut_main_speed_rpm'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_motoring'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_braking'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_speed_command'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_torque'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_modulation'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_current'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_frequency'] = DoubleVar(value=0)
        # self.main_parameters['dut_main_angle'] = DoubleVar(value=0)

    def _run_main_spin(self, event=None):
        """
        GUI backend
        DUT quick spin
        """
        if self.dyno and isinstance(self.dyno.devices[1], ASIController):
            if self.main_parameters['dut_main_spin_mode'].get() == 'Speed':
                self.dyno.devices[1].remote_speed_mode(speed=self.main_parameters['dut_main_speed_rpm'].get(),
                                                motoring_current=self.main_parameters['dut_main_motoring'].get(),
                                                speed_command=self.main_parameters['dut_main_speed_command'].get(),
                                                braking_current=self.main_parameters['dut_main_braking'].get())
            elif self.main_parameters['dut_main_spin_mode'].get() == 'Torque':
                self.dyno.devices[1].remote_torque_mode(torque=self.main_parameters['dut_main_torque'].get(),
                                                        motoring_current=self.main_parameters['dut_main_motoring'].get(),
                                                        braking_current=self.main_parameters['dut_main_braking'].get())
            elif self.main_parameters['dut_main_spin_mode'].get() == 'Torque with speed limit':
                self.dyno.devices[1].remote_speed_torque_mode(speed=self.main_parameters['dut_main_speed_rpm'].get(),
                                                       torque=self.main_parameters['dut_main_torque'].get(),
                                                       motoring_current=self.main_parameters['dut_main_motoring'].get())
            elif self.main_parameters['dut_main_spin_mode'].get() == 'Open loop current':
                self.dyno.devices[1].current_mode(motoring_current=self.main_parameters['dut_main_motoring'].get(),
                                           current=self.main_parameters['dut_main_current'].get(),
                                           frequency=self.main_parameters['dut_main_frequency'].get(),
                                           angle=self.main_parameters['dut_main_angle'].get())
            elif self.main_parameters['dut_main_spin_mode'].get() == 'Open loop voltage':
                self.dyno.devices[1].voltage_mode(motoring_current=self.main_parameters['dut_main_motoring'].get(),
                                           modulation=self.main_parameters['dut_main_modulation'].get(),
                                           frequency=self.main_parameters['dut_main_frequency'].get(),
                                           angle=self.main_parameters['dut_main_angle'].get())

    def _e_stop(self, event=None):
        """
        GUI backend + dyno e-stop
        E-stop for home screen
        """
        # if self.dyno:
        #     self._dyno_stop()
        #     if self.run_timer_status.get():
        #         self._run_for()
        if self.stopping:
            pass
        else:
            if self.dyno:
                self.stopping = True
                if self.testing:
                    if self.test_handler is not None:
                        self.sigint_handler()
                    else:
                        self.testing = False
                else:
                    self._dyno_stop()
                if self.run_timer_status.get():
                    self._run_for()
                self.stopping = False

    def _live_tab_change(self, tab=0):
        """
        GUI front end
        Custom tab switching for home screen live section
        """
        self.status_notebook.select(tab)
        if tab == 0:
            self.main_elements['live_graph_tab'].reset(background='white', foreground='#5DA01D')
            # self.main_elements['live_list_tab'].reset(background='white', foreground='black')
            self.main_elements['live_faults_tab'].reset(background='white', foreground='black')
            self.main_elements['live_test_tab'].reset(background='white', foreground='black')

            if self.connection_condition.get() != 'CONNECT':
                for i, graph in enumerate(PLOT_LIST):
                    if i == self.graph_notebook.index(self.graph_notebook.select()):
                        self.graphs[graph].animation.resume()
        # elif tab == 1:
        #     self.main_elements['live_graph_tab'].reset(background='white', foreground='black')
        #     self.main_elements['live_list_tab'].reset(background='white', foreground='#5DA01D')
        #     self.main_elements['live_faults_tab'].reset(background='white', foreground='black')
        #     self.main_elements['live_test_tab'].reset(background='white', foreground='black')
        #     for graph in PLOT_LIST:
        #         self.graphs[graph].animation.pause()
        elif tab == 1:
            self.main_elements['live_graph_tab'].reset(background='white', foreground='black')
            # self.main_elements['live_list_tab'].reset(background='white', foreground='black')
            self.main_elements['live_faults_tab'].reset(background='white', foreground='#5DA01D')
            self.main_elements['live_test_tab'].reset(background='white', foreground='black')
            for graph in PLOT_LIST:
                self.graphs[graph].animation.pause()
        elif tab == 2:
            self.main_elements['live_graph_tab'].reset(background='white', foreground='black')
            # self.main_elements['live_list_tab'].reset(background='white', foreground='black')
            self.main_elements['live_test_tab'].reset(background='white', foreground='black')
            self.main_elements['live_test_tab'].reset(background='white', foreground='#5DA01D')
            for graph in PLOT_LIST:
                self.graphs[graph].animation.pause()
        # elif tab == 4:

    def _graph_tab_change(self, tab=0):
        """
        GUI front end
        Custom tab switching for home screen live section
        """
        self.graph_notebook.select(tab)
        if tab == 0:
            self.main_elements['graph_basic_tab'].reset(background='white', foreground='#5DA01D')
            self.main_elements['graph_temp_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mech_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_elec_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_effi_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mb_tab'].reset(background='white', foreground='black')
            if self.connection_condition.get() != 'CONNECT':
                self.graphs['RPMTorque'].animation.resume()
            else:
                self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif tab == 1:
            self.main_elements['graph_basic_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_temp_tab'].reset(background='white', foreground='#5DA01D')
            self.main_elements['graph_mech_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_elec_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_effi_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mb_tab'].reset(background='white', foreground='black')
            self.graphs['RPMTorque'].animation.pause()
            if self.connection_condition.get() != 'CONNECT':
                self.graphs['temp'].animation.resume()
            else:
                self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif tab == 2:
            self.main_elements['graph_basic_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_temp_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mech_tab'].reset(background='white', foreground='#5DA01D')
            self.main_elements['graph_elec_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_effi_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mb_tab'].reset(background='white', foreground='black')
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            if self.connection_condition.get() != 'CONNECT':
                self.graphs['mech'].animation.resume()
            else:
                self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif tab == 3:
            self.main_elements['graph_basic_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_temp_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mech_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_elec_tab'].reset(background='white', foreground='#5DA01D')
            self.main_elements['graph_effi_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mb_tab'].reset(background='white', foreground='black')
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            if self.connection_condition.get() != 'CONNECT':
                self.graphs['elec'].animation.resume()
            else:
                self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif tab == 4:
            self.main_elements['graph_basic_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_temp_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mech_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_elec_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_effi_tab'].reset(background='white', foreground='#5DA01D')
            self.main_elements['graph_mb_tab'].reset(background='white', foreground='black')
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            if self.connection_condition.get() != 'CONNECT':
                self.graphs['effi'].animation.resume()
            else:
                self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif tab == 5:
            self.main_elements['graph_basic_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_temp_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mech_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_elec_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_effi_tab'].reset(background='white', foreground='black')
            self.main_elements['graph_mb_tab'].reset(background='white', foreground='#5DA01D')
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            if self.connection_condition.get() != 'CONNECT':
                self.graphs['mb'].animation.resume()
            else:
                self.graphs['mb'].animation.pause()

    def _param_menu(self, event=None):
        """
        GUI frontend
        Build right click menu for +/- parameter on controller tab
        """
        if self.connection_condition.get() == "\nCONNECT\n":
            return
        m = Menu(self.root, tearoff=0)
        m.add_command(label='Add', command=lambda: self._popup_add_param(event))
        m.add_command(label='Delete', command=lambda: self._del_parameter(event))

        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _del_parameter(self, event=None):
        """
        GUI backend - can make shorter
        Delete parameter from parameter list on control tab
        """
        if self.dyno is not None:
            index = int(str(event.widget).split(".")[-1].split("_")[-1])
            old_tree = ET.parse(f"{ROOT_DIR}/GUI Controller.xml").getroot()
            old = {'DUT': old_tree.find('DUT'),
                   'BRK': old_tree.find('BRK'),
                   'ABB': old_tree.find('ABB'),
                   'DUT_EXT': old_tree.find('DUT_EXT'),
                   'DUT_EXT_EXT': old_tree.find('DUT_EXT_EXT'),
                   'BRK_EXT': old_tree.find('BRK_EXT'),
                   'BRK_EXT_EXT': old_tree.find('BRK_EXT_EXT')}
            new_tree = ET.Element('Parameters')
            for controller in ['DUT', 'DUT_EXT', 'DUT_EXT_EXT', 'BRK', 'BRK_EXT', 'BRK_EXT_EXT', 'ABB']:
                temp = ET.SubElement(new_tree, controller)
                for i, param in enumerate(old[controller].findall('Name')):
                    if i == index and controller == 'DUT' and event.widget.master == self.dut_frame:
                        continue
                    elif i == index and controller == 'DUT_EXT' and event.widget.master == self.dut_extra_frame:
                        continue
                    elif i == index and controller == 'DUT_EXT_EXT' and event.widget.master == self.dut_extra_frame_1:
                        continue
                    elif i == index and controller == 'BRK' and event.widget.master == self.brk_frame:
                        continue
                    elif i == index and controller == 'BRK_EXT' and event.widget.master == self.brk_extra_frame:
                        continue
                    elif i == index and controller == 'BRK_EXT_EXT' and event.widget.master == self.brk_extra_frame_1:
                        continue
                    ET.SubElement(temp, 'Name').text = param.text
            indent(new_tree)
            new_tree = ET.ElementTree(new_tree)
            new_tree.write(f"{ROOT_DIR}/GUI Controller.xml")
            logging.debug('Delete complete')
            self.controller_params_raw = ET.parse(f"{ROOT_DIR}/GUI Controller.xml")

            self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame_1,
                                              self.brk_extra_frame_1, self.dut_extra_frame, self.brk_extra_frame],
                                             ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                              "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}",
                                              "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}"],
                                             CONTROL_PARAM_INIT)
            Thread(target=lambda: self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                                                                    self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                                                                   ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                                                    "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                                    "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                                   CONTROL_PARAM_UPDATE)).start()


    def _add_parameter(self, top, index, names, controller, all_names):
        """
        GUI backend
        Add parameter to parameter list on control tab
        Adds above the selected parameter
        """
        if self.dyno is not None:
            params_to_add = []
            for i in names:
                params_to_add.append(all_names[i])
                if 'dut' in controller.lower()and isinstance(self.dyno.devices[1], ASIController):
                    self.dyno.devices[1].add_run_parameter(all_names[i])
                elif 'brk' in controller.lower() and isinstance(self.dyno.devices[2], ASIController):
                    self.dyno.devices[2].add_run_parameter(all_names[i])
            if 'dut' in controller.lower():
                old_tree = self.controller_params_raw.getroot()
                old = {'DUT': old_tree.find('DUT'),
                       'BRK': old_tree.find('BRK'),
                       'ABB': old_tree.find('ABB'),
                       'DUT_EXT': old_tree.find('DUT_EXT'),
                       'DUT_EXT_EXT': old_tree.find('DUT_EXT_EXT'),
                       'BRK_EXT': old_tree.find('BRK_EXT'),
                       'BRK_EXT_EXT': old_tree.find('BRK_EXT_EXT')}
                new_tree = ET.Element('Parameters')
                for c in ['DUT', 'DUT_EXT', 'DUT_EXT_EXT', 'BRK', 'BRK_EXT', 'BRK_EXT_EXT', 'ABB']:
                    temp = ET.SubElement(new_tree, c)
                    for i, param in enumerate(old[c].findall('Name')):
                        if i == index and controller == c:
                            for name in params_to_add:
                                ET.SubElement(temp, 'Name').text = name
                        ET.SubElement(temp, 'Name').text = param.text
                indent(new_tree)
                new_tree = ET.ElementTree(new_tree)
                new_tree.write(f"{ROOT_DIR}/GUI Controller.xml")
                logging.debug(f"\'{params_to_add}\' added to {controller} param list")
            elif 'brk' in controller.lower() and isinstance(self.dyno.devices[2], ASIController):
                old_tree = ET.parse(f"{ROOT_DIR}/GUI Controller.xml").getroot()
                old = {'DUT': old_tree.find('DUT'),
                       'BRK': old_tree.find('BRK'),
                       'ABB': old_tree.find('ABB'),
                       'DUT_EXT': old_tree.find('DUT_EXT'),
                       'DUT_EXT_EXT': old_tree.find('DUT_EXT_EXT'),
                       'BRK_EXT': old_tree.find('BRK_EXT'),
                       'BRK_EXT_EXT': old_tree.find('BRK_EXT_EXT')}
                new_tree = ET.Element('Parameters')
                for c in ['DUT', 'DUT_EXT', 'DUT_EXT_EXT', 'BRK', 'BRK_EXT', 'BRK_EXT_EXT', 'ABB']:
                    temp = ET.SubElement(new_tree, c)
                    for i, param in enumerate(old[c].findall('Name')):
                        if i == index and controller == c:
                            for name in params_to_add:
                                ET.SubElement(temp, 'Name').text = name
                        ET.SubElement(temp, 'Name').text = param.text
                indent(new_tree)
                new_tree = ET.ElementTree(new_tree)
                new_tree.write(f"{ROOT_DIR}/GUI Controller.xml")
                self.controller_params_raw = ET.parse(f"{ROOT_DIR}/GUI Controller.xml")
                logging.info(f"\'{params_to_add}\' added to {controller} param list")
            if top:
                top.destroy()
            self.controller_params_raw = ET.parse(f"{ROOT_DIR}/GUI Controller.xml")
            self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame_1,
                                              self.brk_extra_frame_1, self.dut_extra_frame, self.brk_extra_frame],
                                             ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                              "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}",
                                              "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}"],
                                             CONTROL_PARAM_INIT)
            Thread(target=lambda: self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                                                                    self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                                                                   ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                                                    "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                                    "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                                   CONTROL_PARAM_UPDATE)).start()

    def _move_parameter(self, controller, src, dest):
        """
        GUI backend
        WIP
        """
        print('move')
        if self.dyno is not None:
            if src > dest:
                src += 1

            # add parameter to destination
            old_tree = ET.parse(f"{ROOT_DIR}/GUI Controller.xml").getroot()
            old = {'DUT': old_tree.find('DUT'),
                   'BRK': old_tree.find('BRK'),
                   'ABB': old_tree.find('ABB'),
                   'DUT_EXT': old_tree.find('DUT_EXT'),
                   'DUT_EXT_EXT': old_tree.find('DUT_EXT_EXT'),
                   'BRK_EXT': old_tree.find('BRK_EXT'),
                   'BRK_EXT_EXT': old_tree.find('BRK_EXT_EXT')}

            new_tree = ET.Element('Parameters')
            temp_element = None
            for c in ['DUT', 'DUT_EXT', 'DUT_EXT_EXT', 'BRK', 'BRK_EXT', 'BRK_EXT_EXT', 'ABB']:
                temp = ET.SubElement(new_tree, c)
                for i, param in enumerate(old[c].findall('Name')):
                    if i == dest and c == controller:
                        ET.SubElement(temp, 'Name').text = temp_element
                        print(c, temp_element)
                    ET.SubElement(temp, 'Name').text = param.text
                    
            # delete parameter at source
            old_tree_1 = new_tree
            
            old = {'DUT': old_tree_1.find('DUT'),
                    'BRK': old_tree_1.find('BRK'),
                    'ABB': old_tree_1.find('ABB'),
                    'DUT_EXT': old_tree_1.find('DUT_EXT'),
                    'DUT_EXT_EXT': old_tree_1.find('DUT_EXT_EXT'),
                    'BRK_EXT': old_tree_1.find('BRK_EXT'),
                    'BRK_EXT_EXT': old_tree_1.find('BRK_EXT_EXT')}
            new_tree = ET.Element('Parameters')
            for c in ['DUT', 'DUT_EXT', 'DUT_EXT_EXT', 'BRK', 'BRK_EXT', 'BRK_EXT_EXT', 'ABB']:
                temp = ET.SubElement(new_tree, c)
                for i, param in enumerate(old[c].findall('Name')):
                    if i == dest and c == controller:
                        temp_element = param.text
                        continue
                    ET.SubElement(temp, 'Name').text = param.text
            

            indent(new_tree)
            new_tree = ET.ElementTree(new_tree)
            new_tree.write(f"{ROOT_DIR}/GUI Controller.xml")

            self.controller_params_raw = ET.parse(f"{ROOT_DIR}/GUI Controller.xml")
            self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame_1,
                                              self.brk_extra_frame_1, self.dut_extra_frame, self.brk_extra_frame],
                                             ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                              "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}",
                                              "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}"],
                                             CONTROL_PARAM_INIT)
            Thread(target=lambda: self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                                                                    self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                                                                   ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                                                    "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                                    "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                                   CONTROL_PARAM_UPDATE)).start()
        
            # event.widget.configure(background=f'{"#ccccff" if "dut" in str(event.widget).lower() else "#ccffcc"}')

    def _drop_handler(self, event):
        print(event.y)
        half = self._widget_half(event.widget, event.y, event.widget.winfo_height())
        print(event.widget, half[2], half[3])
        self._move_parameter(event, half[2], half[3])

    def _widget_half(self, widget, y, height):
        # print(widget.winfo_rooty(), widget.winfo_height(), y)
        return_value = []
        if y > widget.winfo_rooty():  # move to parameter above
            scaled_pos = [int((widget.winfo_rooty() - y) / height), 
                          ((widget.winfo_rooty() - y) % height) / height]
        elif y < widget.winfo_rooty() - widget.winfo_height():  # move to parameter below
            scaled_pos = [-1 * int((y - widget.winfo_rooty() + height) / height),
                          ((y - widget.winfo_rooty() + height) % height) / height]
        else:
            scaled_pos = [0, 0]

        widget_prefix = str(widget).split('_')[:-1]
        widget_suffix = int(str(widget).split('_')[-1])
        dest_suffix = widget_suffix - scaled_pos[0]
        if dest_suffix < 0:
            dest_suffix = 0

        dest_widget = '_'.join(widget_prefix) + f'_{dest_suffix}'
        # print(dest_widget)
        return_value.append(self.root.nametowidget(dest_widget))

        if scaled_pos[1] >= 0.5:
            # print('top')
            return_value.append('top')
        else:
            # print('bottom')
            return_value.append('bottom')

        return_value.append(widget_suffix)
        return_value.append(dest_suffix)

        return return_value

    def _drag_handler(self, event):
        source_widget_height = event.widget.winfo_height()
        event.widget.configure(background="#cccccc")
        half = self._widget_half(event.widget, event.widget.winfo_rooty(), source_widget_height)
        dest_widget = half[0]
        if half[1] == 'top':
            dest_widget.configure(background="#cccccc")
        elif half[1] == 'bottom':
            dest_widget.configure(background="#cccccc")
        else:
            dest_widget.configure(background=f'{"#ccccff" if "dut" in str(event.widget).lower() else "#ccffcc"}')

        # self._move_parameter(event, half[2], half[3])

        # print(event.widget.winfo_rootx(), event.widget.winfo_rooty())

    def _popup_add_param(self, event=None):
        """
        GUI front end
        Build pop up window for +/- parameters on control tab
        """
        top = Toplevel(self.root)
        popup = Frame(top)
        popup.grid(column=0, row=0)
        search_var = StringVar()
        search = Entry(popup, textvariable=search_var,
                       font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        search.grid(column=0, row=0, columnspan=2, sticky='we')
        param_list = Listbox(popup, width=50, height=20, exportselection=False, selectmode='multiple')
        temp = []
        search_var.trace_add('write', lambda x, y, z: self._filter_param(search_var.get(), param_list))
        index = int(str(event.widget).split(".")[-1].split("_")[-1])
        if event.widget.master == self.dut_frame:
            if self.dyno is not None and self.dyno.devices[1] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_parameter(top, index, param_list.curselection(),
                                                                              'DUT', param_list.get(0, END))).grid(column=0, row=2)
            for element in self.dyno.devices[1].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        elif event.widget.master == self.dut_extra_frame:
            if self.dyno is not None and self.dyno.devices[1] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_parameter(top, index, param_list.curselection(),
                                                                              'DUT_EXT', param_list.get(0, END))).grid(column=0, row=2)
            for element in self.dyno.devices[1].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        elif event.widget.master == self.dut_extra_frame_1:
            if self.dyno is not None and self.dyno.devices[1] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_parameter(top, index, param_list.curselection(),
                                                                              'DUT_EXT_EXT', param_list.get(0, END))).grid(column=0, row=2)
            for element in self.dyno.devices[1].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        elif event.widget.master == self.brk_frame:
            if self.dyno is not None and self.dyno.devices[2] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_parameter(top, index, param_list.curselection(),
                                                                              'BRK', param_list.get(0, END))).grid(column=0, row=2)
            for element in self.dyno.devices[2].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        elif event.widget.master == self.brk_extra_frame:
            if self.dyno is not None and self.dyno.devices[2] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_parameter(top, index, param_list.curselection(),
                                                                              'BRK_EXT', param_list.get(0, END))).grid(column=0, row=2)
            for element in self.dyno.devices[2].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        elif event.widget.master == self.brk_extra_frame_1:
            if self.dyno is not None and self.dyno.devices[2] is None:
                top.destroy()
                return
            ttk.Button(popup, text='Add', command=lambda: self._add_parameter(top, index, param_list.curselection(),
                                                                              'BRK_EXT_EXT', param_list.get(0, END))).grid(column=0, row=2)
            for element in self.dyno.devices[2].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        names = StringVar(value=temp)
        param_list.configure(listvariable=names)
        param_list.grid(column=0, row=1, columnspan=2, sticky='news')
        ttk.Button(popup, text='Cancel', command=top.destroy).grid(column=1, row=2)

    def _filter_param(self, to_search, param_list):
        """
        GUI backend
        Search bar for parameter list
        """
        param_list.delete(0, END)
        temp = []
        if self.dyno.devices[1] and isinstance(self.dyno.devices[1], ASIController):
            for element in self.dyno.devices[1].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        elif self.dyno.devices[2] and isinstance(self.dyno.devices[2], ASIController):
            for element in self.dyno.devices[2].etree.iter("ParameterDescription"):
                temp.append(element.find('Name').text)
        else:
            return

        names = StringVar(value=temp)
        if to_search == "":
            param_list.configure(listvariable=names)
            return

        filtered = []
        for name in temp:
            if name.lower().find(to_search) >= 0 or name.find(to_search) >= 0:
                filtered.append(name)
        names = StringVar(value=filtered)
        param_list.configure(listvariable=names)

    def _bind_edit(self, config_list=None):
        """
        GUI backend
        Allow editing test config list on double click
        """
        if self.config_value.get() != "":
            if config_list is None:
                config_list = self.config_list
            for i, child in enumerate(config_list.scrollable_frame.winfo_children()):
                child.bind("<Double-Button-1>", lambda e : self._edit_config_list(e, config_list=config_list))

    def _unbind_edit(self):
        """
        GUI backend - obsolete - now binds edit on default and never unbinding
        Unbinds edit config list button
        """
        for i, child in enumerate(self.config_list.scrollable_frame.winfo_children()):
            child.unbind("<Double-Button-1>")

        # self.config_popup.lift()

    def _edit_config_list(self, event=None, config_list=None):
        """
        GUI backend 
        Popup window to change config list value
        """
        if self.config_value.get() != "":
            if config_list is None:
                config_list = self.config_list
            header = ""
            original_value = ''
            for child in config_list.scrollable_frame.winfo_children():
                if child == event.widget:
                    header = child["text"].strip().split(":")[0]
                    original_value = child["text"].strip().split(":")[1].strip()
            if header != "":
                new_value = simpledialog.askstring(title="Caution: Editing Configuration",
                                                   prompt=f"New value for {header} @ "
                                                          f"{self.config_value.get()}",
                                                   initialvalue=original_value)
                if new_value is None:
                    return
                for key, value in CONFIG_MAP.items():
                    if value == header:
                        header = key
                        break
                if new_value.isnumeric():
                    self.configs.loc[self.config_value.get(), header] = int(new_value)
                else:
                    try:
                        self.configs.loc[self.config_value.get(), header] = float(new_value)
                    except ValueError:
                        self.configs.loc[self.config_value.get(), header] = new_value
                self._populate_config_list()
                # self.edit_popup.set("Edit")
                self._bind_edit(config_list)
                self.update_main_gui_controllers()
                self._save_config_list()
            # self.config_popup.lift()
        else:
            messagebox.showerror("No! No! NOOOO!", "Pick a preset first!!!")

    def _save_config_list(self):
        """
        GUI backend
        Save configurations to file
        """
        self.configs.to_csv(f"{ROOT_DIR}/dyno_config.csv", mode='w')
        # if self.config_value.get() != "":
        #     save_ask = messagebox.askquestion("Save to dyno_config.csv", "Are you sure?")
        #     if save_ask == 'yes':
        #         self.configs.to_csv(f"{ROOT_DIR}/dyno_config.csv", mode='w')
        #         messagebox.showinfo("Save to dyno_config.csv", "Save successful!")
        #
        #     self.config_popup.lift()
        #     self.update_main_gui_controllers()
        # else:
        #     messagebox.showerror("No! No! NOOOO!", "Pick a preset first!!!")

    def _new_config(self):
        """
        GUI backend
        Create new configuration from current - does not save to file
        """
        if self.config_value.get() != "":
            name = simpledialog.askstring("Copy current configuration",
                                          f"Enter a unique name, e.g. "
                                          f"{self.test_tab.children['test_btn_frame'].children['config_combo'].get()}-1")
            for col in self.configs.columns:
                if name == col:
                    messagebox.showerror("Duplicated Entry", "Please try something else again")
                    return
            self.configs.loc[name] = self.configs.loc[self.config_value.get()]
            moving_list = self.configs.index.to_list()
            moving_list.insert(moving_list.index(self.config_value.get()) + 1, moving_list.pop(len(moving_list) - 1))
            self.configs = self.configs.reindex(moving_list)
            self.test_tab.children['test_btn_frame'].children['config_combo']['values'] = self.configs.index.to_list()
            self.test_tab.children['test_btn_frame'].children['config_combo'].set(name)
            self._populate_config_list()
            self._save_config_list()

            self.config_popup.lift()
        else:
            messagebox.showerror("No! No! NOOOO!", "Pick a preset first!!!")

    def _del_config(self):
        """
        GUI backend
        Delete current configuration - does not save to file by default
        """
        if self.test_tab.children['test_btn_frame'].children['config_combo'].get() != "":
            del_ask = messagebox.askquestion("Delete preset", "Are you sure?")
            if del_ask == 'yes':
                old_index = self.configs.index.to_list().index(self.config_value.get())
                self.configs.drop([self.config_value.get()], inplace=True)
                self.test_tab.children['test_btn_frame'].children['config_combo']['values'] = self.configs.index.to_list()
                self.test_tab.children['test_btn_frame'].children['config_combo'].set(self.configs.index.to_list()[old_index - 1])
                self._populate_config_list()

                save_ask = messagebox.askquestion("Delete preset", "Save changes to file?")
                if save_ask == 'yes':
                    self._save_config_list()

            self.config_popup.lift()
        else:
            messagebox.showerror("No! No! NOOOO!", "Pick a preset first!!!")

    def _build_config_popup(self, mainframe):
        """
        GUI front end
        Constructing popup for config list on home screen
        """
        self.config_popup = Toplevel(mainframe)
        self.config_popup.resizable(False, False)
        self.config_popup.minsize(CONFIG_LIST_WIDTH + 40, 535)
        self.config_popup.geometry(f"{CONFIG_LIST_WIDTH + 40}x535")
        self.config_popup.withdraw()
        pop_frame = ttk.Frame(self.config_popup)
        pop_frame.pack(fill='both')
        pop_frame.grid_columnconfigure((0, 1, 2), weight=1)
        # test list
        tests = ttk.Combobox(pop_frame, textvariable=self.test,
                             font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}')
        tests.grid(column=0, row=0, sticky='we')
        tests['values'] = TEST_SCRIPTS
        tests.bind('<<ComboboxSelected>>', self.test_inputs)
        # preset list
        ttk.Combobox(pop_frame, textvariable=self.config_value, name='config_combo',
                     font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=1, row=0, columnspan=2, sticky='news')
        pop_frame.children['config_combo']['values'] = self.configs.index.to_list()
        ToolTip(pop_frame.children['config_combo'], delay=TOOLTIP_DELAY,
                msg="Select a preset for connection and test configurations")
        pop_frame.children['config_combo'].bind('<<ComboboxSelected>>', self.test_inputs)
        self.main_elements['popup_config_combo'] = pop_frame.children['config_combo']
        # buttons
        ttk.Button(pop_frame, text="Save to file", command=self._save_config_list, name="save_config_btn").grid(
            column=0, row=1, sticky='news')
        ToolTip(pop_frame.children['save_config_btn'], delay=TOOLTIP_DELAY,
                msg="Save onboard configurations to file (persist after restart)")
        ttk.Button(pop_frame, text="New preset", command=self._new_config, name="new_config_btn").grid(
            column=1, row=1, sticky='news')
        ToolTip(pop_frame.children['new_config_btn'], delay=TOOLTIP_DELAY,
                msg="Create a new configuration from current preset. Save to file to keep the changes")
        ttk.Button(pop_frame, text="Delete preset", command=self._del_config, name='del_config_btn').grid(
            column=2, row=1, sticky='news')
        # Configuration list
        self.popup_config_list = ScrollableFrame(pop_frame, width=CONFIG_LIST_WIDTH + 20, height=480)
        self.popup_config_list.grid(column=0, row=2, columnspan=3, sticky='news')
        self.config_list.canvas.config()
        ToolTip(self.popup_config_list, delay=TOOLTIP_DELAY, msg="Onboard preset configurations.")

        self.config_popup.protocol("WM_DELETE_WINDOW", self._popup_config_list)
        self._bind_edit(self.popup_config_list)

    def init_config_list(self, root):
        """
        GUI front end
        initialize configuration list with parameter names and empty value
        """
        for i in range(len(self.configs.columns)):
            header = self.configs.columns[i]
            if header == "description":
                root.children['config_desc_text'].delete('1.0', END)
                root.children['config_desc_text'].insert('1.0', self.configs.loc[self.config_value.get()]['description'])
                root.children['config_desc_text'].update()
            else:
                ttk.Label(self.config_list.scrollable_frame, width=CONFIG_LIST_LABEL_WIDTH,
                          font=(OPTION_FONT_NAME, f"{CONFIG_LIST_FONT_SIZE}"),
                          text=f"{CONFIG_MAP[header.lower()]}: {self.configs.loc[self.config_value.get()][header]}",
                          name=f'{i % CONFIG_LIST_COL}_{int(i / CONFIG_LIST_COL)}_{header}').grid(
                    column=i % CONFIG_LIST_COL, row=int(i / CONFIG_LIST_COL), sticky='w')
                self.config_list.scrollable_frame.children[f'{i % CONFIG_LIST_COL}_{int(i / CONFIG_LIST_COL)}_{header}'].bind(
                    '<MouseWheel>', self.config_list.scrollable_frame.master.master.on_mousewheel)

                if self.config_popup:
                    ttk.Label(self.popup_config_list.scrollable_frame,
                              text=f"{CONFIG_MAP[header.lower()]}: {self.configs.loc[self.config_value.get()][header]}",
                              width=CONFIG_LIST_LABEL_WIDTH, font=("", f"{CONFIG_LIST_FONT_SIZE}"),
                              name=f'{i % CONFIG_LIST_COL}_{int(i / CONFIG_LIST_COL)}_{header}').grid(
                        column=i % CONFIG_LIST_COL, row=int(i / CONFIG_LIST_COL), sticky='w')
                    self.popup_config_list.scrollable_frame.children[f'{i % CONFIG_LIST_COL}_{int(i / CONFIG_LIST_COL)}_{header}'].bind(
                        '<MouseWheel>', self.popup_config_list.scrollable_frame.master.master.on_mousewheel)

    def _reset_config_list(self, output):
        """
        GUI backend
        Resets configuration list with shortened list based on chosen test
        """
        self._orphan(self.config_list.scrollable_frame.winfo_children())
        if self.config_popup:
            self._orphan(self.popup_config_list.scrollable_frame.winfo_children())

        if self.test.get() in OPERATIONAL_TESTS:
            filter_col = [col for col in self.configs if not any(map(col.startswith, TEST_FILTERS[self.test.get()]))]
            filtered_presets = self.configs.loc[self.configs['test'] == self.test.get()]
        else:
            filter_col = self.configs.columns
            filtered_presets = self.configs

        self.main_elements['main_test_preset']['value'] = filtered_presets.index.to_list()
        self.test_tab.children['test_btn_frame'].children['config_combo']['value'] = filtered_presets.index.to_list()
        if self.config_popup:
            self.main_elements['popup_config_combo']['value'] = filtered_presets.index.to_list()

        for i in range(int(len(filter_col))):
            header = filter_col[i]
            if header == "description":
                self.test_tab.children['config_desc_text'].delete('1.0', END)
                self.test_tab.children['config_desc_text'].insert('1.0', output[header])
                self.test_tab.children['config_desc_text'].update()
            else:
                ttk.Label(self.config_list.scrollable_frame, text=f"{CONFIG_MAP[header.lower()]}: "
                                                                  f"{output[header]}",
                          width=CONFIG_LIST_LABEL_WIDTH, font=("", f"{CONFIG_LIST_FONT_SIZE}"),
                          name=f'{i % CONFIG_LIST_COL}_{int(i / CONFIG_LIST_COL)}_{header}').grid(
                    column=i % CONFIG_LIST_COL, row=int(i / CONFIG_LIST_COL), sticky='w')
                self.config_list.scrollable_frame.children[f'{i % CONFIG_LIST_COL}_' \
                                                           f'{int(i / CONFIG_LIST_COL)}_{header}'].bind(
                    '<MouseWheel>', self.config_list.scrollable_frame.master.master.on_mousewheel)

                if self.config_popup:
                    ttk.Label(self.popup_config_list.scrollable_frame, text=f"{CONFIG_MAP[header.lower()]}: "
                                                                            f"{output[header]}",
                              width=CONFIG_LIST_LABEL_WIDTH, font=("", f"{CONFIG_LIST_FONT_SIZE}"),
                              name=f'{i % CONFIG_LIST_COL}_{int(i / CONFIG_LIST_COL)}_{header}').grid(
                        column=i % CONFIG_LIST_COL, row=int(i / CONFIG_LIST_COL), sticky='w')
                    self.popup_config_list.scrollable_frame.children[f'{i % CONFIG_LIST_COL}_' \
                                                                     f'{int(i / CONFIG_LIST_COL)}_{header}'].bind(
                        '<MouseWheel>', self.popup_config_list.scrollable_frame.master.master.on_mousewheel)
        self._bind_edit()
        if self.config_popup:
            self._bind_edit(self.popup_config_list)

    def _update_description(self, event=None):
        """
        GUI backend
        Update description test box to self.configs 
        """
        self.configs.loc[self.config_value.get(), 'description'] = self.test_tab.children['config_desc_text'].get('1.0', 'end - 1c')

    def _construct_config_list(self):
        """
        GUI backend
        Build dyno config based on home screen selections (beta)
        """
        dut_controller = self.main_parameters['dut_controller'].get()
        brk_controller = self.main_parameters['brk_controller'].get()
        if brk_controller.lower() == 'nan':
            brk_controller = None
        dut_motor = self.main_parameters['dut_motor'].get()
        brk_motor = self.main_parameters['brk_motor'].get()
        if brk_motor.lower() == 'nan':
            brk_motor = None
        dut_port = self.dut_port.get()
        try:
            dut_rate = self.dut_rate.get()
        except ValueError:
            dut_rate = None
        try:
            dut_id = self.dut_id.get()
        except ValueError:
            dut_id = None
        brk_port = self.brk_port.get()
        if brk_port.lower() == 'nan':
            brk_port = None
        try:
            brk_rate = self.brk_rate.get()
        except ValueError:
            brk_rate = None
        try:
            brk_id = self.brk_id.get()
        except ValueError:
            brk_id = None
        try:
            yoko_ip = self.yoko_ip.get()
        except ValueError:
            yoko_ip = 0
        upper_limit = self.speed_limit_upper.get()
        lower_limit = self.speed_limit_lower.get()
        torque_limit = self.torque_limit.get()
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        test = self.test.get()
        create_new_preset = False

        current_preset = self.configs.loc[self.config_value.get()]
        if (not _equal_config_value(dut_controller, current_preset['dut_controller']) or
                not _equal_config_value(brk_controller, current_preset['brk_controller']) or
                not _equal_config_value(dut_motor, current_preset['dut_motor']) or
                not _equal_config_value(brk_motor, current_preset['brk_motor']) or
                not _equal_config_value(test, current_preset['test']) or
                not _equal_config_value(dut_port, current_preset['dut_port']) or
                not _equal_config_value(dut_rate, float(current_preset['dut_baud'])) or
                not _equal_config_value(dut_id, float(current_preset['dut_id'])) or
                not _equal_config_value(brk_port, current_preset['brk_port']) or
                not _equal_config_value(brk_rate, float(current_preset['brk_baud'])) or
                not _equal_config_value(brk_id, float(current_preset['brk_id'])) or
                not _equal_config_value(yoko_ip, float(current_preset['yoko_ip'])) or
                not _equal_config_value(upper_limit, float(current_preset['upper_speed'])) or
                not _equal_config_value(lower_limit, float(current_preset['lower_speed'])) or
                not _equal_config_value(torque_limit, float(current_preset['max_torque']))):
            create_new_preset = True

        if create_new_preset:
            # try:
            #     new_name = parse(self.config_value.get().strip(), fuzzy_with_tokens=True)
            #     new_name = f'{" ".join([x.strip() for x in new_name[1]])} {start_time}'.strip()
            # except ParserError:
            #     new_name = f'{self.config_value.get()} {start_time}'
            new_name = f'{DYNO_SET}-{dut_controller}-{dut_motor}-{brk_controller}-{brk_motor}-{test} {start_time}'
            self.configs.loc[new_name] = self.configs.loc[self.config_value.get()]
            moving_list = self.configs.index.to_list()
            moving_list.insert(moving_list.index(self.config_value.get()) + 1, moving_list.pop(len(moving_list) - 1))
            self.configs = self.configs.reindex(moving_list)
            self.test_tab.children['test_btn_frame'].children['config_combo']['values'] = self.configs.index.to_list()
            self.config_value.set(new_name)

            # update to UI values
            self.configs.at[new_name, 'dut_port'] = dut_port
            self.configs.at[new_name, 'dut_baud'] = dut_rate
            self.configs.at[new_name, 'dut_id'] = dut_id
            self.configs.at[new_name, 'dut_controller'] = dut_controller
            self.configs.at[new_name, 'dut_motor'] = dut_motor
            self.configs.at[new_name, 'brk_port'] = brk_port
            self.configs.at[new_name, 'brk_baud'] = brk_rate
            self.configs.at[new_name, 'brk_id'] = brk_id
            self.configs.at[new_name, 'brk_controller'] = brk_controller
            self.configs.at[new_name, 'brk_motor'] = brk_motor
            self.configs.at[new_name, 'yoko_ip'] = yoko_ip
            self.configs.at[new_name, 'test'] = test
            self.configs.at[new_name, 'upper_speed'] = upper_limit
            self.configs.at[new_name, 'lower_speed'] = lower_limit
            self.configs.at[new_name, 'max_torque'] = torque_limit

            self._populate_config_list()
            self.configs.to_csv(f"{ROOT_DIR}/dyno_config.csv", mode='w')

    def _populate_config_list(self, event=None, *args, **kwargs):
        """
        GUI backend
        Populate configurations onto tester tab list - Updates connector info as well
        """
        if self.config_value.get() != "":
            output = self.configs.loc[self.config_value.get()]
            if self.dyno is None:
                pass
            else:
                self.dyno.config = output
            self._reset_config_list(output)
            
            # home screen elements
            if output["brk_controller"] == "ABB":
                self.abb.set(True)
                # self.main_elements['abb_remote_check']['state'] = NORMAL
                # self.main_elements['abb_local_check']['state'] = NORMAL
                self.main_elements['abb_mode_label']['state'] = NORMAL
                self.main_elements['abb_dir_label']['state'] = NORMAL
                self.main_elements['abb_dir']['state'] = NORMAL
                # self.main_elements['abb_mode']['state'] = NORMAL
                self.main_elements['brk_save2flash_btn']['state'] = DISABLED
                self.main_elements['brk_load_param_btn']['state'] = DISABLED
                self.main_elements['brk_save_param_btn']['state'] = DISABLED
                self.main_elements['brk_motor_discovery_btn_1']['state'] = DISABLED
                self.main_elements['brk_motor_discovery_btn_2']['state'] = DISABLED
            else:
                self.abb.set(False)
                # self.main_elements['abb_remote_check']['state'] = DISABLED
                # self.main_elements['abb_local_check']['state'] = DISABLED
                self.main_elements['abb_mode_label']['state'] = DISABLED
                self.main_elements['abb_dir_label']['state'] = DISABLED
                self.main_elements['abb_dir']['state'] = DISABLED
                # self.main_elements['abb_mode']['state'] = DISABLED
                self.main_elements['brk_save2flash_btn']['state'] = NORMAL
                self.main_elements['brk_load_param_btn']['state'] = NORMAL
                self.main_elements['brk_save_param_btn']['state'] = NORMAL
                self.main_elements['brk_motor_discovery_btn_1']['state'] = NORMAL
                self.main_elements['brk_motor_discovery_btn_2']['state'] = NORMAL

            # connection variables
            if pd.isna(output['dut_port']):
                self.dut_port.set(output["dut_port"])
            elif 'can' in output["dut_port"].lower():
                self.dut_port.set('CAN')
            else:
                self.dut_port.set(output["dut_port"])
            self.dut_rate.set(output["dut_baud"])
            self.dut_id.set(output["dut_id"])
            if pd.isna(output['brk_port']):
                self.brk_port.set(output["brk_port"])
            elif 'can' in output["brk_port"].lower():
                self.brk_port.set('CAN')
            else:
                self.brk_port.set(output["brk_port"])
            if pd.isna(output["brk_baud"]):
                self.brk_rate.set(output["brk_baud"])
            else:
                self.brk_rate.set(int(output["brk_baud"]))
            if pd.isna(output["brk_id"]):
                self.brk_id.set(output["brk_id"])
            else:
                self.brk_id.set(int(output["brk_id"]))
            self.yoko_ip.set(output["yoko_ip"])

            # update limits
            self.speed_limit_lower.set(output['lower_speed'])
            self.speed_limit_upper.set(output['upper_speed'])
            self.torque_limit.set(output['max_torque'])

            # for main gui parameters
            self.main_parameters['dut_controller'].set(output['dut_controller'])
            self.main_parameters['brk_controller'].set(output['brk_controller'])
            self.main_parameters['dut_motor'].set(output['dut_motor'])
            self.main_parameters['brk_motor'].set(output['brk_motor'])

            self.update_main_gui_controllers()
            self.main_elements['main_test_preset_tt'].msg = self.config_value.get()

            # self.edit_popup.set("Edit")
            if self.show_config:
                self.config_popup.lift()

    def _popup_config_list(self, event=None):
        """
        GUI backend
        Toggles config list popup on home screen
        """
        if self.show_config:
            self.show_config = False
            # self.test_tab.children['edit_config_btn'].grid_remove()
            self.config_popup.withdraw()
        else:
            self.show_config = True
            self._build_config_popup(self.root)
            # self.test_tab.children['edit_config_btn'].grid(
            #     column=0, row=13, columnspan=2, sticky='news')
            self.config_popup.deiconify()
            self._populate_config_list()
            self.config_popup.lift()
            self.config_popup.update_idletasks()

    def _popup_filter(self):
        """
        GUI front end
        Constructing filter popup for config list on test tab
        """
        def _pack_filter(master, index):
            temp = ttk.Label(popup.children[master], text=CONFIG_MAP[self.configs.columns[index]], anchor='center')
            temp.pack(fill='both')
            temp.bind('<MouseWheel>', temp.master.master.master.master.on_mousewheel)
            col_content = self.configs[self.configs.columns[index]]
            unique_values = col_content.unique().tolist()
            filtered_values = []
            for value in unique_values:
                if not pd.isna(value):
                    filtered_values.append(value)
            unique_values = filtered_values
            col_type = 'str'
            for content in unique_values:
                try:
                    int(float(content))
                except (ValueError, TypeError):
                    pass
                else:
                    col_type = 'number'
                    break
            if col_type == 'str':
                for i in range(len(unique_values)):
                    self.config_filter[f'{self.configs.columns[index]}_{i}'] = {'var': BooleanVar(value=False), 'value': unique_values[i]}
                    temp = ttk.Checkbutton(popup.children[master], text=unique_values[i], style='filter.TCheckbutton',
                                    variable=self.config_filter[f'{self.configs.columns[index]}_{i}']['var'],
                                    name=f'filter_{self.configs.columns[index]}_{unique_values[i]}')
                    temp.pack(anchor='w')
                    temp.bind('<MouseWheel>', temp.master.master.master.master.on_mousewheel)
            elif col_type == 'number':
                if len(unique_values) < 5:
                    for i in range(len(unique_values)):
                        self.config_filter[f'{self.configs.columns[index]}_{i}'] = {'var': BooleanVar(value=False), 'value': unique_values[i]}
                        temp = ttk.Checkbutton(popup.children[master], text=f'{unique_values[i]:.6g}', style='filter.TCheckbutton',
                                               variable=self.config_filter[f'{self.configs.columns[index]}_{i}']['var'],
                                               name=f'filter_{self.configs.columns[index]}_{i}')
                        temp.pack(anchor='w')
                        temp.bind('<MouseWheel>', temp.master.master.master.master.on_mousewheel)
                else:
                    min_value = min(unique_values)
                    max_value = max(unique_values)
                    inc = (max_value - min_value) / 4
                    for i in range(4):
                        self.config_filter[f'{self.configs.columns[index]}_{i}'] = {'var': BooleanVar(value=False),
                                                                           'value': [min_value + i * inc, min_value + (i + 1) * inc]}
                        temp = ttk.Checkbutton(popup.children[master], style='filter.TCheckbutton',
                                               text=f'{min_value + i * inc:.5g} to {min_value + (i + 1) * inc:<5g}',
                                               variable=self.config_filter[f'{self.configs.columns[index]}_{i}']['var'],
                                               name=f'filter_{self.configs.columns[index]}_{i}')
                        temp.pack(anchor='w')
                        temp.bind('<MouseWheel>', temp.master.master.master.master.on_mousewheel)

        top = Toplevel(self.root)
        top.resizable(True, True)
        top.columnconfigure(0, weight=1)
        popup = ScrollableFrame(top, width=1365, height=600)
        popup.grid(column=0, row=0, sticky='news')
        popup = popup.scrollable_frame
        ttk.Button(top, text='Apply', command=self._apply_filter).grid(column=0, row=1, sticky='news')
        ttk.Button(top, text='Reset', command=self._reset_filter).grid(column=0, row=2, sticky='news')
        self.config_filter = {}
        frames = ['COM', 'Basic', 'Cycle', 'Production/Rundown', 'Validation', 'ThermalMax', 'Life Test/Cyclic Test']
        for frame in frames:
            ttk.LabelFrame(popup, text=frame, name=f'filter_{frame.lower()}', padding='2 0 2 0').pack(fill='both', side='left')
            popup.children[f'filter_{frame.lower()}'].bind('<MouseWheel>',
                                                           popup.children[f'filter_{frame.lower()}'].master.master.master.on_mousewheel)
            # self.config_filter[f'filter_{frame.lower()}'] = {}
        for i in range(len(self.configs.columns)):
            if self.configs.columns[i].startswith('basic_'):
                _pack_filter('filter_basic', i)
            elif self.configs.columns[i].startswith('pt_'):
                _pack_filter('filter_production/rundown', i)
            elif self.configs.columns[i].startswith('pv_'):
                _pack_filter('filter_validation', i)
            elif self.configs.columns[i].startswith('ctm_'):
                _pack_filter('filter_thermalmax', i)
            elif self.configs.columns[i].startswith('cycle_'):
                _pack_filter('filter_cycle', i)
            elif self.configs.columns[i].startswith('jw_cyclic_'):
                _pack_filter('filter_life test/cyclic test', i)
            elif self.configs.columns[i] == 'Description':
                pass
            else:
                _pack_filter('filter_com', i)

    def _apply_filter(self):
        """
        GUI backend
        Applying filter to config list
        """
        filtered_configs = pd.DataFrame()
        for var in self.config_filter:
            param = '_'.join(var.split('_')[:-1])
            if self.config_filter[var]['var'].get():
                if isinstance(self.config_filter[var]['value'], list):
                    filtered_configs = pd.concat(
                        [filtered_configs,
                         self.configs.loc[self.configs[param].between(self.config_filter[var]['value'][0],
                                                                          self.config_filter[var]['value'][1])]])
                else:
                    filtered_configs = pd.concat(
                        [filtered_configs,
                         self.configs.loc[self.configs[param] == self.config_filter[var]['value']]])

        self.test_tab.children['test_btn_frame'].children['config_combo']['values'] = filtered_configs.index.to_list()

    def _reset_filter(self):
        """
        GUI backend 
        Resets filter for config list
        """
        for var in self.config_filter:
            self.config_filter[var]['var'].set(False)
        self.test_tab.children['test_btn_frame'].children['config_combo']['values'] = self.configs.index.to_list()

    def _new_yoko(self):
        """
        GUI backend
        Update all associated yoko_ip on config list
        """
        if self.config_value.get() == "":
            self.config_value.set('default')
            self._populate_config_list()
        if int(self.configs.loc[self.config_value.get(), 'yoko_ip']) != int(self.yoko_ip.get()):
            # messagebox.showinfo("New YOKOGAWA IP Detected!", "Updating new YOKOGAWA IP address to file")
            dyno = str(self.configs.loc[self.config_value.get(), 'dyno'])
            self.configs['yoko_ip'].replace(
                [self.configs.loc[self.configs['dyno'] == dyno, 'yoko_ip']], int(self.yoko_ip.get()), inplace=True)
            self.configs.to_csv("dyno_config.csv", mode='w')
            logging.info("YOKOGAWA IP updated")
            self._populate_config_list()

    def _new_dut(self):
        """
        GUI backend
        Update all associated dut_port
        """
        if self.config_value.get() == "":
            self.config_value.set('default')
            self._populate_config_list()
        if self.dut_port.get() != 'CAN' and self.configs.loc[self.config_value.get(), 'dut_port'] != self.dut_port.get():
            # messagebox.showinfo("New COM device Detected!", "Updating new DUT COM Port to file")
            dyno = str(self.configs.loc[self.config_value.get(), 'dyno'])
            old = str(self.configs.loc[self.config_value.get(), 'dut_port'])
            self.configs['dut_port'] = np.where((self.configs['dyno'] == dyno) & (self.configs['dut_port'] == old),
                                                self.dut_port.get(), self.configs['dut_port'])
            # self.configs['dut_port'].replace(
            #     [self.configs.loc[self.configs['Dyno'] == dyno, 'dut_port']], self.dut_port.get(), inplace=True)
            self.configs.to_csv("dyno_config.csv", mode='w')
            logging.info("DUT COM Port updated")
            self._populate_config_list()

    def _new_brk(self):
        """
        GUI backend
        Update all associated brk_port
        """
        if self.config_value.get() == "":
            self.config_value.set('default')
            self._populate_config_list()
        if self.brk_port.get() != 'CAN' and self.configs.loc[self.config_value.get(), 'brk_port'] != self.brk_port.get():
            # messagebox.showinfo("New COM Device Detected!", "Updating new BRK COM Port to file")
            dyno = str(self.configs.loc[self.config_value.get(), 'dyno'])
            old = str(self.configs.loc[self.config_value.get(), 'brk_port'])
            self.configs['brk_port'] = np.where((self.configs['dyno'] == dyno) & (self.configs['brk_port'] == old),
                                                self.brk_port.get(), self.configs['brk_port'])
            # self.configs['brk_port'].replace(
            #     [self.configs.loc[self.configs['Dyno'] == dyno, 'brk_port']], self.brk_port.get(), inplace=True)
            self.configs.to_csv("dyno_config.csv", mode='w')
            logging.info("BRK COM Port updated")
            self._populate_config_list()

    def _update_connection_status(self, mainframe):
        """
        GUI backend + dyno devices' connection check
        checks and updates status indicators for DUT/BRK/YOKO
        """
        if self.dyno is not None:
            if self.dyno.devices[1] is not None:
                if (hasattr(self.dyno.devices[1], 'can_bus') and
                    not self.dyno.devices[1].can_bus.disconnected) or (hasattr(self.dyno.devices[1], 'modbus') and
                                                                hasattr(self.dyno.devices[1].modbus, 'modbus')):
                    self.connection_status[0].set(True)
            if self.dyno.devices[2] is not None:
                if not self.abb.get():
                    if (hasattr(self.dyno.devices[2], 'can_bus') and not self.dyno.devices[2].can_bus.disconnected) or (
                            hasattr(self.dyno.devices[2], 'modbus') and hasattr(self.dyno.devices[2].modbus, 'modbus')):
                        self.connection_status[1].set(True)
                else:
                    if hasattr(self.dyno.devices[2].device, 'modbus'):
                        self.connector_tab.children['abb_toggle_btn']['state'] = NORMAL
                        self.connection_status[1].set(True)
            if self.dyno.devices[PA] is not None:
                if hasattr(self.dyno.devices[PA], 'device'):
                    self.connection_status[2].set(True)
                    
        # update connection tab indicators
        for i in range(3):
            canvas = Canvas(mainframe, width=20, height=20, background='white', borderwidth=0,
                            highlightthickness=0, relief='flat', name=f'status_{i}')
            canvas.grid(column=8, row=7 + i, sticky='news', pady=5)
            canvas.create_oval(2, 2, 18, 18, fill=f"{'green' if self.connection_status[i].get() else 'red'}")
        # for i, j in zip(['dut_indicator', 'brk_indicator', 'yoko_indicator'], self.connection_status):
        #     if j.get():
        #         self.main_elements[i].status = j.get()
        #         self.main_elements[i].update_status()

    def update_main(self, event=None):
        """
        GUI backend
        Update home screen device and button states based on dyno_set selection
        """
        # if self.main_parameters['dyno_set'].get() == DYNO_SET:
        #     self.configs.loc['default']['dut_controller'] = self.main_parameters['dut_controller'].get()
        #     self.configs.loc['default']['brk_controller'] = self.main_parameters['brk_controller'].get()
        #     self.configs.loc['default']['dut_motor'] = self.main_parameters['dut_motor'].get()
        #     self.configs.loc['default']['brk_motor'] = self.main_parameters['brk_motor'].get()
        #     self.config_value.set('default')
        # elif self.main_parameters['dut_controller'].get() in ASI_CONTROLLERS and \
        #         self.main_parameters['brk_controller'].get() in ASI_CONTROLLERS:
        #     self.configs.loc['BAC2BAC']['dut_controller'] = self.main_parameters['dut_controller'].get()
        #     self.configs.loc['BAC2BAC']['brk_controller'] = self.main_parameters['brk_controller'].get()
        #     self.configs.loc['BAC2BAC']['dut_motor'] = self.main_parameters['dut_motor'].get()
        #     self.configs.loc['BAC2BAC']['brk_motor'] = self.main_parameters['brk_motor'].get()
        #     self.config_value.set('BAC2BAC')

        if self.main_parameters['brk_controller'].get() == 'ABB':
            # self.main_elements['abb_remote_check']['state'] = NORMAL
            # self.main_elements['abb_local_check']['state'] = NORMAL
            self.main_elements['abb_mode_label']['state'] = NORMAL
            self.main_elements['abb_dir_label']['state'] = NORMAL
            self.main_elements['abb_dir']['state'] = NORMAL
            self.main_elements['abb_limit_label']['state'] = NORMAL
            self.main_elements['abb_limit']['state'] = NORMAL
            # self.main_elements['abb_mode']['state'] = NORMAL
            self.main_elements['abb_local_toggle']['state'] = NORMAL
            self.main_elements['abb_speed_torque_toggle']['state'] = NORMAL
        else:
            # self.main_elements['abb_remote_check']['state'] = DISABLED
            # self.main_elements['abb_local_check']['state'] = DISABLED
            self.main_elements['abb_mode_label']['state'] = DISABLED
            self.main_elements['abb_dir_label']['state'] = DISABLED
            self.main_elements['abb_dir']['state'] = DISABLED
            self.main_elements['abb_limit_label']['state'] = DISABLED
            self.main_elements['abb_limit']['state'] = DISABLED
            # self.main_elements['abb_mode']['state'] = DISABLED
            self.main_elements['abb_local_toggle']['state'] = DISABLED
            self.main_elements['abb_speed_torque_toggle']['state'] = DISABLED

        # for button states
        if self.dyno:
            if isinstance(self.dyno.devices[2], AbbAcs800):
                self.main_elements['set_dir_btn']['state'] = DISABLED
                self.main_elements['brk_save2flash_btn']['state'] = DISABLED
                self.main_elements['brk_load_param_btn']['state'] = DISABLED
                self.main_elements['brk_save_param_btn']['state'] = DISABLED
                self.main_elements['brk_motor_discovery_btn_1']['state'] = DISABLED
                self.main_elements['brk_motor_discovery_btn_2']['state'] = DISABLED

            elif isinstance(self.dyno.devices[2], ASIController):
                self.main_elements['set_dir_btn']['state'] = NORMAL
                self.main_elements['brk_save2flash_btn']['state'] = NORMAL
                self.main_elements['brk_load_param_btn']['state'] = NORMAL
                self.main_elements['brk_save_param_btn']['state'] = NORMAL
                self.main_elements['brk_motor_discovery_btn_1']['state'] = NORMAL
                self.main_elements['brk_motor_discovery_btn_2']['state'] = NORMAL

        self.update_main_gui_controllers()

    def update_main_gui_controllers(self):
        """
        GUI backend
        Update home screen dyno_gui based on controller selection
        """
        self.dyno_gui.dut_controller.update_device(self.main_parameters['dut_controller'].get())
        self.dyno_gui.brk_controller.update_device(self.main_parameters['brk_controller'].get())

    def update_main_set(self, event=None):
        """
        GUI backend 
        Updates home screen based on dyno_set selection - all-in-one
        """
        if self.main_parameters['dyno_set'].get() == DYNO_SET:
            self.config_value.set('default')
            self.main_parameters['dut_controller'].set(self.configs.loc['default']['dut_controller'])
            self.main_parameters['brk_controller'].set(self.configs.loc['default']['brk_controller'])
            self.main_parameters['dut_motor'].set(self.configs.loc['default']['dut_motor'])
            self.main_parameters['brk_motor'].set(self.configs.loc['default']['brk_motor'])
        elif self.main_parameters['dyno_set'].get() == 'BAC2BAC':
            self.config_value.set('BAC2BAC')
            self.main_parameters['dut_controller'].set(self.configs.loc['BAC2BAC']['dut_controller'])
            self.main_parameters['brk_controller'].set(self.configs.loc['BAC2BAC']['brk_controller'])
            self.main_parameters['dut_motor'].set(self.configs.loc['BAC2BAC']['dut_motor'])
            self.main_parameters['brk_motor'].set(self.configs.loc['BAC2BAC']['brk_motor'])

        self.update_main_gui_controllers()
        self._populate_config_list()

    def post_main_connect(self):
        """
        GUI backend
        Affix to on_connect for home screen update
        """
        if self.dyno and self.connection_condition.get() not in ['CONNECT']: # Connecting

            # Update status
            if self.dyno.devices[1]:
                self.main_elements['dut_indicator'].status = True
            else:
                self.main_elements['dut_indicator'].status = False
            self.main_elements['dut_check']['state'] = DISABLED

            if self.dyno.devices[2]:
                self.main_elements['brk_indicator'].status = True
            else:
                self.main_elements['brk_indicator'].status = False
            self.main_elements['brk_check']['state'] = DISABLED

            if self.dyno.devices[PA]:
                self.main_elements['yoko_indicator'].status = True
                self.dyno_gui.yoko.start_yoko()
            else:
                self.main_elements['yoko_indicator'].status = False
                self.dyno_gui.yoko.disable_yoko()
            self.main_elements['yoko_check']['state'] = DISABLED


            self.main_elements['start_logging']['state'] = NORMAL

            # Link main elements to new dyno
            temp_widget = self.main_elements['brk_torque']

            def upload(event=None):

                def action():
                    # if self.brk_torque_timeout_id is not None:
                    #     self.root.after_cancel(self.brk_torque_timeout_id)
                    if isinstance(self.dyno.devices[2], ASIController):
                        self.calc_torque.set(temp_widget.textvariable.get())
                        self.dyno.devices[2].set_torque(temp_widget.textvariable.get())
                    elif isinstance(self.dyno.devices[2], AbbAcs800):
                        if self.dyno.devices[2].mode == 'torque':
                            self.controller_params['ABB']["Torque"].set(temp_widget.textvariable.get())
                            self.controller_params['ABB']["Speed"].set(0)
                            self.dyno.devices[2].set_torque(
                                _param_value_handler(self.controller_params['ABB']["Torque"].get()))
                            self.dyno.devices[2].set_rpm(0)
                        else:
                            self.controller_params['ABB']["Speed"].set(temp_widget.textvariable.get())
                            self.controller_params['ABB']["Torque"].set(0)
                            self.dyno.devices[2].set_rpm(
                                _param_value_handler(self.controller_params['ABB']["Speed"].get()))
                            self.dyno.devices[2].set_torque(0)

                Thread(target=action).start()

            def inc_torque(value):
                prev = temp_widget.textvariable.get()
                temp_widget.textvariable.set(prev + value)
                upload()

            def dec_torque(value):
                prev = temp_widget.textvariable.get()
                temp_widget.textvariable.set(prev - value)
                upload()

            def zero(event=None):
                temp_widget.textvariable.set(0)
                upload()

            # def brake_torque_changed(*args):
            #     if self.brk_torque_timeout_id:
            #         self.root.after_cancel(self.brk_torque_timeout_id)
            #     try:
            #         self.main_parameters['brk_torque'].get()
            #     except TclError:
            #         pass
            #     else:
            #         self.brk_torque_timeout_id = self.root.after(1000, upload)

            temp_widget.inc_torque = inc_torque
            temp_widget.dec_torque = dec_torque
            temp_widget.reset.canvas.bind('<Button-1>', zero)
            # temp_widget.up_leap = up_leap
            # temp_widget.down_leap = down_leap
            temp_widget.entry.bind('<Return>', upload)
            # self.main_parameters['brk_torque'].trace('w', brake_torque_changed)

            self.update_main()
            self._update_main()

            if self.dyno.devices[1] is not None:
                mode = self.dyno.devices[1].read('Test mode')
                if mode == 0:
                    mode = self.dyno.devices[1].read('Speed regulator mode')
                    if mode == 0:
                        self.main_parameters['dut_main_spin_mode'].set('Speed')
                    elif mode == 1:
                        self.main_parameters['dut_main_spin_mode'].set('Torque')
                    elif mode == 2:
                        self.main_parameters['dut_main_spin_mode'].set('Torque with speed limit')
                elif mode == 2:
                    self.main_parameters['dut_main_spin_mode'].set('Open loop voltage')
                elif mode == 3:
                    self.main_parameters['dut_main_spin_mode'].set('Open loop current')
                for p in MAIN_SPIN_PARAMETERS:
                    self.main_parameters[p].set(self.dyno.devices[1].read(MAIN_SPIN_PARAMETERS[p]))

            self._update_main_spin()
            if self.dyno.devices[2] and isinstance(self.dyno.devices[2], ASIController):
                for frame in ['brk_motor_param_frame', 'brk_motor_halls_frame']:
                    for child in self.main_elements[frame].winfo_children():
                        child.config(state=NORMAL)
            else:
                for frame in ['brk_motor_param_frame', 'brk_motor_halls_frame']:
                    for child in self.main_elements[frame].winfo_children():
                        child.config(state=DISABLED)
            self._start_live()

        elif self.connection_condition.get() == 'CONNECT': # Disconnecting
            self.main_elements['dut_indicator'].status = False
            self.main_elements['brk_indicator'].status = False
            self.main_elements['yoko_indicator'].status = False
            self.main_elements['dut_check']['state'] = NORMAL
            self.main_elements['brk_check']['state'] = NORMAL
            self.main_elements['yoko_check']['state'] = NORMAL
            if self.dyno_gui.yoko.state > 0:
                self.dyno_gui.yoko.stop_yoko()
            # self.dyno_gui.yoko.enable_yoko()

        self.main_elements['dut_indicator'].update_status()
        self.main_elements['brk_indicator'].update_status()
        self.main_elements['yoko_indicator'].update_status()

    def pre_main_connect(self):
        """
        GUI backend
        Prefix to on_connect for home screen update
        """
        if self.connection_condition.get() == 'CONNECT': # Connecting
            pass
        elif self.connection_condition.get() != 'CONNECT': # Disconnecting
            self._end_live()

    def pre_main_run_script(self):
        """
        GUI backend
        Prefix to _run_script (beta)
        Construct config line for dyno test based on home screen selection
        """
        self._construct_config_list()

    def toggle_yoko(self):
        """
        GUI backend
        Toggle dyno_gui yoko state
        """
        if self.yoko_var.get():
            self.dyno_gui.yoko.enable_yoko()
        else:
            self.dyno_gui.yoko.disable_yoko()

    def toggle_status_bar(self):
        """
        GUI backend
        Toggle status bar
        """
        if self.dyno:
            if self.status_bar:
                self._stop_status_thread()
                self.status_bar.master.destroy()
                self.status_bar = None
            else:
                self.build_status_bar()

    def _main_connect(self):
        """
        GUI backend
        New connection methods since 0.7
        """
        self.pre_main_connect()
        self._on_connect()
        self.post_main_connect()

    def _on_connect(self):
        """
        GUI backend + dyno devices' connection check
        Connect/Disconnect button
        """
        def action():
            logging.info("_on_connect called")

            if self.connection_condition.get() == "CONNECT":  # Connecting
                logging.info("Connection Attempted")
                self.dyno = None
                dut = None
                brk = None
                yoko = None
                logging.info("Connection Reset!")
                self.connection_condition.set("CONNECTING...")
                # DUT
                if self.dut_var.get():
                    logging.info("Connecting to DUT")
                    try:
                        if 'can' in self.dut_port.get().lower() or 'default' in self.dut_port.get():
                            logging.info("Connecting via CAN")
                            if 'can' in self.brk_port.get().lower() or 'default' in self.brk_port.get():
                                dut = ASIController(com_port='PCAN_USBBUS1', baud_rate=self.dut_rate.get(),
                                                    mb_address=[self.dut_id.get(), self.brk_id.get()],
                                                    is_can=True, root=ROOT_DIR)
                            else:
                                dut = ASIController(com_port='PCAN_USBBUS1', baud_rate=self.dut_rate.get(),
                                                    mb_address=self.dut_id.get(), is_can=True, root=ROOT_DIR)
                        else:
                            logging.info("Connecting via TTL")
                            dut = ASIController(com_port=self.dut_port.get(), baud_rate=self.dut_rate.get(),
                                                mb_address=self.dut_id.get(), root=ROOT_DIR)
                    except ConnectionError:
                        print("Connection to DUT failed!")

                    if (hasattr(dut, 'can_bus') and not dut.can_bus.disconnected) or \
                            (hasattr(dut, 'modbus') and hasattr(dut.modbus, 'modbus')) and \
                            (dut.firmware != 0 and dut.firmware is not None):
                        self.connection_status[0].set(True)
                        logging.info("Connected to DUT")
                        print(dut)
                        self._new_dut()
                    else:
                        print("Error: Bad Connection with driver! Please retry!")
                        self.connection_condition.set("CONNECT")
                        logging.info("Connection Failed")
                        self.testing = False
                        return
                # BRK
                if self.brk_var.get() and self.brk_port.get() != "nan":
                    logging.info("Connecting to BRK")
                    if self.abb.get():
                        logging.info("Connecting to ABB")
                        self.main_parameters['abb_dir'].set("FORWARD")
                        self.main_parameters['abb_limit'].set("REVERSE")
                        try:
                            brk = AbbAcs800(port=self.brk_port.get(),
                                            baud=self.brk_rate.get(),
                                            auto=self.abb_auto.get(),
                                            mode=self.main_parameters['abb_speed_torque'].get().lower(),
                                            root=ROOT_DIR)
                        except ConnectionError:
                            print('Connecting to BRK failed!')

                        if hasattr(brk.device, 'modbus'):
                            self.connector_tab.children['abb_toggle_btn']['state'] = NORMAL
                            self.connection_status[1].set(True)
                            logging.info("Connected to ABB")
                            print(brk)
                            self._new_brk()
                        else:
                            print("Error: Bad Connection with brake! Please retry!")
                            self.connection_condition.set("CONNECT")
                            logging.info("Connection Failed")
                            self.testing = False
                            return
                    else:
                        logging.info("Connecting to ASI Controller")
                        try:
                            if 'can' in self.brk_port.get().lower() and \
                                    ('can' not in self.dut_port.get().lower() or not self.dut_var.get()):
                                logging.info("Connecting via CAN")
                                brk = ASIController(com_port='PCAN_USBBUS1', baud_rate=self.brk_rate.get(),
                                                    mb_address=self.brk_id.get(), is_can=True, root=ROOT_DIR)
                                brk.can_bus.can_pdo_handle = brk.can_pdo_handle
                            elif 'can' in self.brk_port.get().lower() and \
                                    ('can' in self.dut_port.get().lower() and self.dut_var.get()):
                                logging.info("Connecting 2 devices via CAN")
                                brk = ASIController(is_can=True, root=ROOT_DIR, baud_rate=self.brk_rate.get(),
                                                    secondary=self.brk_id.get(), can_bus=dut.can_bus)
                                dut.can_bus.can_pdo_handle = dut.can_pdo_handle
                            else:
                                logging.info("Connecting via TTL")
                                brk = ASIController(com_port=self.brk_port.get(), baud_rate=self.brk_rate.get(),
                                                    mb_address=self.brk_id.get(), root=ROOT_DIR)
                        except ConnectionError:
                            print('Connection to BRK failed!')

                        if (hasattr(brk, 'can_bus') and not brk.can_bus.disconnected) or (
                                hasattr(brk, 'modbus') and hasattr(brk.modbus, 'modbus')) and \
                                (brk.firmware != 0 and brk.firmware is not None):
                            self.connection_status[1].set(True)
                            logging.info("Connected to BRK")
                            print(brk)
                            self._new_brk()
                        else:
                            print("Error: Bad Connection with brake! Please retry!")
                            self.connection_condition.set("CONNECT")
                            logging.info("Connection Failed")
                            self.testing = False
                            return
                # YOKO
                if self.yoko_var.get() and self.yoko_ip.get() != 0:
                    logging.info("Connecting to YOKOGAWA")
                    try:
                        yoko = Yokogawa_WT1806(IP=f"192.168.1.{self.yoko_ip.get()}",
                                               file=YOKO_PARAMETER_FILE)
                    except ConnectionError:
                        print("Connection to Yokogawa failed!")
                        self.connection_condition.set("CONNECT")

                    if hasattr(yoko, 'device'):
                        self.connection_status[2].set(True)
                        logging.info("Connected to YOKOGAWA")
                        print(yoko)
                        self._new_yoko()
                    else:
                        print("Error: Bad Connection with YOKOGAWA! Please retry!")
                        self.connection_condition.set("CONNECT")
                        logging.info("Connection Failed")
                        self.testing = False
                        return
                try:
                    self.dyno = ASIDynoModule(dut=dut, brake=brk, yoko=yoko, root=ROOT_DIR,
                                              enable_email=self.enable_email.get(),
                                              enable_int_email=self.enable_int_email.get())
                except TypeError as e:
                    self.connection_condition.set("CONNECT")
                    self.connection_status[0].set(False)
                    self.connection_status[1].set(False)
                    self.connection_status[2].set(False)
                    logging.info(f"Failed to create DynoModule: {e}")
                    self.testing = False
                    return
                else:
                    self._update_limits()
                    logging.info("DynoModule created successfully")
                    self.connection_condition.set("DISCONNECT")
                    # self.controller_tab.children['rest_frame'].children['start_log_btn']['state'] = NORMAL
                    self._init_graphing()

                self._update_connection_status(self.connector_tab)
                self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame_1,
                                                  self.brk_extra_frame_1, self.dut_extra_frame, self.brk_extra_frame],
                                                 ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                                  "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}",
                                                  "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}"],
                                                 CONTROL_PARAM_INIT)
                logging.info("Control parameters initialized")
                # self._controller_read()
                # self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                #                                   self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                #                                  ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                #                                   "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                #                                   "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                #                                  CONTROL_PARAM_UPDATE)
                Thread(target=lambda : self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                                                  self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                                                                        ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                                  "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                  "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                                        CONTROL_PARAM_UPDATE)).start()

                logging.info("Control parameters updated")
                if self.status_bar:
                    self._start_status_thread()
                self.controller_tab.children['start_btn']['state'] = NORMAL
                self.test_tab.children['test_btn_frame'].children['stop_btn']['state'] = NORMAL
                self.controller_tab.children['dut_motor_discovery_btn_1']['state'] = NORMAL
                self.controller_tab.children['brk_motor_discovery_btn_1']['state'] = NORMAL
                self.controller_tab.children['dut_motor_discovery_btn_2']['state'] = NORMAL
                self.controller_tab.children['brk_motor_discovery_btn_2']['state'] = NORMAL
                # self.advanced_tab.children['dut_motor_discovery_btn_3']['state'] = NORMAL
                # self.advanced_tab.children['brk_motor_discovery_btn_3']['state'] = NORMAL

                return

            if (self.connection_condition.get() == "DISCONNECT"
                  or self.connection_condition.get() == "TESTING"
                  or self.connection_condition.get() == "CONNECTING..."):  # Disconnecting
                logging.info("Disconnect Attempted")
                self.connection_condition.set("DISCONNECTING...")
                self._stop_status_thread()
                self.testing = False
                self.cyclic = False
                self._stop_logging()
                self._end_graphing()
                try:
                    self.test_handler.interrupt()
                except (AttributeError, TestInterrupt):
                    pass
                else:
                    logging.info("Test interrupted while disconnecting")
                    self.test_handler = None

                if self.dyno:
                    self.dyno.__del__()

                # if self.connection_status[0].get() or self.connection_status[1].get():
                #     try:
                #         self._stop_logging()
                #     except (AttributeError, CommLossError):
                #         pass
                #     self._close_can_interface()
                #     self._dyno_stop()
                #     try:
                #         if self.dyno.devices[1].can:
                #             self.dyno.devices[1].can_bus.__del__()
                #             # if self.dyno is not None and self.dyno.devices[1] is not None:
                #
                #         # else:
                #
                #     except (AttributeError, CommLossError):
                #         pass
                #
                #     try:
                #         self.dyno.devices[1].__del__()
                #         self.dyno.devices[1] = None
                #     except (ValueError, AttributeError, CommLossError):
                #         pass
                #     else:
                #         logging.info("DUT reset")
                #     try:
                #         if self.dyno.devices[2].can:
                #             self.dyno.devices[2].can_bus.__del__()
                #         else:
                #             self.dyno.devices[2].__del__()
                #             self.dyno.devices[2] = None
                #     except (ValueError, AttributeError):
                #         pass
                #     else:
                #         logging.info("BRK reset")
                # if self.connection_status[2].get():
                #     try:
                #         self.dyno.devices[PA] = None
                #     except (ValueError, AttributeError):
                #         pass
                #     else:
                #         logging.info("YOKOGAWA reset")
                try:
                    # self.dyno.__del__()
                    self.dyno = None
                except (ValueError, AttributeError):
                    pass
                else:
                    logging.info("DYNO reset")
                finally:
                    for i in range(3):
                        self.connection_status[i].set(False)
                    self._update_connection_status(self.connector_tab)
                    # self.controller_tab.children['rest_frame'].children['start_log_btn']['state'] = DISABLED
                    self.connector_tab.children['abb_toggle_btn']['state'] = DISABLED
                    self.connection_condition.set("CONNECT")
                    self.test_tab.children['test_btn_frame'].children['stop_btn']['state'] = NORMAL
                    self.controller_tab.children['dut_motor_discovery_btn_1']['state'] = NORMAL
                    self.controller_tab.children['brk_motor_discovery_btn_1']['state'] = NORMAL
                    self.controller_tab.children['dut_motor_discovery_btn_2']['state'] = NORMAL
                    self.controller_tab.children['brk_motor_discovery_btn_2']['state'] = NORMAL
                    # self.advanced_tab.children['dut_motor_discovery_btn_3']['state'] = NORMAL
                    # self.advanced_tab.children['brk_motor_discovery_btn_3']['state'] = NORMAL
                    # self.bac_2_bac.set('Disable')
                    # self._bac_2_bac()
                print('Disconnected!')
                logging.info("Disconnected")

        action()

    def _close_can_interface(self):
        """
        GUI backend
        Closing popup for CAN interface
        """
        if self.can_interface is not None:
            self.can_interface.device.can_bus.__del__()
            self.can_interface.root.destroy()
            self.can_interface = None

    def _update_limits(self):
        """
        GUI backend
        Updates GUI limits with dyno limits
        """
        if self.dyno:
            self.speed_limit_lower.set(self.dyno.speed_limit_lower)
            self.speed_limit_upper.set(self.dyno.speed_limit_upper)
            self.torque_limit.set(self.dyno.torque_limit)

    def _upload_limits(self):
        """
        GUI backend
        Uploads GUI limits to dyno
        """
        if self.dyno:
            self.dyno.speed_limit_upper = self.speed_limit_upper.get()
            self.dyno.speed_limit_lower = self.speed_limit_lower.get()
            self.dyno.torque_limit = self.torque_limit.get()

    def _limit_changed(self, *args):
        """
        GUI backend
        Upload brake torque on text change
        """
        if self.limit_timeout_id:
            self.root.after_cancel(self.limit_timeout_id)
        if self.speed_limit_upper.get() != 0 and self.speed_limit_lower.get() != 0 and self.torque_limit.get() != 0:
            self.limit_timeout_id = self.root.after(500, self._upload_limits)

    def _dyno_start(self):
        """
        GUI backend + Dyno start sequence
        Starts logging - 2 sec - start_remote_motor for DUT
        """
        if self.dyno.devices[1] is not None:
            logging.info('Dyno Module Start Sequence Initiated')
            self.controller_tab.children['start_btn']['state'] = DISABLED
            print("Dyno Module Start Sequence Initiated!")
            try:
                self._start_logging()
                sleep(2)
                self.dyno.devices[1].start_remote_motor()
                Thread(target=self.controller_params_operation([self.dut_frame, self.dut_extra_frame, self.dut_extra_frame_1],
                                                                             ["DUT", "DUT_EXT", "DUT_EXT_EXT"],
                                                                             CONTROL_PARAM_UPDATE)).start()
            except AttributeError:
                pass
            finally:
                self.controller_tab.children['start_btn']['state'] = NORMAL
                self.main_gui_start()

    def main_gui_start(self, device='DUT'):
        """
        GUI backend
        Starting home screen dyno_gui animation
        """
        if device == 'DUT':
            if self.dyno.devices[1]:
                self.dyno_gui.dut.start_motor()
                command = self.dyno.devices[1].read('Remote speed command')
                rpm = self.dyno.devices[1].read('Remote Speed Command in RPM')
                if command == 0 and rpm == 0:
                    self.dyno_gui.dut.update_direction(0)
                elif command > 0 or rpm > 0:
                    self.dyno_gui.dut.update_direction(1)
                elif command < 0 or rpm < 0:
                    self.dyno_gui.dut.update_direction(-1)
        else:
            self.dyno_gui.brk.start_motor()
            if isinstance(self.dyno.devices[2], ASIController):
                command = self.dyno.devices[2].read('Remote speed command')
                rpm = self.dyno.devices[2].read('Remote Speed Command in RPM')
                if command == 0 and rpm == 0:
                    self.dyno_gui.brk.update_direction(0)
                elif command > 0 or rpm > 0:
                    self.dyno_gui.brk.update_direction(1)
                elif command < 0 or rpm < 0:
                    self.dyno_gui.brk.update_direction(-1)
            else:
                self.dyno_gui.brk.update_direction(1)

    def _dut_start(self):
        """
        GUI backend 
        start_remote_motor for DUT
        """
        if self.dyno.devices[1] is not None:
            self.dyno.devices[1].start_remote_motor()
            Thread(target=lambda :self.controller_params_operation([self.dut_frame, self.dut_extra_frame, self.dut_extra_frame_1],
                                                                                 ["DUT", "DUT_EXT", "DUT_EXT_EXT"],
                                                                                 CONTROL_PARAM_UPDATE)).start()
        self.main_gui_start()

    def _dut_stop(self):
        """
        GUI backend
        stop_remote_motor for DUT
        """
        if self.dyno.devices[1] is not None:
            self.dyno.devices[1].stop_remote_motor()
            Thread(target=lambda :self.controller_params_operation([self.dut_frame, self.dut_extra_frame, self.dut_extra_frame_1],
                                                                                 ["DUT", "DUT_EXT", "DUT_EXT_EXT"],
                                                                                 CONTROL_PARAM_UPDATE)).start()

            self.dyno_gui.dut.stop_motor()

    def _dut_idle(self):
        """
        GUI backend
        idle_remote_motor for DUT
        """
        if self.dyno.devices[1] is not None:
            self.dyno.devices[1].idle_remote_motor()
            Thread(target=lambda :self.controller_params_operation([self.dut_frame, self.dut_extra_frame, self.dut_extra_frame_1],
                                                                                 ["DUT", "DUT_EXT", "DUT_EXT_EXT"],
                                                                                 CONTROL_PARAM_UPDATE)).start()

            self.dyno_gui.dut.stop_motor()

    def _brk_start(self):
        """
        GUI backend
        Starts brake
        """
        if self.dyno.devices[2] is not None:
            self.dyno.devices[2].start()
            self.update_brk_torque()
            temp_thread = Thread(target=lambda :self.controller_params_operation([self.brk_frame,
                                                                                  self.brk_extra_frame,
                                                                                  self.brk_extra_frame_1],
                                                                                 [f"{'ABB' if self.abb.get() else 'BRK'}",
                                                                                  f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                                                  f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                                                 CONTROL_PARAM_UPDATE))
            temp_thread.start()

            self.main_gui_brk_start()

    def main_gui_brk_start(self):
        """
        GUI backend 
        Command for home screen brake start
        """
        if self.dyno.devices[2]:
            if self.dyno.devices[1]:
                self.dyno_gui.brk.start_motor()
                self.dyno_gui.brk.update_direction(self.dyno_gui.dut.direction)
            else:
                self.main_gui_start('BRK')

    def _brk_stop(self):
        """
        GUI backend
        Stops brake
        """
        if self.dyno.devices[2] is not None:
            self.dyno.devices[2].stop()
            temp_thread = Thread(target=lambda: self.controller_params_operation([self.brk_frame,
                                                                                  self.brk_extra_frame,
                                                                                  self.brk_extra_frame_1],
                                                                                 [f"{'ABB' if self.abb.get() else 'BRK'}",
                                                                                  f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                                                  f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                                                 CONTROL_PARAM_UPDATE))
            temp_thread.start()

            self.dyno_gui.brk.stop_motor()

    def _gui_motor_discovery(self, device, mode):
        """
        GUI backend + popup
        Motor discovery for DUT
        """
        if self.dyno.devices[device] is not None and not self.testing:
            popup = Toplevel(self.root, background='#ccccff' if device == 1 else '#ccffcc')
            popup.attributes('-topmost', 'true')
            popup.geometry(f'400x500+10+10')
            popup.resizable(True, True)
            popup.columnconfigure(0, weight=1)
            popup.rowconfigure(1, weight=1)
            label_text = StringVar(value='Motor Discovery')
            Label(popup, textvariable=label_text, background='#ccccff' if device == 1 else '#ccffcc',
                  anchor='center', pady=5, font=f'{OPTION_FONT_NAME} 15 bold').grid(
                column=0, row=0, sticky='news')
            popup.bind('<Escape>', self.dyno.devices[device].stop_motor_discovery)
            Button(popup, text='Interrupt', command=self.dyno.devices[device].stop_motor_discovery,
                   background='red', activebackground='red', foreground='white', activeforeground='white').grid(
                column=0, row=3, sticky='news')

            container = Frame(popup, background='#ccccff' if device == 1 else '#ccffcc')
            container.grid(column=0, row=2)
            container.columnconfigure((0, 1, 2, 3), weight=1)
            values = []
            checked = []
            if mode == 1:
                for _ in range(2):
                    values.append(StringVar())
                    checked.append(BooleanVar(value=True))
                Checkbutton(container, onvalue=True, variable=checked[0],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(
                    column=0, row=0)
                Label(container, text="autotune Rs", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=0, sticky='e')
                Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=2, row=0, sticky='we')
                Label(container, text="m\u03A9", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=0, sticky='w')

                Checkbutton(container, onvalue=True, variable=checked[1],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=1)
                Label(container, text="autotune Ls", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=1, sticky='we')
                Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=2, row=1, sticky='we')
                Label(container, text="\u03BCH", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=1, sticky='w')
            elif mode == 2:
                for _ in range(10):
                    values.append(StringVar())
                    checked.append(BooleanVar(value=True))
                Checkbutton(container, onvalue=True, variable=checked[0],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=0)
                Label(container, text="autotune rated rpm", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=0, sticky='e')
                Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=2, row=0, sticky='we')
                Label(container, text="rpm", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=0, sticky='w')

                Checkbutton(container, onvalue=True, variable=checked[1],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=1)
                Label(container, text="autotune hall offset angle", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=1, sticky='we')
                Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2, anchor='w').grid(
                    column=2, row=1, sticky='we')
                Label(container, text="degree", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=1, sticky='w')

                for i in range(8):
                    Checkbutton(container, onvalue=True, variable=checked[i + 2],
                                background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=2 + i)
                    Label(container, text=f"autotune hall sector[{0 + i}]", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                          background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                        column=1, row=2 + i, sticky='e')
                    Label(container, textvariable=values[2 + i], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                          background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                        column=2, row=2 + i, sticky='we')
            elif mode == 9:
                for _ in range(12):
                    values.append(StringVar())
                    checked.append(BooleanVar(value=True))
                Checkbutton(container, onvalue=True, variable=checked[0],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=0)
                Label(container, text="autotune Rs", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=0, sticky='e')
                Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=2, row=0, sticky='we')
                Label(container, text="m\u03A9", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=0, sticky='w')

                Checkbutton(container, onvalue=True, variable=checked[1],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=1)
                Label(container, text="autotune Ls", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=1, sticky='we')
                Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=2, row=1, sticky='we')
                Label(container, text="\u03BCH", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=1, sticky='w')

                Checkbutton(container, onvalue=True, variable=checked[2],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=2)
                Label(container, text="autotune rated rpm", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=2, sticky='e')
                Label(container, textvariable=values[2], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=2, row=2, sticky='we')
                Label(container, text="rpm", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=2, sticky='w')

                Checkbutton(container, onvalue=True, variable=checked[3],
                            background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=3)
                Label(container, text="autotune hall offset angle", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=1, row=3, sticky='we')
                Label(container, textvariable=values[3], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                      background='#ccccff' if device == 1 else '#ccffcc', pady=2, anchor='w').grid(
                    column=2, row=3, sticky='we')
                Label(container, text="degree", background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                    column=3, row=3, sticky='w')

                for i in range(8):
                    Checkbutton(container, onvalue=True, variable=checked[i + 4],
                                background='#ccccff' if device == 1 else '#ccffcc').grid(column=0, row=i + 4)
                    Label(container, text=f"autotune hall sector[{0 + i}]", width=MOTOR_DISCOVERY_LABEL_WIDTH,
                          background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                        column=1, row=4 + i, sticky='e')
                    Label(container, textvariable=values[4 + i], width=MOTOR_DISCOVERY_VALUE_WIDTH,
                          background='#ccccff' if device == 1 else '#ccffcc', pady=2).grid(
                        column=2, row=4 + i, sticky='we')

            def retrieve():
                results = self.dyno.devices[device].retrieve_discovery(mode)
                if results is None:
                    pass
                else:
                    if len(results) == 2:
                        values[0].set(results[0])
                        values[1].set(results[1])
                    if len(results) == 3:
                        values[0].set(results[0])
                        values[1].set(f"{results[1]}")
                        for i in range(8):
                            values[2 + i].set(results[2][i])
                    if len(results) == 5:
                        values[0].set(results[0])
                        values[1].set(results[1])
                        values[2].set(results[2])
                        values[3].set(f"{results[3]}")
                        for i in range(8):
                            values[4 + i].set(results[4][i])

            def close():
                self.dyno.devices[device].stop_motor_discovery()
                popup.destroy()

            def update():
                if mode == 1:
                    for i in range(len(values)):
                        if checked[i].get():
                            if i == 0:
                                self.dyno.devices[device].write('Rs', float(values[i].get()))
                            else:
                                self.dyno.devices[device].write('Ls', float(values[i].get()))
                if mode == 2:
                    for i in range(2):
                        if checked[i].get():
                            if i == 0:
                                self.dyno.devices[device].write('Rated motor speed', float(values[i].get()))
                            else:
                                self.dyno.devices[device].write('Hall offset', float(values[i].get()))
                    for i in range(8):
                        if checked[2 + i].get():
                            self.dyno.devices[device].write(f'Hall sector{i}', float(values[2 + i].get()))
                if mode == 9:
                    for i in range(4):
                        if checked[i].get():
                            if i == 0:
                                self.dyno.devices[device].write('Rs', float(values[i].get()))
                            elif i == 1:
                                self.dyno.devices[device].write('Ls', float(values[i].get()))
                            elif i == 2:
                                self.dyno.devices[device].write('Rated motor speed', float(values[i].get()))
                            else:
                                self.dyno.devices[device].write('Hall offset', float(values[i].get()))
                    for i in range(8):
                        if checked[4 + i].get():
                            self.dyno.devices[device].write(f'Hall sector{i}', float(values[4 + i].get()))


            Button(popup, text='Read Discovery', command=retrieve,
                   background='green', activebackground='green', foreground='white',
                   activeforeground='white').grid(
                column=0, row=4, sticky='news')
            Button(popup, text='Write Discovery', command=update,
                   background='blue', activebackground='blue', foreground='white',
                   activeforeground='white').grid(
                column=0, row=5, sticky='news')
            popup.protocol("WM_DELETE_WINDOW", close)
            popup.lift()
            popup.update_idletasks()
            self.dyno.devices[device].motor_discovery(mode=mode, blocking=False, retrieve=False)

    # def _dut_motor_discovery(self, mode):
    #     """
    #     GUI backend + popup
    #     Motor discovery for DUT
    #     """
    #     if self.dyno.devices[1] is not None and not self.testing:
    #         popup = Toplevel(self.root, background='#ccccff')
    #         popup.attributes('-topmost', 'true')
    #         popup.geometry(f'350x410+10+10')
    #         popup.resizable(True, True)
    #         popup.columnconfigure(0, weight=1)
    #         popup.rowconfigure(1, weight=1)
    #         label_text = StringVar(value='Motor Discovering')
    #         Label(popup, textvariable=label_text, background='#ccccff', anchor='center', pady=5, font=f'{OPTION_FONT_NAME} 15 bold').grid(
    #             column=0, row=0, sticky='news')
    #         popup.bind('<Escape>', self.dyno.devices[1].stop_motor_discovery)
    #         Button(popup, text='Interrupt', command=self.dyno.devices[1].stop_motor_discovery,
    #                background='red', activebackground='red', foreground='white', activeforeground='white').grid(
    #             column=0, row=3, sticky='news')
    #
    #         container = Frame(popup, background='#ccccff')
    #         container.grid(column=0, row=2)
    #         values = []
    #         checked = []
    #         if mode == 1:
    #             for _ in range(2):
    #                 values.append(StringVar())
    #                 checked.append(BooleanVar(value=True))
    #             Checkbutton(container, onvalue=True, variable=checked[0], background='#ccccff').grid(column=0, row=0)
    #             Label(container, text="autotune Rs", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=0, sticky='e')
    #             Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=2, row=0, sticky='we')
    #             Label(container, text="m\u03A9", background='#ccccff', pady=2).grid(
    #                 column=3, row=0, sticky='w')
    #
    #             Checkbutton(container, onvalue=True, variable=checked[1], background='#ccccff').grid(column=0, row=1)
    #             Label(container, text="autotune Ls", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=1, sticky='we')
    #             Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=2, row=1, sticky='we')
    #             Label(container, text="\u03BCH", background='#ccccff', pady=2).grid(
    #                 column=3, row=1, sticky='w')
    #         elif mode == 2:
    #             for _ in range(10):
    #                 values.append(StringVar())
    #                 checked.append(BooleanVar(value=True))
    #             Checkbutton(container, onvalue=True, variable=checked[0], background='#ccccff').grid(column=0, row=0)
    #             Label(container, text="autotune rated rpm", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=0, sticky='e')
    #             Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=2, row=0, sticky='we')
    #             Label(container, text="rpm", background='#ccccff', pady=2).grid(
    #                 column=3, row=0, sticky='w')
    #
    #             Checkbutton(container, onvalue=True, variable=checked[1], background='#ccccff').grid(column=0, row=1)
    #             Label(container, text="autotune hall offset angle", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=1, sticky='we')
    #             Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2, anchor='w').grid(
    #                 column=2, row=1, sticky='we')
    #             Label(container, text="degree", background='#ccccff', pady=2).grid(
    #                 column=3, row=1, sticky='w')
    #
    #             for i in range(8):
    #                 Checkbutton(container, onvalue=True, variable=checked[i + 2], background='#ccccff').grid(column=0, row=2 + i)
    #                 Label(container, text=f"autotune hall sector[{0 + i}]", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                       background='#ccccff', pady=2).grid(
    #                     column=1, row=2 + i, sticky='e')
    #                 Label(container, textvariable=values[2 + i], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                       background='#ccccff', pady=2).grid(
    #                     column=2, row=2 + i, sticky='we')
    #         elif mode == 9:
    #             for _ in range(12):
    #                 values.append(StringVar())
    #                 checked.append(BooleanVar(value=True))
    #             Checkbutton(container, onvalue=True, variable=checked[0], background='#ccccff').grid(column=0, row=0)
    #             Label(container, text="autotune Rs", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=0, sticky='e')
    #             Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=2, row=0, sticky='we')
    #             Label(container, text="m\u03A9", background='#ccccff', pady=2).grid(
    #                 column=3, row=0, sticky='w')
    #
    #             Checkbutton(container, onvalue=True, variable=checked[1], background='#ccccff').grid(column=0, row=1)
    #             Label(container, text="autotune Ls", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=1, sticky='we')
    #             Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=2, row=1, sticky='we')
    #             Label(container, text="\u03BCH", background='#ccccff', pady=2).grid(
    #                 column=3, row=1, sticky='w')
    #
    #             Checkbutton(container, onvalue=True, variable=checked[2], background='#ccccff').grid(column=0, row=2)
    #             Label(container, text="autotune rated rpm", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=2, sticky='e')
    #             Label(container, textvariable=values[2], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=2, row=2, sticky='we')
    #             Label(container, text="rpm", background='#ccccff', pady=2).grid(
    #                 column=3, row=2, sticky='w')
    #
    #             Checkbutton(container, onvalue=True, variable=checked[3], background='#ccccff').grid(column=0, row=3)
    #             Label(container, text="autotune hall offset angle", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccccff', pady=2).grid(
    #                 column=1, row=3, sticky='we')
    #             Label(container, textvariable=values[3], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccccff', pady=2, anchor='w').grid(
    #                 column=2, row=3, sticky='we')
    #             Label(container, text="degree", background='#ccccff', pady=2).grid(
    #                 column=3, row=3, sticky='w')
    #
    #             for i in range(8):
    #                 Checkbutton(container, onvalue=True, variable=checked[i + 4], background='#ccccff').grid(column=0, row=i + 4)
    #                 Label(container, text=f"autotune hall sector[{0 + i}]", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                       background='#ccccff', pady=2).grid(
    #                     column=1, row=4 + i, sticky='e')
    #                 Label(container, textvariable=values[4 + i], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                       background='#ccccff', pady=2).grid(
    #                     column=2, row=4 + i, sticky='we')
    #
    #         def retrieve():
    #             results = self.dyno.devices[1].retrieve_discovery(mode)
    #             if results is None:
    #                 pass
    #             else:
    #                 if len(results) == 2:
    #                     values[0].set(results[0])
    #                     values[1].set(results[1])
    #                 if len(results) == 3:
    #                     values[0].set(results[0])
    #                     values[1].set(f"{results[1]}")
    #                     for i in range(8):
    #                         values[2 + i].set(results[2][i])
    #                 if len(results) == 5:
    #                     values[0].set(results[0])
    #                     values[1].set(results[1])
    #                     values[2].set(results[2])
    #                     values[3].set(f"{results[3]}")
    #                     for i in range(8):
    #                         values[4 + i].set(results[4][i])
    #
    #         def close():
    #             self.dyno.devices[1].stop_motor_discovery()
    #             popup.destroy()
    #
    #         def update():
    #             if mode == 1:
    #                 for i in range(len(values)):
    #                     if checked[i].get():
    #                         if i == 0:
    #                             self.dyno.devices[1].write('Rs', float(values[i].get()))
    #                         else:
    #                             self.dyno.devices[1].write('Ls', float(values[i].get()))
    #             if mode == 2:
    #                 for i in range(2):
    #                     if checked[i].get():
    #                         if i == 0:
    #                             self.dyno.devices[1].write('Rated motor speed', float(values[i].get()))
    #                         else:
    #                             self.dyno.devices[1].write('Hall offset', float(values[i].get()))
    #                 for i in range(8):
    #                     if checked[2 + i].get():
    #                         self.dyno.devices[1].write(f'Hall sector{i}', float(values[2 + i].get()))
    #             if mode == 9:
    #                 for i in range(4):
    #                     if checked[i].get():
    #                         if i == 0:
    #                             self.dyno.devices[1].write('Rs', float(values[i].get()))
    #                         elif i == 1:
    #                             self.dyno.devices[1].write('Ls', float(values[i].get()))
    #                         elif i == 2:
    #                             self.dyno.devices[1].write('Rated motor speed', float(values[i].get()))
    #                         else:
    #                             self.dyno.devices[1].write('Hall offset', float(values[i].get()))
    #                 for i in range(8):
    #                     if checked[4 + i].get():
    #                         self.dyno.devices[1].write(f'Hall sector{i}', float(values[4 + i].get()))
    #
    #
    #         Button(popup, text='Retrieve Discovery', command=retrieve,
    #                background='green', activebackground='green', foreground='white',
    #                activeforeground='white').grid(
    #             column=0, row=4, sticky='news')
    #         Button(popup, text='Update', command=update,
    #                background='green', activebackground='green', foreground='white',
    #                activeforeground='white').grid(
    #             column=0, row=5, sticky='news')
    #         popup.protocol("WM_DELETE_WINDOW", close)
    #         popup.lift()
    #         popup.update_idletasks()
    #         self.dyno.devices[1].motor_discovery(mode=mode, blocking=False, retrieve=False)
    #
    # def _brk_motor_discovery(self, mode):
    #     """
    #     GUI backend + popup
    #     Motor discovery for brake
    #     Can combine with _dut_motor_discovery
    #     """
    #     if self.dyno.devices[2] is not None and not self.testing:
    #         # self.controller_tab.children['brk_motor_discovery_btn_1']['state'] = DISABLED
    #         # self.controller_tab.children['brk_motor_discovery_btn_2']['state'] = DISABLED
    #         popup = Toplevel(self.root, background='#ccffcc')
    #         popup.attributes('-topmost', 'true')
    #         popup.geometry(f'350x400+10+10')
    #         popup.resizable(True, True)
    #         # popup.attributes('-fullscreen', 'true')
    #         # popup.attributes('-alpha', 0.75)
    #         popup.columnconfigure(0, weight=1)
    #         popup.rowconfigure(1, weight=1)
    #         label_text = StringVar(value='Motor Discovering')
    #         # Label(popup, text='Motor Discovering...\nPlease wait...\nProgram will appear unresponsive.',
    #         #       background='white', anchor='center').grid(column=0, row=0, sticky='news')
    #         Label(popup, textvariable=label_text, background='#ccffcc', anchor='center', pady=5).grid(
    #             column=0, row=0, sticky='news')
    #         popup.bind('<Escape>', self.dyno.devices[2].stop_motor_discovery)
    #         Button(popup, text='\nInterrupt Motor Discovery\n', command=self.dyno.devices[2].stop_motor_discovery,
    #                background='red', activebackground='red', foreground='white', activeforeground='white').grid(
    #             column=0, row=3, sticky='new')
    #
    #         container = Frame(popup, background='#ccffcc')
    #         container.grid(column=0, row=2)
    #         values = []
    #         if mode == 1:
    #             for _ in range(2):
    #                 values.append(StringVar())
    #             Label(container, text="autotune Rs", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=0, sticky='e')
    #             Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=1, row=0, sticky='we')
    #             Label(container, text="m\u03A9", background='#ccffcc', pady=2).grid(
    #                 column=2, row=0, sticky='w')
    #
    #             Label(container, text="autotune Ls", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=1, sticky='we')
    #             Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=1, row=1, sticky='we')
    #             Label(container, text="\u03BCH", background='#ccffcc', pady=2).grid(
    #                 column=2, row=1, sticky='w')
    #         elif mode == 2:
    #             for _ in range(10):
    #                 values.append(StringVar())
    #             Label(container, text="autotune rated rpm", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=0, sticky='e')
    #             Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=1, row=0, sticky='we')
    #             Label(container, text="rpm", background='#ccffcc', pady=2).grid(
    #                 column=2, row=0, sticky='w')
    #
    #             Label(container, text="autotune hall offset angle", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=1, sticky='we')
    #             Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2, anchor='w').grid(
    #                 column=1, row=1, sticky='we')
    #             Label(container, text="degree", background='#ccffcc', pady=2).grid(
    #                 column=2, row=1, sticky='w')
    #
    #             for i in range(8):
    #                 Label(container, text=f"autotune hall sector[{0 + i}]", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                       background='#ccffcc', pady=2).grid(
    #                     column=0, row=2 + i, sticky='e')
    #                 Label(container, textvariable=values[2 + i], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                       background='#ccffcc', pady=2).grid(
    #                     column=1, row=2 + i, sticky='we')
    #         elif mode == 9:
    #             for _ in range(12):
    #                 values.append(StringVar())
    #             Label(container, text="autotune Rs", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=0, sticky='e')
    #             Label(container, textvariable=values[0], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=1, row=0, sticky='we')
    #             Label(container, text="m\u03A9", background='#ccffcc', pady=2).grid(
    #                 column=2, row=0, sticky='w')
    #
    #             Label(container, text="autotune Ls", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=1, sticky='we')
    #             Label(container, textvariable=values[1], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=1, row=1, sticky='we')
    #             Label(container, text="\u03BCH", background='#ccffcc', pady=2).grid(
    #                 column=2, row=1, sticky='w')
    #
    #             Label(container, text="autotune rated rpm", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=2, sticky='e')
    #             Label(container, textvariable=values[2], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=1, row=2, sticky='we')
    #             Label(container, text="rpm", background='#ccffcc', pady=2).grid(
    #                 column=2, row=2, sticky='w')
    #
    #             Label(container, text="autotune hall offset angle", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                   background='#ccffcc', pady=2).grid(
    #                 column=0, row=3, sticky='we')
    #             Label(container, textvariable=values[3], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                   background='#ccffcc', pady=2, anchor='w').grid(
    #                 column=1, row=3, sticky='we')
    #             Label(container, text="degree", background='#ccffcc', pady=2).grid(
    #                 column=2, row=3, sticky='w')
    #
    #             for i in range(8):
    #                 Label(container, text=f"autotune hall sector[{0 + i}]", width=MOTOR_DISCOVERY_LABEL_WIDTH,
    #                       background='#ccffcc', pady=2).grid(
    #                     column=0, row=4 + i, sticky='e')
    #                 Label(container, textvariable=values[4 + i], width=MOTOR_DISCOVERY_VALUE_WIDTH,
    #                       background='#ccffcc', pady=2).grid(
    #                     column=1, row=4 + i, sticky='we')
    #
    #         def retrieve():
    #             results = self.dyno.devices[2].retrieve_discovery(mode)
    #             if results is None:
    #                 pass
    #             else:
    #                 # print('BRK Motor discovery result:')
    #                 if len(results) == 2:
    #                     values[0].set(results[0])
    #                     values[1].set(results[1])
    #                     # print(f"autotune Rs: {results[0]} m\u03A9 | autotune Ls: {results[1]} \u03BCH")
    #                 if len(results) == 3:
    #                     values[0].set(results[0])
    #                     values[1].set(f"{results[1]}")
    #                     for i in range(8):
    #                         values[2 + i].set(results[2][i])
    #                 if len(results) == 5:
    #                     values[0].set(results[0])
    #                     values[1].set(results[1])
    #                     values[2].set(results[2])
    #                     values[3].set(f"{results[3]}")
    #                     for i in range(8):
    #                         values[4 + i].set(results[4][i])
    #                     # print(f"autotune Rs: {results[0]} m\u03A9 | autotune Ls: {results[1]} \u03BCH\n"
    #                     #       f"autotune rated rpm: {results[2]} rpm | autotune hall offset angle: {results[3]} degree\n"
    #                     #       f"autotune hall sector[0]: {results[4][0]}\n"
    #                     #       f"autotune hall sector[1]: {results[4][1]}\n"
    #                     #       f"autotune hall sector[2]: {results[4][2]}\n"
    #                     #       f"autotune hall sector[3]: {results[4][3]}\n"
    #                     #       f"autotune hall sector[4]: {results[4][4]}\n"
    #                     #       f"autotune hall sector[5]: {results[4][5]}\n"
    #                     #       f"autotune hall sector[6]: {results[4][6]}\n"
    #                     #       f"autotune hall sector[7]: {results[4][7]}")
    #
    #         def close():
    #             self.dyno.devices[2].stop_motor_discovery()
    #             popup.destroy()
    #
    #         Button(popup, text='\nRetrieve Discovery\n', command=retrieve,
    #                background='green', activebackground='green', foreground='white',
    #                activeforeground='white').grid(
    #             column=0, row=4, sticky='new')
    #         popup.protocol("WM_DELETE_WINDOW", close)
    #         popup.lift()
    #         popup.update_idletasks()
    #         self.dyno.devices[2].motor_discovery(mode=mode, blocking=False)
    #
    #         # self.controller_tab.children['brk_motor_discovery_btn_1']['state'] = NORMAL
    #         # self.controller_tab.children['brk_motor_discovery_btn_2']['state'] = NORMAL

    def _fault_clear(self):
        """
        GUI backend
        Clears faults for DynoModule - DUT & BRK
        """
        if self.dyno.devices[1] is not None:
            self.dyno.devices[1].clear_faults()
        if self.dyno.devices[2] is not None and isinstance(self.dyno.devices[2], ASIController):
            self.dyno.devices[2].clear_faults()
        elif self.dyno.devices[2] is not None and isinstance(self.dyno.devices[2], AbbAcs800):
            self.dyno.devices[2].clearFault()
        print("Fault Cleared")

    def _check_fault(self):
        """
        GUI backend
        Checks and prints fault - for ASI Controllers
        """
        if self.dyno.devices[1] is not None:
            print(f"DUT Faults:\n{self.dyno.devices[1].check_faults()}")
        if self.dyno.devices[2] is not None and isinstance(self.dyno.devices[2], ASIController):
            print(f"BRK Faults:\n{self.dyno.devices[2].check_faults()}")

    def _set_torque(self, event=None):
        """
        GUI backend
        Set brake torque for controller tab
        """
        if self.dyno is not None and isinstance(self.dyno.devices[2], ASIController):
            self.dyno.devices[2].set_torque(self.calc_torque.get())
            self.update_brk_torque()
            self.controller_params_operation([self.brk_frame, self.brk_extra_frame, self.brk_extra_frame_1],
                                             [f"{'ABB' if self.abb.get() else 'BRK'}",
                                              f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                              f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                             CONTROL_PARAM_UPDATE)

    def _set_brk_dir(self, event=None):
        """
        GUI backend
        Set/reset brake direction if BRK is ASIController
        """
        if self.dyno is not None and isinstance(self.dyno.devices[2], ASIController):
            self.dyno.devices[2].set_direction()

    def update_brk_torque(self):
        if self.dyno.devices[2].mode == 'torque':
            torque_read = self.dyno.devices[2].cur_torque
            self.main_parameters['brk_torque'].set(torque_read)
            self.calc_torque.set(torque_read)
        else:
            torque_read = self.dyno.devices[2].cur_rpm
            self.main_parameters['brk_torque'].set(torque_read)

    def _brk_ramp(self):
        """
        GUI backend
        Starts brake ramping
        """
        def action():
            if self.dyno.devices[2] is not None:
                orig_color = self.main_elements['main_brk_ramp_btn'].cget("background")
                self.main_elements['main_brk_ramp_btn'].config(bg='#aaffaa')
                self.dyno.devices[2].ramp_to(self.ramp_target.get(), self.ramp_step.get(), self.ramp_duration.get())
                self.update_brk_torque()
                self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                                                  self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                                                 ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                                  "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                  "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                 CONTROL_PARAM_UPDATE)
                self.main_elements['main_brk_ramp_btn'].config(bg=orig_color)

        Thread(target=action).start()

    def _run_for(self):
        """
        GUI backend
        Toggles dyno stop timer - Stops dyno and logging
        """
        if self.dyno is not None:
            if self.run_timer_status.get():
                logging.info('Stopping dyno stop timer')
                self.run_timer_status.set(False)
                self.countdown_thread = None
                self.controller_tab.children['btn_frame'].children['ctrl_timer_btn'].config(bg=DEFAULT_GREY)
            else:
                logging.info('Starting dyno stop timer')
                self.run_timer_status.set(True)
                self.countdown_thread = Thread(target=self._count_down)
                self.countdown_thread.start()
                self.controller_tab.children['btn_frame'].children['ctrl_timer_btn'].config(bg='#aaffaa')

    def _count_down(self):
        """
        GUI backend
        Dyno stop timer target - countdown thread - max 99:59:59
        """
        if self.run_duration_s.get() > 59:
            self.run_duration_s.set(59)
        if self.run_duration_m.get() > 59:
            self.run_duration_m.set(59)
        if self.run_duration_h.get() > 999:
            self.run_duration_h.set(999)

        while self.run_timer_status.get():
            sleep(1)
            if self.run_duration_s.get() > 0:
                self.run_duration_s.set(self.run_duration_s.get() - 1)
            elif self.run_duration_m.get() > 0:
                self.run_duration_s.set(59)
                self.run_duration_m.set(self.run_duration_m.get() - 1)
            elif self.run_duration_h.get() > 0:
                self.run_duration_s.set(59)
                self.run_duration_m.set(59)
                self.run_duration_h.set(self.run_duration_h.get() - 1)
            else:
                self._dyno_stop()
                self._stop_logging()
                self._run_for()

    def _dyno_stop(self, event=None):
        """
        GUI backend
        Stops DynoModule - only stops dyno, doesn't stop logging
        """
        if self.dyno is not None:
            logging.info("DYNO STOP")
            self.controller_tab.children['dyno_stop_btn']['state'] = DISABLED
            try:
                self.dyno.stop_test()
                if event is not None:
                    self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                                                      self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                                                     ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                                      "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                                      "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                                     CONTROL_PARAM_UPDATE)
            except (AttributeError, CommLossError):
                pass
            finally:
                self.controller_tab.children['dyno_stop_btn']['state'] = NORMAL
                self.dyno_gui.dut.stop_motor()
                self.dyno_gui.brk.stop_motor()

    def _init_abb(self):
        """
        GUI backend
        Initiates ABB based on auto/loc mode
        """
        if self.abb_auto.get() and self.connection_status[1].get() and \
                isinstance(self.dyno.devices[2], AbbAcs800):
            self.dyno.devices[2].init_ABB(self.abb_auto.get())
            print("ABB in auto mode!")
            logging.info("ABB switched to auto mode")
        elif (not self.abb_auto.get()) and self.connection_status[1].get() and \
                isinstance(self.dyno.devices[2], AbbAcs800):
            self.dyno.devices[2].init_ABB(self.abb_auto.get())
            print("ABB in manual mode!")
            logging.info("ABB switched to manual mode")

    def _toggle_abb(self):
        """
        GUI backend
        Toggles between ABB auto & loc mode
        """
        if self.abb_auto.get():
            self.abb_auto.set(False)
        else:
            self.abb_auto.set(True)
        self._init_abb()
        self._update_abb_mode()

    def _toggle_abb_speed_torque(self):
        """
        GUI backend
        Toggles between ABB speed & torque mode
        """
        if self.dyno and self.dyno.devices[2] and isinstance(self.dyno.devices[2], AbbAcs800):
            self.main_parameters['brk_torque'].set(0)
            if self.dyno.devices[2].mode == 'torque':
                self.dyno.devices[2].speed_mode()
                self.dyno.devices[2].set_rpm(0)
                self.main_parameters['abb_speed_torque'].set('Speed')
                self.main_parameters['abb_dir'].set('REQUEST')
                self.main_parameters['abb_limit'].set('BOTH')
                self.dyno.devices[2].set_limits('b')
                self.dyno.devices[2].set_abb_direction('b')
            else:
                self.dyno.devices[2].torque_mode()
                self.dyno.devices[2].set_torque(0)
                self.main_parameters['abb_speed_torque'].set("Torque")
                self.main_parameters['abb_dir'].set('FORWARD')
                self.main_parameters['abb_limit'].set('REVERSE')
            print(f"ABB now in {self.dyno.devices[2].mode} mode")
        else:
            if self.main_parameters['abb_speed_torque'].get() == 'Speed':
                self.main_parameters['abb_speed_torque'].set('Torque')
            else:
                self.main_parameters['abb_speed_torque'].set('Speed')

    def _update_abb_direction(self, event=None):
        if self.dyno and self.dyno.devices[2] and isinstance(self.dyno.devices[2], AbbAcs800):
            self.dyno.devices[2].set_abb_direction(
                self.main_parameters['abb_dir'].get().lower())
            print(f"ABB now in {self.main_parameters['abb_dir'].get()} direction")

    def _update_abb_limits(self, event=None):
        if self.dyno and self.dyno.devices[2] and isinstance(self.dyno.devices[2], AbbAcs800):
            self.dyno.devices[2].set_limits(
                self.main_parameters['abb_limit'].get().lower())
            print(f"ABB now in {self.main_parameters['abb_dir'].get()} direction")

    def _update_abb_mode(self):
        if self.dyno and isinstance(self.dyno.devices[2], AbbAcs800):
            if self.dyno.devices[2].remote:
                self.main_parameters['abb_mode'].set('Remote')
                self.abb_auto.set(True)
            else:
                self.main_parameters['abb_mode'].set('Local')
                self.abb_auto.set(False)

    def _controller_write(self, event=None):
        """
        GUI backend
        Writes parameter(s) to controller - both DUT & BRK - can target single parameter now
        Controller tab
        """
        if self.dyno is not None:
            if event is not None:
                # "Return" key
                if self.dyno.devices[2] is not None and \
                        isinstance(self.dyno.devices[2], AbbAcs800) and \
                        event.widget.master == self.brk_frame:
                    temp_thread = Thread(target=lambda: self.controller_params_operation([self.brk_frame],
                                                                                         ['ABB'], CONTROL_PARAM_UPLOAD))
                    temp_thread.start()
                    return
                event.widget.select_range(0, END)
                name = str(event.widget).split(".")[-1]
                label_name = name[:-6]
                widgets = [event.widget.master.children[label_name], event.widget]
                temp_thread = Thread(target=lambda: self.controller_params_operation([event.widget.master], None,
                                                                                     CONTROL_PARAM_UPLOAD, widgets))
                temp_thread.start()

            else:
                # "PARAMETER WRITE" button
                temp_thread = Thread(target=lambda:self.controller_params_operation(
                    [self.dut_frame, self.brk_frame,
                     self.dut_extra_frame, self.brk_extra_frame,
                     self.dut_extra_frame_1, self.brk_extra_frame_1],
                    ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                     "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                     "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                    CONTROL_PARAM_UPLOAD))
                temp_thread.start()

    def _controller_read(self):
        """
        GUI backend
        Reads all parameters to controller - both DUT & BRK
        """
        temp_thread = Thread(target=lambda:self.controller_params_operation(
            [self.dut_frame, self.brk_frame, self.dut_extra_frame,
             self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
            ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
             "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
             "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
            CONTROL_PARAM_UPDATE))
        temp_thread.start()

    def _start_live(self):
        """
        GUI backend
        Starts live_thread_faults
        """
        self.dyno_gui.start()
        self.graph_params = self.dyno.getcsvline(getnames=True)

        self.dyno.start_time = datetime.now()
        self._reset_live()
        
        current_tab = self.graph_notebook.index(self.graph_notebook.select())
        if current_tab == 0:
            self.graphs['RPMTorque'].animation.resume()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif current_tab == 1:
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.resume()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif current_tab == 2:
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.resume()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif current_tab == 3:
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.resume()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.pause()
        elif current_tab == 4:
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.resume()
            self.graphs['mb'].animation.pause()
        elif current_tab == 5:
            self.graphs['RPMTorque'].animation.pause()
            self.graphs['temp'].animation.pause()
            self.graphs['mech'].animation.pause()
            self.graphs['elec'].animation.pause()
            self.graphs['effi'].animation.pause()
            self.graphs['mb'].animation.resume()
        logging.info("Live status thread started")
        print("GUI Initialized!")
        
    def _reset_live(self):
        """
        GUI backend
        Resets live section
        """
        self.main_parameters['graphing'] = True

        # List
        # for i, p in enumerate(self.main_parameters['live_list_parameters']):
        #     self.main_elements['live_param_frame'].children[f"main_live_list_param_{p}_{i}"].destroy()
        #     self.main_elements['live_param_frame'].children[f"main_live_list_param_{p}_{i}_value"].destroy()
        #
        # # self.main_parameters['live_list_parameters'] = {}
        # for controller in ['DUT', 'BRK', 'ABB']:
        #     if controller == 'DUT' and not self.dyno.devices[1]:
        #         continue
        #
        #     if controller == 'BRK' and not isinstance(self.dyno.devices[2], ASIController):
        #         continue
        #
        #     if controller == 'ABB' and not isinstance(self.dyno.devices[2], AbbAcs800):
        #         continue
        #
        #     for element in self.main_parameters['live_list_params'].findall(f"{controller}/Name"):
        #         if f'{controller} {element.text}' not in self.main_parameters['live_list_parameters'].keys():
        #             self.main_parameters['live_list_parameters'][f'{controller} {element.text}'] = DoubleVar(value=0)
        # for i, p in enumerate(self.main_parameters['live_list_parameters']):
        #     Label(self.main_elements['live_param_frame'], text=p, background='white',
        #           name=f"main_live_list_param_{p}_{i}", font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}',
        #           pady=2, justify='center', anchor='center').grid(column=(i % 2), row=int(i / 2) * 2, sticky='we')
        #     self.main_elements['live_param_frame'].children[f"main_live_list_param_{p}_{i}"].bind(
        #         '<MouseWheel>',
        #         self.main_elements['live_param_frame'].master.master.on_mousewheel)
        #     # self.main_parameters[f'live_list_param_{p}_{i}'] = StringVar(value='0')
        #     Label(self.main_elements['live_param_frame'],
        #           textvariable=self.main_parameters[f'live_list_param_{p}_{i}'],
        #           width=6, name=f"main_live_list_param_{p}_{i}_value",
        #           font=f'{OPTION_FONT_NAME} {LIST_FONT_SIZE}', background='white', pady=2).grid(
        #         column=(i % 2), row=int(i / 2) * 2 + 1, sticky='we')
        #     self.main_elements['live_param_frame'].children[f"main_live_list_param_{p}_{i}_value"].bind(
        #         '<MouseWheel>',
        #         self.main_elements['live_param_frame'].master.master.on_mousewheel)

        # warnings & faults
        for i in range(9):
            for j in range(17):
                try:
                    self.main_elements['live_faults_frame'].children[
                        f'!frame{"" if i == 0 else i}'].children[f'!frame{"" if j == 0 else j}'].destroy()
                except KeyError:
                    pass
            try:
                self.main_elements['live_faults_frame'].children[f'!frame{"" if i == 0 else i}'].destroy()
            except KeyError:
                pass
        for i in ['', '2']:
            try:
                self.main_elements['live_faults_frame'].children[f'!canvas{i}'].destroy()
            except KeyError:
                pass

        self.main_parameters['live_faults'] = {}
        if self.dyno.devices[1]:
            self.main_parameters['live_faults_tree'] = self.dyno.devices[1].etree
        elif isinstance(self.dyno.devices[2], ASIController):
            self.main_parameters['live_faults_tree'] = self.dyno.devices[2].etree
        for controller in ['DUT', 'BRK']:
            if controller == 'DUT' and not self.dyno.devices[1]:
                continue

            if controller == 'BRK' and not isinstance(self.dyno.devices[2], ASIController):
                continue

            temp_widget = Canvas(self.main_elements['live_faults_frame'],
                                 width=MIN_WIDTH * 0.29, height=MIN_HEIGHT * 0.2,
                                 background='#ccffcc' if controller == 'BRK' else '#ccccff')
            temp_widget.grid(column=0, row=0 if controller == 'DUT' else 1)
            # temp_widget.place(relx=0, rely=0.5 if controller == 'BRK' else 0, anchor='nw')
            temp_widget.create_text(MIN_WIDTH * 0.01, MIN_HEIGHT * 0.1, text=controller, angle=90)
            for i in range(16):
                temp_widget.create_text(MIN_WIDTH * 0.065 + i * 26, MIN_HEIGHT * 0.02, text=15 - i)
            for i, f in enumerate(['faults', 'faults2', 'warnings', 'warnings2']):
                temp_widget.create_text(MIN_WIDTH * 0.04,
                                        MIN_HEIGHT * (0.055 + i * 0.032),
                                        text=f, font=f'{OPTION_FONT_NAME} 9')
                self.main_parameters['live_faults'][f'{controller} {f}'] = IntVar(value=0)
                temp_indicator = ASIFaultsIndicator(self.main_elements['live_faults_frame'],
                                                    self.main_parameters['live_faults'][f'{controller} {f}'],
                                                    self.main_parameters['live_faults_tree'], f, width=MIN_WIDTH * 0.2)
                temp_indicator.container.place(relx=0.2,
                                               rely=(0.1 if controller == 'DUT' else 0.6) + i * 0.08, anchor='nw')
                self.main_elements[f'live_faults_indicator_{controller}_{f}'] = temp_indicator

        # reset plots
        for graph in PLOT_LIST:
            self.graphs[graph].dyno = self.dyno
            self.graphs[graph].data = pd.DataFrame(columns=self.dyno.getcsvline(getnames=True))
            self.graphs[graph].init_graphing()

        self.main_parameters['live_thread'] = Thread(target=self.live_thread)
        self.main_parameters['live_thread'].start()
        self.main_parameters['live_thread_list'] = Thread(target=self.live_thread_list)
        self.main_parameters['live_thread_list'].start()
        self.main_parameters['live_thread_yoko'] = Thread(target=self.live_thread_yoko)
        self.main_parameters['live_thread_yoko'].start()

        self.main_elements['dyno_plots'].start_graphing()
        # for graph in PLOT_LIST:
        #     self.graphs[graph].start_graphing()
        self._start_graphing()

    def _end_live(self):
        """
        GUI backend
        Stops live threads
        """
        self.dyno_gui.stop()
        if self.main_parameters['graphing']:
            self.main_parameters['graphing'] = False
            self.main_parameters['live_thread'] = None
            self.main_parameters['live_thread_list'] = None
            self.main_elements['dyno_plots'].end_graphing()
            self._end_graphing()
            # for graph in PLOT_LIST:
            #     self.graphs[graph].end_graphing()
            logging.info("Live status thread stopped")

    # Unit testing for graphing & logging will be done on desktop (visual verification preferred)
    def _init_graphing(self):
        """
        GUI backend
        Initiates graphing
        """
        self.graphs['adv'].dyno = self.dyno
        self.graphs['adv'].data = pd.DataFrame(columns=self.dyno.getcsvline(getnames=True))
        self.graphs['adv'].init_graphing()
        # self.graph_params = self.dyno.getcsvline(getnames=True)
        # self.y_params_var.set(self.graph_params)
        # self.graph_tab.children['x_combo']['value'] = self.graph_params
        # self.graph_tab.children['x_combo'].set("Elapsed")
        # logging.info("Graphing tab initiated")

    def _start_graphing(self):
        """
        GUI backend
        Starts graphing thread
        """
        names = self.dyno.getcsvline(getnames=True)
        # self.main_elements["dyno_plots"].data['adv'] = pd.DataFrame(columns=names)
        # self.main_elements["dyno_plots"].data['current'] = pd.DataFrame(columns=names)
        self.graphs['adv'].data = pd.DataFrame(columns=names)
        self.graphs['adv'].dyno = self.dyno
        self.graphs['adv'].start_graphing()

    def _end_graphing(self):
        """
        GUI backend
        Stops graphing thread
        """
        self.graphs['adv'].end_graphing()
        # self.main_elements["dyno_plots"].end_graphing()
        # if self.graphing:
        #     self.graphing = False
        #     self._graphing_thread.join()
        #     self._graphing_thread = None
        #     self.graph_tab.children['ani_pause_btn']['state'] = DISABLED
        #     self.paused.set("UNPAUSE")
        #     logging.info("Graphing thread stopped")

    def live_thread(self):
        """
        GUI backend + graphing + dyno data grabbing
        Main Live Status thread target
        Checks faults and warnings
        """

        def faults():
            if self.dyno is not None:
                # Update faults and warnings
                try:
                    if self.status_notebook.index(self.status_notebook.select()) == 1:
                        for controller in ['DUT', 'BRK']:
                            if controller == 'DUT' and not isinstance(self.dyno.devices[1], ASIController):
                                continue

                            if controller == 'BRK' and not isinstance(self.dyno.devices[2], ASIController):
                                continue

                            for i, f in enumerate(['faults', 'faults2', 'warnings', 'warnings2']):
                                if controller == 'DUT' and self.dyno.devices[1]:
                                    self.main_parameters['live_faults'][f'{controller} {f}'].set(
                                        self.dyno.devices[1].read(f))
                                elif controller == 'BRK' and isinstance(self.dyno.devices[2], ASIController):
                                    self.main_parameters['live_faults'][f'{controller} {f}'].set(
                                        self.dyno.devices[2].read(f))
                                self.main_elements[f'live_faults_indicator_{controller}_{f}'].reset()
                        self.root.update()
                    else:
                        faults = {}
                        if not isinstance(self.dyno.devices[1], ASIController) or \
                                not isinstance(self.dyno.devices[2], ASIController):
                            return
                        if isinstance(self.dyno.devices[1], ASIController):
                            faults['warnings_1'] = self.dyno.devices[1].read('warnings')
                            faults['warnings2_1'] = self.dyno.devices[1].read('warnings2')
                            faults['faults_1'] = self.dyno.devices[1].read('faults')
                            faults['faults2_1'] = self.dyno.devices[1].read('faults2')
                        if isinstance(self.dyno.devices[2], ASIController):
                            faults['warnings_2'] = self.dyno.devices[2].read('warnings')
                            faults['warnings2_2'] = self.dyno.devices[2].read('warnings2')
                            faults['faults_2'] = self.dyno.devices[2].read('faults')
                            faults['faults2_2'] = self.dyno.devices[2].read('faults2')

                        faults_sum = 0
                        warnings_sum = 0
                        for key in faults:
                            if 'warnings' in key:
                                warnings_sum += faults[key]
                            elif 'faults' in key:
                                faults_sum += faults[key]

                        if warnings_sum > 0:
                            self.main_elements['live_faults_tab'].reset(background='white',
                                                                        foreground='orange')
                        if faults_sum > 0:
                            self.main_elements['live_faults_tab'].reset(background='white',
                                                                        foreground='red')
                        if faults_sum == 0 and warnings_sum == 0:
                            self.main_elements['live_faults_tab'].reset(background='white',
                                                                        foreground='black')
                except CommLossError:
                    self.main_parameters['graphing'] = False

        # def live_list():
        #     if self.dyno is not None:
        #         # Update parameters in list tab
        #         if self.status_notebook.index(self.status_notebook.select()) == 1:
        #             for i, p in enumerate(self.main_parameters['live_list_parameters']):
        #                 if self.dyno:
        #                     if self.dyno.devices[1] and p.split(' ')[0] == 'DUT':
        #                         self.main_parameters[f'live_list_param_{p}_{i}'].set(self.dyno.devices[1].log_params[p[4:]].Value)
        #
        #                     if self.dyno.devices[2] and isinstance(self.dyno.devices[2], ASIController) and p.split(' ')[0] == 'BRK':
        #                         self.main_parameters[f'live_list_param_{p}_{i}'].set(self.dyno.devices[2].log_params[p[4:]].Value)
        #
        #                     if self.dyno.devices[2] and isinstance(self.dyno.devices[2], AbbAcs800) and p.split(' ')[0] == 'ABB':
        #                         self.main_parameters[f'live_list_param_{p}_{i}'].set(self.dyno.devices[2].read(p[4:]))
        #                 else:
        #                     break

        def status():
            if self.dyno is not None:
                try:
                    if self.connection_status[0].get():
                        self._connection_check('dut')  # Check connection
                        # Speed check
                        if self.dyno.devices[1].get_rpm() > self.speed_limit_upper.get():
                            self.speed_limit_frame.children['upper_limit'].config(background='red',
                                                                                  foreground='white')
                        elif self.dyno.devices[1].get_rpm() < self.speed_limit_lower.get():
                            self.speed_limit_frame.children['lower_limit'].config(background='red',
                                                                                  foreground='white')
                        else:
                            self.speed_limit_frame.children['upper_limit'].config(background='white',
                                                                                  foreground='red')
                            self.speed_limit_frame.children['lower_limit'].config(background='white',
                                                                                  foreground='red')

                    # BRK status
                    if self.connection_status[1].get():
                        if self.abb.get():
                            self._connection_check('abb')
                        else:
                            self._connection_check('brk')

                    # yoko status
                    if self.connection_status[2].get():
                        self._connection_check('yoko')

                except (AttributeError, TypeError):
                    pass
                except CommLossError:
                    self.main_parameters['graphing'] = False

                if self.dyno:
                    if self.dyno.devices[1]:
                        if self.dyno.devices[1].get_rpm() > 0:
                            self.dyno_gui.dut.direction = 1
                        elif self.dyno.devices[1].get_rpm() < 0:
                            self.dyno_gui.dut.direction = -1
                        else:
                            self.dyno_gui.dut.direction = 0
                    if self.dyno.devices[2] and isinstance(self.dyno.devices[2], ASIController):
                        if self.dyno.devices[2].get_rpm() > 0:
                            self.dyno_gui.brk.direction = 1
                        elif self.dyno.devices[2].get_rpm() < 0:
                            self.dyno_gui.brk.direction = -1
                        else:
                            self.dyno_gui.brk.direction = 0
                    elif self.dyno.devices[2] and isinstance(self.dyno.devices[2], AbbAcs800):
                        if self.dyno.devices[1]:
                            if self.dyno.devices[1].get_rpm() > 0:
                                self.dyno_gui.brk.direction = 1
                            elif self.dyno.devices[1].get_rpm() < 0:
                                self.dyno_gui.brk.direction = -1
                            else:
                                self.dyno_gui.brk.direction = 0

        # def yoko():
        #     if self.dyno is not None:
        #         if self.dyno.devices[PA]:
        #             try:
        #                 if self.dyno.devices[PA].getMeasurement('Torque') > self.torque_limit.get():
        #                     self.speed_limit_frame.children['torque_limit'].config(background='red', foreground='white')
        #                 else:
        #                     self.speed_limit_frame.children['torque_limit'].config(background='white', foreground='red')
        #             except (AttributeError, TypeError):
        #                 pass
        #
        #             # try:
        #             for i, d in enumerate(zip(self.yoko_params.index, self.graph_params[2:])):
        #                 self.main_parameters[f'yoko_param_{self.yoko_params.loc[i]["Shortened Name"]}_{i}'].set(
        #                     self.dyno.devices[PA].getMeasurement(d[1]))

        def test():
            if self.dyno is not None:
                try:
                    # Update test duration
                    if self.test_handler:
                        self.test_start_time = self.test_handler.test_parameters['Start Time']
                        self.status_params['TEST']['Start Time'].set(f'{self.test_start_time.strftime("%H:%M:%S")}')
                        self.test_duration = (datetime.now() - self.test_start_time).total_seconds()
                        self.status_params['TEST']['Duration'].set(self.test_handler.test_parameters['Duration'])
                    else:
                        self.test_duration = (datetime.now() - self.test_start_time).total_seconds()
                        if self.test_duration > 600:
                            hours = self.test_duration // 3600
                            minutes = (self.test_duration % 3600) // 60
                            seconds = self.test_duration % 60
                            self.status_params['TEST']['Duration'].set(f'{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}')
                        else:
                            self.status_params['TEST']['Duration'].set(f'{self.test_duration:.1f}')
                except AttributeError:
                    pass

                # Cyclic test email notification triggers
                if self.test_handler and self.test_handler.cyclic:
                    try:
                        if self.enable_email.get() and (self.status_params['TEST']['Cycles'].get() == 'N/A' or
                                                        int(self.status_params['TEST']['Cycles'].get().split('/')[
                                                                0]) != self.test_handler.current_cycle or
                                                        int(self.status_params['TEST']['Cycles'].get().split('/')[
                                                                1]) != self.test_handler.cycle):
                            email = ''
                            if self.notify_progress.get():
                                email = self.test_tab.children['test_btn_frame'].children[
                                    'email_progress_entry'].get()
                                if self.notify and email.strip() != "":
                                    email = email.strip() + '@acceleratedsystems.com'
                            progress_email(to=AUTHOR_EMAIL, msg=f"Test @ {self.test_handler.current_cycle}/{self.test_handler.cycle}",
                                           attach=f"{ROOT_DIR}\\Logs\\std-9.log", cc=email)
                    except AttributeError:
                        pass
                    try:
                        self.status_params['TEST']['Cycles'].set(f'{self.test_handler.test_parameters["Cycles"]}')
                        self.status_params['TEST']['Steps'].set(f'{self.test_handler.test_parameters["Steps"]}')
                        self._update_test_duration()
                    except AttributeError:
                        pass
                else:
                    self.status_params['TEST']['Cycles'].set('N/A')

        while self.main_parameters['graphing']:
            # self.root.after(10, faults)
            # self.root.after(20, status)
            # self.root.after(300, yoko)
            # self.root.after(30, test)
            faults()
            status()
            test()
            self.root.update()
            # sleep(self.main_parameters['graphing_interval'])

    def live_thread_list(self):
        """
        GUI backend + graphing + dyno data grabbing
        Main Live Status thread target
        Updates DUT & BRK parameters
        """

        def action():
            if self.dyno is not None:
                # Update parameters in list tab
                # if self.status_notebook.index(self.status_notebook.select()) == 1:
                for i, p in enumerate(self.main_parameters['live_list_parameters']):
                    if self.dyno:
                        if self.dyno.devices[1] and p.split(' ')[0] == 'DUT':
                            self.main_parameters[f'live_list_param_{p}_{i}'].set(
                                self.dyno.devices[1].log_params[p[4:]].Value)

                        if self.dyno.devices[2] and \
                                isinstance(self.dyno.devices[2], ASIController) and \
                                p.split(' ')[0] == 'BRK':
                            self.main_parameters[f'live_list_param_{p}_{i}'].set(
                                self.dyno.devices[2].log_params[p[4:]].Value)

                        if self.dyno.devices[2] and \
                                isinstance(self.dyno.devices[2], AbbAcs800) and \
                                p.split(' ')[0] == 'ABB':
                            self.main_parameters[f'live_list_param_{p}_{i}'].set(
                                self.dyno.devices[2].read(p[4:]))
                    else:
                        break

        while self.main_parameters['graphing']:

            # self.root.update()
            # sleep(self.main_parameters['graphing_interval'])
            self.root.after(100, action)
            # action()
            sleep(1)

    def live_thread_yoko(self):
        """
        GUI backend + graphing + dyno data grabbing
        Main Live Status thread target
        Updates yoko parameters & Torque checks
        """

        def action():
            if self.dyno is not None:
                if self.dyno.devices[PA]:
                    try:
                        if self.dyno.devices[PA].getMeasurement('Torque') > self.torque_limit.get():
                            # logging.warning("Torque out of range")
                            self.speed_limit_frame.children['torque_limit'].config(background='red',
                                                                                   foreground='white')
                        else:
                            self.speed_limit_frame.children['torque_limit'].config(background='white',
                                                                                   foreground='red')
                    except (AttributeError, TypeError):
                        pass

                    # try:
                    for i, d in enumerate(zip(self.yoko_params.index, self.graph_params[2:])):
                        self.main_parameters[
                            f'yoko_param_{self.yoko_params.loc[i]["Shortened Name"]}_{i}'].set(
                            self.dyno.devices[PA].getMeasurement(d[1]))

        while self.main_parameters['graphing']:
            self.root.after(100, action)
            # action()
            sleep(1)

    def _start_logging(self):
        """
        GUI backend
        Starts logging thread - Starts graphing too
        """
        if self.dyno is not None and not self.dyno.is_logging_enabled():
            # self.controller_tab.children['rest_frame'].children['start_log_btn']['state'] = DISABLED
            self.main_elements['start_logging']['state'] = DISABLED
            self.testing = True
            try:
                self._update_test_start_time()
                self.dyno.start_logging(float(self.log_interval.get()),
                                        run_down=self.main_parameters['log_note_var'].get())
                # self._start_graphing()
                # self._start_live()
                self.main_elements['dyno_plots'].data['current'] = pd.DataFrame(
                    columns=self.dyno.getcsvline(getnames=True))
                for graph in self.graphs:
                    self.graphs[graph].data = pd.DataFrame(columns=self.dyno.getcsvline(getnames=True))
                # self.main_parameters['graphing_data'] = pd.DataFrame(columns=self.graph_params)
                # self._end_live()
                # self._start_live()
            finally:
                # self.controller_tab.children['rest_frame'].children['update_log_btn']['state'] = NORMAL
                self.main_elements['update_log']['state'] = NORMAL
                # self.controller_tab.children['rest_frame'].children['stop_log_btn']['state'] = NORMAL
                self.main_elements['stop_logging']['state'] = NORMAL
                # self.controller_tab.children['rest_frame'].children['extra_log_btn']['state'] = NORMAL
                self.main_elements['create_extra_log']['state'] = NORMAL
                # self.controller_tab.children['rest_frame'].children['extra_line_btn']['state'] = DISABLED
                self.main_elements['extra_log']['state'] = DISABLED
                # self.main_elements['open_results']['state'] = NORMAL
                self.main_parameters['result_dir'].set(str(self.dyno.logdir).split('\\')[-1])
            logging.info("Logging thread started")

    def _stop_logging(self):
        """
        GUI backend
        Stops logging threads - stops graphing too
        """
        if self.dyno is not None and self.dyno.is_logging_enabled():
            # self.controller_tab.children['rest_frame'].children['stop_log_btn']['state'] = DISABLED
            self.main_elements['stop_logging']['state'] = DISABLED
            try:
                # self._end_graphing()
                self.dyno.stop_logging()
                self.testing = False
            finally:
                # self.controller_tab.children['rest_frame'].children['update_log_btn']['state'] = DISABLED
                self.main_elements['update_log']['state'] = DISABLED
                # self.controller_tab.children['rest_frame'].children['start_log_btn']['state'] = NORMAL
                self.main_elements['start_logging']['state'] = NORMAL
                # self.controller_tab.children['rest_frame'].children['extra_log_btn']['state'] = DISABLED
                self.main_elements['create_extra_log']['state'] = DISABLED
                # self.controller_tab.children['rest_frame'].children['extra_line_btn']['state'] = DISABLED
                self.main_elements['extra_log']['state'] = DISABLED
                self.main_parameters['previous_result_dir'].set(self.dyno.logdir)
            logging.info("Logging thread stopped")

    def _update_log_interval(self):
        """
        GUI backend
        Updates logging interval
        """
        if self.dyno is not None and self.dyno.is_logging_enabled():
            self.dyno.update_log_interval(self.log_interval.get())

    def _extra_logging(self):
        """
        GUI backend
        Invokes DynoModule Extra logging
        """
        if self.dyno is not None:
            self.dyno.extra_logging(file_name=self.extra_file.get(), same_folder=self.same_folder.get())
            # self.controller_tab.children['rest_frame'].children['extra_line_btn']['state'] = NORMAL
            self.main_elements['extra_log']['state'] = NORMAL
            logging.info("Extra logging enabled")

    def _extra_line(self):
        """
        GUI backend
        Invokes DynoModule Extra line
        """
        if self.dyno is not None:
            self.dyno.extra_line(file_name=self.extra_file.get(), same_folder=self.same_folder.get())
            logging.info("Extra log")

    def _open_result_folder(self, *args):
        """
        GUI backend
        Opens results folder 
        """
        if self.dyno is not None:
            subprocess.Popen(f'explorer /open,"{self.dyno.logdir}"')
        else:
            subprocess.Popen(f'explorer /open,"{self.main_parameters["previous_result_dir"]}"')

    def _basic_plot(self):
        """
        GUI backend
        Creates basic plot
        """
        if self.dyno is not None:
            if "both" in self.plot_display.get():
                self.dyno.plot_basic(output=2)
            elif "display" in self.plot_display.get():
                self.dyno.plot_basic(output=1)
            elif "save" in self.plot_display.get():
                self.dyno.plot_basic(output=0)

    def _plot_errors(self):
        """
        GUI backend
        Creates error plot
        """
        if self.dyno is not None:
            if "both" in self.error_display.get():
                self.dyno.plot_error(error=self.error2display.get(), output=2)
            elif "display" in self.error_display.get():
                self.dyno.plot_error(error=self.error2display.get(), output=1)
            elif "save" in self.error_display.get():
                self.dyno.plot_error(error=self.error2display.get(), output=0)

    def _reset_can_move(self, device=1):

        def action():
            if self.dyno and isinstance(self.dyno.devices[device], ASIController):
                self.dyno.devices[device].can_motor_move()
                print(f'Device {device} can move motor: {self.dyno.devices[device].can_move}')

        Thread(target=action).start()

    def _flash_dut(self):
        """
        GUI backend
        DUT save to flash
        """
        if self.dyno is not None and isinstance(self.dyno.devices[1], ASIController):
            if self.dyno.devices[1].save_to_flash():
                messagebox.showinfo("DUT", "DUT: Saved to flash")

    def _flash_brk(self):
        """
        GUI backend
        BRK save to flash
        """
        if self.dyno is not None and isinstance(self.dyno.devices[2], ASIController):
            if self.dyno.devices[2].save_to_flash():
                messagebox.showinfo("BRK", "BRK: Saved to flash")

    def _file_save_dut(self):
        """
        GUI backend
        DUT save parameters to file - set access level to 3 before and back to 0 after
        """
        def action():
            if self.dyno is not None and \
                    isinstance(self.dyno.devices[1], ASIController):
                file = filedialog.asksaveasfile(mode='w', defaultextension=".xml",
                                                filetypes=(("ASI files", "*.xml*"),
                                                           ("all files", "*.*")))
                if file is None:  # asksaveasfile return `None` if dialog closed with "cancel".
                    return
                self.dyno.devices[1].set_access_level(3)
                self.dyno.devices[1].backup_parameters(file.name, master=self.root)
                self.dyno.devices[1].set_access_level(0)

        Thread(target=action).start()

    def _file_save_brk(self):
        """
        GUI backend
        BRK save parameters to file - set access level to 3 before and back to 0 after
        """
        def action():
            if self.dyno is not None and \
                    isinstance(self.dyno.devices[2], ASIController):
                file = filedialog.asksaveasfile(mode='w', defaultextension=".xml",
                                                filetypes=(("ASI files", "*.xml*"),
                                                           ("all files", "*.*")))
                if file is None:  # asksaveasfile return `None` if dialog closed with "cancel".
                    return
                self.dyno.devices[2].set_access_level(3)
                self.dyno.devices[2].backup_parameters(file.name, master=self.root)
                self.dyno.devices[2].set_access_level(0)

        Thread(target=action).start()

    def _file_load_dut(self):
        """
        GUI backend
        DUT load parameters from file - set access level to 3 before and back to 0 after
        """
        def action():
            if self.dyno is not None and isinstance(self.dyno.devices[1], ASIController):
                self._stop_status_thread()
                file = browse_files()
                if file is None or file == "":  # askopenfilename return `None` if dialog closed with "cancel".
                    return
                self.dyno.devices[1].set_access_level(3)
                self.dyno.devices[1].load_parameters(file, master=self.root)
                self.dyno.devices[1].set_access_level(0)
                self._start_status_thread()

        Thread(target=action).start()

    def _file_load_brk(self):
        """
        GUI backend
        BRK load parameters from file - set access level to 3 before and back to 0 after
        """
        def action():
            if self.dyno is not None and isinstance(self.dyno.devices[2], ASIController):
                self._stop_status_thread()
                file = browse_files()
                if file is None or file == "":  # askopenfilename return `None` if dialog closed with "cancel".
                    return
                self.dyno.devices[2].set_access_level(3)
                self.dyno.devices[2].load_parameters(file, master=self.root)
                self.dyno.devices[2].set_access_level(0)
                self._start_status_thread()

        Thread(target=action).start()

    def _load_firmware_dut(self):
        """
        GUI backend
        DUT load firmware from file - needs manual power cycle
        """
        def action():
            if self.dyno is not None and isinstance(self.dyno.devices[1], ASIController):
                self._stop_status_thread()
                self._end_live()
                self.dyno.stop_status()
                file = browse_files()
                if file is None or file == "":  # askopenfilename return `None` if dialog closed with "cancel".
                    return
                self._stop_status_thread()
                self._end_graphing()
                self.dyno.stop_polling()
                sleep(5)
                # popup = Toplevel(self.root, background='white')
                # popup.attributes('-topmost', 'true')
                # popup.attributes('-fullscreen', 'true')
                # popup.attributes('-alpha', 0.75)
                # popup.columnconfigure(0, weight=1)
                # popup.rowconfigure(0, weight=1)
                # Label(popup, text='Updating...\nPlease wait for update to finish.\nProgram will appear unresponsive.',
                #       background='white', anchor='center').grid(column=0, row=0, sticky='news')
                # popup.lift()
                # popup.update_idletasks()
                result = self.dyno.devices[1].load_firmware(file)
                # popup.destroy()
                if result == 0:
                    messagebox.showinfo('Action Required!', 'Update Successful! Please Power Cycle DUT and confirm!')
                else:
                    messagebox.showinfo('Action Required!', 'Update Failed! Please Power Cycle DUT and retry!')
                self._main_connect()

        temp = Thread(target=action)
        temp.start()

    def _load_firmware_brk(self):
        """
        GUI backend
        BRK load firmwere from file - needs manual power cycle
        """
        if self.dyno is not None and isinstance(self.dyno.devices[2], ASIController):
            self._stop_status_thread()
            self._end_live()
            self.dyno.stop_status()
            file = browse_files()
            if file is None or file == "":  # askopenfilename return `None` if dialog closed with "cancel".
                return
            self._stop_status_thread()
            self._end_graphing()
            self.dyno.stop_polling()
            sleep(5)
            # popup = Toplevel(self.root, background='white')
            # popup.attributes('-topmost', 'true')
            # popup.attributes('-fullscreen', 'true')
            # popup.attributes('-alpha', 0.75)
            # popup.columnconfigure(0, weight=1)
            # popup.rowconfigure(0, weight=1)
            # Label(popup, text='Updating...\nPlease wait for update to finish.\nProgram will appear unresponsive.',
            #       background='white', anchor='center').grid(column=0, row=0, sticky='news')
            # popup.lift()
            # popup.update_idletasks()
            result = self.dyno.devices[2].load_firmware(file)
            # popup.destroy()
            if result == 0:
                messagebox.showinfo('Action Required!', 'Update Successful! Please Power Cycle BRK and confirm!')
            else:
                messagebox.showinfo('Action Required!', 'Update Failed! Please Power Cycle BRK and retry!')
            self._main_connect()

    def _reset_configs(self):
        """
        GUI backend
        Resets self.configs from dyno_config.csv
        """
        ask = messagebox.askquestion("Reset Configuration from File", "Are you sure?")
        if ask == 'yes':
            self.configs = config_reader()
            self._populate_config_list()
            self.init_config_list(self.test_tab)
            if self.dyno:
                self.dyno.configs = config_reader()
                self._update_dyno_config()

    def _result_destination(self):
        """
        GUI backend
        Sets result destination for tests
        """
        ans = filedialog.askdirectory(title="Browse", initialdir="C:/DynoResults")
        self.result_destination.set(ans if ans != "" else "C:/DynoResults")
        self._update_dyno_log_dir()

    def _connect_default(self):
        """
        GUI backend
        Sets up DYNO default communication
        """
        self.config_value.set("default")
        self._populate_config_list()

    def _connect_dyno(self):
        """
        GUI backend - obsolete
        Sets up DYNO default communication
        """
        self.config_value.set("DYNO")
        self._populate_config_list()

    def _connect_hi_speed(self):
        """
        GUI backend - obsolete
        Sets up HiSpeed default communication
        """
        self.config_value.set("HiSpeed")
        self._populate_config_list()

    def _connect_mini(self):
        """
        GUI backend - obsolete
        Sets up mini default communication
        """
        self.config_value.set("mini")
        self._populate_config_list()

    def scan_barcode(self, driver="DUT"):
        """
        GUI backend
        Handles barcode scan
        """
        if not (len(self.barcode_var.get().split('~')) == 8 or
                len(self.barcode_var.get().split('~')) == 9 or
                len(self.barcode_var.get().split('~')) == 6):
            try:
                response = simpledialog.askstring("Bad barcode detected!", "Please scan again!")
            except TclError:
                print('Please restart test')
                self.testing = False
                raise TestInterrupt
            if not (len(response.split('~')) == 8 or
                    len(response.split('~')) == 9 or
                    len(response.split('~')) == 6):
                self.testing = False
                return False
            self.barcode_var.set(response)
        if driver == "DUT":
            self.dyno.devices[1].barcode_scanned(self.barcode_var.get())
            self.current_motor.set(self.dyno.devices[1].barcode)
            return [self.dyno.devices[1].barcode, '']
        if driver == "BRK":
            self.dyno.devices[2].barcode_scanned(self.barcode_var.get())
            self.current_motor.set(self.dyno.devices[2].barcode)
            return [self.dyno.devices[2].barcode, '']
        if driver == "both":
            self.dyno.devices[1].barcode_scanned(self.barcode_var.get())
            if not (len(self.barcode_2_var.get().split('~')) == 8 or
                    len(self.barcode_2_var.get().split('~')) == 9 or
                    len(self.barcode_2_var.get().split('~')) == 6):
                try:
                    response = simpledialog.askstring("Bad barcode detected!", "Please scan again!")
                except TclError:
                    print('Please restart test')
                    self.testing = False
                    raise TestInterrupt
                if not (len(response.split('~')) == 8 or
                        len(response.split('~')) == 9 or
                        len(response.split('~')) == 6):
                    self.testing = False
                    return False
                self.barcode_2_var.set(response)
            self.dyno.devices[2].barcode_scanned(self.barcode_2_var.get())
            return [self.dyno.devices[1].barcode, self.dyno.devices[2].barcode]
        return False

    def _barcode2sn(self):
        """
        GUI backend
        Toggles barcode mode or manual mode for test tab
        """
        if self.with_barcode.get():
            self.test_tab.children['test_btn_frame'].children['sn_entry']['state'] = DISABLED
            self.test_tab.children['test_btn_frame'].children['barcode_entry']['state'] = NORMAL
            self.test_tab.children['test_btn_frame'].children['sn_entry_2']['state'] = DISABLED
            self.test_tab.children['test_btn_frame'].children['barcode_2_entry']['state'] = NORMAL

            self.main_elements['main_sn_entry']['state'] = DISABLED
            self.main_elements['main_barcode_entry']['state'] = NORMAL
            self.main_elements['main_sn_2_entry']['state'] = DISABLED
            self.main_elements['main_barcode_2_entry']['state'] = NORMAL
        else:
            self.test_tab.children['test_btn_frame'].children['sn_entry']['state'] = NORMAL
            self.test_tab.children['test_btn_frame'].children['barcode_entry']['state'] = DISABLED
            self.test_tab.children['test_btn_frame'].children['sn_entry_2']['state'] = NORMAL
            self.test_tab.children['test_btn_frame'].children['barcode_2_entry']['state'] = DISABLED

            self.main_elements['main_sn_entry']['state'] = NORMAL
            self.main_elements['main_barcode_entry']['state'] = DISABLED
            self.main_elements['main_sn_2_entry']['state'] = NORMAL
            self.main_elements['main_barcode_2_entry']['state'] = DISABLED

    def _select_all(self, event=None):
        """
        GUI backend
        Select all text in barcode entry
        """
        self.test_tab.children['test_btn_frame'].children['barcode_entry'].select_range(0, END)
        self.main_elements['main_barcode_entry'].select_range(0, END)

    def _select_all_2(self, event=None):
        """
        GUI backend
        Select all text in barcode entry
        """
        self.test_tab.children['test_btn_frame'].children['barcode_2_entry'].select_range(0, END)
        self.main_elements['main_barcode_2_entry'].select_range(0, END)

    def sigint_handler(self, signum=None, frame=None):
        """
        GUI backend
        Interrupts running script
        """
        if hasattr(self, 'dyno') and self.dyno is not None:
            logging.info("Interrupting test script")
            self.test_tab.children['test_btn_frame'].children['stop_btn']['state'] = DISABLED
            # self.testing = False
            self.dyno.testing = False
            try:
                if self.test_handler is not None:
                    try:
                        self.test_handler.interrupt()
                    except TestInterrupt:
                        pass
                print("\n\nInterrupted")
                self._stop_status_thread()
                self.dyno.stop_test()
                self.dyno.stop_logging()
                # self.dyno.plot_basic()
                # self.dyno.plot_error("DUT warnings")
                # self.dyno.plot_error("DUT faults")
                self._end_test_thread()
            except (AttributeError, FileNotFoundError, ValueError) as e:
                logging.warning(e)
            finally:
                self._log_version()
                self.test_tab.children['test_btn_frame'].children['stop_btn']['state'] = NORMAL
                self.controller_tab.children['dut_motor_discovery_btn_1']['state'] = NORMAL
                self.controller_tab.children['brk_motor_discovery_btn_1']['state'] = NORMAL
                self.controller_tab.children['dut_motor_discovery_btn_2']['state'] = NORMAL
                self.controller_tab.children['brk_motor_discovery_btn_2']['state'] = NORMAL
                # self.advanced_tab.children['dut_motor_discovery_btn_3']['state'] = NORMAL
                # self.advanced_tab.children['brk_motor_discovery_btn_3']['state'] = NORMAL
            logging.info("Test script interrupted")
            if self.enable_email.get() and self.enable_int_email.get() and sys.platform.startswith("win"):
                test_interrupted_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")

    def _start_test_thread(self):
        """
        GUI backend
        Starts test thread
        """
        logging.info("Starting test script thread")
        if self.test.get() in ["", "All"]:
            print("Not a valid test! Aborted")
            return
        if len(self.result_destination.get()) == 0:
            logging.info("Empty save destination! Aborted")
            messagebox.showerror("Empty Field", "Please choose a destination for results and restart script!")
            return
        if self.dyno is not None:
            # self._main_connect()
            self.dyno.configs = config_reader()
            self.dyno.config = self.dyno.configs.loc[self.config_value.get()]
            self.dyno.load_config()
            self.dyno.enable_email = self.enable_email.get()
            self.dyno.enable_int_email = self.enable_int_email.get()
            self.dyno.update_log_dir(self.result_destination.get())
            logging.info("Existing connection updated")
        else:
            self.pre_main_run_script()

            self.dyno = ASIDynoModule(config=self.config_value.get(), root=ROOT_DIR,
                                      log_folder=self.result_destination.get(),
                                      enable_email=self.enable_email.get(),
                                      enable_int_email=self.enable_int_email.get())

            self._clear_output()


            logging.info("DYNO created")
            self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame_1,
                                              self.brk_extra_frame_1, self.dut_extra_frame, self.brk_extra_frame],
                                             ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                              "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}",
                                              "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}"],
                                             CONTROL_PARAM_INIT)
        # self._controller_read()
        temp = Thread(target=lambda : self.controller_params_operation([self.dut_frame, self.brk_frame, self.dut_extra_frame,
                                          self.brk_extra_frame, self.dut_extra_frame_1, self.brk_extra_frame_1],
                                         ["DUT", f"{'ABB' if self.abb.get() else 'BRK'}",
                                          "DUT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT'}",
                                          "DUT_EXT_EXT", f"{'ABB' if self.abb.get() else 'BRK_EXT_EXT'}"],
                                         CONTROL_PARAM_UPDATE))
        temp.start()

        try:
            self._limit_update(self.test.get())
        except TestError as e:
            print("Bad speeds detected! Please double check test configuration details")
            logging.error(e)
            return

        self._update_connection_status(self.connector_tab)
        self.connection_condition.set("TESTING")
        if not self.main_parameters['graphing']:
            self.post_main_connect()
        # else:
        self._start_status_thread()
        self.controller_tab.children['dut_motor_discovery_btn_1']['state'] = DISABLED
        self.controller_tab.children['brk_motor_discovery_btn_1']['state'] = DISABLED
        self.controller_tab.children['dut_motor_discovery_btn_2']['state'] = DISABLED
        self.controller_tab.children['brk_motor_discovery_btn_2']['state'] = DISABLED
        # self.advanced_tab.children['dut_motor_discovery_btn_3']['state'] = DISABLED
        # self.advanced_tab.children['brk_motor_discovery_btn_3']['state'] = DISABLED
        self._init_graphing()
        self._update_test_start_time()
        # self._start_live()
        self.testing = True
        self.dyno.testing = True
        self.test_thread = Thread(target=self._run_script)
        self.test_thread.start()
        self._start_graphing()

        logging.info("Test script thread started")

    def _end_test_thread(self):
        """
        GUI backend
        Stops test thread
        """
        print("\n\n\n\n\nEnding script!")
        self.testing = False
        if self.dyno is not None:
            if self.dyno.is_logging_enabled():
                self.dyno.stop_logging()
        # No need to join as the test thread only runs once. Interrupt brings all inner threads to an end
        self.test_thread = None
        # self.test_thread.join()
        logging.info("Test script thread stopped and reset")
        if self.dyno:
            self._main_connect()

    def _update_test_start_time(self):
        """
        GUI backend
        Updates test start time in status bar
        """
        self.test_start_time = datetime.now()
        self.status_params['TEST']['Start Time'].set(f'{self.test_start_time.strftime("%H:%M:%S")}')

    def _run_script(self):
        """
        GUI backend + test handle
        Test script thread target
        """
        try:
            if self.test.get() != 'Life Test/Cyclic Test':
                if self.with_barcode.get():
                    barcode = self.scan_barcode()
                    if not barcode:
                        print("Bad barcode! Please retry! ")
                        return
                else:
                    barcode = [None, None]
            else:
                if self.with_barcode.get():
                    barcode = self.scan_barcode('both')
                    if not barcode:
                        print("Bad barcode! Please retry! ")
                        return
                else:
                    barcode = [None, None]
        except TestInterrupt:
            return

        try:
            if self.connection_condition.get() == "TESTING":
                self.test_handler = ScriptRunner(self.config_value.get(), self.dyno,
                                                 self.with_barcode.get(),
                                                 barcode[0], self.serial_num.get(),
                                                 self.motor_type.get(),
                                                 barcode[1], self.serial_num_1.get(),
                                                 zoom_lo=self.test_tab.children['test_btn_frame'].children[
                                                     'zoom_lo_entry'].get(),
                                                 zoom_hi=self.test_tab.children['test_btn_frame'].children[
                                                     'zoom_hi_entry'].get(),
                                                 zoom=self.rundown_zoom.get(),
                                                 enable_email=self.enable_email.get(),
                                                 enable_int_email=self.enable_int_email.get(),
                                                 effi_target=self.main_parameters['effi_target'].get(),
                                                 result_dir_var=self.main_parameters['result_dir'])
                for graph in PLOT_LIST:
                    self.graphs[graph].reset()
                self.test_handler.run()
        except (TestInterrupt, TestError) as e:
            logging.info(e)
        # if self.test.get() == "Production/Rundown":
        #     self.test_handler = RundownTest(self.dyno, use_barcode=self.with_barcode.get(), zoom=self.rundown_zoom.get(),
        #                                     lo=self.test_tab.children['test_btn_frame'].children[
        #                                         'zoom_lo_entry'].get(),
        #                                     hi=self.test_tab.children['test_btn_frame'].children[
        #                                         'zoom_hi_entry'].get(),
        #                                     motor_type=self.motor_type.get(), barcode=barcode, sn=self.serial_num.get())
        #     self.test_handler.rundown_test()
        # elif self.test.get() == "Validation":
        #     self.test_handler = ProductionValidation(self.dyno)
        #     self.test_handler.production_validation(use_barcode=self.with_barcode.get(), zoom=self.rundown_zoom.get(),
        #                                             lo=self.test_tab.children['test_btn_frame'].children[
        #                                                 'zoom_lo_entry'].get(),
        #                                             hi=self.test_tab.children['test_btn_frame'].children[
        #                                                 'zoom_hi_entry'].get(),
        #                                             motor_type=self.motor_type.get(), barcode=barcode, sn=self.serial_num.get())
        # elif self.test.get() == "ThermalMax":
        #     try:
        #         self._calculate_test_duration()
        #     except TestError as e:
        #         logging.error(e)
        #         return
        #     self.test_handler = ControllerThermalMax(self.dyno, use_barcode=self.with_barcode.get(),
        #                                           motor_type=self.motor_type.get(), barcode=barcode, sn=self.serial_num.get())
        #     self.test_handler.control_thermal_max()
        # elif self.test.get() == 'Life Test/Cyclic Test':
        #     self.cyclic = True
        #     try:
        #         self._calculate_test_duration()
        #     except TestError as e:
        #         logging.error(e)
        #         return
        #     self.test_handler = CyclicTest(self.dyno, use_barcode=self.with_barcode.get(), barcode2=barcode[1], sn2=self.serial_num_1.get(),
        #                                    motor_type=self.motor_type.get(), barcode=barcode[0], sn=self.serial_num.get())
        #     self.test_handler.cyclic_test()
        #     if self.dyno:
        #         self.dyno.stop_test()
        #         self.dyno.stop_logging()
        # elif self.test.get() == 'Efficiency Map':
        #     self.cyclic = True
        #     try:
        #         self._calculate_test_duration()
        #     except TestError as e:
        #         logging.error(e)
        #         return
        #     self.test_handler = EfficiencyMapTest(self.dyno, use_barcode=self.with_barcode.get(),
        #                                           motor_type=self.motor_type.get(), barcode=barcode,
        #                                           sn=self.serial_num.get())
        #     try:
        #         self.test_handler.cyclic_test()
        #     except TestInterrupt:
        #         logging.info("Test Interrupted")
        #     except TestError:
        #         logging.error("Error during Test")
        #     if self.dyno:
        #         self.dyno.stop_test()
        #         self.dyno.stop_logging()
        # elif self.test.get() == 'Line Reactor Test':
        #     self.cyclic = True
        #     try:
        #         self._calculate_test_duration()
        #     except TestError as e:
        #         logging.error(e)
        #         return
        #     self.test_handler = CyclicOpenLoopTest(self.dyno, use_barcode=self.with_barcode.get(),
        #                                           motor_type=self.motor_type.get(), barcode=barcode,
        #                                           sn=self.serial_num.get())
        #     try:
        #         self.test_handler.cyclic_test()
        #     except TestInterrupt:
        #         logging.info("Test Interrupted")
        #     except TestError:
        #         logging.error("Error during Test")
        #     if self.dyno:
        #         self.dyno.stop_test()
        #         self.dyno.stop_logging()
        # elif self.test.get() == "LineReactor":
        #     self.test_handler = LineReactorTest(self.dyno, use_barcode=self.with_barcode.get(),
        #                                         motor_type=self.motor_type.get(), barcode=barcode, sn=self.serial_num.get())
        #     self.test_handler.line_reactor_test()
        # elif self.test.get() == "Debug":
        #     self.cyclic = True
        #     self.status_params['TEST']['Est. Test Time'].set(f'{10} s')
        #     self.test_handler = ForDebug(self.dyno)
        #     self.test_handler.debug()
        #     if self.enable_email.get():
        #         test_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")
        # elif self.test.get() == "Debug Dyno Start/Stop":
        #     self.test_handler = DebugStartStop(self.dyno)
        #     self.test_handler.debug()
        self._end_graphing()
        self._log_version()
        try:
            if self.enable_email.get():
                email = ''
                if self.notify.get():
                    email = self.test_tab.children['test_btn_frame'].children['email_entry'].get()
                    if self.notify and email.strip() != "":
                        email = email.strip() + '@acceleratedsystems.com'
                end_of_script_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log",
                                    test=self.test.get(), cc=email)
        except (AttributeError, TypeError):
            pass

        self.test_handler = None
        # self._main_connect()
        if self.testing:
            self.connection_condition.set("DISCONNECT")
            self._main_connect()
        self.test_tab.children['test_btn_frame'].children['barcode_entry'].focus_set()
        self.controller_tab.children['dut_motor_discovery_btn_1']['state'] = NORMAL
        self.controller_tab.children['brk_motor_discovery_btn_1']['state'] = NORMAL
        self.controller_tab.children['dut_motor_discovery_btn_2']['state'] = NORMAL
        self.controller_tab.children['brk_motor_discovery_btn_2']['state'] = NORMAL
        # self.advanced_tab.children['dut_motor_discovery_btn_3']['state'] = NORMAL
        # self.advanced_tab.children['brk_motor_discovery_btn_3']['state'] = NORMAL
        logging.info("End of _run_script")

    def _log_version(self):
        """
        GUI backend
        Logs software version at end of test scripts
        """
        if self.dyno:
            result_txt = self.dyno.logdir / "DynoController Version.txt"
            with open(result_txt, "a") as txt:
                txt.write(f"{__version__}")

    def _update_dyno_config(self):
        """
        GUI backend
        Updates dyno config
        """
        if self.dyno:
            self.dyno.config = self.config_value.get()
            self.dyno.load_config()

    def _update_dyno_log_dir(self):
        """
        GUI backend
        Updates dyno logging directory
        """
        if self.dyno:
            self.dyno.update_log_dir(self.result_destination.get())

    def _cyclic_limit_parse(self):
        """
        GUI backend
        Updates speed limits for cyclic tests
        """
        upper = 1000
        lower = -1000
        if self.dyno.devices[1]:
            raw = self.dyno.config["jw_cyclic_speed_a"]
            if raw.startswith('[') and raw.endswith(']'):
                raw = raw.strip('[]').split(', ')
                temp = []
                for u in raw:
                    temp.append(abs(float(u)))
                if upper < max(temp):
                    upper = max(temp)
                if lower > min(temp):
                    lower = min(temp)
            elif float(raw):
                if upper < float(raw):
                    upper = float(raw)
                if lower > float(raw):
                    lower = float(raw)
            else:
                raise TestError('Bad values for DUT A speeds')
        if self.dyno.devices[2]:
            raw = self.dyno.config["jw_cyclic_speed_b"]
            if raw.startswith('[') and raw.endswith(']'):
                raw = raw.strip('[]').split(', ')
                temp = []
                for u in raw:
                    temp.append(float(u))
                if upper < max(temp):
                    upper = max(temp)
                if lower > min(temp):
                    lower = min(temp)
            elif float(raw):
                if upper < float(raw):
                    upper = float(raw)
                if lower > float(raw):
                    lower = float(raw)
            else:
                raise TestError('Bad values for DUT B speeds')
        return upper, lower

    def _limit_update(self, test):
        """
        GUI backend
        Updates safety limits
        """
        if test == "Production/Rundown":
            if self.speed_limit_upper.get() - 200 <= int(self.dyno.config["pt_speed"]):
                self.speed_limit_upper.set(int(self.dyno.config["pt_speed"]) + 200)
            if self.speed_limit_lower.get() >= -200:
                self.speed_limit_lower.set(-200)
            if self.torque_limit.get() < float(self.dyno.config["max_torque"]):
                self.torque_limit.set(float(self.dyno.config["max_torque"]))
        elif test == "Validation":
            if self.speed_limit_upper.get() - 200 <= int(self.dyno.config["pt_speed"]):
                self.speed_limit_upper.set(int(self.dyno.config["pt_speed"]) + 200)
            if self.speed_limit_lower.get() >= -200:
                self.speed_limit_lower.set(-200)
            if self.torque_limit.get() < float(self.dyno.config["max_torque"]):
                self.torque_limit.set(float(self.dyno.config["max_torque"]))
        elif test == "ThermalMax":
            if self.speed_limit_upper.get() - 200 <= int(self.dyno.config["ctm_rpm"]):
                self.speed_limit_upper.set(int(self.dyno.config["ctm_rpm"]) + 200)
            if self.speed_limit_lower.get() >= -200:
                self.speed_limit_lower.set(-200)
            if self.torque_limit.get() < float(self.dyno.config["max_torque"]):
                self.torque_limit.set(float(self.dyno.config["max_torque"]))
        elif test == 'Life Test/Cyclic Test':
            hi, lo = self._cyclic_limit_parse()
            if self.speed_limit_upper.get() < hi + 1000:
                self.speed_limit_upper.set(int(hi + 1000))
            if self.speed_limit_lower.get() > lo - 1000:
                self.speed_limit_lower.set(int(lo - 1000))
        elif test == 'Efficiency Map':
            if self.speed_limit_upper.get() <= 5200:
                self.speed_limit_upper.set(5200)
            if self.speed_limit_lower.get() >= -200:
                self.speed_limit_lower.set(-200)
        elif test == "LineReactor":
            return
        elif test == "Debug":
            if self.speed_limit_upper.get() <= 400:
                self.speed_limit_upper.set(400)
            if self.speed_limit_lower.get() >= -200:
                self.speed_limit_lower.set(-200)
        elif test == "Debug Dyno Start/Stop":
            return
        self._upload_limits()

    def _advanced_access_level(self, level=0):
        """
        GUI backend
        Updates access level in advanced tab
        """
        if self.dyno and self.dyno.devices[1]:
            self.dyno.devices[1].set_access_level(level)

        if self.dyno and isinstance(self.dyno.devices[2], ASIController):
            self.dyno.devices[2].set_access_level(level)

    def _clear_output(self):
        """
        GUI backend
        Clears output
        """
        self.text['state'] = NORMAL
        self.text.delete('1.0', END)
        self.text.update()
        self.text['state'] = DISABLED

    def _clear_error(self):
        """
        GUI backend
        Clears error
        """
        self.error_text['state'] = NORMAL
        self.error_text.delete('1.0', END)
        self.error_text.update()
        self.error_text['state'] = DISABLED

    def _resize(self, event):
        """
        GUI backend
        Updates screen size indicator values upon root resize
        """
        if event.widget == self.root:
            if (self.width.get() != event.width) and (self.height.get() != event.height):
                self.width.set(event.width)
                self.height.set(event.height)

    def _resize_hd(self):
        self.root.geometry(HD_SIZE)
        self.root.update()
        self.width.set(int(HD_SIZE.split('x')[0]))
        self.height.set(int(HD_SIZE.split('x')[1]))

    def _on_closing(self):
        """
        GUI backend
        Handles program closing
        """
        logging.info("DynoController shutting down")
        if (self.connection_condition.get() == "DISCONNECT"
                or self.connection_condition.get() == "TESTING"):
            self._main_connect()
        if self.can_interface:
            self._closing_can_interface()
        config = ConfigParser()
        config.read('gui.ini')
        config.set('GUI', 'geometry', f'{self.root.geometry()}')
        config.set('GUI', 'out_geometry', f'{self.out_level.geometry()}')
        with open('gui.ini', 'w') as file:
            config.write(file)
        self.root.update_idletasks()
        self.root.update()
        self.root.destroy()
        logging.info("DynoController terminated")

    def _dark_light_mode(self):
        """
        GUI backend
        Toggles between light & dark mode (beta)
        """
        if self.dark_mode.get() == 'Enable':
            self.root.config(bg="#26242f")
            styling(False)
            self.connector_tab.children['status_0'].config(background="#26242f")
            self.connector_tab.children['status_1'].config(background="#26242f")
            self.connector_tab.children['status_2'].config(background="#26242f")
            self.dark_mode.set('Disable')
        else:
            self.root.config(bg="white")
            styling(True)
            self.connector_tab.children['status_0'].config(background="white")
            self.connector_tab.children['status_1'].config(background="white")
            self.connector_tab.children['status_2'].config(background="white")
            self.dark_mode.set('Enable')

    def _output_toggle(self):
        """
        GUI backend - needs update for v0.7
        Toggles output 
        """
        if self.output_toggle.get() == 'Hide':
            self.n_out.grid_remove()
            self.root.columnconfigure(1, weight=0)
            self.output_toggle.set('Show')
        else:
            self.n_out.grid(column=1, row=0, sticky='news')
            self.root.columnconfigure(1, weight=1)
            self.output_toggle.set('Hide')

    def _bac_2_bac(self):
        """
        GUI backend
        Toggles BAC2BAC mode for controller tab BACDoor section
        """
        if self.bac_2_bac.get() == 'Enable':
            self.dut_extra_frame.master.master.pack(fill='both')
            self.dut_extra_frame.master.master.master.grid(column=1, row=0, sticky='news', padx=2)
            self.dut_extra_frame_1.master.master.pack(fill='both')
            self.dut_extra_frame_1.master.master.master.grid(column=1, row=1, sticky='news', padx=2)
            self.brk_frame.master.master.master.grid(column=2, row=0, sticky='news', padx=2)
            self.brk_extra_frame.master.master.pack(fill='both')
            self.brk_extra_frame.master.master.master.grid(column=3, row=0, sticky='news', padx=2)
            self.brk_extra_frame_1.master.master.pack(fill='both')
            self.brk_extra_frame_1.master.master.master.grid(column=3, row=1, sticky='news', padx=2)
            self.controller_tab.children['param_frame'].columnconfigure((2, 3), weight=1)
            self.bac_2_bac.set('Disable')
            self.output_toggle.set('Hide')
            # self._output_toggle()
            # self.controller_tab.children['btn_frame'].grid_remove()
            # self.controller_tab.children['btn_frame_2'].grid_remove()
            # self.controller_tab.children['rest_frame'].grid_remove()
        else:
            self.dut_extra_frame.master.master.master.grid_remove()
            self.dut_extra_frame.master.master.pack_forget()
            self.dut_extra_frame_1.master.master.master.grid_remove()
            self.dut_extra_frame_1.master.master.pack_forget()
            self.brk_extra_frame.master.master.master.grid_remove()
            self.brk_extra_frame.master.master.pack_forget()
            self.brk_extra_frame_1.master.master.master.grid_remove()
            self.brk_extra_frame_1.master.master.pack_forget()
            self.brk_frame.master.master.master.grid(column=1, row=0, sticky='news', padx=2)
            self.controller_tab.children['param_frame'].columnconfigure((2, 3), weight=0)
            self.bac_2_bac.set('Enable')
            self.output_toggle.set('Show')
            # self._output_toggle()
            # self.controller_tab.children['btn_frame'].grid(column=0, row=15, columnspan=2, sticky='news')
            # self.controller_tab.children['btn_frame_2'].grid(column=2, row=START_ROW+ 15,
            #                                                  columnspan=2, sticky='news', padx=20)
            # self.controller_tab.children['rest_frame'].grid(column=0, row=17, columnspan=4, sticky='news')

    def _update_font_size(self, event=None):
        """
        GUI backend
        Update software font size
        """
        # default_font = font.nametofont(OPTION_FONT_NAME)
        # default_font.configure(size=self.font_size.get())
        styler = ttk.Style()
        styler.configure(".", font=f'{OPTION_FONT_NAME} {self.font_size.get()}')
        sleep(0.1)
        # self.speed_limit_frame.children['upper_limit'].configure(size=self.font_size.get())
        # self.speed_limit_frame.children['lower_limit'].configure(size=self.font_size.get())
        # self.speed_limit_frame.children['torque_limit'].configure(size=self.font_size.get())
        # x, y = self.status_bar.children['status_pane'].sash_coord(3)
        # self.status_bar.children['status_pane'].sash_place(3, x + 1, y)
        self.status_bar.children['status_pane'].paneconfig(height=self.dut_status_frame.winfo_height())

    def _update_test_duration(self):
        """
        GUI backend
        Updates status bar test duration
        """
        if self.test_handler:
            self.status_params['TEST']['Est. Test Time'].set(self.test_handler.plot_parameters['Est. Test Time'])

    def _calculate_test_duration(self):
        """
        GUI backend
        Updates status bar test duration
        """
        if self.dyno is not None:
            if self.test.get() == 'ThermalMax':
                self.status_params['TEST']['Est. Test Time'].set(f'{self.dyno.config["basic_testtime"] + 2} min')
            elif self.test.get() == 'Life Test/Cyclic Test':
                cycle_mode = 0
                if pd.isna(self.dyno.config['cycle_type']) or self.dyno.config['cycle_type'] == '':
                    self.status_params['TEST']['Est. Test Time'].set('0')
                    # raise TestError('Bad Cycle Mode')
                    return
                else:
                    cycle_mode = int(self.dyno.config['cycle_type'])
                if int(self.dyno.config['cycle_type']) == 0:
                    try:
                        cycles = int(self.dyno.config['jw_cyclic_cycle'])
                    except TypeError:
                        print('Bad value for total total_cycles')
                        raise TestError('Bad value for total total_cycles')

                    try:
                        steps = self.dyno.config['jw_cyclic_step']
                    except (AttributeError, TypeError) as e:
                        logging.error(f"{e}\nWhen loading cyclic test hold times (jw_cyclic_step)")
                        raise TestError("Can't read cyclic total_steps")
                    else:
                        if steps.startswith('[') and steps.endswith(']'):
                            steps = steps.strip('[]').split(', ')
                        elif float(steps):
                            steps = [float(steps)]
                        else:
                            logging.error("Bad total_steps format")
                            raise TestError("Bad total_steps format")
                    def parse_param(var):
                        ans = [0] * len(steps)
                        if isinstance(var, str):
                            if var.startswith('[') and var.endswith(']'):
                                ans = var.strip('[]').split(', ')
                        elif pd.isna(var):
                            ans = [0] * len(steps)
                        else:
                            try:
                                float(var)
                            except (ValueError, TypeError):
                                pass
                            else:
                                ans = [float(var)] * len(steps)
                        if len(ans) == 1:
                            if pd.isna(ans[0]):
                                ans = [0] * len(steps)
                        return ans

                    cd = self.dyno.config['cycle_cd']
                    cd = parse_param(cd)
                    ramp = self.dyno.config['jw_cyclic_ramp']
                    ramp = parse_param(ramp)

                    duration_sec = 0
                    for i in range(len(steps)):
                        duration_sec += ramp[i] * 2 + float(steps[i])
                        # print(duration_sec)
                        if cycle_mode == 1:
                            duration_sec += cd[0] * 60
                        elif cycle_mode > 1:
                            duration_sec += 1800
                    duration_sec = cycles * duration_sec + 10

                    self.status_params['TEST']['Est. Test Time'].set(
                        f'{duration_sec // 3600:03g}:{(duration_sec % 3600) // 60:02g}:{duration_sec % 60:02g}')
            elif self.test.get() == "Production/Rundown":
                self.status_params['TEST']['Est. Test Time'].set('~3 min')
            elif self.test.get() == "Efficiency Map":
                self.status_params['TEST']['Est. Test Time'].set('~2 hrs')

    @staticmethod
    def _orphan(widget):
        """
        GUI backend
        Destroys all children in a TK widget
        """
        for child in widget:
            child.destroy()

    def _update_ports(self, event=None):
        """
        GUI backend
        Updates com port dropdown values
        """
        ports = _com_ports()
        self.connector_tab.children['dut_port_combo']['values'] = ports
        self.connector_tab.children['brk_port_combo']['values'] = ports

    def _update_baud(self, event=None):
        """
        GUI backend
        Update baud rate based on selected com port
        """
        # if event.widget == self.connector_tab.children['dut_port_combo']:
        if 'COM' in self.dut_port.get():
            self.connector_tab.children['dut_baud_combo']['values'] = COM_BAUD_RATE
            self.dut_rate.set(COM_BAUD_RATE[0])
        else:
            self.connector_tab.children['dut_baud_combo']['values'] = CAN_BAUD_RATE
            self.dut_rate.set(CAN_BAUD_RATE[0])
        # if event.widget == self.connector_tab.children['brk_port_combo']:
        if 'COM' in self.brk_port.get():
            self.connector_tab.children['brk_baud_combo']['values'] = COM_BAUD_RATE
            self.brk_rate.set(COM_BAUD_RATE[0])
        else:
            self.connector_tab.children['brk_baud_combo']['values'] = CAN_BAUD_RATE
            self.brk_rate.set(CAN_BAUD_RATE[0])

    def _value_format(self, name, controller, value):
        """
        GUI backend
        Format parameter value
        """
        if self.dyno:
            if controller in ["DUT", 'DUT_EXT', 'DUT_EXT']:
                if len(self.dyno.devices[1].run_parameters[name].Bits) >= 8:
                    return f'{int(value):016b}'
                elif self.dyno.devices[1].run_parameters[name].Scale == 'hex':
                    return f'{hex(int(value))[2:].upper()}'
            elif controller in ["BRK", 'BRK_EXT', "BRK_EXT_EXT"] and isinstance(self.dyno.devices[2], ASIController):
                if len(self.dyno.devices[2].run_parameters[name].Bits) >= 8:
                    return f'{int(value):016b}'
                elif self.dyno.devices[2].run_parameters[name].Scale == 'hex':
                    return f'{hex(int(value))[2:].upper()}'
        return value

    def _can_interface(self):
        """
        GUI backend
        Toggles up CAN interface
        """
        if self.can_interface is None:
            # self.advanced_tab.children['can_interface_btn'].configure(text='Stop')
            if self.dyno is None:
                logging.info("Launching CAN Interface")
                self._popup_can_connect()
            elif self.dyno.devices[1].can:
                logging.info("Launching CAN Interface for monitoring")
                self.can_interface = CANInterface(self.root, f"{ROOT_DIR}\\dyno_v2", device=self.dyno.devices[1], rate=self.dyno.devices[1].baud_rate,
                                                  device_id=self.dyno.devices[1].can_bus.id, dictionary=self.dyno.devices[1].dictionary_file)
                self.can_interface.init_interface()
                self.can_interface.device.can_bus.can_pdo_handle = self.can_interface.can_pdo_handle
                self.can_interface.root.protocol("WM_DELETE_WINDOW", self._closing_can_interface)
        else:
            self._closing_can_interface()
            # self.can_interface = None
            # self.advanced_tab.children['can_interface_btn'].configure(text='Launch')

    def _closing_can_interface(self):
        """
        GUI backend
        Closes CAN interface
        """
        logging.info('Closing CAN PDO Interface')
        self.can_interface.stop_rpdo_thread()
        if isinstance(self.can_interface.device, ASIController):
            if self.can_interface.monitor:
                self.can_interface.device.can_bus.can_pdo_handle = self.can_interface.can_pdo_handle_original
                self.dyno.devices[1] = self.can_interface.device
                self.can_interface.device.can_bus.__del__()
                # self._stop_status_thread()
                # self._end_graphing()
                # self.dyno.devices[1].can_bus = CANcom(can_port=self.dyno.devices[1].port_name,
                #                                bit_rate=self.dyno.devices[1].baud_rate, can_id=self.dyno.devices[1].com_id)
                # self._start_status_thread()
                # self._start_graphing()
                self._on_connect()
                self._on_connect()
                # self.dyno.devices[1].can_bus.can_pdo_handle = self.can_interface.can_pdo_handle_original
            else:
                self.can_interface.device.__del__()
        elif isinstance(self.can_interface.device, J1939com):
            self.can_interface.device.__del__()
        else:
            self.can_interface.can_bus.__del__()
        self.can_interface.root.destroy()
        self.can_interface = None
        # self.advanced_tab.children['can_interface_btn'].configure(text='Launch')
        # print(self.can_interface.device)

    def _popup_can_connect(self):
        """
        GUI backend + popup 
        Constructing CAN interface popup
        """
        popup = Toplevel(self.root, background='white')
        popup.geometry(f'700x180+10+10')
        popup.resizable(True, True)
        popup.columnconfigure(2, weight=1)
        baud_var = IntVar(value=250000)
        id_var = IntVar(value=42)
        dictionary = StringVar(
            value='C:\\Users\\twu\\PycharmProjects\\dyno-v2\\dyno_v2\\Dictionary\\6024_ASIObjectDictionary.xml')
        device = StringVar(value='BAC')
        ttk.Label(popup, text='Baud Rate').grid(column=0, row=0)
        ttk.Combobox(popup, textvariable=baud_var, width=6, name='can_interface_baud_combo',
                     font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=1, row=0, sticky='we')
        popup.children['can_interface_baud_combo']['values'] = CAN_BAUD_RATE
        # Entry(popup, textvariable=baud_var, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}', name='baud_entry').grid(column=1, row=0)
        ttk.Label(popup, text='ID').grid(column=0, row=1)
        Entry(popup, textvariable=id_var, font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}',
              name='id_entry').grid(column=1, row=1)

        ttk.Label(popup, text="Dictionary: ").grid(column=0, row=2, pady=10)
        Entry(popup, textvariable=dictionary, name='dict_entry',
              font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=1, row=2, sticky='we', columnspan=2)

        ttk.Label(popup, text="Device: ").grid(column=0, row=3, pady=10)
        ttk.Combobox(popup, textvariable=device, name='device_combo',
                     font=f'{OPTION_FONT_NAME} {OPTION_FONT_SIZE}').grid(
            column=1, row=3, sticky='we', columnspan=2)
        popup.children['device_combo']['value'] = CAN_INTERFACE_OPTIONS

        def update_interface(event=None):
            dictionary.set(CAN_INTERFACE_DEFAULT_DICTIONARY[device.get()])

        def connect():
            popup.destroy()
            interface = CANInterface(self.root, f"{ROOT_DIR}\\dyno_v2", baud_var.get(), id_var.get(),
                                     device=device.get(), dictionary=dictionary.get())
            interface.init_interface()
            self.can_interface = interface
            self.can_interface.root.protocol("WM_DELETE_WINDOW", self._closing_can_interface)

        def cancel():
            popup.destroy()
            # self.advanced_tab.children['can_interface_btn'].configure(text='Launch')

        def set_dictionary():
            dictionary.set(filedialog.askopenfilename(initialdir="C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Dictionary",
                                                      initialfile="6023_ASIObjectDictionary.xml",
                                                      title="Select a File",
                                                      filetypes=(("ASI files", "*.xml*"), ("all files", "*.*"))))
            popup.lift()

        popup.children['device_combo'].bind('<<ComboboxSelected>>', update_interface)
        Button(popup, text="Browse", command=set_dictionary, name='browse_btn').grid(
            column=3, row=2, sticky='we')
        Button(popup, text='Connect', command=connect).grid(column=2, row=10)
        Button(popup, text='Cancel', command=cancel).grid(column=3, row=10)
        popup.protocol("WM_DELETE_WINDOW", cancel)

    @staticmethod
    def _open_cedar_guide():
        import subprocess
        subprocess.Popen(['CEDAR MOTOR TESTING PROCEDURE.docx'], shell=True)


if __name__ == "__main__":
    logging.info("Initiating...")
    gui = Tk()
    DynoConnector(gui)
    gui.mainloop()
