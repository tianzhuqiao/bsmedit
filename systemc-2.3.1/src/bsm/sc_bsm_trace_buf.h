#ifndef SC_BSM_TRACE_BUF_H
#define SC_BSM_TRACE_BUF_H


#include <cstdio>
#include "sysc/utils/sc_pvector.h"
class bsm_buf_write_inf;
namespace sc_core {
    class sc_interface;
    class sc_port_base;
    class buf_trace;  // defined in buf_trace.cpp
    template<class T> class buf_T_trace;

    // Print BSM error message
    void buf_put_error_message(const char* msg, bool just_warning);


    // ----------------------------------------------------------------------------
    //  CLASS : bsm_trace_buf
    //
    //  ...
    // ----------------------------------------------------------------------------

    class bsm_trace_buf
        //: public sc_trace_file
    {
    public:

        enum bsm_enum { BSM_WIRE = 0, BSM_REAL = 1, BSM_LAST };
        void sc_set_bsm_time_unit(int exponent10_seconds); // -7 -> 100ns

        // Create a Vcd trace file.
        // `Name' forms the base of the name to which `.bsm' is added.
        bsm_trace_buf(const char *name);

        // Flush results and close file.
        ~bsm_trace_buf();

    public:


        // These are all virtual functions in sc_trace_file and
        // they need to be defined here.

        // Trace a boolean object (single bit)
        void trace(const bool& object);

        // Trace a sc_bit object (single bit)
        virtual void trace(const sc_dt::sc_bit& object);

        // Trace a sc_logic object (single bit)
        void trace(const sc_dt::sc_logic& object);

        // Trace an unsigned char with the given width
        void trace(const unsigned char& object, int width);

        // Trace an unsigned short with the given width
        void trace(const unsigned short& object, int width);

        // Trace an unsigned int with the given width
        void trace(const unsigned int& object, int width);

        // Trace an unsigned long with the given width
        void trace(const unsigned long& object, int width);

        // Trace a signed char with the given width
        void trace(const char& object, int width);

        // Trace a signed short with the given width
        void trace(const short& object, int width);

        // Trace a signed int with the given width
        void trace(const int& object, int width);

        // Trace a signed long with the given width
        void trace(const long& object, int width);

        // Trace an int64 with a given width
        void trace(const sc_dt::int64& object, int width);

        // Trace a uint64 with a given width
        void trace(const sc_dt::uint64& object, int width);

        // Trace a float
        void trace(const float& object);

        // Trace a double
        void trace(const double& object);

        // Trace sc_dt::sc_uint_base
        void trace(const sc_dt::sc_uint_base& object);

        // Trace sc_dt::sc_int_base
        void trace(const sc_dt::sc_int_base& object);

        // Trace sc_dt::sc_unsigned
        void trace(const sc_dt::sc_unsigned& object);

        // Trace sc_dt::sc_signed
        void trace(const sc_dt::sc_signed& object);

        // Trace sc_dt::sc_fxval
        void trace(const sc_dt::sc_fxval& object);

        // Trace sc_dt::sc_fxval_fast
        void trace(const sc_dt::sc_fxval_fast& object);

        // Trace sc_dt::sc_fxnum
        void trace(const sc_dt::sc_fxnum& object);

        // Trace sc_dt::sc_fxnum_fast
        void trace(const sc_dt::sc_fxnum_fast& object);

        template<class T>
        void traceT(const T& object)
        {
            if(initialized)
                buf_put_error_message("No traces can be added once simulation has"
                    " started.\nTo add traces, create a new bsm trace file.", false);
            else
                traces.push_back(new buf_T_trace<T>(object));
        }

        // Trace sc_dt::sc_bv_base (sc_dt::sc_bv)
        virtual void trace(const sc_dt::sc_bv_base& object);

        // Trace sc_dt::sc_lv_base (sc_dt::sc_lv)
        virtual void trace(const sc_dt::sc_lv_base& object);
        // Trace an enumerated object - where possible output the enumeration literals
        // in the trace file. Enum literals is a null terminated array of null
        // terminated char* literal strings.
        void trace(const unsigned& object, const char** enum_literals);

        void trace(const sc_interface* object);
        void trace(const sc_port_base* object);


        // Also trace transitions between delta cycles if flag is true.
        void delta_cycles(bool flag);

        // Write trace info for cycle.
        void cycle(bool delta_cycle);

    private:

        // Initialize the tracing
        void initialize();
        // Create BSM names for each variable
        void create_bsm_name(std::string* p_destination);

        // Pointer to the file that needs to be written
        bsm_buf_write_inf* buf;

        double timescale_unit;      // in seconds
        bool timescale_set_by_user; // = 1 means set by user
        bool trace_delta_cycles;    // = 1 means trace the delta cycles

        unsigned bsm_name_index;    // Number of variables traced

        unsigned previous_time_units_low, previous_time_units_high; // Previous time unit as 64-bit integer

    public:

        // Array to store the variables traced
        sc_pvector<buf_trace*> traces;
        bool initialized;           // = 1 means initialized

        void set_bsm_trace_type(int index,
            unsigned int nTrigger,
            unsigned int nTrace);
        void set_bsm_buffer(bsm_buf_write_inf* f) { buf = f; }
        bool    bsm_trace_enable;
        void    enable_bsm_trace(bool bEnable = true) { bsm_trace_enable = bEnable; }
        bool    is_enable_bsm_trace() { return bsm_trace_enable; }
    };


    // ----------------------------------------------------------------------------

    // Create BSM file
    extern bsm_trace_buf *sc_create_bsm_trace_buf(const char* name);
    extern void sc_close_bsm_trace_buf(bsm_trace_buf* tf);
    extern bool bsm_trace_buf_object(bsm_trace_buf *tf, sc_object* scObj);


    // ----------------------------------------------------------------------------
    /*****************************************************************************/

    // Now comes all the SystemC defined tracing functions.
    // We define two sc_trace() versions for scalar types; one where the object to
    // be traced is passed as a reference and the other where a pointer to the
    // tracing object is passed.

#define DECL_TRACE_BUF_FUNC_REF_A(tp)     \
void sc_trace_buf( bsm_trace_buf* tf, const tp& object);

#define DECL_TRACE_BUF_FUNC_PTR_A(tp)     \
void sc_trace_buf( bsm_trace_buf* tf, const tp* object );        \

#define DECL_TRACE_BUF_FUNC_A(tp)         \
DECL_TRACE_BUF_FUNC_REF_A(tp)             \
DECL_TRACE_BUF_FUNC_PTR_A(tp)


    DECL_TRACE_BUF_FUNC_A(sc_dt::sc_bit)
    DECL_TRACE_BUF_FUNC_A(sc_dt::sc_logic)

    DECL_TRACE_BUF_FUNC_A(sc_dt::sc_int_base)
    DECL_TRACE_BUF_FUNC_A(sc_dt::sc_uint_base)
    DECL_TRACE_BUF_FUNC_A(sc_dt::sc_signed)
    DECL_TRACE_BUF_FUNC_A(sc_dt::sc_unsigned)

    DECL_TRACE_BUF_FUNC_REF_A(sc_dt::sc_bv_base)
    DECL_TRACE_BUF_FUNC_REF_A(sc_dt::sc_lv_base)


#undef DECL_TRACE_BUF_FUNC_REF_A
#undef DECL_TRACE_BUF_FUNC_PTR_A
#undef DECL_TRACE_BUF_FUNC_A


#define DEFN_TRACE_BUF_FUNC_REF_A(tp)                                         \
inline void sc_trace_buf( bsm_trace_buf* tf, const tp& object)                \
{                                                                             \
    if( tf ) {                                                                \
        tf->trace( object );                                                  \
    }                                                                         \
}

#define DEFN_TRACE_BUF_FUNC_PTR_A(tp)                                         \
inline void sc_trace_buf( bsm_trace_buf* tf, const tp* object )               \
{                                                                             \
    if( tf ) {                                                                \
        tf->trace( *object );                                                 \
    }                                                                         \
}

#define DEFN_TRACE_BUF_FUNC_A(tp)                                             \
DEFN_TRACE_BUF_FUNC_REF_A(tp)                                                 \
DEFN_TRACE_BUF_FUNC_PTR_A(tp)


#define DEFN_TRACE_BUF_FUNC_REF_B(tp)                                         \
inline void sc_trace_buf( bsm_trace_buf* tf, const tp& object,   \
          int width = 8 * sizeof( tp ) )                                      \
{                                                                             \
    if( tf ) {                                                                \
        tf->trace( object,  width );                                          \
    }                                                                         \
}

#define DEFN_TRACE_BUF_FUNC_PTR_B(tp)                                         \
inline void sc_trace_buf( bsm_trace_buf* tf, const tp* object,   \
          int width = 8 * sizeof( tp ) )                                      \
{                                                                             \
    if( tf ) {                                                                \
        tf->trace( *object,  width );                                         \
    }                                                                         \
}


#define DEFN_TRACE_BUF_FUNC_B(tp)                                             \
DEFN_TRACE_BUF_FUNC_REF_B(tp)                                                 \
DEFN_TRACE_BUF_FUNC_PTR_B(tp)

    DEFN_TRACE_BUF_FUNC_A(bool)
    DEFN_TRACE_BUF_FUNC_A(float)
    DEFN_TRACE_BUF_FUNC_A(double)
    
    DEFN_TRACE_BUF_FUNC_B(unsigned char)
    DEFN_TRACE_BUF_FUNC_B(unsigned short)
    DEFN_TRACE_BUF_FUNC_B(unsigned int)
    DEFN_TRACE_BUF_FUNC_B(unsigned long)
    DEFN_TRACE_BUF_FUNC_B(char)
    DEFN_TRACE_BUF_FUNC_B(short)
    DEFN_TRACE_BUF_FUNC_B(int)
    DEFN_TRACE_BUF_FUNC_B(long)
    DEFN_TRACE_BUF_FUNC_B(sc_dt::int64)
    DEFN_TRACE_BUF_FUNC_B(sc_dt::uint64)


#undef DEFN_TRACE_BUF_FUNC_REF_A
#undef DEFN_TRACE_BUF_FUNC_PTR_A
#undef DEFN_TRACE_BUF_FUNC_A

#undef DEFN_TRACE_BUF_FUNC_REF_B
#undef DEFN_TRACE_BUF_FUNC_PTR_B
#undef DEFN_TRACE_BUF_FUNC_B

    // ----------------------------------------------------------------------------
    template <class T>
    inline void sc_trace_buf(bsm_trace_buf* tf, const sc_signal_in_if<T>& object)
    {
        sc_trace_buf(tf, object.get_data_ref());
    }

    // specializations for signals of type char, short, int, long
    void sc_trace_buf(bsm_trace_buf* tf,
        const sc_signal_in_if<char>& object,
        int width);

    void sc_trace_buf(bsm_trace_buf* tf,
        const sc_signal_in_if<short>& object,
        int width);

    void sc_trace_buf(bsm_trace_buf* tf,
        const sc_signal_in_if<int>& object,
        int width);

    void sc_trace_buf(bsm_trace_buf* tf,
        const sc_signal_in_if<long>& object,
        int width);


    // 1. non-template function is better than template
    // 2. more-specialized template is better than less-specialized
    // 3. no partial specialization for template functions


    // Trace an enumerated object - where possible output the enumeration literals
    // in the trace file. Enum literals is a null terminated array of null
    // terminated char* literal strings.

    void sc_trace_buf(bsm_trace_buf* tf, const unsigned int& object,
                     const char** enum_literals);


    // Dummy function for arbitrary types of value, does nothing

    extern void sc_trace_buf(bsm_trace_buf* tf, const void* object);

} // namespace sc_core
#endif
