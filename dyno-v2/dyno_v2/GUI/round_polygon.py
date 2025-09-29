from tkinter import *


class RoundPolygon:

    def __init__(self, master, x, y, sharpness, *args, **kwargs):
        self.canvas = master

        # The sharpness here is just how close the sub-points
        # are going to be to the vertex. The more the sharpness,
        # the more the sub-points will be closer to the vertex.
        # (This is not normalized)
        if sharpness < 2:
            sharpness = 2
        self.radius = sharpness

        ratioMultiplier = sharpness - 1
        ratioDividend = sharpness

        # Array to store the points
        self.points = []

        # Iterate over the x points
        for i in range(len(x)):
            # Set vertex
            self.points.append(x[i])
            self.points.append(y[i])

            # If it's not the last point
            if i != (len(x) - 1):
                # Insert submultiples points. The more the sharpness, the more these points will be
                # closer to the vertex.
                self.points.append((ratioMultiplier*x[i] + x[i + 1])/ratioDividend)
                self.points.append((ratioMultiplier*y[i] + y[i + 1])/ratioDividend)
                self.points.append((ratioMultiplier*x[i + 1] + x[i])/ratioDividend)
                self.points.append((ratioMultiplier*y[i + 1] + y[i])/ratioDividend)
            else:
                # Insert submultiples points.
                self.points.append((ratioMultiplier*x[i] + x[0])/ratioDividend)
                self.points.append((ratioMultiplier*y[i] + y[0])/ratioDividend)
                self.points.append((ratioMultiplier*x[0] + x[i])/ratioDividend)
                self.points.append((ratioMultiplier*y[0] + y[i])/ratioDividend)
                # Close the polygon
                self.points.append(x[0])
                self.points.append(y[0])

        self.polygon = self.make_shape(*args, **kwargs)

    def make_shape(self, *args, **kwargs):
        return self.canvas.create_polygon(self.points, smooth=TRUE, *args, **kwargs)


if __name__ == '__main__':
    root = Tk()
    canvas = Canvas(root, width=1000, height=1000)
    canvas.pack()

    my_rectangle = RoundPolygon(master=canvas, x=[50, 350, 350, 50], y=[50, 50, 350, 350], sharpness=10, width=5, outline="#82B366", fill="#D5E8D4")
    my_triangle = RoundPolygon(master=canvas, x=[50, 650, 50], y=[400, 700, 1000], sharpness=8, width=5, outline="#82B366", fill="#D5E8D4")

    root.mainloop()