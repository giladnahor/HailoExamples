import matplotlib.pyplot as plt
import random
from collections import deque
import time

class RealTimePlotter:
    def __init__(self, plot_length=100, named_series=False):
        self.plot_length = plot_length
        self.y_data = {}
        self.x_data = deque(maxlen=self.plot_length)
        self.named_series = named_series
        self.series_colors = {}
        self.init = True # This flage is used to dump the first data point which might be corrupted due to serial initialization
        
        # Initialize matplotlib
        self.fig, self.ax = plt.subplots()
        plt.ion()  # Turn on interactive mode
        self.fig.show()
        plt.xlabel('Time')
        plt.ylabel('Value')

    def update_plot(self):
        self.ax.clear()
        for series, y_series in self.y_data.items():
            line, = self.ax.plot(self.x_data, y_series, label=series)
            self.series_colors[series] = line.get_color()
        plt.legend()
        plt.xlabel('Time')
        plt.ylabel('Value')
        self.fig.canvas.flush_events()

    def add_data(self, data_str):
        if self.init:
            self.init = False
            return
        try:
            values = data_str.split(',')
            if self.named_series:
                values = [(values[i].strip(), float(values[i+1].strip())) for i in range(0, len(values), 2)]
            else:
                values = [(str(i), float(values[i].strip())) for i in range(len(values))]
        except ValueError:
            print(f"Invalid data: {data_str}")
            return

        for series_name, value in values:
            if series_name not in self.y_data:
                self.y_data[series_name] = deque(maxlen=self.plot_length)
            self.y_data[series_name].append(value)
        self.x_data.append(self.x_data[-1] + 1 if self.x_data else 0)

# Test with randomized data when run standalone
if __name__ == "__main__":
    plotter = RealTimePlotter(plot_length=200, named_series=True)

    for i in range(100):
        random_data = "Series_1, {:.2f}, Series_2, {:.2f}, Series_3, {:.2f}".format(
            random.uniform(0, 10), random.uniform(0, 10), random.uniform(0, 10))
        plotter.add_data(random_data)
        plotter.update_plot()
        time.sleep(0.1)
