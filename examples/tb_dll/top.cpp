// top.cpp: implementation of the top class.
//
//////////////////////////////////////////////////////////////////////
#include <math.h>
#include "top.h"
#include "sub.h"
#ifndef M_PI
#define M_PI       3.14159265358979323846
#endif
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////


top::~top() {
    if (interface_sub)
        delete interface_sub;
    interface_sub = NULL;
}

void top::Initialize() {
    sig_bool.write(false);
    sig_float.write((float)0.0);
    sig_double.write(0.0);
    sig_char.write(0);
    sig_uchar.write(0);
    sig_short.write(0);
    sig_ushort.write(0);
    sig_int.write(0);
    sig_uint.write(0);
    sig_long.write(0);
    sig_ulong.write(0);
    sig_longlong.write(0);
    sig_ulonglong.write(0);
    sig_std_string.write("hello");
    sig_sc_bit.write(sc_bit(0));
    sig_sc_logic.write(sc_logic(0));
    sig_sc_lv.write(sc_lv<16>("zx10"));
    sig_sc_bv.write(sc_bv<16>("01"));
    sig_sc_int.write(0);
    sig_sc_uint.write(0);
    sig_sc_bigint.write(0);
    sig_sc_biguint.write(0);
    sig_sc_fixed.write(0.0);
    sig_sc_fixed_fast.write(0.0);
    sig_sc_ufixed.write(0.0);

    interface_sub = new sub("interface");
    interface_sub->clock(clock);

    interface_sub->in_bool(sig_bool);
    interface_sub->in_float(sig_float);
    interface_sub->in_double(sig_double);
    interface_sub->in_char(sig_char);
    interface_sub->in_uchar(sig_uchar);
    interface_sub->in_short(sig_short);
    interface_sub->in_ushort(sig_ushort);
    interface_sub->in_int(sig_int);
    interface_sub->in_uint(sig_uint);
    interface_sub->in_long(sig_long);
    interface_sub->in_ulong(sig_ulong);
    interface_sub->in_longlong(sig_longlong);
    interface_sub->in_ulonglong(sig_ulonglong);
    // interface_sub->in_std_string(sig_std_string);
    interface_sub->in_sc_bit(sig_sc_bit);
    interface_sub->in_sc_logic(sig_sc_logic);
    interface_sub->in_sc_lv(sig_sc_lv);
    interface_sub->in_sc_bv(sig_sc_bv);
    interface_sub->in_sc_int(sig_sc_int);
    interface_sub->in_sc_uint(sig_sc_uint);
    interface_sub->in_sc_bigint(sig_sc_bigint);
    interface_sub->in_sc_biguint(sig_sc_biguint);
    interface_sub->in_sc_fixed(sig_sc_fixed);
    interface_sub->in_sc_fixed_fast(sig_sc_fixed_fast);
    interface_sub->in_sc_ufixed(sig_sc_ufixed);

    interface_sub->out_bool(sig_bool);
    interface_sub->out_float(sig_float);
    interface_sub->out_double(sig_double);
    interface_sub->out_char(sig_char);
    interface_sub->out_uchar(sig_uchar);
    interface_sub->out_short(sig_short);
    interface_sub->out_ushort(sig_ushort);
    interface_sub->out_int(sig_int);
    interface_sub->out_uint(sig_uint);
    interface_sub->out_long(sig_long);
    interface_sub->out_ulong(sig_ulong);
    interface_sub->out_longlong(sig_longlong);
    interface_sub->out_ulonglong(sig_ulonglong);
    // interface_sub->out_std_string(sig_std_string);
    interface_sub->out_sc_bit(sig_sc_bit);
    interface_sub->out_sc_logic(sig_sc_logic);
    interface_sub->out_sc_lv(sig_sc_lv);
    interface_sub->out_sc_bv(sig_sc_bv);
    interface_sub->out_sc_int(sig_sc_int);
    interface_sub->out_sc_uint(sig_sc_uint);
    interface_sub->out_sc_bigint(sig_sc_bigint);
    interface_sub->out_sc_biguint(sig_sc_biguint);
    interface_sub->out_sc_fixed(sig_sc_fixed);
    interface_sub->out_sc_fixed_fast(sig_sc_fixed_fast);
    interface_sub->out_sc_ufixed(sig_sc_ufixed);
}

void top::InitPort() {
}

void top::Reset() {
    Initialize();
    InitPort();
}

void top::Action() {
    sig_bool.write(!sig_bool.read());
    sig_float.write(sig_float.read() + (float)0.1);
    sig_double.write(sig_double.read() + 0.3);
    sig_char.write(sig_char.read() + 1);
    sig_uchar.write(sig_uchar.read() + 1);
    sig_short.write(sig_short.read() + 1);
    sig_ushort.write(sig_ushort.read() + 1);
    sig_int.write(sig_int.read() + 1);
    sig_uint.write(sig_uint.read() + 1);
    sig_long.write(sig_long.read() + 1);
    sig_ulong.write(sig_ulong.read() + 1);
    sig_longlong.write(sig_longlong.read() + 1);
    sig_ulonglong.write(sig_ulonglong.read() + 1);
    const char * str[] = { "hello", "benben", "merry xmas", "happy new year", "helen" };

    sig_std_string.write(str[sig_uint.read() % 5]);

    sig_sc_bit.write(sig_sc_bit.read().to_bool() ? sc_bit(0) : sc_bit(1));

    int sc_logic_val = sig_sc_logic.read().value();
    sc_logic_val = (sc_logic_val + 1) % 4;
    sig_sc_logic.write(sc_logic(sc_logic_val));
    sig_sc_lv.write(sig_sc_lv.read().operator <<(1));
    sig_sc_bv.write(sig_sc_bv.read().operator <<(1));
    sig_sc_int.write((int)sig_sc_int.read() + 1);
    sig_sc_uint.write((unsigned int)sig_sc_uint.read() + 1);
    sig_sc_bigint.write(sig_sc_bigint.read() + 1);
    sig_sc_biguint.write(sig_sc_biguint.read() + 1);
    sig_sc_fixed.write((double)sig_sc_fixed.read() + 0.1);
    sig_sc_fixed_fast.write((double)sig_sc_fixed_fast.read() + 0.1);
    sig_sc_ufixed.write((double)sig_sc_ufixed.read() + 0.1);

    sig_sin.write(sin(m_phase));
    sig_cos.write(cos(m_phase));
    m_phase = m_phase + M_PI / 256;
    if (m_phase > 2 * M_PI) m_phase -= 2 * M_PI;
}
