import tkinter as tk
from tkinter import *
from tkinter import ttk
from dyno_v2.GUI.round_polygon import RoundPolygon
import logging
from threading import Thread
from time import sleep
from dyno_v2.GUI.tooltip import ToolTip

ANIMATION_INTERVAL = 0.5


class DUT:

    def __init__(
            self,
            canvas: tk.Canvas,
            width,
            height
    ):
        self.canvas = canvas
        self.start = False
        self.direction = 0 # 0 - stopped | 1 - positive RPM | -1 - negative RPM
        self.width = width
        self.height = height
        self.boundary = 5, 5, width - 5, height - 5
        self.background = self.canvas.create_oval(self.boundary, fill='white')
        self.indicator_offset = 0
        self.indicator_color = 'gray'
        self.init_phase_cables()
        self.create_indicator()
        self.handler = None


    def init_phase_cables(self):
        self.connector = {
            'U': self.canvas.create_line(0.25 * self.width, 0.9 * self.height, 0.25 * self.width, self.height, width=5, fill='green'),
            'V': self.canvas.create_line(0.5 * self.width, 0.9 * self.height, 0.5 * self.width, self.height, width=5, fill='yellow'),
            'W': self.canvas.create_line(0.75 * self.width, 0.9 * self.height, 0.75 * self.width, self.height, width=5, fill='blue')
        }

    def create_indicator(self):
        self.indicator = {}
        for i in range(8):
            self.indicator[i] = self.canvas.create_arc(self.boundary, start=i * 45 + self.indicator_offset,
                                                       extent=30, fill=self.indicator_color, outline='')

    def update_indicator(self):
        for i in range(8):
            self.canvas.delete(self.indicator[i])
            self.indicator[i] = self.canvas.create_arc(self.boundary, start=i * 45 + self.indicator_offset,
                                                       extent=30, fill=self.indicator_color, outline='')

    def motoring(self):
        def action():
            if self.direction == 0:
                pass
            elif self.direction > 0:
                self.indicator_offset += 15
            elif self.direction < 0:
                self.indicator_offset -= 15
            self.update_indicator()

        while self.start:
            self.canvas.update()
            self.canvas.after(100, action)
            sleep(ANIMATION_INTERVAL)


    def start_motor(self):
        if self.start == False:
            self.start = True
            self.handler = Thread(target=self.motoring)
            self.handler.start()

    def stop_motor(self):
        if self.start == True:
            self.start = False
            self.handler = None

    def update_direction(self, direction):
        self.direction = direction

    def update_color(self, color):
        self.indicator_color = color


class YOKO:

    def __init__(
            self,
            canvas: tk.Canvas,
            width,
            height
    ):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.x_gap = 150
        self.boundary = 5 + self.x_gap, 20, width - 5 + self.x_gap, height - 20
        self.panel_boundary = 5 + 0.5 * width + self.x_gap, 25, width - 15 + self.x_gap, 0.4 * height
        self.btn_boundary = 5 + 0.5 * width + self.x_gap, 0.45 * height, width - 15 + self.x_gap, height - 25
        self.indicator_boundary = 15 + self.x_gap, 25, 0.5 * width + self.x_gap, height - 25
        self.state = 0 # 0 - off | 1 - on | -1 - disabled
        self.init_yoko()


    def init_yoko(self):
        self.background = RoundPolygon(self.canvas,
                                       x=[self.boundary[0], self.boundary[2], self.boundary[2], self.boundary[0]],
                                       y=[self.boundary[1], self.boundary[1], self.boundary[3], self.boundary[3]],
                                       sharpness=2, width=2, outline='gray', fill='#fcfcfc')
        self.panel = RoundPolygon(self.canvas,
                                  x=[self.panel_boundary[0], self.panel_boundary[2], self.panel_boundary[2], self.panel_boundary[0]],
                                  y=[self.panel_boundary[1], self.panel_boundary[1], self.panel_boundary[3], self.panel_boundary[3]],
                                  sharpness=2, outline='black', fill='#afafcf')
        self.buttons = RoundPolygon(self.canvas,
                                    x=[self.btn_boundary[0], self.btn_boundary[2], self.panel_boundary[2], self.btn_boundary[0]],
                                    y=[self.btn_boundary[1], self.btn_boundary[1], self.btn_boundary[3], self.btn_boundary[3]],
                                    sharpness=2, outline='black', fill='#cfcfcf')
        self.indicator = RoundPolygon(self.canvas,
                                      x=[self.indicator_boundary[0], self.indicator_boundary[2], self.indicator_boundary[2],
                                         self.indicator_boundary[0]],
                                      y=[self.indicator_boundary[1], self.indicator_boundary[1], self.indicator_boundary[3],
                                         self.indicator_boundary[3]],
                                      sharpness=2, outline='black', fill='black')

    def disable_yoko(self):
        self.state = -1
        self.canvas.delete(self.background.polygon)
        self.canvas.delete(self.panel.polygon)
        self.canvas.delete(self.buttons.polygon)
        self.canvas.delete(self.indicator.polygon)
        self.background = RoundPolygon(self.canvas,
                                       x=[self.boundary[0], self.boundary[2], self.boundary[2], self.boundary[0]],
                                       y=[self.boundary[1], self.boundary[1], self.boundary[3], self.boundary[3]],
                                       sharpness=2, width=2, outline='gray', fill='gray')
        self.panel = RoundPolygon(self.canvas,
                                  x=[self.panel_boundary[0], self.panel_boundary[2], self.panel_boundary[2], self.panel_boundary[0]],
                                  y=[self.panel_boundary[1], self.panel_boundary[1], self.panel_boundary[3], self.panel_boundary[3]],
                                  sharpness=2, outline='gray', fill='gray')
        self.buttons = RoundPolygon(self.canvas,
                                    x=[self.btn_boundary[0], self.btn_boundary[2], self.panel_boundary[2], self.btn_boundary[0]],
                                    y=[self.btn_boundary[1], self.btn_boundary[1], self.btn_boundary[3], self.btn_boundary[3]],
                                    sharpness=2, outline='gray', fill='gray')
        self.indicator = RoundPolygon(self.canvas,
                                      x=[self.indicator_boundary[0], self.indicator_boundary[2], self.indicator_boundary[2],
                                         self.indicator_boundary[0]],
                                      y=[self.indicator_boundary[1], self.indicator_boundary[1], self.indicator_boundary[3],
                                         self.indicator_boundary[3]],
                                      sharpness=2, outline='gray', fill='gray')

    def enable_yoko(self):
        self.state = 0
        self.canvas.delete(self.background.polygon)
        self.canvas.delete(self.panel.polygon)
        self.canvas.delete(self.buttons.polygon)
        self.canvas.delete(self.indicator.polygon)
        self.init_yoko()


    def start_yoko(self):
        self.state = 1
        self.canvas.delete(self.indicator.polygon)
        self.indicator = RoundPolygon(self.canvas,
                                      x=[self.indicator_boundary[0], self.indicator_boundary[2], self.indicator_boundary[2],
                                         self.indicator_boundary[0]],
                                      y=[self.indicator_boundary[1], self.indicator_boundary[1], self.indicator_boundary[3],
                                         self.indicator_boundary[3]],
                                      sharpness=2, outline='black', fill='blue')

    def stop_yoko(self):
        self.state = 0
        self.canvas.delete(self.indicator.polygon)
        self.indicator = RoundPolygon(self.canvas,
                                      x=[self.indicator_boundary[0], self.indicator_boundary[2], self.indicator_boundary[2],
                                         self.indicator_boundary[0]],
                                      y=[self.indicator_boundary[1], self.indicator_boundary[1], self.indicator_boundary[3],
                                         self.indicator_boundary[3]],
                                      sharpness=2, outline='black', fill='black')


class BRK:

    def __init__(
            self,
            canvas: tk.Canvas,
            width,
            height,
            motor='ASI'
    ):
        self.canvas = canvas
        self.start = False
        self.direction = 0 # 0 - stopped | 1 - positive RPM | -1 - negative RPM
        self.width = width
        self.height = height
        self.x_gap = 300
        self.boundary = 5 + self.x_gap, 25, 35 + self.x_gap, 75
        self.motor_type = motor
        self.create_brake()
        self.background = self.canvas.create_oval(self.boundary, fill='white')
        self.indicator_offset = 0
        self.indicator_color = 'gray'
        self.init_phase_cables()
        self.create_indicator()
        self.handler = None

    def create_brake(self):
        # brake
        self.canvas.create_rectangle(15 + self.x_gap, 5, 55 + self.x_gap, self.height - 5, outline='black')
        self.canvas.create_line(55 + self.x_gap, 5, self.width - 5 + self.x_gap, 10, fill='black')
        self.canvas.create_line(55 + self.x_gap,
                                self.height - 5,
                                self.width - 5 + self.x_gap,
                                self.height - 10, fill='black')

        # shaft
        self.canvas.create_arc(self.boundary[0] + 10, self.boundary[1], self.boundary[2] + 10, self.boundary[3],
                               fill='white', outline='black', start=-90, extent=180, style='arc')
        self.canvas.create_line(20 + self.x_gap, 25, 35 + self.x_gap, 25, fill='black')
        self.canvas.create_line(20 + self.x_gap, 75, 35 + self.x_gap, 75, fill='black')
        self.canvas.create_text(70 + self.x_gap, 50, text='BRK',
                                angle=90, font='TKDefaultFont 15 bold')

    def init_phase_cables(self):
        self.connector = {
            'U': self.canvas.create_line(0.25 * self.width + self.x_gap, 0.9 * self.height,
                                         0.25 * self.width + self.x_gap, self.height,
                                         width=5, fill='green'),
            'V': self.canvas.create_line(0.35 * self.width + self.x_gap, 0.9 * self.height,
                                         0.35 * self.width + self.x_gap, self.height,
                                         width=5, fill='yellow'),
            'W': self.canvas.create_line(0.45 * self.width + self.x_gap, 0.9 * self.height,
                                         0.45 * self.width + self.x_gap, self.height,
                                         width=5, fill='blue')
        }

    def create_indicator(self):
        self.indicator = {}
        for i in range(8):
            self.indicator[i] = self.canvas.create_arc(self.boundary, start=i * 45 + self.indicator_offset,
                                                       extent=30, fill=self.indicator_color, outline='')

    def update_indicator(self):
        for i in range(8):
            self.canvas.delete(self.indicator[i])
            self.indicator[i] = self.canvas.create_arc(self.boundary, start=i * 45 + self.indicator_offset,
                                                       extent=30, fill=self.indicator_color, outline='')

    def motoring(self):
        def action():
            if self.direction == 0:
                pass
            elif self.direction > 0:
                self.indicator_offset += 15
            elif self.direction < 0:
                self.indicator_offset -= 15
            self.update_indicator()

        while self.start:
            self.canvas.update()
            self.canvas.after(100, action)
            sleep(ANIMATION_INTERVAL)

    def start_motor(self):
        if not self.start:
            self.start = True
            self.handler = Thread(target=self.motoring)
            self.handler.start()

    def stop_motor(self):
        if self.start:
            self.start = False
            self.handler = None

    def update_direction(self, d):
        self.direction = d

    def update_color(self, color):
        self.indicator_color = color


class Controller:

    def __init__(
            self,
            canvas: tk.Canvas,
            width,
            height,
            name,
            side='DUT'
    ):
        self.canvas = canvas
        self.name = name
        self.side = side
        self.width = width
        self.height = height
        if self.side == 'DUT':
            self.x_gap = 0
        else:
            self.x_gap = 300
        self.boundary = 5 + self.x_gap, 105, width - 5 + self.x_gap, height + 95
        self.gui = {}
        self.create_controller()

    def create_controller(self):
        if self.name == 'BAC2000':
            self.gui['background'] = self.canvas.create_rectangle(
                self.boundary[0] + 20, self.boundary[1] + 40, self.boundary[2] - 20, self.boundary[3],
                outline='orange', fill='orange')
            self.gui['left'] = self.canvas.create_rectangle(
                self.boundary[0] + 5, self.boundary[1] + 40, self.boundary[0] + 20, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['right'] = self.canvas.create_rectangle(
                self.boundary[2] - 20, self.boundary[1] + 40, self.boundary[2] - 5, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['7-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                             x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                self.boundary[2] - 8, self.boundary[2] - 18],
                                             y=[self.boundary[1] + 45, self.boundary[1] + 45,
                                                self.boundary[1] + 45 + 0.1 * self.height, self.boundary[1] + 45 + 0.1 * self.height],
                                             outline='black', fill='#0f0fff')
            self.gui['16-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                              x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                 self.boundary[2] - 8, self.boundary[2] - 18],
                                              y=[self.boundary[1] + 50 + 0.1 * self.height, self.boundary[1] + 50 + 0.1 * self.height,
                                                 self.boundary[1] + 50 + 0.35 * self.height, self.boundary[1] + 50 + 0.35 * self.height],
                                              outline='black', fill='#0f0fff')
            self.gui['divider'] = []
            gap = (self.boundary[2] - self.boundary[0] - 50) / 5
            for i in range(4):
                self.gui['divider'].append(self.canvas.create_line(self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 45,
                                                                   self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 60,
                                                                   fill='black'))
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5, 0.25 * self.width, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 20,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5, 0.5 * self.width, self.boundary[1] + 55,
                                                        fill='yellow', width=5)]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width + 3, self.boundary[1] + 20,
                                            self.boundary[0] + 18 + gap * 5, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 70, anchor='n', text='2000')
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 25,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                           self.boundary[0] + 23 + gap * 3, self.boundary[1] + 20,
                                           fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 3, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 3, self.boundary[1] + 55,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[0] + 23 + gap * 5, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 15,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 70, anchor='n', text='2000')
        elif self.name == 'BAC4000':
            self.gui['background'] = self.canvas.create_rectangle(
                self.boundary[0] + 20, self.boundary[1] + 40, self.boundary[2] - 20, self.boundary[3],
                outline='orange', fill='orange')
            self.gui['left'] = self.canvas.create_rectangle(
                self.boundary[0] + 5, self.boundary[1] + 40, self.boundary[0] + 20, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['right'] = self.canvas.create_rectangle(
                self.boundary[2] - 20, self.boundary[1] + 40, self.boundary[2] - 5, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['7-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                             x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                self.boundary[2] - 8, self.boundary[2] - 18],
                                             y=[self.boundary[1] + 45, self.boundary[1] + 45,
                                                self.boundary[1] + 45 + 0.1 * self.height, self.boundary[1] + 45 + 0.1 * self.height],
                                             outline='black', fill='#0f0fff')
            self.gui['16-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                              x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                 self.boundary[2] - 8, self.boundary[2] - 18],
                                              y=[self.boundary[1] + 50 + 0.1 * self.height, self.boundary[1] + 50 + 0.1 * self.height,
                                                 self.boundary[1] + 50 + 0.35 * self.height, self.boundary[1] + 50 + 0.35 * self.height],
                                              outline='black', fill='#0f0fff')
            self.gui['divider'] = []
            gap = (self.boundary[2] - self.boundary[0] - 50) / 5
            for i in range(4):
                self.gui['divider'].append(self.canvas.create_line(self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 45,
                                                                   self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 60,
                                                                   fill='black'))
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5, 0.25 * self.width, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 20,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5, 0.5 * self.width, self.boundary[1] + 55,
                                                         fill='yellow', width=5)]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width + 3, self.boundary[1] + 20,
                                            self.boundary[0] + 18 + gap * 5, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 70, anchor='n', text='4000')
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 25,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.boundary[0] + 23 + gap * 3, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 3, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 3, self.boundary[1] + 55,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[0] + 23 + gap * 5, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 15,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 70, anchor='n', text='4000')
        elif self.name == 'BAC3000':
            self.gui['background'] = self.canvas.create_rectangle(
                self.boundary[0] + 20, self.boundary[1] + 40, self.boundary[2] - 20, self.boundary[3],
                outline='orange', fill='orange')
            self.gui['left'] = self.canvas.create_rectangle(
                self.boundary[0] + 5, self.boundary[1] + 40, self.boundary[0] + 20, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['right'] = self.canvas.create_rectangle(
                self.boundary[2] - 20, self.boundary[1] + 40, self.boundary[2] - 5, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['7-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                             x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                self.boundary[2] - 8, self.boundary[2] - 18],
                                             y=[self.boundary[1] + 45, self.boundary[1] + 45,
                                                self.boundary[1] + 45 + 0.1 * self.height, self.boundary[1] + 45 + 0.1 * self.height],
                                             outline='black', fill='#0f0fff')
            self.gui['16-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                              x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                 self.boundary[2] - 8, self.boundary[2] - 18],
                                              y=[self.boundary[1] + 50 + 0.1 * self.height, self.boundary[1] + 50 + 0.1 * self.height,
                                                 self.boundary[1] + 50 + 0.35 * self.height, self.boundary[1] + 50 + 0.35 * self.height],
                                              outline='black', fill='#0f0fff')
            self.gui['divider'] = []
            gap = (self.boundary[2] - self.boundary[0] - 50) / 5
            for i in range(4):
                self.gui['divider'].append(self.canvas.create_line(self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 45,
                                                                   self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 60,
                                                                   fill='black'))
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5, 0.25 * self.width, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 20,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5, 0.5 * self.width, self.boundary[1] + 55,
                                                         fill='yellow', width=5)]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width + 3, self.boundary[1] + 20,
                                            self.boundary[0] + 18 + gap * 5, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 70, anchor='n', text='3000')
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 25,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.boundary[0] + 23 + gap * 3, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 3, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 3, self.boundary[1] + 55,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[0] + 23 + gap * 5, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 15,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 70, anchor='n', text='3000')
        elif self.name == 'BAC8000':
            self.gui['background'] = self.canvas.create_rectangle(
                self.boundary[0] + 20, self.boundary[1] + 40, self.boundary[2] - 20, self.boundary[3],
                outline='orange', fill='orange')
            self.gui['left'] = self.canvas.create_rectangle(
                self.boundary[0] + 5, self.boundary[1] + 40, self.boundary[0] + 20, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['right'] = self.canvas.create_rectangle(
                self.boundary[2] - 20, self.boundary[1] + 40, self.boundary[2] - 5, self.boundary[3],
                outline='#0f0fff', fill='#0f0fff')
            self.gui['7-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                             x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                self.boundary[2] - 8, self.boundary[2] - 18],
                                             y=[self.boundary[1] + 45, self.boundary[1] + 45,
                                                self.boundary[1] + 45 + 0.1 * self.height, self.boundary[1] + 45 + 0.1 * self.height],
                                             outline='black', fill='#0f0fff')
            self.gui['16-pin'] = RoundPolygon(master=self.canvas, sharpness=2,
                                              x=[self.boundary[2] - 18, self.boundary[2] - 8,
                                                 self.boundary[2] - 8, self.boundary[2] - 18],
                                              y=[self.boundary[1] + 50 + 0.1 * self.height, self.boundary[1] + 50 + 0.1 * self.height,
                                                 self.boundary[1] + 50 + 0.35 * self.height, self.boundary[1] + 50 + 0.35 * self.height],
                                              outline='black', fill='#0f0fff')
            self.gui['divider'] = []
            gap = (self.boundary[2] - self.boundary[0] - 50) / 5
            for i in range(4):
                self.gui['divider'].append(self.canvas.create_line(self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 45,
                                                                   self.boundary[0] + 25 + gap * (i + 1), self.boundary[1] + 60,
                                                                   fill='black'))
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5, 0.25 * self.width, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 20,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5, 0.5 * self.width, self.boundary[1] + 55,
                                                         fill='yellow', width=5)]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width + 3, self.boundary[1] + 20,
                                            self.boundary[0] + 18 + gap * 5, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 70, anchor='n', text='8000')
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 25 + gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 22 + gap, self.boundary[1] + 25,
                                            self.boundary[0] + 22 + gap, self.boundary[1] + 55,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.boundary[0] + 23 + gap * 3, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 3, self.boundary[1] + 20,
                                            self.boundary[0] + 20 + gap * 3, self.boundary[1] + 55,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[0] + 23 + gap * 5, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 20 + gap * 5, self.boundary[1] + 15,
                                            self.boundary[0] + 20 + gap * 5, self.boundary[1] + 55,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 70, anchor='n', text='8000')
        elif self.name == 'BAC355':
            self.gui['background'] = self.canvas.create_polygon(
                self.boundary[0], self.boundary[1] + 70,
                self.boundary[0], self.boundary[3],
                self.boundary[2], self.boundary[3],
                self.boundary[2], self.boundary[1] + 40,
                self.boundary[0] + 30, self.boundary[1] + 40,
                outline='black', fill='black')
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5,
                                            0.25 * self.width, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 25,
                                            self.boundary[0] + 48, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 45, self.boundary[1] + 25,
                                            self.boundary[0] + 45, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5,
                                            0.5 * self.width, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.5 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 63, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 60, self.boundary[1] + 20,
                                            self.boundary[0] + 60, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 78, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 75, self.boundary[1] + 20,
                                            self.boundary[0] + 75, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 60, anchor='n', text='355', fill='white')
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 48, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 45, self.boundary[1] + 25,
                                            self.boundary[0] + 45, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.boundary[0] + 63, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 60, self.boundary[1] + 20,
                                            self.boundary[0] + 60, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[0] + 78, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 75, self.boundary[1] + 15,
                                            self.boundary[0] + 75, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 60,
                                                           anchor='n', text='355', fill='white')
        elif self.name == 'BAC555':
            self.gui['background'] = self.canvas.create_polygon(
                self.boundary[0], self.boundary[1] + 70,
                self.boundary[0], self.boundary[3],
                self.boundary[2], self.boundary[3],
                self.boundary[2], self.boundary[1] + 40,
                self.boundary[0] + 30, self.boundary[1] + 40,
                outline='black', fill='black')
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5,
                                            0.25 * self.width, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 25,
                                            self.boundary[0] + 48, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 45, self.boundary[1] + 25,
                                            self.boundary[0] + 45, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5,
                                            0.5 * self.width, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.5 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 63, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 60, self.boundary[1] + 20,
                                            self.boundary[0] + 60, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 78, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 75, self.boundary[1] + 20,
                                            self.boundary[0] + 75, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 60, anchor='n', text='555', fill='white')
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 48, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 45, self.boundary[1] + 25,
                                            self.boundary[0] + 45, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.boundary[0] + 63, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 60, self.boundary[1] + 20,
                                            self.boundary[0] + 60, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[0] + 78, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 75, self.boundary[1] + 15,
                                            self.boundary[0] + 75, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 60,
                                                           anchor='n', text='555', fill='white')
        elif self.name == 'BAC855':
            self.gui['background'] = self.canvas.create_polygon(
                self.boundary[0], self.boundary[1] + 70,
                self.boundary[0], self.boundary[3],
                self.boundary[2], self.boundary[3],
                self.boundary[2], self.boundary[1] + 40,
                self.boundary[0] + 30, self.boundary[1] + 40,
                outline='black', fill='green')
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5,
                                            0.25 * self.width, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 25,
                                            self.boundary[0] + 48, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 45, self.boundary[1] + 25,
                                            self.boundary[0] + 45, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5,
                                            0.5 * self.width, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.5 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 63, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 60, self.boundary[1] + 20,
                                            self.boundary[0] + 60, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 78, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 75, self.boundary[1] + 20,
                                            self.boundary[0] + 75, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 60, anchor='n', text='855', fill='black')
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 48, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 45, self.boundary[1] + 25,
                                            self.boundary[0] + 45, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.boundary[0] + 63, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.boundary[0] + 60, self.boundary[1] + 20,
                                            self.boundary[0] + 60, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[0] + 78, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[0] + 75, self.boundary[1] + 15,
                                            self.boundary[0] + 75, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 60,
                                                           anchor='n', text='855', fill='black')
        elif self.name == '2B':
            self.gui['background'] = self.canvas.create_rectangle(
                self.boundary[0] + 0.35 * self.width, self.boundary[1] + 40,
                self.boundary[2] - 0.35 * self.width, self.boundary[3],
                outline='black', fill='blue')
            if self.side == 'DUT':
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width, self.boundary[1] - 5,
                                            0.25 * self.width, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2, self.boundary[1] + 20,
                                            self.boundary[0] + 0.4 * self.width + 3, self.boundary[1] + 20,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 0.4 * self.width, self.boundary[1] + 20,
                                            self.boundary[0] + 0.4 * self.width, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.5 * self.width, self.boundary[1] - 5,
                                            0.5 * self.width, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.75 * self.width, self.boundary[1] - 5, 0.75 * self.width, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.75 * self.width + 3, self.boundary[1] + 20,
                                            self.boundary[2] - 0.4 * self.width - 2, self.boundary[1] + 20,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[2] - 0.4 * self.width, self.boundary[1] + 20,
                                            self.boundary[2] - 0.4 * self.width, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 60,
                                                           anchor='center', text='2B', fill='white', angle=270)
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 0.4 * self.width + 3, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 0.4 * self.width, self.boundary[1] + 25,
                                            self.boundary[0] + 0.4 * self.width, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.x_gap + 0.5 * self.width + 3, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.x_gap + 0.5 * self.width, self.boundary[1] + 20,
                                            self.x_gap + 0.5 * self.width, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[2] - 0.4 * self.width + 3, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[2] - 0.4 * self.width, self.boundary[1] + 15,
                                            self.boundary[2] - 0.4 * self.width, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 60,
                                                           anchor='center', text='2B', fill='white', angle=270)
        elif self.name == 'ABB':
            self.gui['background'] = self.canvas.create_rectangle(
                self.boundary[0] + 0.25 * self.width, self.boundary[1] + 40,
                self.boundary[2] - 0.25 * self.width, self.boundary[3],
                outline='black', fill='#f0f0f0', width=2)
            if self.side == 'DUT':
                self.gui['name'] = self.canvas.create_text(0.5 * self.width, self.boundary[1] + 60,
                                                           anchor='center', text='ABB', fill='white', angle=270)
            else:
                self.gui['U'] = [
                    self.canvas.create_line(0.25 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.25 * self.width + self.x_gap, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(0.25 * self.width - 2 + self.x_gap, self.boundary[1] + 25,
                                            self.boundary[0] + 0.4 * self.width + 3, self.boundary[1] + 25,
                                            fill='green', width=5),
                    self.canvas.create_line(self.boundary[0] + 0.4 * self.width, self.boundary[1] + 25,
                                            self.boundary[0] + 0.4 * self.width, self.boundary[1] + 40,
                                            fill='green', width=5)
                ]
                self.gui['V'] = [
                    self.canvas.create_line(0.35 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.35 * self.width + self.x_gap, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(0.35 * self.width - 2 + self.x_gap, self.boundary[1] + 20,
                                            self.x_gap + 0.5 * self.width + 3, self.boundary[1] + 20,
                                            fill='yellow', width=5),
                    self.canvas.create_line(self.x_gap + 0.5 * self.width, self.boundary[1] + 20,
                                            self.x_gap + 0.5 * self.width, self.boundary[1] + 40,
                                            fill='yellow', width=5)
                ]
                self.gui['W'] = [
                    self.canvas.create_line(0.45 * self.width + self.x_gap, self.boundary[1] - 5,
                                            0.45 * self.width + self.x_gap, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(0.45 * self.width - 2 + self.x_gap, self.boundary[1] + 15,
                                            self.boundary[2] - 0.4 * self.width + 3, self.boundary[1] + 15,
                                            fill='blue', width=5),
                    self.canvas.create_line(self.boundary[2] - 0.4 * self.width, self.boundary[1] + 15,
                                            self.boundary[2] - 0.4 * self.width, self.boundary[1] + 40,
                                            fill='blue', width=5)
                ]
                self.gui['name'] = self.canvas.create_text(0.5 * self.width + self.x_gap, self.boundary[1] + 60,
                                                           anchor='center', text='ABB', fill='black')
        else:
            pass

    def reset_controller(self):
        for i in self.gui:
            if isinstance(self.gui[i], list):
                for j in self.gui[i]:
                    try:
                        self.canvas.delete(j)
                    except IndexError:
                        logging.error(f'Failed to reset {j}')
            elif isinstance(self.gui[i], RoundPolygon):
                self.gui[i].canvas.delete(self.gui[i].polygon)
            else:
                self.canvas.delete(self.gui[i])
        self.create_controller()

    def update_device(self, name, side=None):
        self.name = name
        if side:
            self.side = side
        if self.side == 'DUT':
            self.x_gap = 0
        else:
            self.x_gap = 300
        self.boundary = 5 + self.x_gap, 105, self.width - 5 + self.x_gap, self.height + 95
        self.reset_controller()


class DynoSet:

    def __init__(
            self,
            canvas: tk.Canvas,
            dut='',
            brk=''
    ):
        self.canvas = canvas
        self.dut = DUT(canvas, 100, 100)
        self.yoko = YOKO(canvas, 100, 100)
        self.brk = BRK(canvas, 100, 100)
        self.dut_controller = Controller(canvas, 100, 100, dut, 'DUT')
        self.brk_controller = Controller(canvas, 100, 100, brk, 'BRK')

    def start(self):
        self.dut.start_motor()
        if self.yoko.state != -1:
            self.yoko.start_yoko()
        self.brk.start_motor()

    def stop(self):
        self.dut.stop_motor()
        if self.yoko.state != -1:
            self.yoko.stop_yoko()
        self.brk.stop_motor()


class ASISpinBox:

    def __init__(self, master, textvariable, width=50, **kwargs):
        self.master = master
        self.container = Frame(self.master, width=width,
                               background=kwargs['background'] if 'background' in kwargs.keys() else "white")
        self.textvariable = textvariable
        self.width = width
        self.entry = Entry(self.container, textvariable=self.textvariable, width=self.width-30,
                           font='TkDefaultFont 18 bold')
        self.entry.grid(column=0, row=0, rowspan=2, sticky='news')
        self.up = Button(self.container, command=lambda: self.inc_torque(0.5), text='+0.5', width=4)
        self.up.grid(column=3, row=0, sticky='news')
        self.down = Button(self.container, command=lambda: self.dec_torque(0.5), text='-0.5', width=4)
        self.down.grid(column=3, row=1, sticky='news')
        self.up_1 = Button(self.container, command=lambda: self.inc_torque(1), text='+1', width=3)
        self.up_1.grid(column=2, row=0, sticky='news')
        self.down_1 = Button(self.container, command=lambda: self.dec_torque(1), text='-1', width=3)
        self.down_1.grid(column=2, row=1, sticky='news')
        self.up_5 = Button(self.container, command=lambda: self.inc_torque(5), text='+5', width=3)
        self.up_5.grid(column=1, row=0, sticky='news')
        self.down_5 = Button(self.container, command=lambda: self.dec_torque(5), text='-5', width=3)
        self.down_5.grid(column=1, row=1, sticky='news')
        self.reset = ASIIcons(self.container, size=30, item='reset', **kwargs)
        self.reset.canvas.bind('<Button-1>', self.zero_torque)
        self.reset.canvas.grid(column=4, row=0, rowspan=2, sticky='ew')

    def inc_torque(self, value):
        prev = self.textvariable.get()
        self.textvariable.set(prev + value)

    def dec_torque(self, value):
        prev = self.textvariable.get()
        self.textvariable.set(prev - value)

    def zero_torque(self, event):
        self.textvariable.set(0.0)


class ASIStatusIndicator:

    def __init__(
            self,
            master,
            device,
            status=False,
            size=20,
            padding=2
    ):
        self.master = master
        self.device = device
        self.size = size
        self.status = status
        self.padding = padding
        if self.device == 'DUT':
            self.background = '#ccccff'
        elif self.device == 'BRK':
            self.background = '#ccffcc'
        else:
            self.background = '#ffffcc'
        self.canvas = Canvas(self.master, width=self.size, height=self.size,
                             background=self.background, borderwidth=0,
                             highlightthickness=0, relief='flat')
        self.indicator = self.canvas.create_oval(self.padding, self.padding,
                                                 self.size - self.padding, self.size - self.padding,
                                                 outline='', fill=f"{'green' if self.status else 'red'}")

    def update_status(self):
        self.canvas.delete(self.indicator)
        self.indicator = self.canvas.create_oval(self.padding, self.padding,
                                                 self.size - self.padding, self.size - self.padding,
                                                 outline='', fill=f"{'green' if self.status else 'red'}")


class ASIStopButton:

    def __init__(self, master, size=50, *args, **kwargs):
        self.master = master
        self.size = size
        self.canvas = Canvas(self.master, width=self.size, height=self.size,
                             background='red', borderwidth=0,
                             highlightthickness=0, relief='flat', *args, **kwargs)
        self.canvas.bind("<Enter>", self.check_hand_enter)
        self.canvas.bind("<Leave>", self.check_hand_leave)
        try:
            self.canvas.pack()
        except TclError:
            pass
        self.background = {'nw': self.canvas.create_polygon(0, 0, self.size * 0.25, 0, 0, self.size * 0.25,
                                                            fill='white', outline='', tags='background'),
                           'ne': self.canvas.create_polygon(self.size * 0.75, 0, self.size, 0, self.size, self.size * 0.25,
                                                            fill='white', outline='', tags='background'),
                           'sw': self.canvas.create_polygon(self.size, self.size * 0.75, self.size, self.size, self.size * 0.75, self.size,
                                                            fill='white', outline='', tags='background'),
                           'se': self.canvas.create_polygon(0, self.size, self.size * 0.25, self.size, 0, self.size * 0.75,
                                                            fill='white', outline='', tags='background')}
        self.text = self.canvas.create_text(self.size * 0.5, self.size * 0.5, text='STOP', fill='white',
                                            anchor='center', justify='center',
                                            font=f'TkDefaultFont {int(self.size * 0.2)} bold')

        # self.canvas.tag_bind('background', '<Enter>', lambda event: self.check_hand_enter())
        # self.canvas.tag_bind('background', '<Leave>', lambda event: self.check_hand_leave())

    def check_hand_enter(self, event=None):
        self.canvas.config(cursor="target")

    def check_hand_leave(self, event=None):
        self.canvas.config(cursor="")


class ASIIcons:

    def __init__(
            self,
            master,
            size=20,
            item='graph',
            background='white',
            foreground='black',
            width=1,
            *args,
            **kwargs):
        self.master = master
        self.size = size
        self.item = item
        self.width = width
        self.background = background
        self.foreground = foreground
        self.canvas = Canvas(self.master, width=self.size, height=self.size, borderwidth=0, background=background,
                             highlightthickness=0, relief='flat', *args, **kwargs)
        self.draw()

    def reset(self, background, foreground):
        self.background = background
        self.foreground = foreground
        for i in self.content:
            self.canvas.delete(i)
        self.draw()

    def draw(self):
        if self.item == 'graph':
            self.content = [
                self.canvas.create_line((0, 0,
                                         0, self.size - 1,
                                         self.size, self.size - 1),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0, self.size * 0.5,
                                         self.size, self.size * 0.5),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0, self.size * 0.2,
                                         self.size * 0.3, self.size * 0.8,
                                         self.size, self.size * 0.3),
                                        fill=self.foreground, width=self.width)
            ]

        elif self.item == 'grid':
            self.content = [
                self.canvas.create_rectangle(self.size * 0.15, self.size * 0.15,
                                             self.size * 0.45, self.size * 0.45,
                                             fill=self.background, outline=self.foreground,
                                             width=self.width),
                self.canvas.create_rectangle(self.size * 0.55, self.size * 0.15,
                                             self.size * 0.85, self.size * 0.45,
                                             fill=self.background, outline=self.foreground,
                                             width=self.width),
                self.canvas.create_rectangle(self.size * 0.15, self.size * 0.55,
                                             self.size * 0.45, self.size * 0.85,
                                             fill=self.background, outline=self.foreground,
                                             width=self.width)
            ]

        elif self.item == 'list':
            self.content = [
                self.canvas.create_line((0.1 * self.size, 0.2 * self.size,
                                         0.9 * self.size, 0.2 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.1 * self.size, 0.5 * self.size,
                                         0.9 * self.size, 0.5 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.1 * self.size, 0.8 * self.size,
                                         0.9 * self.size, 0.8 * self.size),
                                        fill=self.foreground, width=self.width)
            ]

        elif self.item == 'faults':
            self.content = [
                self.canvas.create_line((self.size * 0.5, self.size * 0.1,
                                         self.size * 0.1, self.size * 0.9,
                                         self.size * 0.9, self.size * 0.9,
                                         self.size * 0.5, self.size * 0.1),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.5 * self.size, 0.4 * self.size,
                                         0.5 * self.size, 0.75 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_oval((0.5 * self.size, 0.8 * self.size,
                                         0.5 * self.size, 0.81 * self.size),
                                        fill=self.foreground, outline=self.foreground,
                                        width=self.width)
            ]

        elif self.item == 'home':
            self.content = [
                self.canvas.create_line((0, self.size * 0.6,
                                         self.size * 0.5, self.size * 0.1,
                                         self.size, self.size * 0.6),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((self.size * 0.25, self.size * 0.38,
                                         self.size * 0.25, self.size * 0.85,
                                         self.size * 0.75, self.size * 0.85,
                                         self.size * 0.75, self.size * 0.38),
                                        fill=self.foreground, width=self.width)
            ]

        elif self.item == 'test':
            self.content = [
                self.canvas.create_rectangle(self.size * 0.15, self.size * 0.10,
                                             self.size * 0.85, self.size * 0.90,
                                             fill=self.background, outline=self.foreground,
                                             width=self.width),
                self.canvas.create_line((self.size * 0.25, self.size * 0.25,
                                         self.size * 0.8, self.size * 0.25),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((self.size * 0.25, self.size * 0.5,
                                         self.size * 0.4, self.size * 0.5),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((self.size * 0.25, self.size * 0.75,
                                         self.size * 0.4, self.size * 0.75),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((self.size * 0.55, self.size * 0.7,
                                         self.size * 0.65, self.size * 0.8,
                                         self.size * 0.8, self.size * 0.5),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'temp':
            self.content = [
                self.canvas.create_arc((0.3 * self.size, 0.5 * self.size,
                                        0.7 * self.size, 0.9 * self.size),
                                       start=-250, extent=320, style='chord',
                                       outline=self.foreground, width=self.width),
                self.canvas.create_rectangle((0.4 * self.size, 0.2 * self.size,
                                              0.6 * self.size, 0.6 * self.size),
                                             outline=self.background, fill=self.background,
                                             width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.15 * self.size,
                                         0.4 * self.size, 0.55 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.6 * self.size, 0.15 * self.size,
                                         0.6 * self.size, 0.55 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.25 * self.size,
                                         0.5 * self.size, 0.25 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.35 * self.size,
                                         0.5 * self.size, 0.35 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.45 * self.size,
                                         0.5 * self.size, 0.45 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'lightning bolt':
            self.content = [
                self.canvas.create_line((0.7 * self.size, 0.1 * self.size,
                                         0.3 * self.size, 0.45 * self.size,
                                         0.5 * self.size, 0.55 * self.size,
                                         0.3 * self.size, 0.9 * self.size,
                                         0.7 * self.size, 0.55 * self.size,
                                         0.5 * self.size, 0.45 * self.size,
                                         0.7 * self.size, 0.1 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'nut':
            self.content = [
                self.canvas.create_polygon((0.5 * self.size, 0.1 * self.size,
                                            0.16 * self.size, 0.3 * self.size,
                                            0.16 * self.size, 0.7 * self.size,
                                            0.5 * self.size, 0.9 * self.size,
                                            0.84 * self.size, 0.7 * self.size,
                                            0.84 * self.size, 0.3 * self.size),
                                           fill=self.background, outline=self.foreground,
                                           width=self.width),
                self.canvas.create_oval((0.3 * self.size, 0.3 * self.size,
                                         0.7 * self.size, 0.7 * self.size),
                                        fill=self.background, outline=self.foreground,
                                        width=self.width)
            ]

        elif self.item == 'dyno':
            self.content = [
                self.canvas.create_rectangle((0.1 * self.size, 0.1 * self.size,
                                              0.3 * self.size, 0.9 * self.size),
                                             fill=self.background, outline=self.foreground,
                                             width=self.width),
                self.canvas.create_rectangle((0.3 * self.size, 0.4 * self.size,
                                              0.7 * self.size, 0.6 * self.size),
                                             fill=self.background, outline=self.foreground,
                                             width=self.width),
                self.canvas.create_rectangle((0.7 * self.size, 0.1 * self.size,
                                              0.9 * self.size, 0.9 * self.size),
                                             fill=self.background, outline=self.foreground,
                                             width=self.width),
                self.canvas.create_line((0.55 * self.size, 0.525 * self.size,
                                         0.7 * self.size, 0.525 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.45 * self.size, 0.55 * self.size,
                                         0.7 * self.size, 0.55 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.35 * self.size, 0.575 * self.size,
                                         0.7 * self.size, 0.575 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'top':
            self.content = [
                self.canvas.create_line((0.1 * self.size, 0.1 * self.size,
                                         0.9 * self.size, 0.1 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.4 * self.size,
                                         0.5 * self.size, 0.1 * self.size,
                                         0.6 * self.size, 0.4 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.5 * self.size, 0.1 * self.size,
                                         0.5 * self.size, 0.9 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'bottom':
            self.content = [
                self.canvas.create_line((0.1 * self.size, 0.9 * self.size,
                                         0.9 * self.size, 0.9 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.6 * self.size,
                                         0.5 * self.size, 0.9 * self.size,
                                         0.6 * self.size, 0.6 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.5 * self.size, 0.1 * self.size,
                                         0.5 * self.size, 0.9 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'tblimit':
            self.content = [
                self.canvas.create_line((0.1 * self.size, 0.1 * self.size,
                                         0.9 * self.size, 0.1 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.4 * self.size,
                                         0.5 * self.size, 0.1 * self.size,
                                         0.6 * self.size, 0.4 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.4 * self.size, 0.6 * self.size,
                                         0.5 * self.size, 0.9 * self.size,
                                         0.6 * self.size, 0.6 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.1 * self.size, 0.9 * self.size,
                                         0.9 * self.size, 0.9 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.5 * self.size, 0.1 * self.size,
                                         0.5 * self.size, 0.9 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'eta':
            self.content = [
                self.canvas.create_text((0.5 * self.size, 0.35 * self.size),
                                        fill=self.foreground, text=f'\u03B7',
                                        anchor='center', justify='center',
                                        font=f'segoe {int(0.7 * self.size)}',
                                        width=self.width),
            ]

        elif self.item == 'RPMTorque':
            self.content = [
                self.canvas.create_text((0.5 * self.size, 0.3 * self.size),
                                        fill=self.foreground, text=f'RPM',
                                        anchor='center', justify='center',
                                        font=f'segoe {int(0.25 * self.size)}'),
                self.canvas.create_text((0.5 * self.size, 0.6 * self.size),
                                        fill=self.foreground, text=f'Torque',
                                        anchor='center', justify='center',
                                        font=f'segoe {int(0.25 * self.size)}'),
            ]

        elif self.item == 'reset':
            self.content = [
                self.canvas.create_arc((0.2 * self.size, 0.2 * self.size,
                                        0.8 * self.size, 0.8 * self.size),
                                       start=0, extent=320, style='arc',
                                       fill=self.background, outline=self.foreground,
                                       width=self.width),
                self.canvas.create_line((0.8 * self.size, 0.5 * self.size,
                                         0.85 * self.size, 0.35 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.8 * self.size, 0.5 * self.size,
                                         0.65 * self.size, 0.38 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'check':
            self.content = [
                self.canvas.create_oval((0.2 * self.size, 0.2 * self.size,
                                         0.8 * self.size, 0.8 * self.size),
                                        fill=self.background, outline=self.foreground),
                self.canvas.create_line((0.3 * self.size, 0.5 * self.size,
                                         0.45 * self.size, 0.65 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.45 * self.size, 0.65 * self.size,
                                         0.7 * self.size, 0.35 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'cross':
            self.content = [
                self.canvas.create_oval((0.2 * self.size, 0.2 * self.size,
                                         0.8 * self.size, 0.8 * self.size),
                                        fill=self.background, outline=self.foreground,
                                        width=self.width),
                self.canvas.create_line((0.35 * self.size, 0.35 * self.size,
                                         0.65 * self.size, 0.65 * self.size),
                                        fill=self.foreground, width=self.width),
                self.canvas.create_line((0.35 * self.size, 0.65 * self.size,
                                         0.65 * self.size, 0.35 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'popout':
            self.content = [
                self.canvas.create_rectangle((0.2 * self.size, 0.4 * self.size,
                                              0.65 * self.size, 0.8 * self.size),
                                             fill=self.background, width=self.width,
                                             outline=self.foreground),
                self.canvas.create_line((0.3 * self.size, 0.4 * self.size,
                                         0.3 * self.size, 0.2 * self.size,
                                         0.8 * self.size, 0.2 * self.size,
                                         0.8 * self.size, 0.7 * self.size,
                                         0.65 * self.size, 0.7 * self.size),
                                        fill=self.foreground, width=self.width),
            ]

        elif self.item == 'folder':
            self.content = [
                self.canvas.create_rectangle((0.2 * self.size, 0.3 * self.size,
                                              0.8 * self.size, 0.75 * self.size),
                                             fill=self.background, width=self.width,
                                             outline=self.foreground),
                self.canvas.create_line((0.2 * self.size, 0.3 * self.size,
                                         0.25 * self.size, 0.25 * self.size,
                                         0.4 * self.size, 0.25 * self.size,
                                         0.45 * self.size, 0.3 * self.size),
                                        fill=self.foreground, width=self.width),
            ]


class ASIFaultsIndicator:

    def __init__(self, master, textvariable, tree, indicator, width=50):
        self.master = master
        self.width = width
        self.height = width / 16
        self.container = Frame(self.master, width=width, height=self.height, background='white')
        for i in range(16):
            self.container.grid_columnconfigure(i, minsize=self.height)
        self.textvariable = textvariable
        self.indicator = indicator
        self._init_fault_descriptions(tree)
        self.lamps = []
        self.draw()

    def _init_fault_descriptions(self, tree):
        faults_xpath = "//ParameterDescription[Name='faults']//Description"
        faults2_xpath = "//ParameterDescription[Name='faults2']//Description"
        warnings_xpath = "//ParameterDescription[Name='warnings']//Description"
        warnings2_xpath = "//ParameterDescription[Name='warnings2']//Description"

        self.faults_parameters = {
                "faults": [description.text for description in tree.findall(faults_xpath)][::-1],
                "faults2": [description.text for description in tree.findall(faults2_xpath)][::-1],
                "warnings": [description.text for description in tree.findall(warnings_xpath)][::-1],
                "warnings2": [description.text for description in tree.findall(warnings2_xpath)][::-1]
            }

    def draw(self):
        for i in range(16):
            if (self.textvariable.get() & (1 << i)) >> i == 1:
                temp = Frame(self.container, width=self.height, height=self.height, background='red')
                # Label(temp, text=f"{15 - i}", background='red').grid()
            else:
                temp = Frame(self.container, width=self.height, height=self.height, background='green')
                # Label(temp, text=f"{15 - i}", background='green').grid()
            temp.grid(column=i, row=1, padx=1, sticky='news')
            self.master.update()
            ToolTip(temp, msg=self.faults_parameters[self.indicator][i + 1])
            # ToolTip(temp.children['!label'], msg=self.faults_parameters[self.indicator][i + 1])
            self.lamps.append(temp)

    def reset(self):
        for i, lamp in enumerate(self.lamps):
            if (self.textvariable.get() & (1 << i)) >> i == 1:
                self.lamps[15 - i].config(background='red')
                # self.lamps[15 - i].children['!label'].config(background='red')
            else:
                self.lamps[15 - i].config(background='green')
                # self.lamps[15 - i].children['!label'].config(background='green')
            # self.master.update()

    def update(self):
        self.reset()


if __name__ == '__main__':
    root = Tk()
    canvas = Canvas(root, width=400, height=300, background='white')
    canvas.pack()

    dut = DUT(canvas, 100, 100)
    yoko = YOKO(canvas, 100, 100)
    brk = BRK(canvas, 100, 100)
    dut_controller = Controller(canvas, 100, 100, 'BAC4000', 'DUT')
    brk_controller = Controller(canvas, 100, 100, 'ABB', 'BRK')
    direction = IntVar(value=1)
    fault = IntVar(value=1)

    def start():
        dut.start_motor()
        yoko.start_yoko()
        brk.start_motor()

    def stop():
        dut.stop_motor()
        yoko.stop_yoko()
        brk.stop_motor()

    def update():
        dut.update_direction(direction.get())
        brk.update_direction(direction.get())


    start_btn = Button(root, text='Start', command=start)
    start_btn.pack()
    stop_btn = Button(root, text='Stop', command=stop)
    stop_btn.pack()
    direction_entry = Entry(root, textvariable=direction)
    direction_entry.pack()
    update_btn = Button(root, text='Update', command=update)
    update_btn.pack()
    disable_btn = Button(root, text='Disable', command=yoko.disable_yoko)
    disable_btn.pack()
    enable_btn = Button(root, text='Enable', command=yoko.init_yoko)
    enable_btn.pack()
    temp = DoubleVar(value=0)
    spin = ASISpinBox(root, temp)
    spin.container.pack()
    stop = ASIStopButton(root)
    icon = ASIIcons(root, size=100, item='folder')
    icon.canvas.pack()


    root.mainloop()