// sub.h: interface for the sub class.
//
//////////////////////////////////////////////////////////////////////

#ifndef _SUB_H_
#define _SUB_H_

#include "systemc.h"

#ifdef INI_CHANNEL
#undef INI_CHANNEL
#endif

#define INI_CHANNEL , clock("clock")\
    , in_bool("in_bool")\
    , in_float("in_float")\
    , in_double("in_double")\
    , in_char("in_char")\
    , in_uchar("in_uchar")\
    , in_short("in_short")\
    , in_ushort("in_ushort")\
    , in_int("in_int")\
    , in_uint("in_uint")\
    , in_long("in_long")\
    , in_ulong("in_ulong")\
    , in_longlong("in_longlong")\
    , in_ulonglong("in_ulonglong")\
    /*,in_std_string("in_std_string")*/\
    , in_sc_bit("in_sc_bit")\
    , in_sc_logic("in_sc_logic")\
    , in_sc_lv("in_sc_lv")\
    , in_sc_bv("in_sc_bv")\
    , in_sc_int("in_sc_int")\
    , in_sc_uint("in_sc_uint")\
    , in_sc_bigint("in_sc_bigint")\
    , in_sc_biguint("in_sc_biguint")\
    , in_sc_fixed("in_sc_fixed")\
    , in_sc_fixed_fast("in_sc_fixed_fast")\
    , in_sc_ufixed("in_sc_ufixed")\
    , out_bool("out_bool")\
    , out_float("out_float")\
    , out_double("out_double")\
    , out_char("out_char")\
    , out_uchar("out_uchar")\
    , out_short("out_short")\
    , out_ushort("out_ushort")\
    , out_int("out_int")\
    , out_uint("out_uint")\
    , out_long("out_long")\
    , out_ulong("out_ulong")\
    , out_longlong("out_longlong")\
    , out_ulonglong("out_ulonglong")\
    /*,out_std_string("out_std_string")*/\
    , out_sc_bit("out_sc_bit")\
    , out_sc_logic("out_sc_logic")\
    , out_sc_lv("out_sc_lv")\
    , out_sc_bv("out_sc_bv")\
    , out_sc_int("out_sc_int")\
    , out_sc_uint("out_sc_uint")\
    , out_sc_bigint("out_sc_bigint")\
    , out_sc_biguint("out_sc_biguint")\
    , out_sc_fixed("out_sc_fixed")\
    , out_sc_fixed_fast("out_sc_fixed_fast")\
    , out_sc_ufixed("out_sc_ufixed")\

class sub : public sc_module {
    // interface
 public:
    // input
    sc_in_clk clock;

    sc_in<bool>   in_bool;
    sc_in<float>  in_float;
    sc_in<double> in_double;

    sc_in<char>   in_char;
    sc_in<unsigned char>   in_uchar;

    sc_in<short> in_short;
    sc_in<unsigned short> in_ushort;

    sc_in<int>   in_int;
    sc_in<unsigned int> in_uint;

    sc_in<long> in_long;
    sc_in<unsigned long>   in_ulong;

    sc_in<long long> in_longlong;
    sc_in<unsigned long long > in_ulonglong;
    // sc_in<std::string > in_std_string;

    sc_in<sc_bit>   in_sc_bit;
    sc_in<sc_logic> in_sc_logic;

    sc_in<sc_lv<16> >   in_sc_lv;
    sc_in<sc_bv<16> >   in_sc_bv;

    sc_in<sc_int<16> >   in_sc_int;
    sc_in<sc_uint<16> >   in_sc_uint;

    sc_in<sc_bigint<64> >   in_sc_bigint;
    sc_in<sc_biguint<64> >   in_sc_biguint;

    sc_in<sc_fixed<16, 10, SC_RND, SC_SAT, 0> >        in_sc_fixed;
    sc_in<sc_fixed_fast<16, 10, SC_RND, SC_SAT, 0> >   in_sc_fixed_fast;
    sc_in<sc_ufixed<16, 10, SC_RND, SC_SAT, 0> >       in_sc_ufixed;

    // output
    sc_out<bool>   out_bool;
    sc_out<float>  out_float;
    sc_out<double> out_double;

    sc_out<char>   out_char;
    sc_out<unsigned char>   out_uchar;

    sc_out<short> out_short;
    sc_out<unsigned short> out_ushort;

    sc_out<int>   out_int;
    sc_out<unsigned int> out_uint;

    sc_out<long> out_long;
    sc_out<unsigned long>   out_ulong;

    sc_out<long long> out_longlong;
    sc_out<unsigned long long > out_ulonglong;
    // sc_out<std::string > out_std_string;

    sc_out<sc_bit>   out_sc_bit;
    sc_out<sc_logic> out_sc_logic;

    sc_out<sc_lv<16> >   out_sc_lv;
    sc_out<sc_bv<16> >   out_sc_bv;

    sc_out<sc_int<16> >   out_sc_int;
    sc_out<sc_uint<16> >   out_sc_uint;

    sc_out<sc_bigint<64> >   out_sc_bigint;
    sc_out<sc_biguint<64> >   out_sc_biguint;

    sc_out<sc_fixed<16, 10, SC_RND, SC_SAT, 0> >        out_sc_fixed;
    sc_out<sc_fixed_fast<16, 10, SC_RND, SC_SAT, 0> >   out_sc_fixed_fast;
    sc_out<sc_ufixed<16, 10, SC_RND, SC_SAT, 0> >       out_sc_ufixed;

 public:
    SC_HAS_PROCESS(sub);
    sub(sc_module_name name_)
        :sc_module(name_)
        INI_CHANNEL {
        Initialize();
        SC_METHOD(Action);
        sensitive_pos << clock;
    }
    virtual ~sub();

 public:
    void Action();
    void Initialize();
    void InitPort();
    void Reset();
};
#ifdef INI_CHANNEL
#undef INI_CHANNEL
#endif
#endif  // !defined(_SUB_H_)
