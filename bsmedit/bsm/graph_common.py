import numpy as np

class GraphObject():
    def __init__(self, figure):
        self.figure = figure

    def get_xy_dis_gain(self, ax=None):
        # the gain applied to x/y when calculate the distance between to point
        # e.g., a data point to the mouse position
        # for example, if the figure is square (width == height), but
        # x range is [0, 100], and y range is [0, 0.1], the physical distance
        # in y axis will be `ignored` as x is 1000 times larger than y.
        if ax is None:
            ax = self.figure.gca()
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        box = ax.get_window_extent()
        if xlim[1] - xlim[0] == 0 or ylim[1] - ylim[0] == 0:
            return 1, 1
        gx = box.width / (xlim[1] - xlim[0])
        gy = box.height / (ylim[1] - ylim[0])
        return gx, gy

    def get_closest_line(self, axes, mx, my):
        min_dis = float("inf")
        active_line = None
        for g in axes:
            for line in g.lines:
                if not line.get_visible():
                    continue
                dis = self.distance_to_line(line, mx, my)
                if dis < min_dis:
                    min_dis = dis
                    active_line = line
        return active_line, min_dis

    def distance_to_line(self, line, mx, my):
        # distance from (x2, y2) to line formed by (x0, y0) (closest point on line)
        # and its neighbour (x1, y1)
        # in display coordinate
        inv = line.axes.transData.inverted()
        dmx, dmy = inv.transform((mx, my))
        didx, dx, dy = self.get_closest(line, dmx, dmy)

        x0, y0 = line.axes.transData.transform((dx, dy))
        data_x, data_y = line.get_data(False)
        if len(data_x) == 1:
            # single point line
            x1, y1 = x0, y0
        else:
            if didx == len(data_x) - 1 or (mx < x0 and didx > 0):
                x1, y1 = data_x[didx-1], data_y[didx-1]
            else:
                x1, y1 = data_x[didx+1], data_y[didx+1]
            x1, y1 = line.axes.transData.transform((x1, y1))

        if x0 == x1:
            return abs(mx-x0)
        elif y0 == y1:
            return abs(my-y0)
        # the line formed by (x0,y0) and (x1, y1)
        # ax + by + c = 0
        a = (y1-y0)/(x1-x0)
        b = -1
        c = y0 - a*x0

        dis = np.abs(a*mx+b*my + c)/np.sqrt(a**2+b**2)
        return dis

    def get_closest(self, line, mx, my, tolerance=0):
        """return the index of the points whose distance to (mx, my) is smaller
           than tolerance, or the closest data point to (mx, my)"""
        x, y = line.get_data(False)
        if mx is None and my is None:
            return -1

        gx, gy = self.get_xy_dis_gain(line.axes)
        mini = []
        if tolerance>0:
            if my is None:
                mini = np.where((x-mx)**2 * gx**2 < tolerance**2)[0]
            elif mx is None:
                mini = np.where((y-my)**2 * gx**2 < tolerance**2)[0]
            else:
                mini = np.where(((x-mx)**2 * gx**2 + (y-my)**2 * gy**2) < tolerance**2)[0]
        if len(mini)  == 0:
            if my is None:
                mini = np.argmin((x-mx)**2)
            elif mx is None:
                mini = np.argmin((y-my)**2)
            else:
                mini = np.argmin((x-mx)**2 * gx**2 + (y-my)**2 * gy**2)
        return mini, x[mini], y[mini]

    def GetMenu(self):
        '''return the context menu'''
        return []

    def ProcessCommand(self, cmd):
        '''process the menu command'''

    def pick(self, event):
        '''a line is picked'''

    def key_down(self, event):
        pass

    def key_pressed(self, event):
        pass

    def mouse_pressed(self, event):
        '''the mouse is down'''

    def mouse_released(self, event):
        '''the mouse is up'''

    def mouse_move(self, event):
        '''the mouse is moving'''

    def activated(self):
        '''the object is activated'''

    def deactivated(self):
        '''the obje is deactivated'''
