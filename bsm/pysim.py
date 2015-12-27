from sim import sim, Gcs
from bsmpropgrid import bsmPropGrid
from bsmplot import *
from sim_engine import *
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

def simulation(*args, **kwargs):
    """
    create a simulation

    If the simulation exists, return its handler; otherwise, create it if
    create == True.
    """
    return sim.simulation(*args, **kwargs)

def set_parameter(*args, **kwargs):
    """
    set the parameters for the current simulation
    """
    sim.set_parameter(*args, **kwargs)

def load(*args, **kwargs):
    """
    load the simulation library (e.g., dll)
    """
    sim.load(*args, **kwargs)

def load_interactive(*args, **kwargs):
    """
    open a filedialog to load the simulation
    """
    sim.load_interactive(*args, **kwargs)

def step(*args, **kwargs):
    """
    proceed the simulation with one step

    The step is set with set_parameter(). The GUI components will be updated
    after the running.

    The breakpoints are checked at each delta cycle.
    """
    sim.step(*args, **kwargs)

def run(*args, **kwargs):
    """
    keep running the simulation

    The simulation is executed step by step. After each step, the simulation
    'server' will notify the 'client' to update the GUI.
    """
    sim.run(*args, **kwargs)

def pause(*args, **kwargs):
    """
    pause the simulation after the current step.
    """
    sim.pause(*args, **kwargs)

def stop(*args, **kwargs):
    """
    stop the simulation after the current step.
    """
    return sim.stop(*args, **kwargs)

def reset(*args, **kwargs):
    """
    reset the simulation
    """
    return sim.reset(*args, **kwargs)

def time_stamp(*args, **kwargs):
    """
    get the simulation time stamp

    if block == False, it will return after sending the command; otherwise, it
    will return the current simulation time
    """
    return sim.time_stamp(*args, **kwargs)

def time_stamp_sec(*args, **kwargs):
    return sim.time_stamp_sec(*args, **kwargs)

def get_object_name(name):
    return sim.get_object_name(name)

def get_abs_name(name):
    num, n = get_object_name(name)
    if not num:
        mgr = gcs()
        if mgr:
            return mgr._abs_object_name(n)
    return name

def read(*args, **kwargs):
    """
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
