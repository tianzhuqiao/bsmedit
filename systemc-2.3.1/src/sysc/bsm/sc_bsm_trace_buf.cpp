#include <assert.h>
#include <time.h>
#include <cstdlib>

#include "sysc/kernel/sc_simcontext.h"
#include "sysc/kernel/sc_ver.h"
#include "sysc/datatypes/bit/sc_bit.h"
#include "sysc/datatypes/bit/sc_logic.h"
#include "sysc/datatypes/bit/sc_lv_base.h"
#include "sysc/datatypes/int/sc_signed.h"
#include "sysc/datatypes/int/sc_unsigned.h"
#include "sysc/datatypes/int/sc_int_base.h"
#include "sysc/datatypes/int/sc_uint_base.h"
#include "sysc/datatypes/fx/fx.h"
#include "sysc/bsm/sc_bsm_trace_buf.h"
#include "sysc/utils/sc_string.h"
#include "sysc/communication/sc_interface.h"
#include "sysc/communication/sc_port.h"
#include "sysc/communication/sc_signal_ports.h"
#include "sysc/communication/sc_signal.h"
#include "sysc/datatypes/bit/sc_logic.h"
#include "sysc/datatypes/bit/sc_bit.h"
#include "sysc/tracing/sc_trace_file_base.h"
#include "sysc/bsm/bsm_buffer_intf.h"
namespace sc_core {

    static bool running_regression = false;

    // Forward declarations for functions that come later in the file
    // Map sc_dt::sc_logic to printable BSM
    //static char map_sc_logic_state_to_bsm_state(char in_char);



    // ----------------------------------------------------------------------------
    //  CLASS : buf_trace
    //
    //  Base class for BSM traces.
    // ----------------------------------------------------------------------------

    class buf_trace
    {
    public:
        enum bsm_trace_type {
            BSM_TRACE_ORIG = 0,
            BSM_TRACE_VAL
        };
        enum bsm_trigger_type {
            BSM_TRIGGER_VAL_POS = 0,
            BSM_TRIGGER_VAL_NEG,
            BSM_TRIGGER_VAL_BOTH,
            BSM_TRIGGER_VAL_NONE
        };
        buf_trace(const unsigned trace_type_ = BSM_TRACE_ORIG,
            const unsigned trigger_type_ = BSM_TRIGGER_VAL_BOTH);

        // Needs to be pure virtual as has to be defined by the particular
        // type being traced
        virtual void write(bsm_buf_write_inf* f) = 0;

        virtual void set_width();

        // Comparison function needs to be pure virtual too
        virtual bool changed() = 0;

        virtual ~buf_trace();

        int bit_width;

        unsigned int bsm_trace_type;//0 original, 1 valid
        virtual void set_trace_type(unsigned int nType) {
            bsm_trace_type = nType;
        }
        virtual unsigned int get_trace_type() {
            return bsm_trace_type;
        }
        //0  valid -- pos edge, 1 valid --neg edge, 2 valid signal -- both edge
        unsigned int bsm_trigger_type;
        virtual void set_trigger_type(unsigned int nType) {
            bsm_trigger_type = nType;
        }
        virtual unsigned int get_trigger_type() {
            return bsm_trigger_type;
        }
    };


    buf_trace::buf_trace(const unsigned trace_type_, const unsigned trigger_type_)
        :bit_width(0)
        , bsm_trace_type(trace_type_)
        , bsm_trigger_type(trigger_type_)
    {
        /* Intentionally blank */
    }

    void buf_trace::set_width()
    {
        /* Intentionally Blank, should be defined for each type separately */
    }

    buf_trace::~buf_trace()
    {
        /* Intentionally Blank */
    }


    template <class T>
    class buf_T_trace : public buf_trace
    {
    public:

        buf_T_trace(const T& object_,
            const unsigned trace_type_ = BSM_TRACE_ORIG)
            : buf_trace(trace_type_),
            object(object_),
            old_value(object_)
        {
        }

        void write(bsm_buf_write_inf* f) {
            if(f) {
                float v;
                sscanf(object.to_string().c_str(), "%g", &v);
                f->append((double)v);
            }
            old_value = object;
        }

        bool changed() { return !(object == old_value); }

        void set_width() { bit_width = object.length(); }

    protected:

        const T& object;
        T        old_value;
    };

    typedef buf_T_trace<sc_dt::sc_bv_base> buf_sc_bv_trace;
    typedef buf_T_trace<sc_dt::sc_lv_base> buf_sc_lv_trace;

    // Trace sc_dt::sc_bv_base (sc_dt::sc_bv)
    void bsm_trace_buf::trace(
        const sc_dt::sc_bv_base& object)
    {
        traceT(object);
    }

    // Trace sc_dt::sc_lv_base (sc_dt::sc_lv)
    void bsm_trace_buf::trace(
        const sc_dt::sc_lv_base& object)
    {
        traceT(object);
    }

    /*****************************************************************************/
#define TRACE_CHANGED_IMPLEMENT() \
bool changed()\
{\
    if(object != old_value) {\
        if((bsm_trigger_type == BSM_TRIGGER_VAL_BOTH) ||\
            (bsm_trigger_type == BSM_TRIGGER_VAL_POS&&object > old_value) ||\
            (bsm_trigger_type == BSM_TRIGGER_VAL_NEG&&object < old_value))\
        {\
            return true;\
        } else {\
            write(NULL);\
        }\
    }\
    return false;\
}

    class buf_bool_trace : public buf_trace {
    public:
        buf_bool_trace(const bool& object_,
            const unsigned trace_type_ = BSM_TRACE_ORIG
        );
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const bool& object;
        bool old_value;
    };

    buf_bool_trace::buf_bool_trace(const bool& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = 1;
        old_value = object;
    }

    void buf_bool_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object == true ? 1.0 : 0.0);
        old_value = object;
    }

    //*****************************************************************************

    class buf_sc_bit_trace : public buf_trace {
    public:
        buf_sc_bit_trace(const sc_dt::sc_bit&,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const sc_dt::sc_bit& object;
        sc_dt::sc_bit old_value;
    };

    buf_sc_bit_trace::buf_sc_bit_trace(const sc_dt::sc_bit& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = 1;
        old_value = object;
    }

    void buf_sc_bit_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object == true ? 1.0 : 0.0);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_sc_logic_trace : public buf_trace {
    public:
        buf_sc_logic_trace(const sc_dt::sc_logic& object_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        bool changed();

    protected:
        const sc_dt::sc_logic& object;
        sc_dt::sc_logic old_value;
    };


    buf_sc_logic_trace::buf_sc_logic_trace(const sc_dt::sc_logic& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = 1;
        old_value = object;
    }


    bool buf_sc_logic_trace::changed()
    {
        if(object != old_value) {
            if((bsm_trigger_type == BSM_TRIGGER_VAL_BOTH) ||
                (bsm_trigger_type == BSM_TRIGGER_VAL_POS&&object == 1 && old_value == 0) ||
                (bsm_trigger_type == BSM_TRIGGER_VAL_NEG&&object == 0 && old_value == 1)) {
                return true;
            } else {
                write(NULL);
            }
        }
        return false;
    }


    void buf_sc_logic_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_bool() ? 1.0 : 0.0);
        old_value = object;
    }


    /*****************************************************************************/

    class buf_sc_unsigned_trace : public buf_trace {
    public:
        buf_sc_unsigned_trace(const sc_dt::sc_unsigned& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();
        void set_width();

    protected:
        const sc_dt::sc_unsigned& object;
        sc_dt::sc_unsigned old_value;
    };


    buf_sc_unsigned_trace::buf_sc_unsigned_trace(const sc_dt::sc_unsigned& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_), old_value(object_.length())
        // The last may look strange, but is correct
    {
        old_value = object;
    }

    void buf_sc_unsigned_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    void buf_sc_unsigned_trace::set_width()
    {
        bit_width = object.length();
    }


    /*****************************************************************************/

    class buf_sc_signed_trace : public buf_trace {
    public:
        buf_sc_signed_trace(const sc_dt::sc_signed& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();
        void set_width() { bit_width = object.length(); }

    protected:
        const sc_dt::sc_signed& object;
        sc_dt::sc_signed old_value;
    };


    buf_sc_signed_trace::buf_sc_signed_trace(const sc_dt::sc_signed& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_), old_value(object_.length())
    {
        old_value = object;
    }

    void buf_sc_signed_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    /*****************************************************************************/

    class buf_sc_uint_base_trace : public buf_trace {
    public:
        buf_sc_uint_base_trace(const sc_dt::sc_uint_base& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();
        void set_width() { bit_width = object.length(); }

    protected:
        const sc_dt::sc_uint_base& object;
        sc_dt::sc_uint_base old_value;
    };


    buf_sc_uint_base_trace::buf_sc_uint_base_trace(
        const sc_dt::sc_uint_base& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_), old_value(object_.length())
        // The last may look strange, but is correct
    {
        old_value = object;
    }


    void buf_sc_uint_base_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    /*****************************************************************************/

    class buf_sc_int_base_trace : public buf_trace {
    public:
        buf_sc_int_base_trace(const sc_dt::sc_int_base& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();
        void set_width() { bit_width = object.length(); }

    protected:
        const sc_dt::sc_int_base& object;
        sc_dt::sc_int_base old_value;
    };


    buf_sc_int_base_trace::buf_sc_int_base_trace(const sc_dt::sc_int_base& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_), old_value(object_.length())
    {
        old_value = object;
    }

    void buf_sc_int_base_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    /*****************************************************************************/

    class buf_sc_fxval_trace : public buf_trace
    {
    public:

        buf_sc_fxval_trace(const sc_dt::sc_fxval& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:

        const sc_dt::sc_fxval& object;
        sc_dt::sc_fxval old_value;

    };

    buf_sc_fxval_trace::buf_sc_fxval_trace(const sc_dt::sc_fxval& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_),
        object(object_)
    {
        bit_width = 1;
        old_value = object;
    }

    void buf_sc_fxval_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    /*****************************************************************************/

    class buf_sc_fxval_fast_trace : public buf_trace
    {
    public:

        buf_sc_fxval_fast_trace(const sc_dt::sc_fxval_fast& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:

        const sc_dt::sc_fxval_fast& object;
        sc_dt::sc_fxval_fast old_value;

    };

    buf_sc_fxval_fast_trace::buf_sc_fxval_fast_trace(
        const sc_dt::sc_fxval_fast& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_),
        object(object_)
    {
        bit_width = 1;
        old_value = object;
    }

    void buf_sc_fxval_fast_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    /*****************************************************************************/

    class buf_sc_fxnum_trace : public buf_trace
    {
    public:

        buf_sc_fxnum_trace(const sc_dt::sc_fxnum& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();
        void set_width() { bit_width = object.wl(); }

    protected:

        const sc_dt::sc_fxnum& object;
        sc_dt::sc_fxnum old_value;

    };

    buf_sc_fxnum_trace::buf_sc_fxnum_trace(const sc_dt::sc_fxnum& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_),
        object(object_),
        old_value(object_.m_params.type_params(),
            object_.m_params.enc(),
            object_.m_params.cast_switch(),
            0)
    {
        old_value = object;
    }

    void buf_sc_fxnum_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    /*****************************************************************************/

    class buf_sc_fxnum_fast_trace : public buf_trace
    {
    public:

        buf_sc_fxnum_fast_trace(const sc_dt::sc_fxnum_fast& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();
        void set_width() { bit_width = object.wl(); }

    protected:

        const sc_dt::sc_fxnum_fast& object;
        sc_dt::sc_fxnum_fast old_value;

    };

    buf_sc_fxnum_fast_trace::buf_sc_fxnum_fast_trace(
        const sc_dt::sc_fxnum_fast& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_),
        object(object_),
        old_value(object_.m_params.type_params(),
            object_.m_params.enc(),
            object_.m_params.cast_switch(),
            0)
    {
        old_value = object;
    }

    void buf_sc_fxnum_fast_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object.to_double());
        old_value = object;
    }

    /*****************************************************************************/

    class buf_unsigned_int_trace : public buf_trace {
    public:
        buf_unsigned_int_trace(const unsigned& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const unsigned& object;
        unsigned old_value;
        unsigned mask;
    };


    buf_unsigned_int_trace::buf_unsigned_int_trace(
        const unsigned& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 32) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xffffffff;
        }

        old_value = object;
    }


    void buf_unsigned_int_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_unsigned_short_trace : public buf_trace {
    public:
        buf_unsigned_short_trace(const unsigned short& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const unsigned short& object;
        unsigned short old_value;
        unsigned short mask;
    };


    buf_unsigned_short_trace::buf_unsigned_short_trace(
        const unsigned short& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 16) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xffff;
        }

        old_value = object;
    }

    void buf_unsigned_short_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_unsigned_char_trace : public buf_trace {
    public:
        buf_unsigned_char_trace(const unsigned char& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const unsigned char& object;
        unsigned char old_value;
        unsigned char mask;
    };


    buf_unsigned_char_trace::buf_unsigned_char_trace(
        const unsigned char& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 8) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xff;
        }

        old_value = object;
    }

    void buf_unsigned_char_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_unsigned_long_trace : public buf_trace {
    public:
        buf_unsigned_long_trace(const unsigned long& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const unsigned long& object;
        unsigned long old_value;
        unsigned long mask;
    };

    buf_unsigned_long_trace::buf_unsigned_long_trace(
        const unsigned long& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 32) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xffffffff;
        }

        old_value = object;
    }

    void buf_unsigned_long_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_signed_int_trace : public buf_trace {
    public:
        buf_signed_int_trace(const int& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const int& object;
        int old_value;
        unsigned mask;
    };

    buf_signed_int_trace::buf_signed_int_trace(const signed& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 32) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xffffffff;
        }

        old_value = object;
    }

    void buf_signed_int_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_signed_short_trace : public buf_trace {
    public:
        buf_signed_short_trace(const short& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const short& object;
        short old_value;
        unsigned short mask;
    };


    buf_signed_short_trace::buf_signed_short_trace(
        const short& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 16) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xffff;
        }

        old_value = object;
    }

    void buf_signed_short_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_signed_char_trace : public buf_trace {
    public:
        buf_signed_char_trace(const char& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const char& object;
        char old_value;
        unsigned char mask;
    };


    buf_signed_char_trace::buf_signed_char_trace(const char& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 8) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xff;
        }

        old_value = object;
    }

    void buf_signed_char_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_int64_trace : public buf_trace {
    public:
        buf_int64_trace(const sc_dt::int64& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const sc_dt::int64& object;
        sc_dt::int64 old_value;
        sc_dt::uint64 mask;
    };


    buf_int64_trace::buf_int64_trace(const sc_dt::int64& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        mask = (sc_dt::uint64) - 1;
        if(bit_width < 64)  mask = ~(mask << bit_width);

        old_value = object;
    }

    void buf_int64_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }

    /*****************************************************************************/
    class buf_uint64_trace : public buf_trace {
    public:
        buf_uint64_trace(const sc_dt::uint64& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const sc_dt::uint64& object;
        sc_dt::uint64 old_value;
        sc_dt::uint64 mask;
    };


    buf_uint64_trace::buf_uint64_trace(const sc_dt::uint64& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        mask = (sc_dt::uint64) - 1;
        if(bit_width < 64) mask = ~(mask << bit_width);

        old_value = object;
    }

    void buf_uint64_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }


    /*****************************************************************************/

    class buf_signed_long_trace : public buf_trace {
    public:
        buf_signed_long_trace(const long& object,
            int width_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const long& object;
        long old_value;
        unsigned long mask;
    };


    buf_signed_long_trace::buf_signed_long_trace(const long& object_,
        int width_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = width_;
        if(bit_width < 32) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xffffffff;
        }

        old_value = object;
    }

    void buf_signed_long_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append((double)object);
        old_value = object;
    }


    /*****************************************************************************/

    class buf_float_trace : public buf_trace {
    public:
        buf_float_trace(const float& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const float& object;
        float old_value;
    };

    buf_float_trace::buf_float_trace(const float& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = 1;
        old_value = object;
    }

    void buf_float_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object);
        old_value = object;
    }

    /*****************************************************************************/

    class buf_double_trace : public buf_trace {
    public:
        buf_double_trace(const double& object,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const double& object;
        double old_value;
    };

    buf_double_trace::buf_double_trace(const double& object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = 1;
        old_value = object;
    }

    void buf_double_trace::write(bsm_buf_write_inf* f)
    {
        if(f)f->append(object);
        old_value = object;
    }


    /*****************************************************************************/

    class buf_enum_trace : public buf_trace {
    public:
        buf_enum_trace(const unsigned& object_,
            const char** enum_literals,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        TRACE_CHANGED_IMPLEMENT();

    protected:
        const unsigned& object;
        unsigned old_value;
        unsigned mask;
        const char** literals;
        unsigned nliterals;
    };


    buf_enum_trace::buf_enum_trace(const unsigned& object_,
        const char** enum_literals_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_), literals(enum_literals_)
    {
        // find number of bits required to represent enumeration literal - counting loop
        for(nliterals = 0; enum_literals_[nliterals]; nliterals++);

        // Figure out number of bits required to represent the number of literals
        bit_width = 0;
        unsigned shifted_maxindex = nliterals - 1;
        while(shifted_maxindex != 0) {
            shifted_maxindex >>= 1;
            bit_width++;
        }

        // Set the mask
        if(bit_width < 32) {
            mask = ~(-1 << bit_width);
        } else {
            mask = 0xffffffff;
        }

        old_value = object;
    }

    void buf_enum_trace::write(bsm_buf_write_inf* f)
    {
        if(f) f->append(object);
        old_value = object;
    }


    /*****************************************************************************
               bsm_trace_buf functions
     *****************************************************************************/

    bsm_trace_buf::bsm_trace_buf(const char *name)
    {
        trace_delta_cycles = false; // Make this the default
        initialized = false;
        bsm_name_index = 0;

        // default time step is the time resolution
        timescale_unit = sc_get_time_resolution().to_seconds();

        timescale_set_by_user = false;

        bsm_trace_enable = true;
    }


    void bsm_trace_buf::initialize()
    {
        running_regression = (getenv("SYSTEMC_REGRESSION") != NULL);
        // Don't print message if running regression
        if(!timescale_set_by_user && !running_regression) {
            ::std::cout << "WARNING: Default time step is used for BSM tracing." << ::std::endl;
        }
        //variable definitions:
        int i;
        for(i = 0; i < (int)traces.size(); i++) {
            buf_trace* t = traces[i];
            t->set_width(); // needed for all vectors
        }

        double inittime = sc_time_stamp().to_seconds();
        double_to_special_int64(inittime / timescale_unit,
            &previous_time_units_high,
            &previous_time_units_low);

        for(i = 0; i < (int)traces.size(); i++) {
            buf_trace* t = traces[i];
            if(t->get_trace_type() == buf_trace::BSM_TRACE_ORIG) {
                t->write(buf);
                //fputc('\n', fp);
            } else
                t->write(NULL);
        }
    }


    void bsm_trace_buf::sc_set_bsm_time_unit(int exponent10_seconds)
    {
        if(initialized) {
            buf_put_error_message("BSM trace timescale unit cannot be changed once tracing has begun.\n"
                "To change the scale, create a new trace file.",
                false);
            return;
        }


        if(exponent10_seconds < -15 || exponent10_seconds >  2) {
            buf_put_error_message("set_bsm_time_unit() has valid exponent range -15...+2.", false);
            return;
        }

        if(exponent10_seconds == -15) timescale_unit = 1e-15;
        else if(exponent10_seconds == -14) timescale_unit = 1e-14;
        else if(exponent10_seconds == -13) timescale_unit = 1e-13;
        else if(exponent10_seconds == -12) timescale_unit = 1e-12;
        else if(exponent10_seconds == -11) timescale_unit = 1e-11;
        else if(exponent10_seconds == -10) timescale_unit = 1e-10;
        else if(exponent10_seconds == -9) timescale_unit = 1e-9;
        else if(exponent10_seconds == -8) timescale_unit = 1e-8;
        else if(exponent10_seconds == -7) timescale_unit = 1e-7;
        else if(exponent10_seconds == -6) timescale_unit = 1e-6;
        else if(exponent10_seconds == -5) timescale_unit = 1e-5;
        else if(exponent10_seconds == -4) timescale_unit = 1e-4;
        else if(exponent10_seconds == -3) timescale_unit = 1e-3;
        else if(exponent10_seconds == -2) timescale_unit = 1e-2;
        else if(exponent10_seconds == -1) timescale_unit = 1e-1;
        else if(exponent10_seconds == 0) timescale_unit = 1e0;
        else if(exponent10_seconds == 1) timescale_unit = 1e1;
        else if(exponent10_seconds == 2) timescale_unit = 1e2;

        char buf[200];
        snprintf(buf, 200,
            "Note: BSM trace timescale unit is set by user to 1e%d sec.\n",
            exponent10_seconds);
        ::std::cout << buf << ::std::flush;
        timescale_set_by_user = true;
    }


    // ----------------------------------------------------------------------------

#define DEFN_TRACE_BUF_METHOD(tp)                                             \
void                                                                          \
bsm_trace_buf::trace(const tp& object_)                                       \
{                                                                             \
    if( initialized ) {                                                       \
        buf_put_error_message(                                                \
        "No traces can be added once simulation has started.\n"               \
            "To add traces, create a new bsm trace file.", false );           \
    }                                                                         \
    traces.push_back( new buf_ ## tp ## _trace( object_) );                   \
}

    DEFN_TRACE_BUF_METHOD(bool)
        DEFN_TRACE_BUF_METHOD(float)
        DEFN_TRACE_BUF_METHOD(double)

#undef DEFN_TRACE_BUF_METHOD
#define DEFN_TRACE_BUF_METHOD(tp)                                             \
void                                                                          \
bsm_trace_buf::trace(const sc_dt::tp& object_)                                \
{                                                                             \
    if( initialized ) {                                                       \
        buf_put_error_message(                                                \
        "No traces can be added once simulation has started.\n"               \
            "To add traces, create a new bsm trace file.", false );           \
    }                                                                         \
    traces.push_back( new buf_ ## tp ## _trace( object_ ) );                  \
}

        DEFN_TRACE_BUF_METHOD(sc_bit)
        DEFN_TRACE_BUF_METHOD(sc_logic)

        DEFN_TRACE_BUF_METHOD(sc_signed)
        DEFN_TRACE_BUF_METHOD(sc_unsigned)
        DEFN_TRACE_BUF_METHOD(sc_int_base)
        DEFN_TRACE_BUF_METHOD(sc_uint_base)

        DEFN_TRACE_BUF_METHOD(sc_fxval)
        DEFN_TRACE_BUF_METHOD(sc_fxval_fast)
        DEFN_TRACE_BUF_METHOD(sc_fxnum)
        DEFN_TRACE_BUF_METHOD(sc_fxnum_fast)

#undef DEFN_TRACE_BUF_METHOD


#define DEFN_TRACE_BUF_METHOD_SIGNED(tp)                                      \
void                                                                          \
bsm_trace_buf::trace( const tp&        object_,                               \
                       int              width_ )                              \
{                                                                             \
    if( initialized ) {                                                       \
        buf_put_error_message(                                                \
        "No traces can be added once simulation has started.\n"               \
            "To add traces, create a new bsm trace file.", false );           \
    }                                                                         \
    traces.push_back( new buf_signed_ ## tp ## _trace( object_,               \
    width_) );                                                                \
}

#define DEFN_TRACE_BUF_METHOD_UNSIGNED(tp)                                    \
void                                                                          \
bsm_trace_buf::trace( const unsigned tp& object_,                             \
                       int                width_ )                            \
{                                                                             \
    if( initialized ) {                                                       \
        buf_put_error_message(                                                \
        "No traces can be added once simulation has started.\n"               \
            "To add traces, create a new bsm trace file.", false );           \
    }                                                                         \
    traces.push_back( new buf_unsigned_ ## tp ## _trace( object_,             \
    width_) );   \
}

        DEFN_TRACE_BUF_METHOD_SIGNED(char)
        DEFN_TRACE_BUF_METHOD_SIGNED(short)
        DEFN_TRACE_BUF_METHOD_SIGNED(int)
        DEFN_TRACE_BUF_METHOD_SIGNED(long)

        DEFN_TRACE_BUF_METHOD_UNSIGNED(char)
        DEFN_TRACE_BUF_METHOD_UNSIGNED(short)
        DEFN_TRACE_BUF_METHOD_UNSIGNED(int)
        DEFN_TRACE_BUF_METHOD_UNSIGNED(long)

#undef DEFN_BUF_TRACE_METHOD_SIGNED
#undef DEFN_BUF_TRACE_METHOD_UNSIGNED

#define DEFN_TRACE_BUF_METHOD_LONG_LONG(tp)                                   \
void                                                                          \
bsm_trace_buf::trace( const sc_dt::tp& object_,                               \
                       int                width_ )                            \
{                                                                             \
    if( initialized ) {                                                       \
        buf_put_error_message(                                                \
        "No traces can be added once simulation has started.\n"               \
            "To add traces, create a new bsm trace file.", false );           \
    }                                                                         \
    traces.push_back( new buf_ ## tp ## _trace( object_,                      \
                    width_) );                                                \
}
        DEFN_TRACE_BUF_METHOD_LONG_LONG(int64)
        DEFN_TRACE_BUF_METHOD_LONG_LONG(uint64)

#undef DEFN_TRACE_METHOD_LONG_LONG

        void bsm_trace_buf::trace(const unsigned& object_,
            const char** enum_literals_)
    {
        if(initialized) {
            buf_put_error_message(
                "No traces can be added once simulation has started.\n"
                "To add traces, create a new bsm trace file.", false);
        }
        traces.push_back(new buf_enum_trace(object_,
            enum_literals_));
    }

    void bsm_trace_buf::delta_cycles(bool flag)
    {
        trace_delta_cycles = flag;
    }

    void bsm_trace_buf::cycle(bool this_is_a_delta_cycle)
    {
        char message[4000];
        unsigned this_time_units_high, this_time_units_low;

        // Just to make g++ shut up in the optimized mode
        this_time_units_high = this_time_units_low = 0;

        // Trace delta cycles only when enabled
        if(!trace_delta_cycles && this_is_a_delta_cycle) return;

        // Check for initialization
        if(!initialized) {
            initialize();
            initialized = true;
            return;
        };


        double now_units = sc_time_stamp().to_seconds() / timescale_unit;
        unsigned now_units_high, now_units_low;
        double_to_special_int64(now_units, &now_units_high, &now_units_low);

        bool now_later_than_previous_time = false;
        if((now_units_low > previous_time_units_low
            && now_units_high == previous_time_units_high)
            || now_units_high > previous_time_units_high) {
            now_later_than_previous_time = true;
        }

        bool now_equals_previous_time = false;
        if(now_later_than_previous_time) {
            this_time_units_high = now_units_high;
            this_time_units_low = now_units_low;
        } else {
            if(now_units_low == previous_time_units_low &&
                now_units_high == previous_time_units_high) {
                now_equals_previous_time = true;
                this_time_units_high = now_units_high;
                this_time_units_low = now_units_low;
            }
        }

        // Since BSM does not understand 0 time progression, we have to fake
        // delta cycles with progressing time by one unit
        if(this_is_a_delta_cycle) {
            this_time_units_high = previous_time_units_high;
            this_time_units_low = previous_time_units_low + 1;
            if(this_time_units_low == 1000000000) {
                this_time_units_high++;
                this_time_units_low = 0;
            }
            static bool warned = false;
            if(!warned) {
                ::std::cout << "Note: BSM delta cycling with pseudo timesteps (1 unit) "
                    "is performed.\n" << ::std::endl;
                warned = true;
            }
        }


        // Not a delta cycle and time has not progressed
        if(!this_is_a_delta_cycle && now_equals_previous_time &&
            (now_units_high != 0 || now_units_low != 0)) {
            // Don't print the message at time zero
            static bool warned = false;
            if(!warned && !running_regression) {
                snprintf(message, 4000,
                    "Multiple cycles found with same (%u) time units count.\n"
                    "Waveform viewers will only show the states of the last one.\n"
                    "Use ((bsm_trace_buf*)bsmfile)->sc_set_bsm_time_unit(int exponent10_seconds)\n"
                    "to increase time resolution.",
                    now_units_low
                );
                buf_put_error_message(message, true);
                warned = true;
            }
        }

        // Not a delta cycle and time has gone backward
        // This will happen with large number of delta cycles between two real
        // advances of time
        if(!this_is_a_delta_cycle && !now_equals_previous_time &&
            !now_later_than_previous_time) {
            static bool warned = false;
            if(!warned) {
                snprintf(message, 4000,
                    "Cycle found with falling (%u -> %u) time units count.\n"
                    "This can occur when delta cycling is activated.\n"
                    "Cycles with falling time are not shown.\n"
                    "Use ((bsm_trace_buf*)bsmfile)->sc_set_bsm_time_unit(int exponent10_seconds)\n"
                    "to increase time resolution.",
                    previous_time_units_low, now_units_low);
                buf_put_error_message(message, true);
                warned = true;
            }
            // Note that we don't set this_time_units_high/low to any value only
                // in this case because we are not going to do any tracing. In the
                // optimized mode, the compiler complains because of this. Therefore,
                // we include the lines at the very beginning of this function to make
                // the compiler shut up.
            return;
        }

        // Now do the actual printing
        bool time_printed = true;
        buf_trace* const* const l_traces = traces.raw_data();
        for(int i = 0; i < (int)traces.size(); i++) {
            buf_trace* t = l_traces[i];
            if(t->changed()) {
                if(!bsm_trace_enable) {
                    t->write(NULL);
                } else {
                    // Write the variable

                    if(t->get_trace_type() == buf_trace::BSM_TRACE_ORIG) {
                        t->write(buf);
                    } else {
                        t->write(NULL);
                        i++;
                        assert(i < (int)traces.size());
                        l_traces[i]->write(buf);
                    }
                }
                //fputc('\n', fp);
            }
        }
        // Put another newline after all values are printed
        //if(time_printed) fputc('\n', fp);

        if(time_printed) {
            // We update previous_time_units only when we print time because
            // this field stores the previous time that was printed, not the
            // previous time this function was called
            previous_time_units_high = this_time_units_high;
            previous_time_units_low = this_time_units_low;
        }
    }



    bsm_trace_buf::~bsm_trace_buf()
    {
        for(int i = 0; i < (int)traces.size(); i++) {
            buf_trace* t = traces[i];
            delete t;
        }
    }

    void bsm_trace_buf::set_bsm_trace_type(int index,
        unsigned int nTrigger,
        unsigned int nTrace)
    {
        if(index == -1) index = traces.size() - 1;

        assert(index >= 0 && index < (int)traces.size());
        traces[index]->set_trace_type(nTrace);
        traces[index]->set_trigger_type(nTrigger);
    }

    // Functions specific to BSM tracing

    //static char
    //map_sc_logic_state_to_bsm_state(char in_char)
    //{
    //    char out_char;
    //
    //    switch(in_char){
    //        case 'U':
    //        case 'X':
    //        case 'W':
    //        case 'D':
    //            out_char = 'x';
    //            break;
    //        case '0':
    //        case 'L':
    //            out_char = '0';
    //            break;
    //        case  '1':
    //        case  'H':
    //            out_char = '1';
    //            break;
    //        case  'Z':
    //            out_char = 'z';
    //            break;
    //        default:
    //            out_char = '?';
    //    }
    //
    //    return out_char;
    //}


    void buf_put_error_message(const char* msg, bool just_warning)
    {
        if(just_warning) {
            ::std::cout << "BSM Trace Warning:\n" << msg << "\n" << ::std::endl;
        } else {
            ::std::cout << "BSM Trace ERROR:\n" << msg << "\n" << ::std::endl;
        }
    }


    /*****************************************************************************/

    class buf_interface_trace : public buf_trace {
    public:
        buf_interface_trace(const sc_interface* object_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        bool changed();

    protected:
        const sc_interface* object;
        float old_value;
    };

    buf_interface_trace::buf_interface_trace(const sc_interface* object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = 1;
        std::string value = object->bsm_string();
        float v;
        sscanf(value.c_str(), "%g", &v);
        old_value = v;
    }

    bool buf_interface_trace::changed()
    {
        std::string value = object->bsm_string();
        float v;
        sscanf(value.c_str(), "%g", &v);
        if(v != old_value) {
            if((bsm_trigger_type == BSM_TRIGGER_VAL_BOTH) ||
                (bsm_trigger_type == BSM_TRIGGER_VAL_POS && v > old_value) ||
                (bsm_trigger_type == BSM_TRIGGER_VAL_NEG && v < old_value))
            {
                return true;
            } else {
                write(NULL);
            }
        }
        return false;
    }

    void buf_interface_trace::write(bsm_buf_write_inf* f)
    {
        std::string value = object->bsm_string();
        float v;
        sscanf(value.c_str(), "%g", &v);
        if(f) f->append((double)v);
        old_value = v;
    }
    void bsm_trace_buf::trace(const sc_interface* object_)
    {
        if(initialized) {
            buf_put_error_message(
                "No traces can be added once simulation has started.\n"
                "To add traces, create a new bsm trace file.", false);
        }
        traces.push_back(new buf_interface_trace(object_));
    }
    /*****************************************************************************/

    class buf_port_trace : public buf_trace {
    public:
        buf_port_trace(const sc_port_base* object_,
            const unsigned trace_type_ = BSM_TRACE_ORIG);
        void write(bsm_buf_write_inf* f);
        bool changed();

    protected:
        const sc_port_base* object;
        float old_value;
    };

    buf_port_trace::buf_port_trace(const sc_port_base* object_,
        const unsigned trace_type_)
        : buf_trace(trace_type_), object(object_)
    {
        bit_width = 1;
        std::string value = object->bsm_string();
        float v;
        sscanf(value.c_str(), "%g", &v);
        old_value = v;
    }

    bool buf_port_trace::changed()
    {
        std::string value = object->bsm_string();
        float v;
        sscanf(value.c_str(), "%g", &v);
        if(v != old_value) {
            if((bsm_trigger_type == BSM_TRIGGER_VAL_BOTH) ||
                (bsm_trigger_type == BSM_TRIGGER_VAL_POS&&v > old_value) ||
                (bsm_trigger_type == BSM_TRIGGER_VAL_NEG&&v < old_value)) {
                return true;
            } else {
                write(NULL);
            }
        }
        return false;
    }

    void buf_port_trace::write(bsm_buf_write_inf* f)
    {
        std::string value = object->bsm_string();
        float v;
        sscanf(value.c_str(), "%g", &v);
        if(f) f->append((double)v);

        old_value = v;
    }

    void bsm_trace_buf::trace(const sc_port_base* object_)
    {
        if(initialized) {
            buf_put_error_message(
                "No traces can be added once simulation has started.\n"
                "To add traces, create a new bsm trace file.", false);
        }
        traces.push_back(new buf_port_trace(object_));
    }

    bsm_trace_buf* sc_create_bsm_trace_buf(const char * name)
    {
        bsm_trace_buf *tf;

        tf = new bsm_trace_buf(name);
        sc_get_curr_simcontext()->add_trace_buf(tf);
        return tf;
    }

    void sc_close_bsm_trace_buf(bsm_trace_buf* tf)
    {
        bsm_trace_buf* bsm_tf = tf;
        delete bsm_tf;
    }

    /////////////////////////////////////////////////////////
    ////////////trace bsm object/////////////////////////////
    bool bsm_trace_signal(bsm_trace_buf*tf, sc_object* scObj)
    {
        sc_interface* interf = dynamic_cast<sc_interface*> (scObj);
        if(interf == NULL) return false;

        std::string strBSMType = interf->bsm_type();
        if(strBSMType.compare("Generic") == 0) {
#define  BSM_CHECK_TYPE(type) dynamic_cast< sc_signal<type >* >(scObj)!=NULL
#define  BSM_TRACE_TYPE(type) \
    sc_signal<type > *dyObj = dynamic_cast<sc_signal<type >*>(scObj); \
    assert(dyObj); \
    sc_trace_buf(tf, *dyObj); \
    return true;

            if(BSM_CHECK_TYPE(double)) {
                BSM_TRACE_TYPE(double);
            } else if(BSM_CHECK_TYPE(float)) {
                BSM_TRACE_TYPE(float);
            } else if(BSM_CHECK_TYPE(bool)) {
                BSM_TRACE_TYPE(bool);
            } else if(BSM_CHECK_TYPE(char)) {
                BSM_TRACE_TYPE(char);
            } else if(BSM_CHECK_TYPE(short)) {
                BSM_TRACE_TYPE(short);
            } else if(BSM_CHECK_TYPE(int)) {
                BSM_TRACE_TYPE(int);
            } else if(BSM_CHECK_TYPE(long)) {
                BSM_TRACE_TYPE(long);
            } else if(BSM_CHECK_TYPE(long long)) {
                BSM_TRACE_TYPE(long long);
            } else if(BSM_CHECK_TYPE(unsigned char)) {
                BSM_TRACE_TYPE(unsigned char);
            } else if(BSM_CHECK_TYPE(unsigned short)) {
                BSM_TRACE_TYPE(unsigned short);
            } else if(BSM_CHECK_TYPE(unsigned int)) {
                BSM_TRACE_TYPE(unsigned int);
            } else if(BSM_CHECK_TYPE(unsigned long)) {
                BSM_TRACE_TYPE(unsigned long);
            } else if(BSM_CHECK_TYPE(unsigned long long)) {
                BSM_TRACE_TYPE(unsigned long long);
            }
            //  else if(BSM_CHECK_TYPE(std::string))
            //  {//std::string
            //      sc_signal<std::string > *dyObj =
            //          dynamic_cast< sc_signal<std::string >* >(scObj);
            //      ASSERT(dyObj);
            //      sc_trace_buf(tf,*dyObj);
            //return true;
            //  }
            else if(BSM_CHECK_TYPE(sc_dt::sc_logic)) {
                BSM_TRACE_TYPE(sc_dt::sc_logic);
            } else if(BSM_CHECK_TYPE(sc_dt::sc_bit)) {
                BSM_TRACE_TYPE(sc_dt::sc_bit);
            }
#undef BSM_CHECK_TYPE
#undef BSM_TRACE_TYPE
        } else {
            if(strBSMType.compare(("sc_int")) != std::string::npos ||
                strBSMType.compare(("sc_uint")) != std::string::npos ||
                strBSMType.compare(("sc_bigint")) != std::string::npos ||
                strBSMType.compare(("sc_biguint")) != std::string::npos ||
                strBSMType.compare(("sc_fixed")) != std::string::npos ||
                strBSMType.compare(("sc_fixed_fast")) != std::string::npos ||
                strBSMType.compare(("sc_ufixed")) != std::string::npos ||
                strBSMType.compare(("sc_bv")) != std::string::npos ||
                strBSMType.compare(("sc_lv")) != std::string::npos
                ) {
                tf->trace(interf);
                return true;
            }
        }
        return false;
    }
    bool bsm_trace_in(bsm_trace_buf*tf, sc_object* scObj)
    {
        sc_port_base* interf = dynamic_cast<sc_port_base*> (scObj);
        if(interf == NULL)
            return false;

        std::string strBSMType = interf->bsm_type();
        if(strBSMType.compare("Generic") == 0) {
#define  BSM_CHECK_TYPE(type) dynamic_cast< sc_in<type >* >(scObj)!=NULL
#define  BSM_TRACE_TYPE(type) \
    sc_in<type > *dyObj = dynamic_cast<sc_in<type >*>(scObj); \
    assert(dyObj); \
    sc_trace_buf(tf, *dyObj); \
    return true;

            if(BSM_CHECK_TYPE(double)) {
                BSM_TRACE_TYPE(double);
            } else if(BSM_CHECK_TYPE(float)) {
                BSM_TRACE_TYPE(float);
            } else if(BSM_CHECK_TYPE(bool)) {
                BSM_TRACE_TYPE(bool);
            } else if(BSM_CHECK_TYPE(char)) {
                BSM_TRACE_TYPE(char);
            } else if(BSM_CHECK_TYPE(short)) {
                BSM_TRACE_TYPE(short);
            } else if(BSM_CHECK_TYPE(int)) {
                BSM_TRACE_TYPE(int);
            } else if(BSM_CHECK_TYPE(long)) {
                BSM_TRACE_TYPE(long);
            } else if(BSM_CHECK_TYPE(long long)) {
                BSM_TRACE_TYPE(long long);
            } else if(BSM_CHECK_TYPE(unsigned char)) {
                BSM_TRACE_TYPE(unsigned char);
            } else if(BSM_CHECK_TYPE(unsigned short)) {
                BSM_TRACE_TYPE(unsigned short);
            } else if(BSM_CHECK_TYPE(unsigned int)) {
                BSM_TRACE_TYPE(unsigned int);
            } else if(BSM_CHECK_TYPE(unsigned long)) {
                BSM_TRACE_TYPE(unsigned long);
            } else if(BSM_CHECK_TYPE(unsigned long long)) {
                BSM_TRACE_TYPE(unsigned long long);
            }
            //  else if(BSM_CHECK_TYPE(std::string))
            //  {//std::string
            //      sc_signal<std::string > *dyObj =
            //          dynamic_cast< sc_signal<std::string >* >(scObj);
            //      ASSERT(dyObj);
            //      sc_trace_buf(tf,*dyObj);
            //return true;
            //  }
            else if(BSM_CHECK_TYPE(sc_dt::sc_logic)) {
                BSM_TRACE_TYPE(sc_dt::sc_logic);
            } else if(BSM_CHECK_TYPE(sc_dt::sc_bit)) {
                BSM_TRACE_TYPE(sc_dt::sc_bit);
            }
#undef BSM_CHECK_TYPE
#undef BSM_TRACE_TYPE
        } else {
            if(strBSMType.compare(("sc_int")) != std::string::npos ||
                strBSMType.compare(("sc_uint")) != std::string::npos ||
                strBSMType.compare(("sc_bigint")) != std::string::npos ||
                strBSMType.compare(("sc_biguint")) != std::string::npos ||
                strBSMType.compare(("sc_fixed")) != std::string::npos ||
                strBSMType.compare(("sc_fixed_fast")) != std::string::npos ||
                strBSMType.compare(("sc_ufixed")) != std::string::npos ||
                strBSMType.compare(("sc_bv")) != std::string::npos ||
                strBSMType.compare(("sc_lv")) != std::string::npos
                ) {
                tf->trace(interf);
                return true;
            }
        }
        return false;
    }
    bool bsm_trace_out(bsm_trace_buf*tf, sc_object* scObj)
    {
        sc_port_base* interf = dynamic_cast<sc_port_base*> (scObj);
        if(interf == NULL) return false;

        std::string strBSMType = interf->bsm_type();
        if(strBSMType.compare("Generic") == 0) {
#define  BSM_CHECK_TYPE(type) dynamic_cast< sc_inout<type >* >(scObj)!=NULL
#define  BSM_TRACE_TYPE(type) \
    sc_inout<type > *dyObj = dynamic_cast<sc_inout<type >*>(scObj); \
    assert(dyObj); \
    sc_trace_buf(tf, *dyObj); \
    return true;

            if(BSM_CHECK_TYPE(double)) {
                BSM_TRACE_TYPE(double);
            } else if(BSM_CHECK_TYPE(float)) {
                BSM_TRACE_TYPE(float);
            } else if(BSM_CHECK_TYPE(bool)) {
                BSM_TRACE_TYPE(bool);
            } else if(BSM_CHECK_TYPE(char)) {
                BSM_TRACE_TYPE(char);
            } else if(BSM_CHECK_TYPE(short)) {
                BSM_TRACE_TYPE(short);
            } else if(BSM_CHECK_TYPE(int)) {
                BSM_TRACE_TYPE(int);
            } else if(BSM_CHECK_TYPE(long)) {
                BSM_TRACE_TYPE(long);
            } else if(BSM_CHECK_TYPE(long long)) {
                BSM_TRACE_TYPE(long long);
            } else if(BSM_CHECK_TYPE(unsigned char)) {
                BSM_TRACE_TYPE(unsigned char);
            } else if(BSM_CHECK_TYPE(unsigned short)) {
                BSM_TRACE_TYPE(unsigned short);
            } else if(BSM_CHECK_TYPE(unsigned int)) {
                BSM_TRACE_TYPE(unsigned int);
            } else if(BSM_CHECK_TYPE(unsigned long)) {
                BSM_TRACE_TYPE(unsigned long);
            } else if(BSM_CHECK_TYPE(unsigned long long)) {
                BSM_TRACE_TYPE(unsigned long long);
            }
            //  else if(BSM_CHECK_TYPE(std::string))
            //  {//std::string
            //      sc_signal<std::string > *dyObj =
            //          dynamic_cast< sc_signal<std::string >* >(scObj);
            //      ASSERT(dyObj);
            //      sc_trace_buf(tf,*dyObj);
            //return true;
            //  }
            else if(BSM_CHECK_TYPE(sc_dt::sc_logic)) {
                BSM_TRACE_TYPE(sc_dt::sc_logic);
            } else if(BSM_CHECK_TYPE(sc_dt::sc_bit)) {
                BSM_TRACE_TYPE(sc_dt::sc_bit);
            }
#undef BSM_CHECK_TYPE
        } else {
            if(strBSMType.compare(("sc_int")) != std::string::npos ||
                strBSMType.compare(("sc_uint")) != std::string::npos ||
                strBSMType.compare(("sc_bigint")) != std::string::npos ||
                strBSMType.compare(("sc_biguint")) != std::string::npos ||
                strBSMType.compare(("sc_fixed")) != std::string::npos ||
                strBSMType.compare(("sc_fixed_fast")) != std::string::npos ||
                strBSMType.compare(("sc_ufixed")) != std::string::npos ||
                strBSMType.compare(("sc_bv")) != std::string::npos ||
                strBSMType.compare(("sc_lv")) != std::string::npos
                ) {
                tf->trace(interf);
                return true;
            }
        }
        return false;
    }
    bool bsm_trace_buf_object(bsm_trace_buf *tf, sc_object* scObj)
    {
        std::string strKind = scObj->kind();
        if(strKind.compare("sc_signal") == 0 || strKind.compare("sc_clock") == 0) {
            return bsm_trace_signal(tf, scObj);
        } else if(strKind.compare("sc_in") == 0) {
            return bsm_trace_in(tf, scObj);
        } else if(strKind.compare("sc_out") == 0 ||
            strKind.compare("sc_inout") == 0) {
            return bsm_trace_out(tf, scObj);
        }
        return false;
    }
    /////////////////////////////////////////////////////////

#define DEFN_TRACE_BUF_FUNC_REF_A(tp)                                         \
void                                                                          \
sc_trace_buf( bsm_trace_buf* tf, const tp& object )                           \
{                                                                             \
    if( tf ) tf->trace( object );                                             \
}

#define DEFN_TRACE_BUF_FUNC_PTR_A(tp)                                         \
void                                                                          \
sc_trace_buf( bsm_trace_buf* tf, const tp* object)                            \
{                                                                             \
    if( tf ) tf->trace( *object );                                            \
}

#define DEFN_TRACE_BUF_FUNC_A(tp)                                             \
DEFN_TRACE_BUF_FUNC_REF_A(tp)                                                 \
DEFN_TRACE_BUF_FUNC_PTR_A(tp)


    DEFN_TRACE_BUF_FUNC_A(sc_dt::sc_bit)
        DEFN_TRACE_BUF_FUNC_A(sc_dt::sc_logic)

        DEFN_TRACE_BUF_FUNC_A(sc_dt::sc_int_base)
        DEFN_TRACE_BUF_FUNC_A(sc_dt::sc_uint_base)
        DEFN_TRACE_BUF_FUNC_A(sc_dt::sc_signed)
        DEFN_TRACE_BUF_FUNC_A(sc_dt::sc_unsigned)

        DEFN_TRACE_BUF_FUNC_REF_A(sc_dt::sc_bv_base)
        DEFN_TRACE_BUF_FUNC_REF_A(sc_dt::sc_lv_base)


#undef DEFN_TRACE_BUF_FUNC_REF_A
#undef DEFN_TRACE_BUF_FUNC_PTR_A
#undef DEFN_TRACE_BUF_FUNC_A


        void sc_trace_buf(bsm_trace_buf* tf,
            const unsigned int& object,
            const char** enum_literals)
    {
        if(tf) tf->trace(object, enum_literals);
    }

    void sc_trace_buf(bsm_trace_buf* tf,
        const sc_signal_in_if<char>& object,
        int width)
    {
        if(tf) tf->trace(object.get_data_ref(), width);
    }

    void sc_trace_buf(bsm_trace_buf* tf,
        const sc_signal_in_if<short>& object,
        int width)
    {
        if(tf) tf->trace(object.get_data_ref(), width);
    }

    void sc_trace_buf(bsm_trace_buf* tf, const sc_signal_in_if<int>& object,
        int width)
    {
        if(tf) tf->trace(object.get_data_ref(), width);
    }

    void sc_trace_buf(bsm_trace_buf* tf, const sc_signal_in_if<long>& object,
        int width)
    {
        if(tf) tf->trace(object.get_data_ref(), width);
    }


    void sc_trace_buf(sc_trace_file* /* not used */,
        const void* /* not used */)
    {
        ::std::cout << "Object " << " will not be traced" << ::std::endl;
    }

} // namespace sc_core
