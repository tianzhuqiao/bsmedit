from bsmedit.bsm.pysim import *
from bsmedit.propgrid import formatters as fmt
# create a simulation
s = simulation(None, './examples/tb_dll/libtbdll.so')

assert s.is_valid(), 'Failed to load simulation'
# set the simulation parameters: step = 100us, run infinitely
s.set_parameter('100us', '-1us')

# read the register value and print it
print(s.read('top.sig_int'))

# run the simulation for one step (100us)
s.step()

print(s.read('top.sig_int'))

# set the register to 1000
s.write({'top.sig_int': 1000})

print(s.read('top.sig_int'))

s.run(more='1ps')
# run the simulation for a small step to make the change effective
print(s.read('top.sig_int'))

s.step()

# dump the register value to file
s.trace_file('top.sig_sin')

# create the propgrid window and monitor the register value
s.monitor('top.sig_double')

p = s.monitor('top.sig_sc_logic')
p.SetFormatter(
    fmt.ChoiceFormatter(['1','0','Z','X']))
p.SetControlStyle('radiobox')

# dump the register value to a numpy array
s.trace_buf('top.sig_cos', 500)
s.trace_buf('top.sig_sin', 500)

plot_trace('top.sig_sin')
ylim([-1, 1])
figure()
plot_trace('top.sig_cos', 'top.sig_sin', relim=False)
xlim([-1, 1])
ylim([-1, 1])

s.run(to='1000us')

p = s.monitor('top.sig_bool')
p.SetControlStyle('CheckBox')
p = s.monitor('top.sig_char')
p.SetControlStyle('Slider', min_value=-128, max_value=127)
p = s.monitor('top.sig_cos')
p = s.monitor('top.sig_double')
p = s.monitor('top.sig_float')
p = s.monitor('top.sig_int')
# set breakpoint condition
p.SetBpCondition(cond='$>=6000000', hitcount='')
# enable breakpoint
p.SetChecked(True)
p = s.monitor('top.sig_long')
p.SetBpCondition(cond='$>=6000000', hitcount='#==4')
p.SetChecked(True)
p = s.monitor('top.sig_longlong')
p = s.monitor('top.sig_sc_bigint')
p = s.monitor('top.sig_sc_biguint')
p = s.monitor('top.sig_sc_bit')
p.SetControlStyle('CheckBox')
p = s.monitor('top.sig_sc_bv')
p = s.monitor('top.sig_sc_fixed')
p = s.monitor('top.sig_sc_fixed_fast')
p = s.monitor('top.sig_sc_int')
p = s.monitor('top.sig_sc_logic')
p.SetControlStyle('RadioBox', choice=['1', '0', 'Z', 'X'])
p.SetBpCondition(cond='', hitcount='')
p.SetChecked(True)
p = s.monitor('top.sig_sc_lv')
p = s.monitor('top.sig_sc_ufixed')
p = s.monitor('top.sig_sc_uint')
p = s.monitor('top.sig_short')
p = s.monitor('top.sig_sin')
p = s.monitor('top.sig_std_string')
p = s.monitor('top.sig_uchar')
p.SetControlStyle('Spin', min_value=0, max_value=255)
p = s.monitor('top.sig_uint')
p = s.monitor('top.sig_ulong')
p = s.monitor('top.sig_ulonglong')
p = s.monitor('top.sig_ushort')