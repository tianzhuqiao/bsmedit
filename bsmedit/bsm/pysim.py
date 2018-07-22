from .sim import sim, SimPropGrid

def gcp():
    """
    get the current propgrid manager
    """
    mgr = sim.PropGrid.GCM.get_active()
    if not mgr:
        mgr = sim.propgrid()
    return mgr

# add some shortcuts
progrid = sim.propgrid
simulation = sim.simulation
plot_trace = sim.plot_trace
