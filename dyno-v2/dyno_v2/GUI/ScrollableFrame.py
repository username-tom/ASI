import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, *args, **kwargs)
        # self.canvas.columnconfigure(0, weight=1)
        # self.canvas.rowconfigure(0, weight=1)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, *args, **kwargs)

        self.scrollable_frame.bind("<Configure>", self.on_canvas_config)

        self.content_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self.on_mousewheel)

        # self.canvas.pack(side="left", fill="both")
        # scrollbar.pack(side="right", fill="y")
        self.canvas.grid(column=0, row=0, sticky="news")
        scrollbar.grid(column=1, row=0, sticky='nse')

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_canvas_config(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.itemconfig(self.content_window, window=self.scrollable_frame)