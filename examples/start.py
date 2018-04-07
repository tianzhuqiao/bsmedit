from bsmedit.bsm.pysim import *
# create a simulation
s = simulation(None, './examples/start.dll')

# set the simulation parameters: step = 100us, run infinitely
s.set_parameter('100us', '-1us')

# create the propgrid window and monitor the signals
s.monitor('top.CLOCK')
p = s.monitor('top.sig_steps')
p.SetChoice([256,1024,2048, 8192, 16384])
p.SetControlStyle('combobox')
s.monitor('top.sig_sin')
s.monitor('top.sig_cos')

s.write({'top.sig_steps': 2**16})
# dump the signal value to a numpy array
s.trace_buf('top.sig_cos', 2**14)
s.trace_buf('top.sig_sin', 2**14)

plot_trace('top.sig_cos', 'top.sig_sin', relim=False)
xlim([-1,1])
ylim([-1,1])
grid(ls='dotted')
s.run(to='1000us')
s.wait_until_simulation_paused()

