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
        wx.py.dispatcher.send(signal="frame.addpanel", panel = manager, 
                      title = "Simulation-%d"%manager.num, target = "History")
    # activate the manager
    elif manager and activate:
        wx.py.dispatcher.send(signal = 'frame.showpanel', panel = manager)

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

def step(block = True):
    """
    proceed the simulation with one step 

    The step is set with set_parameter(). The GUI components will be updated
    after the running.
    
    The breakpoints are checked at each delta cycle.
    """
    sim = gcs()
    if not sim: return
    sim.step(block)

def run(block = True):
    """
    keep running the simulation

    The simulation is executed step by step. After each step, the simulation 
    'server' will notify the 'client' to update the GUI.
    """
    sim = gcs()
    if not sim: return
    sim.run(block)

def pause(block = True):
    """
    stop the simulation after the current step.
    """
    sim = gcs()
    if not sim: return
    sim.pause(block)

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

def trace_file(name, trace_type, block = True):
    """
    dump the values to a file
     
    """
    num, obj = get_object_name(name)
    mgr = None
    if not num: mgr = gcs()
    else: mgr = simulation(num, create = False)
    
    if not mgr: return

    return mgr.trace_file(obj, trace_type, block)

def trace_buf(obj, size, block = False):
    sim = gcs()
    if not sim: return
    return sim.trace_buf(obj, size, block)

def read_buf(obj, block = False):
    sim = gcs()
    if not sim: return
    return sim.read_buf(obj, block)

def plot_trace(x, y, autorelim=True, *args, **kwargs):
    if y is None:
        return
    dy = read_buf(y, True)
    y = {y:dy}
    if x is not None:
        dx = read_buf(x, True)
        x = {x:dx}
    mgr = plt.get_current_fig_manager()
    mgr.plot_trace(x, y, autorelim, *args, **kwargs)

def monitor(objects, grid = None):
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

