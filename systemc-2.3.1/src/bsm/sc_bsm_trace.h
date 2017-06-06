#ifndef sc_bsm_trace_H
#define sc_bsm_trace_H


#include <cstdio>
#include "sysc/tracing/sc_trace_file_base.h"
#include "sysc/utils/sc_pvector.h"

namespace sc_core {
    class sc_interface;
    class sc_port_base;
    class bsm_trace;  // defined in bsm_trace.cpp
    template<class T> class bsm_T_trace;

    // Print BSM error message
    void bsm_put_error_message(const char* msg, bool just_warning);


    // ----------------------------------------------------------------------------
    //  CLASS : bsm_trace_file
    //
    //  ...
    // ----------------------------------------------------------------------------

    class bsm_trace_file
        : public sc_trace_file_base
    {
    public:
        enum bsm_type { BT_VCD, BT_SIMPLE };
        enum bsm_enum { BSM_WIRE = 0, BSM_REAL = 1, BSM_LAST };
        void sc_set_bsm_time_unit(int exponent10_seconds); // -7 -> 100ns

        // Create a Vcd trace file.
        // `Name' forms the base of the name to which `.bsm' is added.
        bsm_trace_file(const char *name, unsigned int type = BT_SIMPLE);

        // Flush results and close file.
        ~bsm_trace_file();

    protected:
        // perform format specific initialization
        virtual void do_initialize() {}
    public:

        // These are all virtual functions in sc_trace_file and
        // they need to be defined here.

        // Trace a boolean object (single bit)
        void trace(const bool& object, const std::string& name);

        // Trace a sc_bit object (single bit)
        virtual void trace(const sc_dt::sc_bit& object,
            const std::string& name);

        // Trace a sc_logic object (single bit)
        void trace(const sc_dt::sc_logic& object, const std::string& name);

        // Trace an unsigned char with the given width
        void trace(const unsigned char& object, const std::string& name,
            int width);

        // Trace an unsigned short with the given width
        void trace(const unsigned short& object, const std::string& name,
            int width);

        // Trace an unsigned int with the given width
        void trace(const unsigned int& object, const std::string& name,
            int width);

        // Trace an unsigned long with the given width
        void trace(const unsigned long& object, const std::string& name,
            int width);

        // Trace a signed char with the given width
        void trace(const char& object, const std::string& name, int width);

        // Trace a signed short with the given width
        void trace(const short& object, const std::string& name, int width);

        // Trace a signed int with the given width
        void trace(const int& object, const std::string& name, int width);

        // Trace a signed long with the given width
        void trace(const long& object, const std::string& name, int width);

        // Trace an int64 with a given width
        void trace(const sc_dt::int64& object, const std::string& name,
            int width);

        // Trace a uint64 with a given width
        void trace(const sc_dt::uint64& object, const std::string& name,
            int width);

        // Trace a float
        void trace(const float& object, const std::string& name);

        // Trace a double
        void trace(const double& object, const std::string& name);

        // Trace sc_dt::sc_uint_base
        void trace(const sc_dt::sc_uint_base& object,
            const std::string& name);

        // Trace sc_dt::sc_int_base
        void trace(const sc_dt::sc_int_base& object,
            const std::string& name);

        // Trace sc_dt::sc_unsigned
        void trace(const sc_dt::sc_unsigned& object,
            const std::string& name);

        // Trace sc_dt::sc_signed
        void trace(const sc_dt::sc_signed& object, const std::string& name);

        // Trace sc_dt::sc_fxval
        void trace(const sc_dt::sc_fxval& object, const std::string& name);

        // Trace sc_dt::sc_fxval_fast
        void trace(const sc_dt::sc_fxval_fast& object,
            const std::string& name);

        // Trace sc_dt::sc_fxnum
        void trace(const sc_dt::sc_fxnum& object, const std::string& name);

        // Trace sc_dt::sc_fxnum_fast
        void trace(const sc_dt::sc_fxnum_fast& object,
            const std::string& name);

        template<class T>
        void traceT(const T& object, const std::string& name,
            bsm_enum type = BSM_WIRE)
        {
            if(initialized)
                bsm_put_error_message("No traces can be added once simulation has"
                    " started.\nTo add traces, create a new bsm trace file.", false);
            else
                traces.push_back(new bsm_T_trace<T>(object, name, obtain_name(), type, bsm_print_type));
        }

        // Trace sc_dt::sc_bv_base (sc_dt::sc_bv)
        virtual void trace(const sc_dt::sc_bv_base& object,
            const std::string& name);

        // Trace sc_dt::sc_lv_base (sc_dt::sc_lv)
        virtual void trace(const sc_dt::sc_lv_base& object,
            const std::string& name);
        // Trace an enumerated object - where possible output the enumeration literals
        // in the trace file. Enum literals is a null terminated array of null
        // terminated char* literal strings.
        void trace(const unsigned& object, const std::string& name,
            const char** enum_literals);

        void trace(const sc_interface* object, const std::string& name);
        void trace(const sc_port_base* object, const std::string& name);
        // Output a comment to the trace file
        void write_comment(const std::string& comment);

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
        FILE* fp;

        double timescale_unit;      // in seconds
        bool timescale_set_by_user; // = 1 means set by user
        bool trace_delta_cycles;    // = 1 means trace the delta cycles

        unsigned bsm_name_index;    // Number of variables traced
        // Previous time unit as 64-bit integer
        unsigned previous_time_units_low, previous_time_units_high; 

    public:
        // Array to store the variables traced
        sc_pvector<bsm_trace*> traces;
        bool initialized;           // = 1 means initialized
        // same as create_bsm_name (corrected style)
        std::string obtain_name();

    public:
        void set_bsm_trace_type(int index,
            unsigned int nTrigger,
            unsigned int nTrace);
        void set_bsm_print_type(unsigned int type);
        unsigned int bsm_print_type;
        bool    bsm_trace_enable;
        void    enable_bsm_trace(bool bEnable = true);
        bool    is_enable_bsm_trace() { return bsm_trace_enable; }
    };
    // ----------------------------------------------------------------------------

    // Create BSM file
    extern sc_trace_file *sc_create_bsm_trace_file(const char* name, 
                                unsigned int type = bsm_trace_file::BT_SIMPLE);
    extern void sc_close_bsm_trace_file(sc_trace_file* tf);
    extern bool bsm_trace_object(bsm_trace_file *tf, sc_object* scObj);
} // namespace sc_core
#endif
