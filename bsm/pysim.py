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

def gcs():
    """
    get the active simulation

    If no simulation is available, create a new one.
    """
    s = Gcs.get_active()
    if not s:
        s = simulation()
    return s

@copy_docstring(sim.simulation)
def simulation(*args, **kwargs):
    return sim.simulation(*args, **kwargs)

@copy_docstring(sim.set_parameter)
def set_parameter(*args, **kwargs):
    sim.set_parameter(*args, **kwargs)

@copy_docstring(sim.load)
def load(*args, **kwargs):
    sim.load(*args, **kwargs)

@copy_docstring(sim.load_interactive)
def load_interactive(*args, **kwargs):
    sim.load_interactive(*args, **kwargs)

@copy_docstring(sim.step)
def step(*args, **kwargs):
    sim.step(*args, **kwargs)

@copy_docstring(sim.run)
def run(*args, **kwargs):
    sim.run(*args, **kwargs)

def runto(to, *args, **kwargs):
    """"run(to, *args, **kwargs)"""
    sim.run(to=to, *args, **kwargs)

def runmore(more, *args, **kwargs):
    """"run(more, *args, **kwargs)"""
    sim.run(more=more, *args, **kwargs)

@copy_docstring(sim.pause)
def pause(*args, **kwargs):
    sim.pause(*args, **kwargs)

@copy_docstring(sim.stop)
def stop(*args, **kwargs):
    return sim.stop(*args, **kwargs)

@copy_docstring(sim.reset)
def reset(*args, **kwargs):
    return sim.reset(*args, **kwargs)

@copy_docstring(sim.time_stamp)
def time_stamp(*args, **kwargs):
    return sim.time_stamp(*args, **kwargs)

def get_object_name(name):
    return sim.get_object_name(name)

def get_abs_name(name):
    num, n = get_object_name(name)
    if not num:
        mgr = gcs()
        if mgr:
            return mgr.abs_object_name(n)
    return name

@copy_docstring(sim.read)
def read(*args, **kwargs):
    """
    If block == False, it will return after sending the command; otherwise, it
    will return the values.

    If objects only contains one register, its value will be returned if succeed;
    otherwise a dictionary is returned, where the keys are the items in objects.

    Example: read a single register defined in simulation 1
    >>> read('1.top.sig_bool', True)

    Example: if the simulation num is not included in objects, it will read
    register defined in active simulation
    >>> read('top.sig_bool', True)

    Example: read multiple registers from the same simulation
    >>> read(['top.sig_bool', 'top.sig_cos']

    Example: read multiple registers from multiple simulations
    >>> read(['1.top.sig_bool', '2.top.sig_cos']
    """
    return sim.read(*args, **kwargs)

@copy_docstring(sim.write)
def write(*args, **kwargs):
    """
    Objects should be a dictionary where the keys are the register name. Due to
    the two-step mechanism in SystemC, the value will be updated after the next
    delta cycle. That is, if a read() is called after write(), it will return
    the previous value.

    Example: write a single register defined in simulation 1
    >>> write({'1.top.sig_int': 100}, True)

    Example:
    >>> a = read('top.sig_int', True)
    >>> write({'top.sig_int': 100}, True)
    >>> b = read('top.sig_int', True) # a == b
    >>> step()
    >>> c = read('top.sig_int', True)
    """
    sim.write(*args, **kwargs)

@copy_docstring(sim.trace_file)
def trace_file(*args, **kwargs):
    return sim.trace_file(*args, **kwargs)

@copy_docstring(sim.trace_buf)
def trace_buf(*args, **kwargs):
    return sim.trace_buf(*args, **kwargs)

@copy_docstring(sim.read_buf)
def read_buf(*args, **kwargs):
    return sim.read_buf(*args, **kwargs)

@copy_docstring(sim.monitor)
def monitor(*args, **kwargs):
    return sim.monitor(*args, **kwargs)

@copy_docstring(sim.plot_trace)
def plot_trace(*args, **kwargs):
    return sim.plot_trace(*args, **kwargs)
