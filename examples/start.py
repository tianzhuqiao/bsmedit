from bsm.pysim import *
# create a simulation
simulation(None, './examples/start.dll')

# set the simulation parameters: step = 100us, run infinitely
set_parameter('100us', '-1us')

# create the propgrid window and monitor the signals
monitor('top.CLOCK')
p = monitor('top.sig_steps')
p.SetChoice([256,1024,2048, 8192, 16384])
p.SetControlStyle('combobox')
monitor('top.sig_sin')
monitor('top.sig_cos')

write({'top.sig_steps': 2**16})
# dump the signal value to a numpy array
trace_buf('top.sig_cos', 2**14)
trace_buf('top.sig_sin', 2**14)

plot_trace('top.sig_cos', 'top.sig_sin', False)
xlim([-1,1])
ylim([-1,1])
grid(ls='dotted')
runto('1000us')