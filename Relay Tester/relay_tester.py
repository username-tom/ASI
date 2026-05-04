"""relay_tester: Relay Tester GUI"""

__version__ = '1.0'

from tkinter import *
from tkinter import messagebox, font
from Module.config import *
import Module.ontrak_relay as ontrak
from GUI.tooltip import ToolTip
from threading import Thread, Event

class ASIStatusIndicator:

    def __init__(
            self,
            master,
            status=False,
            size=20,
            padding=2
    ):
        self.master = master
        self.size = size
        self.status = status
        self.padding = padding
        self.background = 'white'
        self.canvas = Canvas(self.master, width=self.size, height=self.size,
                             background=self.background, borderwidth=0,
                             highlightthickness=0, relief='flat')
        self.indicator = self.canvas.create_oval(self.padding, self.padding,
                                                 self.size - self.padding, self.size - self.padding,
                                                 outline='', fill=f"{'green' if self.status else 'red'}")

    def update_status(self):
        self.canvas.itemconfig(self.indicator, fill='green' if self.status else 'red')


class RelayTester:
    """GUI Runner for Relay Tester"""

    def __init__(self, root):
        self.root = root
        self.root.title("Line Reactor Runner")
        self.root.geometry(GEOMETRY)
        self.root.resizable(False, False)
        self.root.iconbitmap('ASI Logo.ico')
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root['background'] = 'white'
        default_font = font.nametofont('TkDefaultFont')
        default_font.config(size=FONT_SIZE)
        self.status = StringVar(value="DISCONNECTED")
        self.int_event = Event()
        self.relay_selected = [BooleanVar(value=True),
                               BooleanVar(value=False)]
        self.indicator = {}
        self.on_interval = IntVar(value=5)
        self.on_interval.trace('w', self._on_cycle_change)
        self.off_interval = IntVar(value=5)
        self.off_interval.trace('w', self._on_cycle_change)
        self.cycles = IntVar(value=100)
        self.cycles.trace('w', self._on_cycle_change)
        self.current_cycle = IntVar(value=0)
        self.duration = IntVar(value=1000)
        self.duration.trace('w', self._on_duration_change)
        self._updating_derived = False
        self.test_stopping = False
        self.worker = None
        self.relay_device = None
        self.testing = False
        self.output_container = None
        self.mainframe = self.build_mainframe()
        self.mainframe.grid(column=0, row=1, sticky='news', columnspan=3)
        self.root.grid_columnconfigure((0, 1, 2), weight=1)

    def build_mainframe(self):
        mainframe = Frame(self.root, padx=10, pady=10, background='white')

        Label(mainframe, name="condition_status", text="STATUS:", background='white').grid(
            column=0, row=1, sticky='e')
        Label(mainframe, name="condition_value", textvariable=self.status, background='white', width=15).grid(
            column=1, row=1, columnspan=3, sticky='news')

        Label(mainframe, name="on_label", text="ON Duration", background='white').grid(
            column=0, row=4, sticky='e')
        Entry(mainframe, name="on_entry", textvariable=self.on_interval,
              font=f'TkDefaultFont {FONT_SIZE}', width=10).grid(
            column=1, row=4, columnspan=3)
        Label(mainframe, name="on_unit", text="seconds", background='white').grid(
            column=4, row=4, sticky='w')
        ToolTip(mainframe.children['on_label'],
                msg="How long relay stays connected in a cycle", delay=0.5)

        Label(mainframe, name="off_label", text="OFF Duration", background='white').grid(
            column=0, row=5, sticky='e')
        Entry(mainframe, name="off_entry", textvariable=self.off_interval,
              font=f'TkDefaultFont {FONT_SIZE}', width=10).grid(
            column=1, row=5, columnspan=3)
        Label(mainframe, name="off_unit", text="seconds", background='white').grid(
            column=4, row=5, sticky='w')
        ToolTip(mainframe.children['off_label'],
                msg="How long relay stays disconnected in a cycle", delay=0.5)

        Label(mainframe, name="cycle_label", text="# of Cycles", background='white').grid(
            column=0, row=6, sticky='e')
        Entry(mainframe, name="cycle_entry", textvariable=self.cycles,
              font=f'TkDefaultFont {FONT_SIZE}', width=10).grid(
            column=1, row=6, columnspan=3)
        Label(mainframe, name="cycle_unit", text="cycles", background='white').grid(
            column=4, row=6, sticky='w')
        ToolTip(mainframe.children['cycle_label'],
                msg="How long relay stays disconnected in a cycle", delay=0.5)

        Label(mainframe, name="c_label", text="Current Cycle", background='white').grid(
            column=0, row=7, sticky='e')
        Label(mainframe, name="c_entry", textvariable=self.current_cycle,
              background='white', width=10, justify='left').grid(
            column=1, row=7, columnspan=4, sticky='w')

        Label(mainframe, name="duration_label", text="Total Duration", background='white').grid(
            column=0, row=8, sticky='e')
        Entry(mainframe, name="duration_entry", textvariable=self.duration,
              font=f'TkDefaultFont {FONT_SIZE}', width=10).grid(
            column=1, row=8, columnspan=3)
        Label(mainframe, name="duration_unit", text="seconds", background='white').grid(
            column=4, row=8, sticky='w')
        ToolTip(mainframe.children['duration_label'],
                msg="How long relay stays disconnected in a cycle", delay=0.5)

        Button(mainframe, name="start_btn", text="Start", command=self._test_start, width=20,
               background='green', activebackground='green').grid(
            column=0, row=18, columnspan=5, pady=2)
        ToolTip(mainframe.children['start_btn'],
                msg="Starts relay test", delay=0.5)
        Button(mainframe, name="stop_btn", text="Stop", command=self._test_stop, width=20,
               background='red', activebackground='red').grid(
            column=0, row=19, columnspan=5, pady=2)
        ToolTip(mainframe.children['stop_btn'],
                msg="Stops relay test", delay=0.5)
        mainframe.children['stop_btn']['state'] = DISABLED

        self.build_out_frame()

        return mainframe

    def build_out_frame(self):
        """Constructing output frame"""
        output_container = Frame(self.root, relief='flat', background='white', name='output_frame')
        output_container.grid(column=0, row=0, columnspan=3)

        relay_selector = LabelFrame(self.root.children['output_frame'], background='white', text='Relay Outputs')
        relay_selector.grid(column=0, row=0, columnspan=2)

        temp_widget = Checkbutton(relay_selector, text='K0', background='white',
                                  onvalue=True, variable=self.relay_selected[0], name='k0_select')
        temp_widget.grid(column=0, row=0)
        temp_widget = ASIStatusIndicator(relay_selector, False, 20)
        temp_widget.canvas.grid(column=1, row=0, padx='5 20')
        self.indicator[0] = temp_widget

        temp_widget = Checkbutton(relay_selector, text='K1', background='white',
                                  onvalue=True, variable=self.relay_selected[1], name='k1_select')
        temp_widget.grid(column=2, row=0)
        temp_widget = ASIStatusIndicator(relay_selector, False, 20)
        temp_widget.canvas.grid(column=3, row=0, padx=5)
        self.indicator[1] = temp_widget

    def _on_cycle_change(self, *args):
        if self._updating_derived:
            return
        try:
            self._updating_derived = True
            self.duration.set(int(self.cycles.get() * (self.on_interval.get() + self.off_interval.get())))
        except TclError:
            pass
        finally:
            self._updating_derived = False

    def _on_duration_change(self, *args):
        if self._updating_derived:
            return
        try:
            self._updating_derived = True
            self.cycles.set(int(self.duration.get() / (self.on_interval.get() + self.off_interval.get())))
        except TclError:
            pass
        finally:
            self._updating_derived = False

    def relay_thread(self):
        while self.testing and self.current_cycle.get() < self.cycles.get():
            self.current_cycle.set(self.current_cycle.get() + 1)
            # connect relay
            for i, check in enumerate(self.relay_selected):
                if check.get():
                    self.relay_device.close_relay(i)
                    self.indicator[i].status = True
                    self.indicator[i].update_status()
            self.int_event.wait(self.on_interval.get())
            # disconnect relay
            for i, check in enumerate(self.relay_selected):
                if check.get():
                    self.relay_device.open_relay(i)
                    self.indicator[i].status = False
                    self.indicator[i].update_status()
            self.int_event.wait(self.off_interval.get())

        self._test_stop()

    def start_relay(self):
        self.worker = Thread(target=self.relay_thread)
        self.worker.start()

    def stop_relay(self):
        self.testing = False
        self.worker = None

    def _on_connect(self):
        if self.status.get() in ["DISCONNECTED", 'CONNECTING']:
            self.status.set("CONNECTING...")
            try:
                self.relay_device = ontrak.OntrakRelay(222)
            except OSError as e:
                print(e)
            except (ValueError, AttributeError) as e:
                if "ADU Device not found" in str(e) or "'NoneType' object has no attribute '_ctx'" in str(e):
                    messagebox.showinfo('Error!',
                                        'ONTRAK relay not found\n'
                                        'Please make sure relay is connected and retry!')
                    self.root.update()
                    self.status.set("DISCONNECTED")
                    return
            else:
                self._reset_relay()
                self.status.set("CONNECTED")

        elif self.status.get() in ["CONNECTED", "TESTING", "CONNECTING..."]:
            self.status.set("DISCONNECTING...")

            try:
                self.relay_device.__del__()
            except (ValueError, AttributeError, OSError):
                pass
            finally:
                self.relay_device = None
                self.status.set("DISCONNECTED")

    def _reset_relay(self):
        self.relay_device.open_relay(0)
        self.relay_device.open_relay(1)

    def _test_start(self):
        def action():

            self.status.set('CONNECTING')

            self.testing = True

            self.mainframe.children['start_btn']['state'] = DISABLED
            self.mainframe.children['stop_btn']['state'] = NORMAL

            self._on_connect()
            if self.status.get() == 'CONNECTED':

                self.status.set('TESTING')
                self.start_relay()
            else:
                self.mainframe.children['start_btn']['state'] = NORMAL
                self.mainframe.children['stop_btn']['state'] = DISABLED

        temp = Thread(target=action)
        temp.start()

    def _test_stop(self):
        if not self.test_stopping:
            def action():
                self.test_stopping = True
                self.current_cycle.set(0)
                self.int_event.set()
                self.stop_relay()
                self.int_event.clear()

                self.status.set('CONNECTED')
                self._on_connect()

                self.mainframe.children['start_btn']['state'] = NORMAL
                self.mainframe.children['stop_btn']['state'] = DISABLED

                self.test_stopping = False


            temp = Thread(target=action)
            temp.start()

    def _on_closing(self):
        if self.testing:
            self._test_stop()
        if (self.status.get() == "CONNECTED"
              or self.status.get() == "TESTING"
              or self.status.get() == "CONNECTING..."):
            self._on_connect()

        config.set('default', 'geometry', f'{self.root.geometry()}')
        with open('config.ini', 'w') as file:
            config.write(file)
        self.root.update()
        self.root.destroy()


if __name__ == "__main__":
    gui = Tk()
    RelayTester(gui)
    gui.mainloop()
