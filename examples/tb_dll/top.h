#ifndef _TOP_H_
#define _TOP_H_

#include "systemc.h"
#include "xsc_array.h"
#ifdef INI_CHANNEL
#undef INI_CHANNEL
#endif

#define INI_CHANNEL ,clock("CLOCK", 10, 0.5, 0.0)\
    ,sig_bool("sig_bool")\
    ,sig_float("sig_float")\
    ,sig_double("sig_double")\
    ,sig_char("sig_char")\
    ,sig_uchar("sig_uchar")\
    ,sig_short("sig_short")\
    ,sig_ushort("sig_ushort")\
    ,sig_int("sig_int")\
    ,sig_uint("sig_uint")\
    ,sig_long("sig_long")\
    ,sig_ulong("sig_ulong")\
    ,sig_longlong("sig_longlong")\
    ,sig_ulonglong("sig_ulonglong")\
    ,sig_std_string("sig_std_string")\
    ,sig_sc_bit("sig_sc_bit")\
    ,sig_sc_logic("sig_sc_logic")\
    ,sig_sc_lv("sig_sc_lv")\
    ,sig_sc_bv("sig_sc_bv")\
    ,sig_sc_int("sig_sc_int")\
    ,sig_sc_uint("sig_sc_uint")\
    ,sig_sc_bigint("sig_sc_bigint")\
    ,sig_sc_biguint("sig_sc_biguint")\
    ,sig_sc_fixed("sig_sc_fixed")\
    ,sig_sc_fixed_fast("sig_sc_fixed_fast")\
    ,sig_sc_ufixed("sig_sc_ufixed")\
    ,sig_sin("sig_sin")\
    ,sig_cos("sig_cos")\
    ,xsc_array_int("xsc_array_int")\

class sub;
class top : public sc_module
{
    //interface
public:

    //signal
    sc_clock clock;

    sc_signal<bool>   sig_bool;
    sc_signal<float>  sig_float;
    sc_signal<double> sig_double;

    sc_signal<char>   sig_char;
    sc_signal<unsigned char>   sig_uchar;

    sc_signal<short> sig_short;
    sc_signal<unsigned short> sig_ushort;

    sc_signal<int>   sig_int;
    sc_signal<unsigned int> sig_uint;

    sc_signal<long> sig_long;
    sc_signal<unsigned long>   sig_ulong;

    sc_signal<long long> sig_longlong;
    sc_signal<unsigned long long > sig_ulonglong;
    sc_signal<std::string > sig_std_string;

    sc_signal<sc_bit>   sig_sc_bit;
    sc_signal<sc_logic> sig_sc_logic;

    sc_signal<sc_lv<16> >   sig_sc_lv;
    sc_signal<sc_bv<16> >   sig_sc_bv;

    sc_signal<sc_int<16> >   sig_sc_int;
    sc_signal<sc_uint<16> >   sig_sc_uint;

    sc_signal<sc_bigint<64> >   sig_sc_bigint;
    sc_signal<sc_biguint<64> >   sig_sc_biguint;

    sc_signal<sc_fixed<16,10,SC_RND,SC_SAT,0> >        sig_sc_fixed;
    sc_signal<sc_fixed_fast<16,10,SC_RND,SC_SAT,0> >   sig_sc_fixed_fast;
    sc_signal<sc_ufixed<16,10,SC_RND,SC_SAT,0> >       sig_sc_ufixed;

    sc_signal<double> sig_sin;
    sc_signal<double> sig_cos;
    xsc_array<int, 5> xsc_array_int;
public:
    SC_HAS_PROCESS(top);
    top(sc_module_name name_):
    sc_module(name_)
        INI_CHANNEL
        ,m_phase(0.0)
    {
        Initialize();
        SC_METHOD(Action);
        sensitive_pos<<clock;
    }
    virtual ~top();

public:
    void Action();
    void Initialize();
    void InitPort();
    void Reset();
private:
    sub* interface_sub;
    double m_phase;
};
#ifdef INI_CHANNEL
#undef INI_CHANNEL
#endif
#endif // !defined(_TOP_H_)
