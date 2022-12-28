
class GraphObject():
    def __init__(self, figure):
        self.figure = figure

    def get_xy_dis_gain(self):
        # the gain applied to x/y when calculate the distance between to point
        # e.g., a data point to the mouse position
        # for example, if the figure is square (width == height), but
        # x range is [0, 100], and y range is [0, 0.1], the physical distance
        # in y axis will be `ignored` as x is 1000 times larger than y.
        xlim = self.figure.gca().get_xlim()
        ylim = self.figure.gca().get_ylim()
        box = self.figure.gca().get_window_extent()
        if xlim[1] - xlim[0] == 0 or ylim[1] - ylim[0] == 0:
            return 1, 1
        gx = box.width / (xlim[1] - xlim[0])
        gy = box.height / (ylim[1] - ylim[0])
        return gx, gy

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
