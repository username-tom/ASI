import tkinter as tk
from tkinter import ttk
from dyno_v2.GUI.round_polygon import RoundPolygon
import logging
from threading import Thread
from time import sleep
from datetime import datetime



class OutputBubble:
    """Custom UI for output texts"""

    def __init__(self, master, logger, alpha=0.5, duration=5, log_level=logging.INFO, *args, **kwargs):
        """Constructor"""
        self.container = master
        self.alpha = alpha
        self.duration = duration
        self.logger = logger
        self.level = log_level
        self.canvas = tk.Canvas(self.container, background='')
        self.output = []
        self.handler = {}


    def write(self, string: str):
        """Overwrites write"""
        self.output.append(string)
        for line in string.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        """Overwrites flush"""


    def make_bubble(self, msg):
        bubble = RoundPolygon(self.canvas, )
        tk.Label(bubble, text=msg, anchor='center', background="black")
        self.handler[bubble] = Thread(target=self.bubble_handler, args=[bubble])
        self.handler[bubble].start()

    def bubble_handler(self, bubble):
        created = datetime.now()
        while (datetime.now() - created).total_seconds() < self.duration:
            sleep(1)
        for i in range(5):
            bubble.config(alpha=(4 - i) * 0.1)

