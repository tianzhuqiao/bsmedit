from bsmedit.bsm.pysim import *
from bsmedit.propgrid import formatters as fmt
# create a simulation
s = simulation(None, './examples/libstart.so')

assert s.is_valid(), "Failed to load simulation"
# set the simulation parameters: step = 100us, run infinitely
s.set_parameter('100us', '-1us')

# create the propgrid window and monitor the signals
s.monitor('top.CLOCK')
p = s.monitor('top.sig_steps')
p.SetFormatter(fmt.IntFormatter(256))
p.SetControlStyle('spin')
s.monitor('top.sig_sin')
s.monitor('top.sig_cos')

s.write({'top.sig_steps': 2**16})
# dump the signal value to a numpy array
s.trace_buf('top.sig_cos', 2**14)
s.trace_buf('top.sig_sin', 2**14)

plot_trace('top.sig_cos', 'top.sig_sin', relim=False)
xlim([-1, 1])
ylim([-1, 1])
grid(ls='dotted')
s.run(more='1000us')
s.wait_until_simulation_paused()
