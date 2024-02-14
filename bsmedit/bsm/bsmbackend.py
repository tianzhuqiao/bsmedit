from matplotlib.figure import Figure
from matplotlib._pylab_helpers import Gcf
from matplotlib.backends.backend_wx import Show
from matplotlib import is_interactive
from matplotlib import get_backend
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas


def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """

    # in order to expose the Figure constructor to the pylab
    # interface we need to create the figure here

    from .graph import Graph
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)

    return Graph.AddFigure('Figure %d' % num, num, thisFig)


def draw_if_interactive():
    """
    This should be overridden in a windowing environment if drawing
    should be done in interactive python mode
    """

    if is_interactive():
        figManager = Gcf.get_active()
        if figManager is not None:
            figManager.canvas.draw()


class ShowFigure(Show):
    def __call__(self, fig=None, block=None):
        """
        Show all figures.  If *block* is not None, then
        it is a boolean that overrides all other factors
        determining whether show blocks by calling mainloop().
        The other factors are:
        it does not block if run inside "ipython --pylab";
        it does not block in interactive mode.
        """

        if isinstance(fig, int):
            manager = Gcf.get_fig_manager(fig)
        else:
            manager = Gcf.get_active()
        if not manager:
            return

        # for manager in managers:

        manager.show()

        if block is not None:
            if block:
                self.mainloop()
                return
            else:
                return

        if not is_interactive() or get_backend() == 'WebAgg':
            self.mainloop()


show = ShowFigure()
