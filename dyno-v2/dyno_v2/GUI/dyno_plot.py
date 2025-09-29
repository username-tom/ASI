import matplotlib
import pandas as pd
from matplotlib import animation, figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import *
from tkinter import ttk
from dyno_v2.Module.ASIDynoModule import *
from dyno_v2.GUI.tooltip import ToolTip
from dyno_v2.Module.gui_parameters import TOOLTIP_DELAY, X_MAX, X_MIN, COLORS, PARAMETER_FOREGROUND, ROOT_DIR
from datetime import datetime


ORDINAL = ['Primary',
           'Secondary',
           'Tertiary',
           'Quaternary',
           'Quinary',
           'Senary',
           'Septenary',
           'Octonary',
           'Nonary',
           'Decenary',
           'Undenary',
           'Duodenary']

class DynoPlot:

    def __init__(
            self,
            master,
            width=6.2,
            height=3.2,
            plot='adv',
            axis=2,
            autolayout=True,
            placement='grid',
            *args,
            **kwargs
    ):
        self.dyno = None
        self.data = None

        for x in args:
            if isinstance(x, ASIDynoModule):
                self.dyno = x
            if isinstance(x, pd.DataFrame):
                self.data = x

        self.plot_parameters = {}
        for arg in kwargs:
            self.plot_parameters[arg] = kwargs[arg]

        self.plot = plot

        if 'grid' in self.plot:
            try:
                self.plot_parameters['status_params']
            except KeyError:
                self.plot_parameters['status_params'] = parse_etree(f"{ROOT_DIR}/live_parameters.xml")

        if self.data is None:
            self.data = pd.DataFrame(columns=self.plot_parameters['graph_params'])
        self.width = width
        self.height = height
        self.axis_num = axis
        self.figures = {}
        self.axis = {}
        self.lines = {}
        self.y_selected = {}
        self.autolayout = autolayout
        self.master = master
        self.graphing = False
        self.graphing_interval = 1
        self.paused = StringVar(value="PAUSE")
        self.graph_tt = None
        self.x_max = X_MAX
        self.x_min = X_MIN
        self.placement = placement
        self.start_time = None
        self._graphing_thread = None
        self.after_id = None
        self.init_plot()

    def init_plot(self):

        matplotlib.rcParams["figure.figsize"] = (self.width, self.height)
        matplotlib.rcParams["figure.autolayout"] = True
        self.figures['main'] = figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.figures['main'], master=self.master)
        if self.placement == 'grid':
            self.canvas.get_tk_widget().grid(
                column=0, row=1, columnspan=12, sticky='news', pady=5)
            for i in range(12):
                self.master.columnconfigure(i, weight=1)
            self.master.rowconfigure(1, weight=1)
        elif self.placement == 'place':
            self.canvas.get_tk_widget().place(relx=0, rely=0, anchor='nw')

        if 'adv' in self.plot.lower():
            ttk.Label(self.master, text="x-axis").grid(column=0, row=6, sticky='e')
            ttk.Combobox(self.master, textvariable=self.plot_parameters['x_combo'],
                         width=50, name='x_combo').grid(column=1, row=6,
                                                        columnspan=8, sticky='we',
                                                        pady=5)

            ttk.Button(self.master, textvariable=self.paused,
                       command=self._graphing_pause, state=DISABLED,
                       name='ani_pause_btn').grid(column=9, row=6,
                                                  sticky='e')

            span = int(12 / self.axis_num)
            for i in range(self.axis_num):
                ttk.Label(self.master, text=f"{ORDINAL[i]} axis").grid(columnspan=span,
                                                                       column=i * span, row=7, pady=5)
                temp = Listbox(self.master,
                               listvariable=self.plot_parameters[f'y_{i}'],
                               width=50, height=5,
                               exportselection=False, selectmode="multiple",
                               name=f'y_list_{i}')
                temp.grid(column=i * span, row=8, columnspan=span, sticky='news', pady=5)

                self.master.children[f'y_list_{i}'].bind('<<ListboxSelect>>', self.y_param_update)

            self.graph_tt = ToolTip(self.canvas.get_tk_widget(), delay=TOOLTIP_DELAY,
                                    msg="Min  0 - 10 | 1 sec/row\n"
                                        "Min 10 - 20 | 2 sec/row\n"
                                        "Min 20 - 45 | 5 sec/row\n"
                                        "Min 45 - 60 | 15 sec/row\n"
                                        "Min 60+     | 1 min/row\n"
                                        "Line colors: Primary >> Secondary in their order from top of the list to the bottom\n"
                                        "Blue -> Red -> Green -> Magenta -> Cyan -> Yellow -> Gray -> Sienna -> Orange -> "
                                        "Gold -> Lime -> Teal -> Sky blue -> Navy -> Purple -> Pink")

            self.axis[0] = self.figures['main'].add_subplot(1, 1, 1)
            for i in range(1, self.axis_num):
                self.axis[i] = self.figures['main'].add_subplot(1, 1, 1, sharex=self.axis[0], frameon=False)
                self.axis[i].yaxis.tick_right()

        elif 'sing' in self.plot.lower():

            self.graph_tt = ToolTip(self.canvas.get_tk_widget(), delay=TOOLTIP_DELAY,
                                    msg=self.plot_parameters['title'])

            self.axis[0] = self.figures['main'].add_subplot(1, 1, 1)
            self.axis[0].spines[['top']].set_visible(False)
            self.axis[0].set_title(self.plot_parameters['title'])
            self.axis[0].set_xlim(self.x_min, self.x_max)
            self.axis[1] = self.figures['main'].add_subplot(1, 1, 1, sharex=self.axis[0], frameon=False)
            self.axis[1].spines[['right']].set_visible(True)
            self.axis[1].yaxis.tick_right()

        elif 'grid' in self.plot.lower():
            self.graph_tt = ToolTip(self.canvas.get_tk_widget(), delay=TOOLTIP_DELAY,
                                    msg=self.plot_parameters['title'])

            self.plot_parameters['plot_count'] = 0
            # for controller in ['DUT', 'BRK', 'ABB', 'YOKO']:
            #     if controller == 'DUT' and self.plot_parameters['dut_controller'] not in ASI_CONTROLLERS:
            #         continue
            #
            #     if controller == 'BRK' and self.plot_parameters['brk_controller'] not in ASI_CONTROLLERS:
            #         continue
            #
            #     if controller == 'YOKO' and self.plot_parameters['yoko_ip'] == 0:
            #         continue
            #
            #     if controller == 'ABB' and self.plot_parameters['brk_controller'] != 'ABB':
            #         continue
            #
            #     new_dict = {}
            #     for element in self.plot_parameters['status_params'].findall(
            #             f"{self.plot_parameters['graph']}/{controller}/Name"):
            #         new_dict[element.text] = DoubleVar(value=0)
            #     self.plot_parameters['grid_parameters'][controller] = new_dict

            self.plot_parameters['plot_count'] = len(
                self.plot_parameters['status_params'].findall(
                    f"{self.plot_parameters['graph']}/plot/Name"))

            row = int(self.plot_parameters['plot_count'] / 2 + 0.5)
            i = 1
            for p in self.plot_parameters['status_params'].findall(
                    f"{self.plot_parameters['graph']}/plot/Name"):
                self.axis[p.text] = self.figures['main'].add_subplot(row, 2, i)
                self.axis[p.text].set_xlim(self.x_min, self.x_max)
                i += 1
                self.axis[p.text].set_title(p.text, fontsize=7, wrap=True)
                self.axis[p.text].tick_params(axis='both', labelsize=7)
                self.axis[p.text].spines[['right', 'top']].set_visible(False)

        self.animation = animation.FuncAnimation(self.figures['main'], func=self.animate,
                                                 interval=self.graphing_interval * 1000, blit=False)
        self.animation.pause()

    def animate(self, counter):
        """
        Graphing animation function
        Graphing tab - old GUI
        """
        if self.graphing:
            try:
                self.refresh()
            except ValueError:
                pass

    def init_graphing(self):
        """
        GUI backend
        Initiates graphing
        """
        logging.info(f'start of dyno_plot init_graphing for [{self.plot}]')
        self.x_max = X_MAX
        self.x_min = X_MIN
        if 'adv' in self.plot.lower():
            self.plot_parameters['graph_params'] = self.dyno.getcsvline(getnames=True)
            for i in range(self.axis_num):
                self.plot_parameters[f'y_{i}'].set(self.plot_parameters['graph_params'])
                self.master.children[f'y_list_{i}'].bind('<<ListboxSelect>>', self.y_param_update)

            self.master.children['x_combo']['value'] = self.plot_parameters['graph_params']
            self.plot_parameters['x_combo'].set("Elapsed")

            logging.info(f"Advanced graph initiated")

        elif 'sing' in self.plot.lower():
            self.lines = {}
            self.axis[0].remove()
            self.axis[0] = self.figures['main'].add_subplot(1, 1, 1)
            self.axis[0].set_title(self.plot_parameters['title'])
            self.axis[1].remove()
            self.axis[1] = self.figures['main'].add_subplot(1, 1, 1,
                                                            sharex=self.axis[0], frameon=False)
            self.axis[1].spines[['right']].set_visible(True)
            self.axis[1].yaxis.tick_right()
            self.graph_tt.msg = self.plot_parameters['title']

            c = 0
            for controller in ['DUT', 'BRK', 'ABB', 'YOKO']:
                if controller == 'DUT' and not self.dyno.devices[1]:
                    continue

                if controller == 'BRK' and not isinstance(self.dyno.devices[2], ASIController):
                    continue

                if controller == 'YOKO' and not self.dyno.devices[PA]:
                    continue

                if controller == 'ABB' and not isinstance(self.dyno.devices[2], AbbAcs800):
                    continue

                for element in self.plot_parameters['status_params'].findall(
                        f"{self.plot_parameters['graph']}/{controller}/Name"):
                    line, = self.axis[0].plot(
                        self.data['Elapsed'],
                        self.data[f'{controller if controller != "YOKO" else ""}'
                                  f'{" " if controller != "YOKO" else ""}'
                                  f'{element.text}'],
                        color=STYLES[c], linestyle='-')
                    self.lines[f'{controller} {element.text}'] = line
                    self.graph_tt.msg += f'\n' \
                                         f'{STYLES[c]}: {controller} {element.text}'
                    c += 1
                for element in self.plot_parameters['status_params'].findall(
                        f"{self.plot_parameters['graph']}/{controller}/Secondary"):
                    line, = self.axis[1].plot(
                        self.data['Elapsed'],
                        self.data[f'{controller if controller != "YOKO" else ""}'
                                  f'{" " if controller != "YOKO" else ""}'
                                  f'{element.text}'],
                        color=STYLES[c], linestyle='-')
                    self.lines[f'{controller} {element.text}'] = line
                    self.graph_tt.msg += f'\n' \
                                         f'{STYLES[c]}: {controller} {element.text}'
                    c += 1

            logging.info(f"Single graph [{self.plot_parameters['graph']}] initiated")

        elif 'grid' in self.plot.lower():
            self.lines = {}
            for p in self.plot_parameters['status_params'].findall(
                    f"{self.plot_parameters['graph']}/plot/Name"):
                self.axis[p.text].remove()
            self.axis = {}
            self.graph_tt.msg = self.plot_parameters['title']
                    
            self.plot_parameters['plot_count'] = 0
            # for controller in ['DUT', 'BRK', 'ABB', 'YOKO']:
            #     if controller == 'DUT' and not self.dyno.devices[1]:
            #         continue
            #
            #     if controller == 'BRK' and not isinstance(self.dyno.devices[2], ASIController):
            #         continue
            #
            #     if controller == 'YOKO' and not self.dyno.devices[PA]:
            #         continue
            #
            #     if controller == 'ABB' and not isinstance(self.dyno.devices[2], AbbAcs800):
            #         continue
            #
            #     new_dict = {}
            #     for element in self.plot_parameters['status_params'].findall(
            #             f"{self.plot_parameters['graph']}/{controller}/Name"):
            #         new_dict[element.text] = DoubleVar(value=0)
            #         # self.plot_parameters['plot_count'] += 1
            #     self.plot_parameters['grid_parameters'][controller] = new_dict

            # self.master.master.config(height=self.plot_parameters['container_height'] *
            #                                  (1 + 0.5 * int((self.plot_parameters['plot_count'] - 6) / 3 + 0.9)))
            # self.master.config(height=self.plot_parameters['container_height'] *
            #                           (1 + 0.5 * int((self.plot_parameters['plot_count'] - 6) / 3 + 0.9)))
            # self.canvas.get_tk_widget().config(
            #     height=self.plot_parameters['container_height'] *
            #            (1 + 0.5 * int((self.plot_parameters['plot_count'] - 6) / 3 + 0.9)))
            # self.figures['main'].set_figheight(self.height *
            #                                    (1 + 0.5 * int((self.plot_parameters['plot_count'] - 6) / 3 + 0.9)))

            self.plot_parameters['plot_count'] = len(
                self.plot_parameters['status_params'].findall(
                    f"{self.plot_parameters['graph']}/plot/Name"))

            row = int(self.plot_parameters['plot_count'] / 2 + 0.5)
            i = 1

            for p in self.plot_parameters['status_params'].findall(
                    f"{self.plot_parameters['graph']}/plot/Name"):
                self.axis[p.text] = self.figures['main'].add_subplot(row, 2, i)
                self.axis[p.text].set_xlim(self.x_min, self.x_max)
                self.axis[p.text].set_title(p.text, fontsize=7, wrap=True)
                self.axis[p.text].tick_params(axis='both', labelsize=7)
                self.axis[p.text].spines[['right', 'top']].set_visible(False)
                i += 1

                for j, controller in enumerate(['DUT', 'BRK', 'ABB', 'YOKO']):
                    for element in self.plot_parameters['status_params'].findall(
                            f"{self.plot_parameters['graph']}/{controller}/Name"):
                        if p.text.lower() in element.text.lower():
                            try:
                                line, = self.axis[p.text].plot(
                                    self.data['Elapsed'],
                                    self.data[f'{controller if controller != "YOKO" else ""}'
                                              f'{" " if controller != "YOKO" else ""}'
                                              f'{element.text}'],
                                    color=STYLES[j], linestyle='-')
                            except KeyError:
                                # self.axis[p.text].remove()
                                # del self.axis[p.text]
                                break
                            else:
                                self.lines[f'{p.text}_{controller} {element.text}'] = line
                                self.graph_tt.msg += f'\n' \
                                                     f'{STYLES[j]}: {p.text}-{controller} {element.text}'

            # self.canvas.get_tk_widget().bind('<MouseWheel>', self.master.master.master.on_mousewheel)

            logging.info(f"Grid graph [{self.plot_parameters['graph']}] initiated")

    def start_graphing(self):
        """
        GUI backend
        Starts graphing thread
        """
        # self.data = pd.DataFrame(columns=self.plot_parameters['graph_params'])
        logging.debug(f'start of dyno_plot start_graphing for [{self.plot}]')
        # self.dyno.start_time = datetime.now()
        # self.start_time = self.dyno.start_time
        if 'adv' in self.plot:
            self.start_time = self.dyno.start_time
            self.reset_xlim()
        else:
            self.start_time = datetime.now()
            self.dyno.start_time = self.start_time
        self.graphing = True
        self._graphing_thread = Thread(target=self.graphing_thread)
        self._graphing_thread.start()
        if 'adv' in self.plot:
            self.master.children['ani_pause_btn']['state'] = NORMAL
        logging.info(f"Graphing thread [{self.plot}] started")
        # self._graphing_pause()

    def end_graphing(self):
        """
        GUI backend
        Stops graphing thread
        """
        if self.graphing:
            if self.after_id:
                self.master.after_cancel(self.after_id)
            self.graphing = False
            # self._graphing_thread.join()
            self._graphing_thread = None
            if 'adv' in self.plot:
                self.master.children['ani_pause_btn']['state'] = DISABLED
                self.paused.set("UNPAUSE")
            logging.info("Graphing thread stopped")

    def _graphing_pause(self):
        """
        GUI backend
        Toggles graphing pause/unpause
        """
        if self.paused.get() == "PAUSE":
            # self.graphing = False
            self.animation.pause()
            self.paused.set("UNPAUSE")
        else:
            # self.graphing = True
            self.animation.resume()
            self.paused.set("PAUSE")

    def refresh(self):
        """
        GUI backend
        Refreshes graph x, y axis limits
        """
        logging.debug('Graph refreshed')
        if 'adv' in self.plot.lower():

            self.y_param_update()

            try:
                if (max(self.data[self.plot_parameters['x_combo'].get()]) > self.x_max or
                        self.x_max > X_MAX):
                    if self.x_max < max(self.data[self.master.children['x_combo'].get()]) <= self.x_max + X_MAX / 4:
                        self.x_max += X_MAX / 4
                    elif max(self.data[self.master.children['x_combo'].get()]) > self.x_max + X_MAX / 4:
                        self.x_max = max(self.data[self.master.children['x_combo'].get()]) + X_MAX / 4
                    elif max(self.data[self.master.children['x_combo'].get()]) < self.x_max - X_MAX / 3:
                        self.x_max -= X_MAX / 3
                    # else:
                    #     self.x_max = max(self.data[self.master.children['x_combo'].get()])
            except TypeError:
                pass

            for i, j in zip(self.lines, self.y_selected):
                for line, y in zip(self.lines[i], self.y_selected[j]):
                    if self.master.children['x_combo'].get() in ['Elapsed', 'Time']:
                        self.x_min = 0
                    else:
                        if min(self.data[self.master.children['x_combo'].get()]) > 0:
                            if self.x_min > min(self.data[self.master.children['x_combo'].get()]) * 0.9:
                                self.x_min = min(self.data[self.master.children['x_combo'].get()]) * 0.9
                        elif min(self.data[self.master.children['x_combo'].get()]) < 0:
                            if self.x_min > min(self.data[self.master.children['x_combo'].get()]) * 1.1:
                                self.x_min = min(self.data[self.master.children['x_combo'].get()]) * 1.1
                        else:
                            if max(self.data[self.master.children['x_combo'].get()]) > 0:
                                self.x_min = max(self.data[self.master.children['x_combo'].get()]) * -0.1
                            else:
                                self.x_min = -1
                        if max(self.data[self.master.children['x_combo'].get()]) > 0:
                            if self.x_max < max(self.data[self.master.children['x_combo'].get()]) * 1.1:
                                self.x_max = max(self.data[self.master.children['x_combo'].get()]) * 1.1
                        elif max(self.data[self.master.children['x_combo'].get()]) < 0:
                            if self.x_max < max(self.data[self.master.children['x_combo'].get()]) * 0.9:
                                self.x_max = max(self.data[self.master.children['x_combo'].get()]) * 0.9
                        else:
                            if min(self.data[self.master.children['x_combo'].get()]) < 0:
                                self.x_max = min(self.data[self.master.children['x_combo'].get()]) * -0.1
                            else:
                                self.x_max = 1
                        # if self.x_min > min(self.data[y]) - 0.1:
                        #     self.x_min = min(self.data[y]) - 0.1
                        # if self.x_max < max(self.data[y]) + 0.1:
                        #     self.x_max = max(self.data[y]) + 0.1

            self.axis[0].set_xlim(self.x_min, self.x_max)
            self.axis[0].relim()
            self.axis[0].autoscale_view(True, True, True)

        elif 'sing' in self.plot.lower():
            self.axis[0].set_xlim(self.x_min, self.x_max)
            self.axis[0].spines[['top']].set_visible(False)
            self.axis[1].spines[['top']].set_visible(False)

            for line in self.lines:
                self.lines[line].set_data(self.data['Elapsed'],
                                          self.data[line if line.split(' ')[0] != 'YOKO'
                                          else ' '.join(line.split(' ')[1:])])
            self.axis[0].relim()
            self.axis[0].autoscale_view(True, True, True)
            self.axis[1].relim()
            self.axis[1].autoscale_view(True, True, True)

        elif 'grid' in self.plot.lower():
            for fig in self.axis:
                self.axis[fig].set_xlim(self.x_min, self.x_max)

                for line in self.lines:
                    if fig == line.split('_')[0]:
                        l = line.split('_')[1]
                        self.lines[line].set_data(self.data['Elapsed'],
                                                  self.data[l if l.split(' ')[0] != 'YOKO'
                                                  else ' '.join(l.split(' ')[1:])])
                self.axis[fig].relim()
                self.axis[fig].autoscale_view(True, True, True)

    def reset(self):
        """
        GUI backend
        Clears data from all lines but keeping the lines
        """
        self.x_max = X_MAX
        self.x_min = X_MIN
        self.data = self.data[0:0]
        self.dyno.start_time = datetime.now()
        self.start_time = self.dyno.start_time
        self.dyno.current_csv_line[1] = 0

        if 'sing' in self.plot.lower():
            self.axis[0].set_xlim(self.x_min, self.x_max)
            self.axis[0].spines[['right', 'top']].set_visible(False)

            for line in self.lines:
                self.lines[line].set_data([], [])
            # self.axis[0].relim()
            # self.axis[0].autoscale_view(True, True, True)

        elif 'grid' in self.plot.lower():
            for fig in self.axis:
                self.axis[fig].set_xlim(self.x_min, self.x_max)

                for line in self.lines:
                    if fig == line.split('_')[0]:
                        # l = line.split('_')[1]
                        self.lines[line].set_data([], [])
                # self.axis[fig].relim()
                # self.axis[fig].autoscale_view(True, True, True)
        logging.info(f"Graph [{self.plot}] reset")

    def reset_xlim(self):
        """
        GUI backend
        Resets graph x axis limits
        """
        self.x_max = X_MAX
        self.x_min = X_MIN
        for i in self.axis:
            self.axis[i].set_xlim(self.x_min, self.x_max)

    def y_param_update(self, event=None):
        """
        GUI backend
        Updates parameters for primary axis
        """
        for i in self.axis:
            self.lines[i] = []
            self.y_selected[i] = []
            self.axis[i].clear()
            self.axis[i].set_xlim(self.x_min, self.x_max)

            for j in range(len(self.plot_parameters['graph_params'])):
                self.master.children[f'y_list_{i}'].itemconfig(j, {'selectbackground': 'white'})

        counter = 0
        self.graph_tt.msg = ''
        for i, j, k in zip(self.y_selected, self.lines, self.axis):
            for param in self.master.children[f'y_list_{i}'].curselection():
                self.y_selected[i].append(self.plot_parameters['graph_params'][param])
                self.master.children[f'y_list_{i}'].itemconfig(param, {'selectbackground': COLORS[counter],
                                                                       'selectforeground': PARAMETER_FOREGROUND[COLORS[counter]]})
                if self.graphing:
                    line, = self.axis[k].plot(
                        self.data[self.plot_parameters['x_combo'].get()],
                        self.data[self.plot_parameters['graph_params'][param]],
                        color=STYLES[counter], linestyle='-')
                    self.lines[j].append(line)
                counter += 1

            for y, c in zip(self.y_selected[i], COLORS):
                if c == 'gray60':
                    c = 'gray'
                self.graph_tt.msg += f'{c}: {y}\n'

            self.axis[k].set_ylim()

        for i, j in zip(self.axis, self.y_selected):
            self.axis[i].set_ylabel(', '.join(self.y_selected[j]), wrap=True)
            if i > 0:
                self.axis[i].yaxis.set_label_position("right")

    def graphing_thread(self):
        """
        GUI backend
        Graphing thread target
        """
        while self.graphing:
            # self.after_id = self.master.after(100, self.action)
            self.action()

            sleep(self.graphing_interval)

    def action(self):
        if self.dyno is not None:
            if 'adv' in self.plot.lower():
                # Showing whole range
                delta = (datetime.now() - self.start_time).total_seconds()
                if delta < 600:
                    self.graphing_interval = 1  # 1 sec/row for the first 10 minutes
                elif len(self.data) == 600 and delta < 650:
                    self.data = self.data.iloc[::2, :]  # halves the data for the first 10 minutes
                    self.data.reset_index(drop=True, inplace=True)
                elif delta <= 1200:
                    self.graphing_interval = 2  # 2 sec/row for the next 10 minutes
                elif delta <= 2700:
                    self.graphing_interval = 5  # 5 sec/row for the next 25 minutes
                elif delta <= 7200:
                    self.graphing_interval = 15  # 15 sec/row for the next 15 minutes
                else:
                    self.graphing_interval = 60  # 1 min/row after 2 hours
                try:
                    self.data.loc[len(self.data)] = self.dyno.getcsvline()
                except ValueError:
                    pass

            elif 'sing' in self.plot.lower() or 'grid' in self.plot.lower():
                # Showing the last 2 minutes
                try:
                    if (len(self.data['Elapsed']) > 100
                            and max(self.data['Elapsed']) > self.x_max):
                        self.data.drop(index=0, inplace=True)
                        self.data.reset_index(drop=True, inplace=True)
                    if (len(self.data['Elapsed']) > 100
                            or max(self.data['Elapsed']) > self.x_max):
                        self.x_min = min(self.data['Elapsed'])
                        self.x_max = max(self.data['Elapsed'])
                except (TypeError, ValueError):
                    pass

                try:
                    new_data = self.dyno.getcsvline()
                    self.data.loc[len(self.data)] = new_data
                except CommLossError:
                    self.graphing = False
                except ValueError as e:
                    logging.error(e)
                    logging.error(str(list(self.data)))
                    if new_data:
                        logging.error(new_data)


class DynoPlotHandler:

    def __init__(self):
        self.plots = {}
        self.data = {"adv": pd.DataFrame(),
                     "current": pd.DataFrame()}
        self.graphing = False
        self.graphing_interval = 1
        self._graphing_thread = None

    def new_plot_name(self, name=""):
        if name == "":
            return f"DynoPlot_{len(self.plots.keys())}"
        else:
            if name in self.plots.keys():
                raise AttributeError(f"Plot name: {name} already exists")
            else:
                return name

    def add_plot(
            self,
            master,
            width=6.2,
            height=3.2,
            plot='adv',
            axis=2,
            autolayout=True,
            placement='grid',
            *args,
            **kwargs
    ):
        plot_name = self.new_plot_name(kwargs["graph"] if "graph" in kwargs.keys() else "")

        self.plots[plot_name] = DynoPlot(master,
                                         width,
                                         height,
                                         plot,
                                         axis,
                                         autolayout,
                                         placement,
                                         *args,
                                         **kwargs)

        self.data["current"] = pd.DataFrame(columns=self.plots[plot_name].plot_parameters['graph_params'])

        return self.plots[plot_name]

    def init_graphing(self):
        for plot in self.plots:
            # self.plots[plot].init_graphing()
            logging.info(f'start of dyno_plot init_graphing for [{plot}]')
            self.plots[plot].x_max = X_MAX
            self.plots[plot].x_min = X_MIN
            if 'sing' in self.plots[plot].plot.lower():
                self.plots[plot].lines = {}
                self.plots[plot].axis[0].remove()
                self.plots[plot].axis[0] = self.plots[plot].figures['main'].add_subplot(1, 1, 1)
                self.plots[plot].axis[0].set_title(self.plots[plot].plot_parameters['title'])
                self.plots[plot].axis[1].remove()
                self.plots[plot].axis[1] = self.plots[plot].figures['main'].add_subplot(1, 1, 1,
                                                                sharex=self.plots[plot].axis[0], frameon=False)
                self.plots[plot].axis[1].spines[['right']].set_visible(True)
                self.plots[plot].axis[1].yaxis.tick_right()
                self.plots[plot].graph_tt.msg = self.plots[plot].plot_parameters['title']

                c = 0
                for controller in ['DUT', 'BRK', 'ABB', 'YOKO']:
                    if controller == 'DUT' and not self.plots[plot].dyno.devices[1]:
                        continue

                    if controller == 'BRK' and not isinstance(self.plots[plot].dyno.devices[2], ASIController):
                        continue

                    if controller == 'YOKO' and not self.plots[plot].dyno.devices[PA]:
                        continue

                    if controller == 'ABB' and not isinstance(self.plots[plot].dyno.devices[2], AbbAcs800):
                        continue

                    for element in self.plots[plot].plot_parameters['status_params'].findall(
                            f"{self.plots[plot].plot_parameters['graph']}/{controller}/Name"):
                        line, = self.plots[plot].axis[0].plot(
                            self.data['current']['Elapsed'],
                            self.data['current'][f'{controller if controller != "YOKO" else ""}'
                                                 f'{" " if controller != "YOKO" else ""}'
                                                 f'{element.text}'],
                            color=STYLES[c], linestyle='-')
                        self.plots[plot].lines[f'{controller} {element.text}'] = line
                        self.plots[plot].graph_tt.msg += f'\n' \
                                             f'{STYLES[c]}: {controller} {element.text}'
                        c += 1
                    for element in self.plots[plot].plot_parameters['status_params'].findall(
                            f"{self.plots[plot].plot_parameters['graph']}/{controller}/Secondary"):
                        line, = self.plots[plot].axis[1].plot(
                            self.data['current']['Elapsed'],
                            self.data['current'][f'{controller if controller != "YOKO" else ""}'
                                                 f'{" " if controller != "YOKO" else ""}'
                                                 f'{element.text}'],
                            color=STYLES[c], linestyle='-')
                        self.plots[plot].lines[f'{controller} {element.text}'] = line
                        self.plots[plot].graph_tt.msg += f'\n' \
                                             f'{STYLES[c]}: {controller} {element.text}'
                        c += 1

                # self.plots[plot].data = self.data['current']

                logging.info(f"Single graph [{self.plots[plot].plot_parameters['graph']}] initiated")

            elif 'grid' in self.plots[plot].plot.lower():
                self.plots[plot].lines = {}
                for p in self.plots[plot].plot_parameters['status_params'].findall(
                        f"{self.plots[plot].plot_parameters['graph']}/plot/Name"):
                    self.plots[plot].axis[p.text].remove()
                self.plots[plot].axis = {}
                self.plots[plot].graph_tt.msg = self.plots[plot].plot_parameters['title']

                self.plots[plot].plot_parameters['plot_count'] = 0

                self.plots[plot].plot_parameters['plot_count'] = len(
                    self.plots[plot].plot_parameters['status_params'].findall(
                        f"{self.plots[plot].plot_parameters['graph']}/plot/Name"))

                row = int(self.plots[plot].plot_parameters['plot_count'] / 2 + 0.5)
                i = 1

                for p in self.plots[plot].plot_parameters['status_params'].findall(
                        f"{self.plots[plot].plot_parameters['graph']}/plot/Name"):
                    self.plots[plot].axis[p.text] = self.plots[plot].figures['main'].add_subplot(row, 2, i)
                    self.plots[plot].axis[p.text].set_xlim(self.plots[plot].x_min, self.plots[plot].x_max)
                    self.plots[plot].axis[p.text].set_title(p.text, fontsize=7, wrap=True)
                    self.plots[plot].axis[p.text].tick_params(axis='both', labelsize=7)
                    self.plots[plot].axis[p.text].spines[['right', 'top']].set_visible(False)
                    i += 1

                    for j, controller in enumerate(['DUT', 'BRK', 'ABB', 'YOKO']):
                        for element in self.plots[plot].plot_parameters['status_params'].findall(
                                f"{self.plots[plot].plot_parameters['graph']}/{controller}/Name"):
                            if p.text.lower() in element.text.lower():
                                try:
                                    line, = self.plots[plot].axis[p.text].plot(
                                        self.data['current']['Elapsed'],
                                        self.data['current'][f'{controller if controller != "YOKO" else ""}'
                                                  f'{" " if controller != "YOKO" else ""}'
                                                  f'{element.text}'],
                                        color=STYLES[j], linestyle='-')
                                except KeyError:
                                    break
                                else:
                                    self.plots[plot].lines[f'{p.text}_{controller} {element.text}'] = line
                                    self.plots[plot].graph_tt.msg += f'\n' \
                                                         f'{STYLES[j]}: {p.text}-{controller} {element.text}'

                # self.plots[plot].data = self.data['current']

                logging.info(f"Grid graph [{self.plots[plot].plot_parameters['graph']}] initiated")

    def refresh(self):
        for plot in self.plots:
            self.plots[plot].data = self.data['current']

            # if 'sing' in self.plots[plot].plot.lower():
            #     self.plots[plot].axis[0].set_xlim(self.plots[plot].x_min, self.plots[plot].x_max)
            #     self.plots[plot].axis[0].spines[['top']].set_visible(False)
            #     self.plots[plot].axis[1].spines[['top']].set_visible(False)
            #
            #     for line in self.plots[plot].lines:
            #         self.plots[plot].lines[line].set_data(self.data['current']['Elapsed'],
            #                                   self.data['current'][line if line.split(' ')[0] != 'YOKO'
            #                                   else ' '.join(line.split(' ')[1:])])
            #     self.plots[plot].axis[0].relim()
            #     self.plots[plot].axis[0].autoscale_view(True, True, True)
            #     self.plots[plot].axis[1].relim()
            #     self.plots[plot].axis[1].autoscale_view(True, True, True)
            #
            # elif 'grid' in self.plots[plot].plot.lower():
            #     for fig in self.plots[plot].axis:
            #         self.plots[plot].axis[fig].set_xlim(self.plots[plot].x_min, self.plots[plot].x_max)
            #
            #         for line in self.plots[plot].lines:
            #             if fig == line.split('_')[0]:
            #                 l = line.split('_')[1]
            #                 self.plots[plot].lines[line].set_data(self.data['current']['Elapsed'],
            #                                           self.data['current'][l if l.split(' ')[0] != 'YOKO'
            #                                           else ' '.join(l.split(' ')[1:])])
            #         self.plots[plot].axis[fig].relim()
            #         self.plots[plot].axis[fig].autoscale_view(True, True, True)

    def graphing_thread(self):
        """
        GUI backend
        Graphing thread target
        """
        while self.graphing:
            # self.after_id = self.master.after(100, self.action)
            self.action()
            self.refresh()

            sleep(self.graphing_interval)

    def action(self):
        try:
            new_data = self.plots[list(self.plots.keys())[0]].dyno.getcsvline()
            self.data['current'].loc[len(self.data['current'])] = new_data
        except CommLossError:
            self.graphing = False
        except ValueError as e:
            logging.error(e)
            logging.error(str(list(self.data['current'])))
            if new_data:
                logging.error(new_data)

        for plot in self.plots:
            if self.plots[plot].dyno is not None:
                # data['current']
                try:
                    if (len(self.data['current']['Elapsed']) > 100
                            and max(self.data['current']['Elapsed']) > self.plots[plot].x_max):
                        self.data['current'].drop(index=0, inplace=True)
                        self.data['current'].reset_index(drop=True, inplace=True)
                    if (len(self.data['current']['Elapsed']) > 100
                            or max(self.data['current']['Elapsed']) > self.plots[plot].x_max):
                        self.plots[plot].x_min = min(self.data['current']['Elapsed'])
                        self.plots[plot].x_max = max(self.data['current']['Elapsed'])
                    if len(self.data['current']['Elapsed']) > 2:
                        if self.data['current'].loc[list(self.data['current'].index)[0], 'Elapsed'] > \
                                self.data['current'].loc[list(self.data['current'].index)[1], 'Elapsed']:
                            self.data['current'].drop(index=0, inplace=True)
                            self.data['current'].reset_index(drop=True, inplace=True)
                except (TypeError, ValueError):
                    pass

    def start_graphing(self):
        """
        GUI backend
        Starts graphing thread
        """
        self.data['current'] = pd.DataFrame(
            columns=self.plots[list(self.plots.keys())[0]].dyno.getcsvline(getnames=True))

        self.init_graphing()
        for plot in self.plots:
            self.plots[plot].graphing = True

        start_time = datetime.now()
        for plot in self.plots:
            self.plots[plot].start_time = datetime.now()
            self.plots[plot].dyno.start_time = start_time
            self.plots[plot].reset_xlim()

        self.graphing = True
        self._graphing_thread = Thread(target=self.graphing_thread)
        self._graphing_thread.start()

        for plot in self.plots:
            self.plots[plot].reset()

    def end_graphing(self):
        """
        GUI backend
        Stops graphing thread
        """
        if self.graphing:
            self.graphing = False
            # self._graphing_thread.join()
            self._graphing_thread = None

