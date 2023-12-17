from .sim import sim, SimPropGrid


def gcp():
    """
    get the current propgrid manager
    """
    mgr = SimPropGrid.GCM.get_active()
    if not mgr:
        mgr = sim.propgrid()
    return mgr


# add some shortcuts
propgrid = sim.propgrid
simulation = sim.simulation
plot_trace = sim.plot_trace
