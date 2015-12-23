from sim import *
from bsmpropgrid import *
from bsmplot import *

def gcp():
    """
    get the current propgrid manager
    """
    mgr = bsmPropGrid.GCM.get_active()
    if not mgr:
        mgr = propgrid()
    return mgr

def propgrid(num = None, create = True, activate = False):
    """
    get the propgrid manager by its number

    If the manager exists, return its handler; otherwise, it will be created.
    """
    return sim.propgrid(num, create, activate)

def gcs():
    """
    get the active simulation

    If no simulation is available, create a new one.
    """
    sim = Gcs.get_active()
    if not sim:
        sim = simulation()
    return sim

def simulation(num = None, filename = None, scilent = False, create = True,
               activate = False):
    """
    create a simulation

    If the simulation exists, return its handler; otherwise, create it if
    create == True.
    """
    manager = Gcs.get_manager(num)
    if manager == None and create:
        manager = ModulePanel(sim.frame, num, filename, scilent)
        wx.py.dispatcher.send(signal="frame.add_panel", panel = manager,
                      title = "Simulation-%d"%manager.num, target = "History")
    # activate the manager
    elif manager and activate:
        wx.py.dispatcher.send(signal = 'frame.show_panel', panel = manager)

    return manager

def set_parameter(step, unitStep, total, unitTotal, block = False):
    """
    set the parameters for the current simulation
    """
    sim = gcs()
    if not sim: return
    sim.set_parameter(step, unitStep, total, unitTotal, block)

def load(filename, block = True):
    """
    load the simulation library (e.g., dll)
    """
    sim = gcs()
    if not sim: return
    sim.load(filename, block)

def load_interactive():
    """
    open a filedialog to load the simulation
    """
    sim = gcs()
    if not sim: return
    sim.load_interactive()

def step():
    """
    proceed the simulation with one step

    The step is set with set_parameter(). The GUI components will be updated
    after the running.

    The breakpoints are checked at each delta cycle.
    """
    sim = gcs()
    if not sim: return
    sim.step()

def run():
    """
    keep running the simulation

    The simulation is executed step by step. After each step, the simulation
    'server' will notify the 'client' to update the GUI.
    """
    sim = gcs()
    if not sim: return
    sim.run()

def pause():
    """
    pause the simulation after the current step.
    """
    sim = gcs()
    if not sim: return
    sim.pause()

def stop():
    """
    stop the simulation after the current step.
    """
    sim = gcs()
    if not sim: return
    sim.stop()

def reset():
    """
    reset the simulation
    """
    sim = gcs()
    if not sim: return
    sim.reset()

def time_stamp(block = True):
    """
    get the simulation time stamp

    if block == False, it will return after sending the command; otherwise, it
    will return the current simulation time
    """
    sim = gcs()
    if not sim: return
    return sim.time_stamp(block)

def time_stamp_sec(block = True):
    sim = gcs()
    if not sim: return
    return sim.time_stamp_sec(block)

def get_object_name(name):
    return sim.get_object_name(name)

def get_abs_name(name):
    num, n = get_object_name(name)
    if not num:
        mgr = gcs()
        if mgr: return mgr._abs_object_name(n)
    return name

def read(objects, block = True):
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
    sim = gcs()
    if not sim: return

    if isinstance(objects, str):
        objects = [objects]
    objs = {}
    for obj in objects:
       num, name = get_object_name(obj)
       if num is None:
           num = sim.num
       if num in objs.keys():
           objs[num].append(name)
       else:
           objs[num] = [name]
    resp = {}
    for num, obj in objs.iteritems():
        mgr = simulation(num)
        if not mgr: continue
        v = mgr.read(obj, block)
        if isinstance(v, str) or isinstance(v, unicode):
            resp[mgr._abs_object_name(obj[0])] = v
            if mgr == sim: resp[obj[0]] = v
        else:
            if mgr == sim: resp.update(v)
            v = {mgr._abs_object_name(name):value for name, value in v.iteritems()}
            resp.update(v)

    resp =  {obj: resp.get(obj, '') for obj in objects}
    if len(resp) == 1:
        return resp.values()[0]
    else:
        return {obj: resp.get(obj, '') for obj in objects}

def write(objects, block = True):
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
    sim = gcs()
    if not sim: return
    objs = {}
    for obj, value in objects.iteritems():
       num, name = get_object_name(obj)
       if num is None:
           num = sim.num
       if num in objs.keys():
           objs[num][name] = value
       else:
           objs[num] = {name:value}

    for num, obj in objs.iteritems():
        mgr = simulation(num, False)
        if not mgr: continue
        mgr.write(obj, block)

def trace_file(name, trace_type = BSM_TRACE_SIMPLE, valid=None,\
              trigger = BSM_BOTHEDGE, block = True):
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
    num, obj = get_object_name(name)
    mgr = None
    if not num: mgr = gcs()
    else: mgr = simulation(num, create = False)

    if not mgr: return False

    return mgr.trace_file(obj, trace_type, valid, trigger, block)

def trace_buf(name, size = 256, valid = None, trigger = BSM_BOTHEDGE, block = True):
    """
    trace the register with a buffer

    """
    num, obj = get_object_name(name)
    mgr = None
    if not num: mgr = gcs()
    else: mgr = simulation(num, create = False)

    if not mgr: return None
    return mgr.trace_buf(obj, size, valid, trigger, block)

def read_buf(name, block = True):
    """
    read the previous traced buffer to an numpy array

    If the buffer is previous traced by calling trace_buf, the array with
    previous defined size will return; otherwise the trace_buf will be called
    with default arguments first.
    """
    num, obj = get_object_name(name)
    mgr = None
    if not num: mgr = gcs()
    else: mgr = simulation(num, create = False)

    if not mgr: return False
    return mgr.read_buf(obj, block)

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

def monitor(objects, grid = None):
    """
    show the register in the active propgrid window

    If no propgrid window has been created, one will be created first.
    """
    sim = gcs()
    if not sim: return

    if grid == None:
        grid = gcp()
    if not grid: return

    if isinstance(objects, str):
        objects = [objects]
    objs = {}
    for obj in objects:
       num, name = get_object_name(obj)
       if num is None:
           num = sim.num
       if num in objs.keys():
           objs[num].append(name)
       else:
           objs[num] = [name]
    for num, obj in objs.iteritems():
        mgr = simulation(num, create = False)
        if not mgr: continue
        mgr.show_prop(grid, obj)

