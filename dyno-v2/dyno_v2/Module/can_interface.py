import tkinter
from threading import Thread
from time import sleep
from dyno_v2.Module.CANcom import CANcom
from dyno_v2.Module.asi_controller import ASIController
from dyno_v2.Module.Parameter import Parameter
from dyno_v2.Module.j1939 import *
from tkinter import ttk
from tkinter import *
from tkinter import messagebox
import can
import xml.etree.ElementTree as ET
from dyno_v2.GUI.ScrollableFrame import ScrollableFrame
from dyno_v2.GUI.tooltip import ToolTip
from dyno_v2.Module.util import parse_etree, load_using_param_names, get_scale_value, signed
import logging

class CANInterface(CANcom):

    def __init__(self, root, root_dir, rate, device_id, dictionary, device):
        self.root = Toplevel(root)
        self.root_dir = root_dir
        self.notebook = None
        self.pdo_tab = None
        self.tpdo_param = {0: {}, 1: {}}
        self.rpdo_param = {0: {}, 1: {}}
        self.sdo_param = {0: {}, 1: {}}
        if dictionary != '':
            self.etree = parse_etree(dictionary)
        self.mainframe = None
        self.tpdo_frame = None
        self.rpdo_frame = None
        self.pdo_frame = None
        self.sdo_frame = None
        self.rpdo_thread = {}
        self.rpdo_running = False

        if device == 'BAC':
            self.device = ASIController(com_port='PCAN_USBBUS1', baud_rate=rate,
                                        mb_address=device_id, is_can=True, root=root_dir)
            self.device.can_bus.can_pdo_handle = self.can_pdo_handle
            self.monitor = False
        elif isinstance(device, ASIController):
            self.device = device
            # self.device.can_bus.can_pdo_handle = self.can_pdo_handle
            self.monitor = True
        elif 'J1939' in device:
            if device == 'BAC_J1939':
                self.device = J1939com(tree=self.etree, can_port='PCAN_USBBUS1', bit_rate=rate, can_id=0xef, device='BAC')
                self.monitor = 'BAC'
                self.run_parameters = load_using_param_names(self.etree,
                                                             f"{self.root_dir}/Parameter Files/Run parameters for ASI controller default.csv")
            elif device == 'Throttle_J1939':
                self.device = J1939com(tree=self.etree, can_port='PCAN_USBBUS1', bit_rate=rate, can_id=0xb1,
                                       device='Throttle', parameters="dyno_v2/Parameter Files/J1939_Throttle.xml")
                self.monitor = 'Throttle'
                self.run_parameters = load_using_param_names(self.etree,
                                                             f"{self.root_dir}/Parameter Files/Run parameters for ASI throttle default.csv")
            elif device == 'VCM_J1939':
                self.device = J1939com(tree=self.etree, can_port='PCAN_USBBUS1', bit_rate=rate, can_id=0x27,
                                       device='VCM', parameters="dyno_v2/Parameter Files/J1939_VCM.xml")
                self.monitor = 'VCM'
                self.run_parameters = load_using_param_names(self.etree,
                                                             f"{self.root_dir}/Parameter Files/Run parameters for ASI VCM default.csv")
            self.read_write_param = StringVar()
            self.read_write_option = StringVar(value='read')
            self.read_write_value = StringVar(value='0')
            self.pgn_broadcast = {}
            self.target = IntVar(value=self.device.id[0])
            self.pgn_params = {}
            self.device.pgn_msg_handle = self.pgn_msg_handle
        else:
            super().__init__('PCAN_USBBUS1', rate, device_id)

            logging.info("Instantiate Parameter Object Dictionary")
            root = ET.parse(dictionary).getroot()
            logging.info("Generating parameter object")
            for section in root.findall('Parameters'):
                for element in section.findall('ParameterDescription'):
                    parameter = Parameter()
                    parameter.set_using_xml_element(element)
                    self.run_parameters[parameter.Name] = parameter

    def init_interface(self):
        self.root.title("ASI CAN Interface")
        if isinstance(self.device, J1939com):
            if self.monitor == 'BAC':
                self.root.geometry(f'1300x1000+1650-800')
            elif self.monitor == 'Throttle':
                self.root.geometry('800x1000+1650-800')
            elif self.monitor == 'VCM':
                self.root.geometry('2300x1300+1650-800')
        else:
            self.root.geometry(f'900x600+50+50')
        # self.root.resizable(True, True)
        self.root.iconbitmap(f'{self.root_dir}/ASI Logo grayscale.ico')
        self.root['background'] = 'white'
        # self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.mainframe = Frame(self.root)
        self.mainframe.pack(fill='both')
        self.mainframe.columnconfigure((0, 1, 2, 3), weight=1)
        # self.mainframe.rowconfigure(0, weight=1)

        self.pdo_frame = self.init_pdo()
        if isinstance(self.device, J1939com):
            self.sdo_frame = self.init_sdo()
        self._init_rpdo_thread()

    def init_buttons(self):
        mainframe = Frame(self.mainframe, name='btn_frame')
        mainframe.grid(column=0, row=1, columnspan=4, sticky='news')


        return mainframe

    def init_pdo(self):
        mainframe = LabelFrame(self.mainframe, name='pdo_frame',
                               text='PDO' if not isinstance(self.device, J1939com) else 'PGN', background='white')
        mainframe.grid(column=0, row=0, columnspan=4, sticky='news')
        mainframe.columnconfigure((0, 1, 2, 3), weight=1)
        mainframe.rowconfigure(1, weight=1)
        if isinstance(self.device, J1939com):
            ttk.Label(mainframe, text='Target Device Source Address', name='label_device_target').grid(column=0, row=0)
            Entry(mainframe, textvariable=self.target, width=5, name=f"entry_device_target").grid(column=1, row=0)

        tpdo_frame = ScrollableFrame(mainframe, height=800 if self.monitor != 'VCM' else 1100, bg='white')
        if self.monitor != 'VCM':
            tpdo_frame.grid(column=0, row=1, columnspan=2, sticky='news')
        else:
            tpdo_frame.grid(column=0, row=1, columnspan=4, sticky='news')

        self.tpdo_frame = tpdo_frame.scrollable_frame
        self.tpdo_frame.rowconfigure(0, weight=1)

        if isinstance(self.device, ASIController):
            for j, id in enumerate(self.device.can_bus.id):
                outer_container = LabelFrame(self.tpdo_frame, background='white', text=f"CAN ID - {id}")
                outer_container.grid(column=j, row=0, sticky='news')
                for tpdo in self.device.can_bus.TPDO[j]:
                    container = LabelFrame(outer_container, background='white', text=f"{'T' if tpdo.tx else 'R'}PDO{tpdo.idx}")
                    container.pack(fill='both')
                    for i, idx in enumerate(tpdo.idx_map):
                        if i < tpdo.size:
                            # print(f"{int(tpdo.idx_map[i][0]):04x}", f"{int(tpdo.idx_map[i][1]):02x}")
                            # address = (tpdo.idx_map[idx][0] - 8192) * 64
                            # param = self.device.can_bus.map2name(address, tpdo.idx_map[idx][1] - 1)
                            # if not idx:
                            #     self.device.add_run_parameter(idx)
                                # param = self.device.can_bus.map2name(address, tpdo.idx_map[idx][1] - 1)
                            # param = self.device.can_bus.map2name(tpdo.idx_map[i][0], tpdo.idx_map[i][1])
                            self.tpdo_param[j][idx] = StringVar(value='0')
                            temp = ttk.Label(container, text=f"{idx}",
                                             name=f"{'device_one' if j == 0 else 'device_two'}_label_{idx}_tpdo{tpdo.idx}", anchor='w')
                            temp.grid(column=0, row=tpdo.idx * 4 + i)
                            temp = ttk.Label(container, textvariable=self.tpdo_param[j][idx],
                                             name=f"{'device_one' if j == 0 else 'device_two'}_value_{idx}_tpdo{tpdo.idx}")
                            temp.grid(column=1, row=tpdo.idx * 4 + i)
        elif isinstance(self.device, J1939com):
            if self.monitor != 'VCM':
                for j, id in enumerate(self.device.id):
                    outer_container = LabelFrame(self.tpdo_frame, background='white', text=f"PDU1 - SA - {id} - {id:02X}")
                    outer_container.grid(column=j, row=0, sticky='nw')
                    outer_container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                    self.pgn_params[id] = {}
                    for pgn in self.device.specific_parameters[id]:
                        self.pgn_params[id][pgn] = {}
                        if self.device.specific_parameters[id][pgn].get_pf() > 240:
                            container = LabelFrame(outer_container, background='white',
                                                   text=f"{self.device.specific_parameters[id][pgn].pgn} - "
                                                        f"{self.device.specific_parameters[id][pgn].pgn:06X}")
                            container.pack(fill='both')
                            container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                            self.pgn_params[id][pgn][self.device.specific_parameters[id][pgn].get_ps()] = {}
                            for i, spn in enumerate(self.device.specific_parameters[id][pgn].spg):
                                self.pgn_params[id][pgn][self.device.specific_parameters[id][pgn].get_ps()][spn] = StringVar(value='0')
                                a = self.device.specific_parameters[id][pgn].pgn
                                b = self.device.specific_parameters[id][pgn].spg[spn].spn
                                # print(spn, self.pgn_params[id][pgn][spn].get())
                                temp = ttk.Label(container, text=f"{self.device.specific_parameters[id][pgn].spg[spn].label}",
                                                 name=f"{id}_pgn_{a}_spn_{b}_label", anchor='w', wraplength=200, justify='center')
                                temp.grid(column=0, row=i)
                                temp.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                                ToolTip(temp, msg=self.device.specific_parameters[id][pgn].spg[spn].description, delay=1, follow=False,
                                        name=f"{id}_pgn_{a}_spn_{b}_tt")
                                temp = ttk.Label(container,
                                                 textvariable=self.pgn_params[id][pgn][self.device.specific_parameters[id][pgn].get_ps()][spn],
                                                 width=10, name=f"{id}_pgn_{a}_spn_{b}_value")
                                temp.grid(column=1, row=i)
                                ttk.Label(container, text=self.device.specific_parameters[id][pgn].spg[spn].unit, width=10,
                                          name=f"{id}_pgn_{a}_spn_{b}_unit").grid(
                                    column=2, row=i)
                                container.children[f"{id}_pgn_{a}_spn_{b}_unit"].bind('<MouseWheel>',
                                                                                       self.tpdo_frame.master.master.on_mousewheel)
            else:
                # for j, id in enumerate(self.device.id):
                self.target.set(39)
                device = 39
                outer_container = LabelFrame(self.tpdo_frame, background='white', text=f"Commands - {device:02X}")
                outer_container.grid(column=0, row=0, sticky='nw')
                outer_container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                status_container = LabelFrame(self.tpdo_frame, name='vcm_status_frame',
                                               text='Status PGNs')
                status_container.grid(column=0, row=1)
                battery_container = LabelFrame(self.tpdo_frame, name='vcm_battery_frame',
                                               text='Battery PGNs')
                battery_container.grid(column=0, row=2)
                self.pgn_params[device] = {}
                for pgn in self.device.specific_parameters[device]:
                    self.pgn_params[device][pgn] = {}
                for k, pgn in enumerate(self.device.specific_parameters[device]):
                    if (self.device.specific_parameters[device][pgn].get_pf() == 0xff and
                            self.device.specific_parameters[device][pgn].get_ps() in [0x10, 0x11]) or \
                        (self.device.specific_parameters[device][pgn].get_pf() == 0xfe and
                            self.device.specific_parameters[device][pgn].get_ps() == 0xca):
                        self.pgn_params[device][pgn][self.device.specific_parameters[device][pgn].get_ps()] = {}
                        # print(device, pgn, self.device.specific_parameters[device][pgn].get_ps())
                        container = LabelFrame(status_container, background='white',
                                               text=f"{self.device.specific_parameters[device][pgn].pgn} - "
                                                    f"{self.device.specific_parameters[device][pgn].pgn:06X}")
                        container.grid(column=k, row=0)
                        container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                        for i, spn in enumerate(self.device.specific_parameters[device][pgn].spg):
                            self.pgn_params[device][pgn][self.device.specific_parameters[device][pgn].get_ps()][spn] = StringVar(value='0')
                            # print(pgn, spn)
                            a = self.device.specific_parameters[device][pgn].pgn
                            b = self.device.specific_parameters[device][pgn].spg[spn].spn
                            # print(spn, self.pgn_params[device][pgn][spn].get())
                            temp = ttk.Label(container, text=f"{self.device.specific_parameters[device][pgn].spg[spn].label}",
                                             name=f"{device}_pgn_{a}_spn_{b}_label", anchor='w', wraplength=250, justify='center')
                            temp.grid(column=0, row=i)
                            temp.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                            ToolTip(temp, msg=self.device.specific_parameters[device][pgn].spg[spn].description, delay=1, follow=False,
                                    name=f"{device}_pgn_{a}_spn_{b}_tt")
                            temp = ttk.Label(container,
                                             textvariable=self.pgn_params[device][pgn][self.device.specific_parameters[device][pgn].get_ps()][spn],
                                             width=10, name=f"{device}_pgn_{a}_spn_{b}_value")
                            temp.grid(column=1, row=i)
                            ttk.Label(container, text=self.device.specific_parameters[device][pgn].spg[spn].unit, width=10,
                                      name=f"{device}_pgn_{a}_spn_{b}_unit").grid(
                                column=2, row=i)
                            container.children[f"{device}_pgn_{a}_spn_{b}_unit"].bind('<MouseWheel>',
                                                                                  self.tpdo_frame.master.master.on_mousewheel)
                    elif self.device.specific_parameters[device][pgn].get_pf() == 27:
                        for j in range(4):
                            self.pgn_params[device][pgn][0xf3 + j] = {}
                            container = LabelFrame(battery_container, background='white',
                                                   text=f"0xF{3 + j} - Battery Check")
                            container.grid(column=j, row=0)
                            container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                            for i, spn in enumerate(self.device.specific_parameters[device][pgn].spg):
                                self.pgn_params[device][pgn][0xf3 + j][spn] = StringVar(value='0')
                                # self.pgn_params[device][pgn][spn] = StringVar(value='0')
                                a = self.device.specific_parameters[device][pgn].pgn
                                b = self.device.specific_parameters[device][pgn].spg[spn].spn
                                # print(spn, self.pgn_params[device][pgn][spn].get())
                                temp = ttk.Label(container, text=f"{self.device.specific_parameters[device][pgn].spg[spn].label}",
                                                 name=f"{device}_pgn_{a}_spn_{b}_label", anchor='w', wraplength=200, justify='center')
                                temp.grid(column=0, row=i)
                                temp.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                                ToolTip(temp, msg=self.device.specific_parameters[device][pgn].spg[spn].description, delay=1, follow=False,
                                        name=f"{device}_pgn_{a}_spn_{b}_tt")
                                temp = ttk.Label(container, textvariable=self.pgn_params[device][pgn][0xf3 + j][spn], width=10,
                                                 name=f"{device}_pgn_{a}_spn_{b}_value")
                                temp.grid(column=1, row=i)
                                ttk.Label(container, text=self.device.specific_parameters[device][pgn].spg[spn].unit, width=10,
                                          name=f"{device}_pgn_{a}_spn_{b}_unit").grid(
                                    column=2, row=i)
                                container.children[f"{device}_pgn_{a}_spn_{b}_unit"].bind('<MouseWheel>',
                                                                                       self.tpdo_frame.master.master.on_mousewheel)
                    elif self.device.specific_parameters[device][pgn].get_pf() == 0xef and \
                            self.device.specific_parameters[device][pgn].get_ps() != 0xca:
                        for j in range(4):
                            self.pgn_params[device][pgn][0xf3 + j] = {}
                            container = LabelFrame(battery_container, background='white',
                                                   text=f"0xF{3 + j} - Battery Feedback")
                            container.grid(column=j, row=1)
                            container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                            for i, spn in enumerate(self.device.specific_parameters[device][pgn].spg):
                                self.pgn_params[device][pgn][0xf3 + j][spn] = StringVar(value='0')
                                # self.pgn_params[device][pgn][spn] = StringVar(value='0')
                                a = self.device.specific_parameters[device][pgn].pgn
                                b = self.device.specific_parameters[device][pgn].spg[spn].spn
                                # print(spn, self.pgn_params[device][pgn][spn].get())
                                temp = ttk.Label(container, text=f"{self.device.specific_parameters[device][pgn].spg[spn].label}",
                                                 name=f"{device}_pgn_{a}_spn_{b}_label", anchor='w', wraplength=200, justify='center')
                                temp.grid(column=0, row=i)
                                temp.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                                ToolTip(temp, msg=self.device.specific_parameters[device][pgn].spg[spn].description, delay=1, follow=False,
                                        name=f"{device}_pgn_{a}_spn_{b}_tt")
                                temp = ttk.Label(container, textvariable=self.pgn_params[device][pgn][0xf3 + j][spn], width=10,
                                                 name=f"{device}_pgn_{a}_spn_{b}_value")
                                temp.grid(column=1, row=i)
                                ttk.Label(container, text=self.device.specific_parameters[device][pgn].spg[spn].unit, width=10,
                                          name=f"{device}_pgn_{a}_spn_{b}_unit").grid(
                                    column=2, row=i)
                                container.children[f"{device}_pgn_{a}_spn_{b}_unit"].bind('<MouseWheel>',
                                                                                       self.tpdo_frame.master.master.on_mousewheel)
                    elif self.device.specific_parameters[device][pgn].get_pf() in [0x26, 0x5e, 0x5f]:
                        for j in range(4):
                            self.pgn_params[device][pgn][0xef + j] = {}
                            container = LabelFrame(outer_container, background='white',
                                                   text=f"{pgn:04X} - {(0xef + j):02X} - Traction")
                            container.grid(column=j, row=self.device.specific_parameters[device][pgn].get_pf())
                            container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                            for i, spn in enumerate(self.device.specific_parameters[device][pgn].spg):
                                self.pgn_params[device][pgn][0xef + j][spn] = StringVar(value='0')
                                a = self.device.specific_parameters[device][pgn].pgn
                                b = self.device.specific_parameters[device][pgn].spg[spn].spn
                                # print(spn, self.pgn_params[device][pgn][spn].get())
                                temp = ttk.Label(container, text=f"{self.device.specific_parameters[device][pgn].spg[spn].label}",
                                                 name=f"{device}_pgn_{a}_spn_{b}_label", anchor='w', wraplength=200, justify='center')
                                temp.grid(column=0, row=i)
                                temp.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                                ToolTip(temp, msg=self.device.specific_parameters[device][pgn].spg[spn].description, delay=1, follow=False,
                                        name=f"{device}_pgn_{a}_spn_{b}_tt")
                                temp = ttk.Label(container, textvariable=self.pgn_params[device][pgn][0xef + j][spn], width=10,
                                                 name=f"{device}_pgn_{a}_spn_{b}_value")
                                temp.grid(column=1, row=i)
                                ttk.Label(container, text=self.device.specific_parameters[device][pgn].spg[spn].unit, width=10,
                                          name=f"{device}_pgn_{a}_spn_{b}_unit").grid(
                                    column=2, row=i)
                                container.children[f"{device}_pgn_{a}_spn_{b}_unit"].bind('<MouseWheel>',
                                                                                       self.tpdo_frame.master.master.on_mousewheel)
                        for j in range(7):
                            self.pgn_params[device][pgn][0xa0 + j] = {}
                            container = LabelFrame(outer_container, background='white',
                                                   text=f"{pgn:04X} - {(0xa0 + j):02X} - Deck")
                            container.grid(column=j, row=self.device.specific_parameters[device][pgn].get_pf() + 0x60)
                            container.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                            for i, spn in enumerate(self.device.specific_parameters[device][pgn].spg):
                                self.pgn_params[device][pgn][0xa0 + j][spn] = StringVar(value='0')
                                a = self.device.specific_parameters[device][pgn].pgn
                                b = self.device.specific_parameters[device][pgn].spg[spn].spn
                                # print(spn, self.pgn_params[device][pgn][spn].get())
                                temp = ttk.Label(container, text=f"{self.device.specific_parameters[device][pgn].spg[spn].label}",
                                                 name=f"{device}_pgn_{a}_spn_{b}_label", anchor='w', wraplength=200, justify='center')
                                temp.grid(column=0, row=i)
                                temp.bind('<MouseWheel>', self.tpdo_frame.master.master.on_mousewheel)
                                ToolTip(temp, msg=self.device.specific_parameters[device][pgn].spg[spn].description, delay=1, follow=False,
                                        name=f"{device}_pgn_{a}_spn_{b}_tt")
                                temp = ttk.Label(container, textvariable=self.pgn_params[device][pgn][0xa0 + j][spn], width=10,
                                                 name=f"{device}_pgn_{a}_spn_{b}_value")
                                temp.grid(column=1, row=i)
                                ttk.Label(container, text=self.device.specific_parameters[device][pgn].spg[spn].unit, width=10,
                                          name=f"{device}_pgn_{a}_spn_{b}_unit").grid(
                                    column=2, row=i)
                                container.children[f"{device}_pgn_{a}_spn_{b}_unit"].bind('<MouseWheel>',
                                                                                       self.tpdo_frame.master.master.on_mousewheel)
        else:
            for device, id in enumerate(self.id):
                outer_container = LabelFrame(self.tpdo_frame, background='white', text=f"CAN ID - {id}")
                outer_container.grid(column=device, row=0, sticky='news')
                for tpdo in self.TPDO[device]:
                    container = LabelFrame(outer_container, background='white', text=f"{'T' if tpdo.tx else 'R'}PDO{tpdo.idx}")
                    container.pack(fill='both')
                    for i, idx in enumerate(tpdo.idx_map):
                        # address = (tpdo.idx_map[idx][0] - 8192) * 64
                        # param = self.map2name(address, tpdo.idx_map[idx][1] - 1)
                        # param = self.map2name(tpdo.idx_map[i][0], tpdo.idx_map[i][1])
                        self.tpdo_param[device][idx] = StringVar(value='0')
                        temp = ttk.Label(container, text=f"{idx}: ",
                                         name=f"{'device_one' if device == 0 else 'device_two'}_label_{idx}_tpdo{tpdo.idx}", anchor='w')
                        temp.grid(column=0, row=tpdo.idx * 4 + i)
                        temp = ttk.Label(container, textvariable=self.tpdo_param[device][idx],
                                         name=f"{'device_one' if device == 0 else 'device_two'}_value_{idx}_tpdo{tpdo.idx}")
                        temp.grid(column=1, row=tpdo.idx * 4 + i)

        rpdo_frame = ScrollableFrame(mainframe, height=600, bg='white')
        if self.monitor != 'VCM':
            rpdo_frame.grid(column=2, row=1, columnspan=2, sticky='news')
            self.rpdo_frame = rpdo_frame.scrollable_frame

        if isinstance(self.device, ASIController):
            for j, id in enumerate(self.device.can_bus.id):
                outer_container = LabelFrame(self.rpdo_frame, background='white', text=f"CAN ID - {id}")
                outer_container.grid(column=0, row=j, sticky='news')
                for rpdo in self.device.can_bus.RPDO[j]:
                    container = LabelFrame(outer_container, background='white', text=f"{'T' if rpdo.tx else 'R'}PDO{rpdo.idx}")
                    container.pack(fill='both')
                    for i, idx in enumerate(rpdo.idx_map):
                        # address = (rpdo.idx_map[idx][0] - 8192) * 64
                        # param = self.device.can_bus.map2name(address, rpdo.idx_map[idx][1] - 1)
                        # if not param:
                        #     self.device.add_run_parameter(address + rpdo.idx_map[idx][1] - 1)
                        #     param = self.device.can_bus.map2name(address, rpdo.idx_map[idx][1] - 1)
                        # param = self.device.can_bus.map2name(rpdo.idx_map[i][0], rpdo.idx_map[i][1])
                        if i < rpdo.size:
                            self.rpdo_param[j][idx] = DoubleVar(value=0)
                            temp = ttk.Label(container, text=f"{idx}: ",
                                             name=f"{'device_one' if j == 0 else 'device_two'}_label_{idx}_rpdo{rpdo.idx}")
                            temp.grid(column=0, row=rpdo.idx * 4 + i)
                            temp = Entry(container, textvariable=self.rpdo_param[j][idx],
                                         name=f"{'device_one' if j == 0 else 'device_two'}_value_{idx}_rpdo{rpdo.idx}")
                            temp.grid(column=1, row=rpdo.idx * 4 + i)
        elif isinstance(self.device, J1939com):
            if self.monitor != 'VCM':
                for j, id in enumerate(self.device.id):
                    outer_container = LabelFrame(self.rpdo_frame, background='white', text=f"PDU2 - SA - {id} - {id:02X}")
                    outer_container.grid(column=j, row=0, sticky='nw')
                    outer_container.bind('<MouseWheel>', self.rpdo_frame.master.master.on_mousewheel)
                    for k, pgn in enumerate(self.device.specific_parameters[id]):
                        if self.device.specific_parameters[id][pgn].get_pf() <= 240:
                            self.pgn_broadcast[pgn] = BooleanVar(value=False)
                            ttk.Checkbutton(outer_container, variable=self.pgn_broadcast[pgn], onvalue=True).grid(
                                row=k, column=0, sticky='e')
                            container = LabelFrame(outer_container, background='white',
                                                   text=f"{self.device.specific_parameters[id][pgn].pgn} - "
                                                        f"{self.device.specific_parameters[id][pgn].pgn:06X}")
                            container.grid(row=k, column=1, sticky='w')
                            container.bind('<MouseWheel>', self.rpdo_frame.master.master.on_mousewheel)
                            for i, spn in enumerate(self.device.specific_parameters[id][pgn].spg):
                                self.pgn_params[id][pgn][spn] = StringVar(value='0')
                                a = self.device.specific_parameters[id][pgn].pgn
                                b = self.device.specific_parameters[id][pgn].spg[spn].spn
                                temp = ttk.Label(container, text=f"{self.device.specific_parameters[id][pgn].spg[spn].label}",
                                                 name=f"{id}_pgn_{a}_spn_{b}_label", anchor='w')
                                temp.grid(column=0, row=i)
                                temp.bind('<MouseWheel>', self.rpdo_frame.master.master.on_mousewheel)
                                ToolTip(temp, msg=self.device.specific_parameters[id][pgn].spg[spn].description, delay=1, follow=False,
                                        name=f"{id}_pgn_{a}_spn_{b}_tt")
                                temp = Entry(container, textvariable=self.pgn_params[id][pgn][spn],
                                             name=f"{id}_pgn_{a}_spn_{b}_value")
                                temp.grid(column=1, row=i)
                                ttk.Label(container, text=self.device.specific_parameters[id][pgn].spg[spn].unit, width=10,
                                          name=f"{id}_pgn_{a}_spn_{b}_unit").grid(
                                    column=2, row=i)
                                container.children[f"{id}_pgn_{a}_spn_{b}_unit"].bind('<MouseWheel>',
                                                                                       self.rpdo_frame.master.master.on_mousewheel)

            self.device.startListening()

        else:
            for device, id in enumerate(self.id):
                outer_container = LabelFrame(self.rpdo_frame, background='white', text=f"CAN ID - {id}")
                outer_container.grid(column=0, row=device, sticky='news')
                for rpdo in self.RPDO[device]:
                    container = LabelFrame(outer_container, background='white', text=f"{'T' if rpdo.tx else 'R'}PDO{rpdo.idx}")
                    container.pack(fill='both')
                    for i, idx in enumerate(rpdo.idx_map):
                        # address = (rpdo.idx_map[i][0] - 8192) * 64
                        # param = self.map2name(address, rpdo.idx_map[i][1] - 1)
                        # param = self.map2name(rpdo.idx_map[i][0], rpdo.idx_map[i][1])
                        if i < rpdo.size:
                            self.rpdo_param[device][idx] = DoubleVar(value=0)
                            temp = ttk.Label(container, text=f"{idx}: ",
                                             name=f"{'device_one' if device == 0 else 'device_two'}_label_{idx}_rpdo{rpdo.idx}")
                            temp.grid(column=0, row=rpdo.idx * 4 + i)
                            temp = Entry(container, textvariable=self.rpdo_param[device][idx],
                                         name=f"{'device_one' if device == 0 else 'device_two'}_value_{idx}_rpdo{rpdo.idx}")
                            temp.grid(column=1, row=rpdo.idx * 4 + i)

        return mainframe

    def init_sdo(self):
        # if self.monitor != 'VCM':
        mainframe = LabelFrame(self.mainframe,
                               text='SDO' if not isinstance(self.device, J1939com) else 'read/write')
        mainframe.grid(column=0, row=5, columnspan=4, sticky='news')
        mainframe.columnconfigure((0, 1, 2, 3), weight=1)

        frame = ScrollableFrame(mainframe, name='sdo_frame', bg='white', height=300)

        frame.grid(column=0, row=0, columnspan=4, sticky='news')
        self.sdo_frame = frame.scrollable_frame

        if isinstance(self.device, ASIController):
            for device, id in enumerate(self.device.can_bus.id):
                container = LabelFrame(self.sdo_frame, background='white', text=f"CAN ID - {id}")
                container.grid(column=0, row=0, sticky='news')
                # container.columnconfigure((0, 1), weight=1)
                for i, param in enumerate(self.device.run_parameters[device]):
                    if self.device.run_parameters[device][param].Value is None:
                        continue
                    self.sdo_param[device][param] = DoubleVar(value=0)
                    temp = ttk.Label(container, text=f"{param}: ", name=f"label_{param}_sdo{id}")
                    temp.grid(column=0, row=i)
                    temp = Entry(container, textvariable=self.sdo_param[device][param], name=f"value_{param}_sdo{id}", width=17)
                    temp.grid(column=1, row=i)
                    temp.bind('<Return>', lambda: self.device.write(param, self.sdo_param[device][param].get()))
        elif isinstance(self.device, J1939com):
            # if self.monitor != 'VCM':
            ttk.Label(self.sdo_frame, text="Parameter: ").grid(column=0, row=3)
            ttk.Combobox(self.sdo_frame, textvariable=self.read_write_param, name='params_combo', width=50).grid(
                column=1, row=3, sticky='we')
            self.sdo_frame.children['params_combo']['value'] = list(self.run_parameters.keys())

            ttk.Combobox(self.sdo_frame, textvariable=self.read_write_option, name='request_combo', width=6).grid(
                column=2, row=3, sticky='we')
            self.sdo_frame.children['request_combo']['value'] = ['read', 'write']
            Entry(self.sdo_frame, textvariable=self.read_write_value, name=f"read_write_value").grid(
                column=3, row=3)
            self.sdo_frame.children['read_write_value'].bind('<Return>', self.read_write_request)

            ttk.Button(self.sdo_frame, text='Clear Faults', name='clear_faults_btn', command=self.clear_faults).grid(
                column=2, row=4)
            ttk.Button(self.sdo_frame, text='Save to Flash', name='save_to_flash_btn', command=self.save_to_flash).grid(
                column=3, row=4)
            ttk.Button(self.sdo_frame, text='Claim Address', name='claim_address_btn', command=self.device.claim_address).grid(
                column=4, row=4)
            # else:
            #     self.sdo_frame.grid_remove()

        else:
            for device, id in enumerate(self.id):
                container = LabelFrame(self.sdo_frame, background='white', text=f"CAN ID - {id}")
                container.grid(column=0, row=0, sticky='news')
                # container.columnconfigure((0, 1), weight=1)
                for i, param in enumerate(self.run_parameters[device]):
                    if self.run_parameters[device][param].Value is None:
                        continue
                    self.sdo_param[device][param] = DoubleVar(value=0)
                    temp = ttk.Label(container, text=f"{param}: ", name=f"label_{param}_sdo{id}")
                    temp.grid(column=0, row=i)
                    temp = Entry(container, textvariable=self.sdo_param[device][param], name=f"value_{param}_sdo{id}", width=17)
                    temp.grid(column=1, row=i)
                    temp.bind('<Return>', lambda: self.write(param, self.sdo_param[device][param].get(), device))

        self._set_sdo_params()

        return mainframe

    def read_write_request(self, event=None):
        def action():
            if self.read_write_option.get() == 'read':
                value = self.device.read(self.read_write_param.get(), self.target.get(), length=1)[0]
                if len(self.run_parameters[self.read_write_param.get()].Bits) >= 8:
                    formatted_value = f'{int(value):016b}'
                elif self.run_parameters[self.read_write_param.get()].Scale == 'hex':
                    formatted_value = f'{int(value):04X}'
                else:
                    formatted_value = value
                self.read_write_value.set(formatted_value)
            elif self.read_write_option.get() == 'write':
                value = self.read_write_value.get()
                if len(self.run_parameters[self.read_write_param.get()].Bits) >= 8:
                    formatted_value = int(value, 2)
                elif self.run_parameters[self.read_write_param.get()].Scale == 'hex':
                    formatted_value = int(value, 16)
                else:
                    formatted_value = float(value)
                self.device.write(self.read_write_param.get(), [formatted_value], self.target.get(), length=1)

        temp = Thread(target=action)
        temp.start()

    def save_to_flash(self):
        def action():
            if self.monitor != 'BAC':
                self.device.write('Flash Commands', [0x3fff], self.target.get(), length=1)
                # for i in range(3):
                #     sleep(1)
                # if self.device.read('Flash Commands', self.target.get(), length=1)[0] == 0x2000:
                #     messagebox.showinfo("Save to Flash", "Successful!")
                # else:
                #     messagebox.showinfo("Save to Flash", "Failed!")
            else:
                self.device.write("write parameters to flash", [0x7fff], self.target.get(), length=1)

        Thread(target=action).start()

    def clear_faults(self):
        def action():
            self.device.write('Special Commands', [0x2fff], self.target.get(), length=1)

        Thread(target=action).start()

    def _set_sdo_params(self):
        if isinstance(self.device, ASIController):
            for i, param in enumerate(self.sdo_param[0]):
                # self.sdo_param[param].set(self.device.run_parameters[param].Value)
                self.sdo_param[0][param].set(self.device.read(param))
        elif isinstance(self.device, J1939com):
            pass
        else:
            for i, param in enumerate(self.sdo_param[0]):
                # self.sdo_param[param].set(self.run_parameters[param].Value)
                self.sdo_param[0][param].set(self.read(param))

    def load_PDO(self, mode):
        if mode == 'BAC':
            self.PDO_parameters = load_using_param_names(self.etree,
                                                         f"{self.root_dir if self.root_dir else ''}"
                                                         f"\\Parameter Files\\Run parameters for ASI controller PDO 6021.csv")
        elif mode == 'GCM/VCM':
            self.PDO_parameters = load_using_param_names(self.etree,
                                                         f"{self.root_dir if self.root_dir else ''}\\Parameter Files\\VCM PDO.csv")
        elif mode == 'Throttle':
            self.PDO_parameters = load_using_param_names(self.etree,
                                                         f"{self.root_dir if self.root_dir else ''}"
                                                         f"\\Parameter Files\\Run parameters for ASI controller PDO 6021.csv")

    def pgn_msg_handle(self, msg: can.Message):
        # def action():
        msg_pgn = (msg.arbitration_id & (0xffff << 8)) >> 8
        msg_sa = msg.arbitration_id & 255
        if self.monitor == 'VCM' and msg_sa != 39:
            return True
        # for pgn in self.device.specific_parameters[msg_sa]:
        try:
            self.device.specific_parameters[msg_sa][msg_pgn]
        except KeyError:
            pass
        else:
            msg_priority = (msg.arbitration_id & (7 << 26)) >> 26
            msg_ps = get_ps(msg_pgn)
            msg_edp = get_edp(msg_pgn)
            msg_dp = get_dp(msg_pgn)
            if self.device.specific_parameters[msg_sa][msg_pgn].pgn == msg_pgn and \
                    self.device.specific_parameters[msg_sa][msg_pgn].priority == msg_priority and \
                    self.device.specific_parameters[msg_sa][msg_pgn].get_edp() == msg_edp and \
                    self.device.specific_parameters[msg_sa][msg_pgn].get_dp() == msg_dp and \
                    msg_sa in self.device.id:
                for sp in self.device.specific_parameters[msg_sa][msg_pgn].spg:
                    sp = self.device.specific_parameters[msg_sa][msg_pgn].spg[sp]
                    value = calculate_sp_value(msg, sp)
                    # word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1
                    # value = 0
                    # if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
                    #     value = (msg.data[word] & ((2 ** sp.length - 1) << index)) >> index
                    # elif sp.length + index <= 16:  # need to split data into 2 bytes
                    #     value = (msg.data[word] & (2 ** (8 - index) - 1) << index) >> index
                    #     value += (msg.data[word + 1] & (2 ** (sp.length - 8 + index) - 1)) << (8 - index)
                    # elif sp.length + index <= 24:  # need to split data into 3 bytes
                    #     value = (msg.data[word] & (2 ** sp.length - 1) << index) >> index
                    #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 8))
                    #     value += (msg.data[word + 2] & ((2 ** (sp.length - 16 + index) - 1) << (16 - index)))
                    # elif sp.length + index <= 32:  # need to split data into 4 bytes
                    #     value = (msg.data[word] & (2 ** sp.length - 1) << index) >> index
                    #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 8))
                    #     value += (msg.data[word + 2] & ((2 ** 8 - 1) << 16))
                    #     value += (msg.data[word + 3] & ((2 ** (sp.length - 24 + index) - 1) << (24 - index)))
                    sp.scaled_value = value * sp.scale + sp.offset
                    # try:
                    if self.pgn_params[msg_sa][msg_pgn][msg_ps][sp.label].get() != str(sp.scaled_value):
                        self.pgn_params[msg_sa][msg_pgn][msg_ps][sp.label].set(sp.scaled_value)
                    # except KeyError:
                    #     pass
                return True
        msg_ps = get_ps(msg_pgn)
        msg_pf = get_pf(msg_pgn)
        msg_pgn = msg_pf << 8
        try:
            self.device.specific_parameters[msg_sa][msg_pgn]
        except KeyError:
            return False
        else:
            msg_priority = (msg.arbitration_id & (7 << 26)) >> 26
            msg_edp = get_edp(msg_pgn)
            msg_dp = get_dp(msg_pgn)
            if self.device.specific_parameters[msg_sa][msg_pgn].get_pf() == msg_pf and \
                    self.device.specific_parameters[msg_sa][msg_pgn].get_pf() not in [0xff] and \
                    self.device.specific_parameters[msg_sa][msg_pgn].priority == msg_priority and \
                    self.device.specific_parameters[msg_sa][msg_pgn].get_edp() == msg_edp and \
                    self.device.specific_parameters[msg_sa][msg_pgn].get_dp() == msg_dp and \
                    msg_sa in self.device.id:
                for sp in self.device.specific_parameters[msg_sa][msg_pgn].spg:
                    sp = self.device.specific_parameters[msg_sa][msg_pgn].spg[sp]
                    value = calculate_sp_value(msg, sp)
                    # word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1
                    # value = 0
                    # if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
                    #     value = (msg.data[word] & ((2 ** sp.length - 1) << index)) >> index
                    # elif sp.length + index <= 16:  # need to split data into 2 bytes
                    #     value = (msg.data[word] & (2 ** (8 - index) - 1) << index) >> index
                    #     value += (msg.data[word + 1] & (2 ** (sp.length - 8 + index) - 1)) << (8 - index)
                    # elif sp.length + index <= 24:  # need to split data into 3 bytes
                    #     value = (msg.data[word] & (2 ** sp.length - 1) << index) >> index
                    #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 8))
                    #     value += (msg.data[word + 2] & ((2 ** (sp.length - 16 + index) - 1) << (16 - index)))
                    # elif sp.length + index <= 32:  # need to split data into 4 bytes
                    #     value = (msg.data[word] & (2 ** sp.length - 1) << index) >> index
                    #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 8))
                    #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 16))
                    #     value += (msg.data[word + 3] & ((2 ** (sp.length - 24 + index) - 1) << (24 - index)))
                    sp.scaled_value = value * sp.scale + sp.offset
                    # try:
                    if self.pgn_params[msg_sa][msg_pgn][msg_ps][sp.label].get() != str(sp.scaled_value):
                        self.pgn_params[msg_sa][msg_pgn][msg_ps][sp.label].set(sp.scaled_value)
                    # except KeyError:
                        # print(msg_sa, pgn, msg_ps, sp.label)
                        # continue
                return True
            return False

    def can_pdo_handle(self, msg: can.Message, index=0) -> bool:
        """

        Args:
            msg: can Message to be handled
            index: can device
        Returns:
            bool: Whether message is handled as PDO

        """
        if isinstance(self.device, ASIController):
            rt, idx = self.device.can_bus.is_PDO(msg, index)
            if idx:
                if rt == 'T':
                    for tpdo in self.device.can_bus.TPDO[index]:
                        if tpdo.idx == idx:
                            for i, idx in enumerate(tpdo.idx_map):
                                # address = (tpdo.idx_map[idx][0] - 8192) * 64
                                # param = self.device.can_bus.map2name(address, tpdo.idx_map[idx][1] - 1)
                                # try:
                                if i < tpdo.size:
                                    self.tpdo_param[index][idx].set(self._value_format(idx,
                                        signed(msg.data[i * 2 + 1] * 0x100 + msg.data[i * 2]) /
                                        get_scale_value(self.device.run_parameters[idx].Scale)))
                    return True
                                # except (KeyError, IndexError) as e:
                                #     print(e)
        else:
            rt, idx = self.is_PDO(msg, index)
            if idx:
                if rt == 'T':
                    for tpdo in self.TPDO[index]:
                        if tpdo.idx == idx:
                            for i, idx in enumerate(tpdo.idx_map):
                                # address = (tpdo.idx_map[i][0] - 8192) * 64
                                # param = self.map2name(address, tpdo.idx_map[i][1])
                                try:
                                    self.tpdo_param[index][idx].set(
                                        signed(msg.data[i * 2 + 1] * 0x100 + msg.data[i * 2]) /
                                        get_scale_value(self.run_parameters[idx].Scale))
                                except KeyError:
                                    pass
                    return True
        return False

    def _init_rpdo_thread(self):

        def _rpdo_update(rpdo, index):
            while self.rpdo_running:
                if isinstance(self.device, ASIController):
                    if self.device.can_bus.auto_rpdo:
                        rpdo_msg = can.Message(arbitration_id=int(rpdo.idx * 0x100 + device), is_extended_id=False, is_error_frame=False,
                                               data=[0] * 8)
                    else:
                        rpdo_msg = can.Message(arbitration_id=int(rpdo.id_lo + device), is_extended_id=False, is_error_frame=False,
                                               data=[0] * 8)
                    for i, name in enumerate(rpdo.idx_map):
                        # address = (rpdo.idx_map[name][0] - 8192) * 64
                        # param = self.device.can_bus.map2name(address, rpdo.idx_map[name][1] - 1)
                        if i < rpdo.size:
                            try:
                                value = int(self.rpdo_param[index][name].get() * get_scale_value(self.device.run_parameters[index][name].Scale))
                            except (tkinter.TclError, KeyError):
                                pass
                            else:
                                byte_1 = value & 0xff
                                byte_2 = (value & 0xff00) >> 8
                                rpdo_msg.data[i * 2] = byte_1
                                rpdo_msg.data[i * 2 + 1] = byte_2
                    self.device.can_bus.msg_buffer.put(rpdo_msg)
                    sleep(int(rpdo.timeout) / 1000 if int(rpdo.timeout) != 0 else 1)
                elif isinstance(self.device, J1939com):
                    pass
                else:
                    if self.auto_rpdo:
                        rpdo_msg = can.Message(arbitration_id=int(rpdo.idx * 0x100 + device), is_extended_id=False, is_error_frame=False,
                                               data=[0] * 8)
                    else:
                        rpdo_msg = can.Message(arbitration_id=int(rpdo.id_lo + device), is_extended_id=False, is_error_frame=False,
                                               data=[0] * 8)
                    for i, name in enumerate(rpdo.idx_map):
                        # address = (rpdo.idx_map[name][0] - 8192) * 64
                        # param = self.map2name(address, rpdo.idx_map[name][1] - 1)
                        if i < rpdo.size:
                            try:
                                value = self.rpdo_param[index][name].get() * get_scale_value(self.run_parameters[index][name].Scale)
                            except tkinter.TclError:
                                value = 0
                            byte_1 = value & 0xff
                            byte_2 = (value & 0xff00) >> 8
                            rpdo_msg.data[i * 2] = byte_1
                            rpdo_msg.data[i * 2 + 1] = byte_2
                    self.msg_buffer.put(rpdo_msg)
                    sleep(int(rpdo.timeout) / 1000 if int(rpdo.timeout) != 0 else 1)


        self.rpdo_running = True
        if isinstance(self.device, ASIController):
            for device in range(len(self.device.can_bus.id)):
                for rpdo in self.device.can_bus.RPDO[device]:
                    self.rpdo_thread[f"{'device_one' if device == 0 else 'device_two'}_RPDO{rpdo.idx}"] = Thread(target=lambda: _rpdo_update(rpdo, device))
                    self.rpdo_thread[f"{'device_one' if device == 0 else 'device_two'}_RPDO{rpdo.idx}"].start()
        elif isinstance(self.device, J1939com):
            pass
        else:
            for device in range(len(self.id)):
                for rpdo in self.RPDO[device]:
                    self.rpdo_thread[f"{'device_one' if device == 0 else 'device_two'}_RPDO{rpdo.idx}"] = Thread(target=lambda: _rpdo_update(rpdo, device))
                    self.rpdo_thread[f"{'device_one' if device == 0 else 'device_two'}_RPDO{rpdo.idx}"].start()

    def stop_rpdo_thread(self):
        self.rpdo_running = False
        # self.rpdo_thread.join()
        # self.rpdo_thread = {}
        for thread in self.rpdo_thread:
            # thread.join()
            self.rpdo_thread[thread] = None

    def _value_format(self, name, value):
        if isinstance(self.device, ASIController):
            if self.device.run_parameters[name].Scale == 'bit vector':
                return f'{int(value):016b}'
            elif self.device.run_parameters[name].Scale == 'hex':
                return f'{hex(int(value))[2:].upper()}'
        return value

    def _on_closing(self):
        logging.info('Closing CAN PDO Interface')
        self.stop_rpdo_thread()
        if isinstance(self.device, ASIController):
            if self.monitor:
                self.device.can_bus.can_pdo_handle = self.can_pdo_handle_original
                # self.device.can_bus.can_pdo_handle = super().can_pdo_handle
            else:
                self.device.__del__()
        elif isinstance(self.device, J1939com):
            self.device.__del__()
        else:
            super().__del__()
        self.root.destroy()
        print(self.device)

    def can_pdo_handle_original(self, msg: can.Message, index=0) -> bool:
        """

        Args:
            msg: can Message to be handled
            index: can device
        Returns:
            bool: Whether message is handled as PDO

        """
        # if isinstance(self.device, ASIController):
        #     rt, idx = self.device.can_bus.is_PDO(msg, index)
        #     if idx:
        #         return True
        #     return False
        # else:
        #     rt, idx = self.is_PDO(msg, index)
        #     if idx:
        #         return True
        #     return False
        rt, idx = self.is_PDO(msg, index)
        if idx:
            return True
        return False