from sim import sim, Gcs
from propgrid import bsmPropGrid
from _docstring import copy_docstring

def gcp():
    """
    get the current propgrid manager
    """
    mgr = bsmPropGrid.GCM.get_active()
    if not mgr:
        mgr = propgrid()
    return mgr

def propgrid(*args, **kwargs):
    """
    get the propgrid manager by its number

    If the manager exists, return its handler; otherwise, it will be created.
    """
    return sim.propgrid(*args, **kwargs)

@copy_docstring(sim.simulation)
def simulation(*args, **kwargs):
    return sim.simulation(*args, **kwargs)

@copy_docstring(sim.plot_trace)
def plot_trace(*args, **kwargs):
    return sim.plot_trace(*args, **kwargs)
