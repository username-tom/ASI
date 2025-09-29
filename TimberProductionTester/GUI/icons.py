from tkinter import Canvas

class ASIIcons:

    def __init__(
            self,
            master,
            size=20,
            item='check',
            background='white',
            foreground='black',
            width=2,
            *args,
            **kwargs):
        self.master = master
        self.size = size
        self.item = item
        self.width = width
        self.background = background
        self.foreground = foreground
        self.canvas = Canvas(self.master, width=self.size, height=self.size,
                             borderwidth=0, background=background,
                             highlightthickness=0, relief='flat',
                             *args, **kwargs)
        self.draw()

    def reset(self, item, background, foreground):
        self.background = background
        self.foreground = foreground
        self.item = item
        for i in self.content:
            self.canvas.delete(i)
        self.draw()

    def draw(self):
        if self.item == 'check':
            self.content = [
                self.canvas.create_oval((0.2 * self.size, 0.2 * self.size,
                                         0.8 * self.size, 0.8 * self.size),
                                        fill=self.background, outline=self.foreground, width=self.width),
                self.canvas.create_line((0.3 * self.size, 0.5 * self.size,
                                         0.45 * self.size, 0.65 * self.size), fill=self.foreground, width=self.width),
                self.canvas.create_line((0.45 * self.size, 0.65 * self.size,
                                         0.7 * self.size, 0.35 * self.size), fill=self.foreground, width=self.width),
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

