from bsmedit.bsm.pysim import *
# create a simulation
s = simulation(None, './examples/tb_dll.dll')

# set the simulation parameters: step = 100us, run infinitely
s.set_parameter('100us', '-1us')

# read the register value and print it
print s.read('top.sig_int')

# run the simulation for one step (100us)
s.step()

print s.read('top.sig_int')

# set the register to 1000
s.write({'top.sig_int':1000})

print s.read('top.sig_int')

s.step('1ps')
# run the simulation for a small step to make the change effective
print s.read('top.sig_int')

s.step('100us')

# dump the register value to file
s.trace_file('top.sig_sin')

# create the propgrid window and monitor the register value
s.monitor('top.sig_double')

p = s.monitor('top.sig_sc_logic')
p.SetChoice({'1':1, '0':0, 'Z':'Z', 'X':'X'})
p.SetControlStyle('radiobox')

# dump the register value to a numpy array
s.trace_buf('top.sig_cos', 500)
s.trace_buf('top.sig_sin', 500)

plot_trace(y='top.sig_sin')
ylim([-1,1])
figure()
plot_trace('top.sig_cos', 'top.sig_sin', False)
xlim([-1,1])
ylim([-1,1])

s.run(to='1000us')
