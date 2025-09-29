import tkinter as tk
from tkinter import ttk
from threading import Thread
from time import sleep

class StatusBubble:

    def __init__(self, container, textvariable, label, shape, dims, threshold, *args, **kwargs):
        self.dims = dims
        self.text_variable = textvariable
        self.threshold = threshold
        self.label = label
        self.shape = shape
        self.canvas = tk.Canvas(container, width=dims[2], height=dims[3], background='#5DA01D', borderwidth=0,
                                highlightthickness=0, relief='flat', name=f'status_{label}')
        self.canvas.grid(column=0, row=0, sticky='news')
        if shape == 'oval':
            self.canvas.create_oval(dims[0], dims[1], dims[2], dims[3], outline='',
                               fill=f"{'green' if float(textvariable.get()) < threshold else 'red'}")
        elif shape == 'square':
            self.canvas.create_rectangle(dims[0], dims[1], dims[2], dims[3], outline='',
                                         fill=f"{'green' if float(textvariable.get()) < threshold else 'red'}")
        self.title_label = tk.Label(self.canvas, text=label, anchor='center',
                                    background=f"{'green' if float(textvariable.get()) < threshold else 'red'}")
        self.title_label.place(rely=0.3, relx=0.5, anchor='center')
        self.value_label = tk.Label(self.canvas, textvariable=textvariable, anchor='center',
                                    background=f"{'green' if float(textvariable.get()) < threshold else 'red'}",
                                    *args, **kwargs)
        self.value_label.place(rely=0.7, relx=0.5, anchor='center')
        self.updating = False
        self.update_thread = Thread(target=self._status_update)

    def _status_update(self):
        while self.updating:
            if self.shape == 'oval':
                self.canvas.create_oval(self.dims[0], self.dims[1], self.dims[2], self.dims[3], outline='',
                                        fill=f"{'green' if float(self.text_variable.get()) < self.threshold else 'red'}")
            elif self.shape == 'square':
                self.canvas.create_rectangle(self.dims[0], self.dims[1], self.dims[2], self.dims[3], outline='',
                                             fill=f"{'green' if float(self.text_variable.get()) < self.threshold else 'red'}")
            self.title_label.config(background=f"{'green' if float(self.text_variable.get()) < self.threshold else 'red'}")
            self.value_label.config(background=f"{'green' if float(self.text_variable.get()) < self.threshold else 'red'}")
            # self.value_label.grid(column=0, row=2, pady=[0, self.dims[3] * 0.1])
            sleep(1)

    def start(self):
        self.updating = True
        self.update_thread.start()

    def stop(self):
        self.updating = False
        self.update_thread = Thread(target=self._status_update)