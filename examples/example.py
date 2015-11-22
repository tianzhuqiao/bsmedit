from bsm.pysim import *
# create a simulation
simulation(None, './examples/tb_dll.dll')

print read(['top.sig_int'], True)
step()
print read(['top.sig_int'], True)
write({'top.sig_int':1000}, True)
print read(['top.sig_int'], True)
step()
print read(['top.sig_int'], True)

monitor('top.sig_double')

trace_buf('top.sig_cos', 256)
trace_buf('top.sig_sin', 256)
plot_trace(None, 'top.sig_sin')
figure()
plot_trace('top.sig_cos', 'top.sig_sin', False)
xlim([-1,1])
ylim([-1,1])