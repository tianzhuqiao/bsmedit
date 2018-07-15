from matplotlib.backends.backend_wx import DEBUG_MSG, Figure
from matplotlib._pylab_helpers import Gcf
from matplotlib.backends.backend_wx import Show
from matplotlib import is_interactive
from matplotlib import get_backend

def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """

    # in order to expose the Figure constructor to the pylab
    # interface we need to create the figure here

    from .graph import MatplotPanel
    DEBUG_MSG('new_figure_manager()', 3, None)
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)

    return MatplotPanel.addFigure('Figure %d' % num, num, thisFig)


def draw_if_interactive():
    """
    This should be overriden in a windowing environment if drawing
    should be done in interactive python mode
    """

    DEBUG_MSG('draw_if_interactive()', 1, None)

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
