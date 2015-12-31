from sim import sim, Gcs
from bsmpropgrid import bsmPropGrid
from bsmplot import *
from sim_engine import *
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

@copy_docstring(sim.propgrid)
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

def read(*args, **kwargs):
    """
    read(objects, block=True)

    get the values of the registers

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

def write(*args, **kwargs):
    """
    write(objects, block=True)

    write the values to registers

    Objects should be a dictionary where the keys are the register name. Due to
    the two-step mechanism in systemc, the value will be updated after the next
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

def trace_file(*args, **kwargs):
    """
    dump the values to a file

    name:
        register name
    trace_type:
        BSM_TRACE_SIMPLE only output the register value, one per line
        BSM_TRACE_VCD output the SystemC VCD format data
    valid:
        the trigger signal. If it is none, the write-operation will be triggered
        by the register itself
    trigger:
        BSM_BOTHEDGE: trigger on both rising and falling edges
        BSM_POSEDGE: trigger on rising edge
        BSM_NEGEDGE: trigger on falling edge
        BSM_NONEEDGE: no triggering

    """
    return sim.trace_file(*args, **kwargs)

def trace_buf(*args, **kwargs):
    """
    trace the register with a buffer

    """
    return sim.trace_buf(*args, **kwargs)

def read_buf(*args, **kwargs):
    """
    read the previous traced buffer to an numpy array

    If the buffer is previous traced by calling trace_buf, the array with
    previous defined size will return; otherwise the trace_buf will be called
    with default arguments first.
    """
    return sim.read_buf(*args, **kwargs)

def plot_trace(x, y, autorelim=True, *args, **kwargs):
    """
    plot the trace

    The trace will be automatically updated when the simulation is running
    """
    if y is None:
        return
    dy = read_buf(y, True)
    y = {get_abs_name(y):dy}
    if x is not None:
        dx = read_buf(x, True)
        x = {get_abs_name(x):dx}
    mgr = plt.get_current_fig_manager()
    mgr.plot_trace(x, y, autorelim, *args, **kwargs)

def monitor(*args, **kwargs):
    """
    show the register in the active propgrid window

    If no propgrid window has been created, one will be created first.
    """
    return sim.monitor(*args, **kwargs)
