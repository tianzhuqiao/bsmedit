from bsm.pysim import *
# create a simulation
simulation(None, './examples/start.dll')

# set the simulation parameters: step = 100us, run infinitely
set_parameter('100us', '-1us')

# create the propgrid window and monitor the signals
monitor('top.CLOCK')
monitor('top.sig_sin')
monitor('top.sig_cos')

# dump the signal value to a numpy array
trace_buf('top.sig_cos', 4096)
trace_buf('top.sig_sin', 4096)

plot_trace('top.sig_cos', 'top.sig_sin', False)
xlim([-1,1])
ylim([-1,1])
runto('1000us')