#include <assert.h>
#include <stdlib.h>
#include <stdio.h>

#include "sysc/kernel/sc_object.h"
#include "sysc/bsm/sc_bsm_trace.h"
#include "sysc/bsm/sc_bsm_trace_buf.h"
#include "sysc/kernel/sc_module.h"
#include "sysc/communication/sc_signal.h"
#include "sysc/communication/sc_signal_ports.h"
#include "sysc/datatypes/bit/sc_bit.h"
#include "sysc/datatypes/bit/sc_logic.h"
using namespace sc_core;
using namespace sc_dt;
#include "bsm_sim_context_impl.h"
#include "sysc/kernel/sc_ver.h"
#include "sysc/datatypes/fx/sc_fix.h"
#include "sysc/datatypes/fx/sc_ufix.h"
bsm_sim_object_impl::bsm_sim_object_impl(sc_object* obj)
    :m_obj(obj)
    , m_bInitialized(false)
    , m_nKind(SC_OBJ_UNKNOWN)
    , m_strBSMType("Unknown")
    , m_nRegType(BSM_REG_UNKNOWN)
    , m_nSCType(BSM_SC_UNKNOWN)
{
}
bsm_sim_object_impl::~bsm_sim_object_impl()
{
}
const char* bsm_sim_object_impl::name()
{
    return m_obj->name();
}
const char* bsm_sim_object_impl::basename()
{
    return m_obj->basename();
}
const char* bsm_sim_object_impl::kind()
{
    return m_obj->kind();
}
void bsm_sim_object_impl::check_kind()
{
    if(m_obj == NULL) return;
    std::string strKind = kind();
    int nKind = SC_OBJ_UNKNOWN;
    if(strKind.compare("sc_signal") == 0)
        nKind = SC_OBJ_SIGNAL;
    else if(strKind.compare("sc_in") == 0)
        nKind = SC_OBJ_INPUT;
    else if(strKind.compare("sc_out") == 0)
        nKind = SC_OBJ_OUTPUT;
    else if(strKind.compare("sc_in_out") == 0)
        nKind = SC_OBJ_INOUT;
    else if(strKind.compare("sc_clock") == 0)
        nKind = SC_OBJ_CLOCK;
    else if(strKind.compare("xsc_property") == 0) {
        nKind = SC_OBJ_XSC_PROP;
        std::string strname = name();
        if(strname.find("[") != std::string::npos &&
            strname.find("]") != std::string::npos)
            nKind = SC_OBJ_XSC_ARRAY_ITEM;
    } else if(strKind.compare("sc_module") == 0)
        nKind = SC_OBJ_MODULE;
    else if(strKind.compare("xsc_array") == 0)
        nKind = SC_OBJ_XSC_ARRAY;

    m_nKind = nKind;
    /*obj->bRegister = (nKind==SC_OBJ_SIGNAL)||
        (nKind==SC_OBJ_INPUT) ||
        (nKind==SC_OBJ_OUTPUT)||
        (nKind==SC_OBJ_INOUT) ||
        (nKind==SC_OBJ_CLOCK) ||
        (nKind==SC_OBJ_XSC_PROP)||
        (nKind==SC_OBJ_XSC_ARRAY_ITEM);*/
}
void bsm_sim_object_impl::Initialize()
{
    if(m_obj == NULL)
        return;
    check_kind();
    if(m_nKind == SC_OBJ_SIGNAL ||
        m_nKind == SC_OBJ_CLOCK ||
        m_nKind == SC_OBJ_XSC_PROP ||
        m_nKind == SC_OBJ_XSC_ARRAY_ITEM) {
        m_nSCType = BSM_SC_SIGNAL;
        sc_interface* interf = dynamic_cast<sc_interface*>(m_obj);
        assert(interf);
        if(interf) {
            m_strBSMType = interf->bsm_type();
            if(m_strBSMType.compare("Generic") == 0)
                CheckSignalType();
        }
    } else if(m_nKind == SC_OBJ_INPUT) {
        m_nSCType = BSM_SC_IN;
        sc_port_base* interf = dynamic_cast<sc_port_base*>(m_obj);
        assert(interf);
        if(interf) {
            m_strBSMType = interf->bsm_type();
            if(m_strBSMType.compare("Generic") == 0)
                CheckInputType();
        }
    } else if(m_nKind == SC_OBJ_OUTPUT || m_nKind == SC_OBJ_INOUT) {
        m_nSCType = BSM_SC_INOUT;
        sc_port_base* interf = dynamic_cast<sc_port_base*>(m_obj);
        assert(interf);
        if(interf) {
            m_strBSMType = interf->bsm_type();
            if(m_strBSMType.compare("Generic") == 0)
                CheckOutputType();
        }
    }

    if(m_strBSMType.compare("sc_int") == 0 ||
        m_strBSMType.compare("sc_uint") == 0 ||
        m_strBSMType.compare("sc_bigint") == 0 ||
        m_strBSMType.compare("sc_biguint") == 0 ||
        m_strBSMType.compare("sc_fixed") == 0 ||
        m_strBSMType.compare("sc_fixed_fast") == 0 ||
        m_strBSMType.compare("sc_ufixed") == 0 ||
        m_strBSMType.compare("sc_bv") == 0 ||
        m_strBSMType.compare("sc_lv") == 0) {
        m_nRegType = BSM_REG_TEMPL;
        m_nDataType = TYPE_STRING;
    }
    if(m_nRegType == BSM_REG_DOUBLE || m_nRegType == BSM_REG_FLOAT)
        m_nDataType = TYPE_FLOAT;
    else if(m_nRegType >= BSM_REG_BOOL || m_nRegType == BSM_REG_INT64)
        m_nDataType = TYPE_INT;
    else if(m_nRegType >= BSM_REG_UCHAR || m_nRegType == BSM_REG_UINT64)
        m_nDataType = TYPE_UINT;
    else if(m_nRegType == BSM_REG_SC_LOGIC || m_nRegType == BSM_REG_SC_BIT)
        m_nDataType = TYPE_INT;
    else
        m_nDataType = TYPE_STRING;

    m_bInitialized = true;
}
void bsm_sim_object_impl::CheckSignalType()
{
    assert(m_obj);
#define  DECLARE_REG_TYPE(type,id) {\
      sc_signal<type > *dyObj = \
      dynamic_cast< sc_signal<type >* >(m_obj);\
      if(dyObj)\
      {\
          m_nRegType = id;\
          return;\
      }\
}
#define DECLARE_REG_TYPE2(type, id) DECLARE_REG_TYPE(type, id)
#define DECLARE_REG_TYPE3(type, id) DECLARE_REG_TYPE(type, id)
#include "reg_type.h"

}
void bsm_sim_object_impl::CheckInputType()
{
    assert(m_obj);
#define  DECLARE_REG_TYPE(type,id) {\
      sc_in<type > *dyObj = \
      dynamic_cast< sc_in<type >* >(m_obj);\
      if(dyObj)\
      {\
          m_nRegType = id;\
          return;\
      }\
}
#define DECLARE_REG_TYPE3(type, id) DECLARE_REG_TYPE(type, id)
#include "reg_type.h"
}

void bsm_sim_object_impl::CheckOutputType()
{
    assert(m_obj);
#define  DECLARE_REG_TYPE(type,id) {\
      sc_inout<type > *dyObj = \
      dynamic_cast< sc_inout<type >* >(m_obj);\
      if(dyObj)\
      {\
          m_nRegType = id;\
          return;\
      }\
}
#define DECLARE_REG_TYPE3(type, id) DECLARE_REG_TYPE(type, id)
#include "reg_type.h"
}

bool bsm_sim_object_impl::is_readable()
{
    if(!m_bInitialized) Initialize();
    return (m_nSCType == BSM_SC_SIGNAL ||
        m_nSCType == BSM_SC_IN ||
        m_nSCType == BSM_SC_INOUT);
}

bool bsm_sim_object_impl::is_writable()
{
    if(!m_bInitialized) Initialize();
    if(m_obj && m_nKind == SC_OBJ_CLOCK)
        return false;
    return (m_nSCType == BSM_SC_SIGNAL ||
        m_nSCType == BSM_SC_INOUT);
}

#define  BSM_CHECK_TYPE(type) (m_nRegType == type)
bool bsm_sim_object_impl::ReadSignal(bsm_object_value * v)
{
    assert(v);
    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_signal<double > *dyObj = dynamic_cast<sc_signal<double >*>(m_obj);
        assert(dyObj);
        v->fValue = dyObj->read();
        v->type = TYPE_FLOAT;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_signal<float > *dyObj = dynamic_cast<sc_signal<float >*>(m_obj);
        assert(dyObj);
        v->fValue = dyObj->read();
        v->type = TYPE_FLOAT;
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_signal<bool > *dyObj = dynamic_cast<sc_signal<bool >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_signal<char > *dyObj = dynamic_cast<sc_signal<char >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_signal<short > *dyObj = dynamic_cast<sc_signal<short >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_signal<int > *dyObj = dynamic_cast<sc_signal<int >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_signal<long > *dyObj = dynamic_cast<sc_signal<long >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_signal<long long > *dyObj =
            dynamic_cast<sc_signal<long long >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_signal<unsigned char > *dyObj =
            dynamic_cast<sc_signal<unsigned char >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;;
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_signal<unsigned short > *dyObj =
            dynamic_cast<sc_signal<unsigned short >*>(m_obj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_signal<unsigned int > *dyObj =
            dynamic_cast<sc_signal<unsigned int >*>(m_obj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;;
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_signal<unsigned long > *dyObj =
            dynamic_cast<sc_signal<unsigned long >*>(m_obj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_signal<unsigned long long > *dyObj =
            dynamic_cast<sc_signal<unsigned long long>*>(m_obj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_LOGIC)) {
        sc_signal<sc_logic > *dyObj =
            dynamic_cast<sc_signal<sc_logic >*>(m_obj);
        assert(dyObj);
        v->sValue[0] = dyObj->read().to_char();
        v->sValue[1] = '\0';
        v->type = TYPE_STRING;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_signal<sc_bit > *dyObj =
            dynamic_cast<sc_signal<sc_bit >*>(m_obj);
        assert(dyObj);
        v->sValue[0] = dyObj->read().to_char();
        v->sValue[1] = '\0';
        v->type = TYPE_STRING;
    } else if(BSM_CHECK_TYPE(BSM_REG_STR)) {
        sc_signal<std::string > *dyObj =
            dynamic_cast<sc_signal<std::string >*>(m_obj);
        assert(dyObj);
        snprintf(v->sValue, 256, "%s", dyObj->read().c_str());
        v->type = TYPE_STRING;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_interface* interf = dynamic_cast<sc_interface*>(m_obj);
        assert(interf);
        int nLen = 256;
        interf->bsm_to_string(v->sValue, nLen);
        v->type = TYPE_STRING;
        /*int nlen = 0;
        if(interf->bsm_to_string(0, nlen)) {
            int nLen = 256;
            interf->bsm_to_string(v->sValue, nLen);
        }*/
    } else {
        return false;
    }
    return true;
}

bool bsm_sim_object_impl::ReadInPort(bsm_object_value* v)
{
    assert(v);
    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_in<double > *dyObj = dynamic_cast<sc_in<double >*>(m_obj);
        assert(dyObj);
        v->fValue = dyObj->read();
        v->type = TYPE_FLOAT;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_in<float > *dyObj = dynamic_cast<sc_in<float >*>(m_obj);
        assert(dyObj);
        v->fValue = dyObj->read();
        v->type = TYPE_FLOAT;
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_in<bool > *dyObj = dynamic_cast<sc_in<bool >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_in<char > *dyObj = dynamic_cast<sc_in<char >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_in<short > *dyObj = dynamic_cast<sc_in<short >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_in<int > *dyObj = dynamic_cast<sc_in<int >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_in<long > *dyObj = dynamic_cast<sc_in<long >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_in<long long > *dyObj =
            dynamic_cast<sc_in<long long >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_in<unsigned char > *dyObj =
            dynamic_cast<sc_in<unsigned char >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_in<unsigned short > *dyObj =
            dynamic_cast<sc_in<unsigned short >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_in<unsigned int > *dyObj =
            dynamic_cast<sc_in<unsigned int >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_in<unsigned long > *dyObj =
            dynamic_cast<sc_in<unsigned long >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_in<unsigned long long > *dyObj =
            dynamic_cast<sc_in<unsigned long long>*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_LOGIC)) {
        sc_in<sc_logic > *dyObj = dynamic_cast<sc_in<sc_logic >*>(m_obj);
        assert(dyObj);
        v->sValue[0] = dyObj->read().to_char();
        v->sValue[1] = '\0';
        v->type = TYPE_STRING;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_in<sc_bit > *dyObj = dynamic_cast<sc_in<sc_bit >*>(m_obj);
        assert(dyObj);
        v->sValue[0] = dyObj->read().to_char();
        v->sValue[1] = '\0';
        v->type = TYPE_STRING;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_port_base* port = dynamic_cast<sc_port_base*>(m_obj);
        assert(port);
        int nLen = 256;
        port->bsm_to_string(v->sValue, nLen);
        v->type = TYPE_STRING;
        /*int nlen = 0;
        if(port->bsm_to_string(0, nlen)) {
            int nLen = 256;
            port->bsm_to_string(v->sValue, nLen);
        }*/
    } else {
        return false;
    }
    return true;
}

bool bsm_sim_object_impl::ReadInoutPort(bsm_object_value* v)
{
    assert(v);
    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_inout<double > *dyObj = dynamic_cast<sc_inout<double >*>(m_obj);
        assert(dyObj);
        v->fValue = dyObj->read();
        v->type = TYPE_FLOAT;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_inout<float > *dyObj = dynamic_cast<sc_inout<float >*>(m_obj);
        assert(dyObj);
        v->fValue = dyObj->read();
        v->type = TYPE_FLOAT;
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_inout<bool > *dyObj = dynamic_cast<sc_inout<bool >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_inout<char > *dyObj = dynamic_cast<sc_inout<char >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_inout<short > *dyObj = dynamic_cast<sc_inout<short >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_inout<int > *dyObj = dynamic_cast<sc_inout<int >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_inout<long > *dyObj = dynamic_cast<sc_inout<long >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_inout<long long > *dyObj =
            dynamic_cast<sc_inout<long long >*>(m_obj);
        assert(dyObj);
        v->iValue = dyObj->read();
        v->type = TYPE_INT;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_inout<unsigned char > *dyObj =
            dynamic_cast<sc_inout<unsigned char >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_inout<unsigned short > *dyObj =
            dynamic_cast<sc_inout<unsigned short >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_inout<unsigned int > *dyObj =
            dynamic_cast<sc_inout<unsigned int >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_inout<unsigned long > *dyObj =
            dynamic_cast<sc_inout<unsigned long >*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_inout<unsigned long long > *dyObj =
            dynamic_cast<sc_inout<unsigned long long>*>(m_obj);
        assert(dyObj);
        v->uValue = dyObj->read();
        v->type = TYPE_UINT;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_LOGIC)) {
        sc_inout<sc_logic > *dyObj = dynamic_cast<sc_inout<sc_logic >*>(m_obj);
        assert(dyObj);
        v->sValue[0] = dyObj->read().to_char();
        v->sValue[1] = '\0';
        v->type = TYPE_STRING;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_inout<sc_bit > *dyObj = dynamic_cast<sc_inout<sc_bit >*>(m_obj);
        assert(dyObj);
        v->sValue[0] = dyObj->read().to_char();
        v->sValue[1] = '\0';
        v->type = TYPE_STRING;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_port_base* port = dynamic_cast<sc_port_base*>(m_obj);
        int nLen = 256;
        port->bsm_to_string(v->sValue, nLen);
        /*int nlen = 0;
        if(port->bsm_to_string(0, nlen)) {
            nlen= nlen>256?256:nlen;
            port->bsm_to_string(v->sValue, nlen);
        }*/
    } else {
        return false;
    }
    return true;
}
bool bsm_sim_object_impl::read(bsm_object_value* v)
{
    if(!m_bInitialized) Initialize();
    if(!is_readable()) {
        return false;
    }
    if(m_nSCType == BSM_SC_SIGNAL)
        return ReadSignal(v);
    else if(m_nSCType == BSM_SC_IN)
        return ReadInPort(v);
    else if(m_nSCType == BSM_SC_INOUT)
        return ReadInoutPort(v);
    return false;
}

bool bsm_sim_object_impl::WriteSignal(const bsm_object_value* v)
{
    assert(v);
    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_signal<double > *dyObj = dynamic_cast<sc_signal<double >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->fValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_signal<float > *dyObj = dynamic_cast<sc_signal<float >*>(m_obj);
        assert(dyObj);
        dyObj->write((float)v->fValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_signal<bool > *dyObj = dynamic_cast<sc_signal<bool >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->iValue == 1);
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_signal<char > *dyObj = dynamic_cast<sc_signal<char >*>(m_obj);
        assert(dyObj);
        dyObj->write((char)v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_signal<short > *dyObj = dynamic_cast<sc_signal<short >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_signal<int > *dyObj = dynamic_cast<sc_signal<int >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_signal<long > *dyObj = dynamic_cast<sc_signal<long >*>(m_obj);
        assert(dyObj);
        dyObj->write((long)v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_signal<long long > *dyObj =
            dynamic_cast<sc_signal<long long >*>(m_obj);
        assert(dyObj);
        dyObj->write((long long)v->fValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_signal<unsigned char > *dyObj =
            dynamic_cast<sc_signal<unsigned char >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned char)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_signal<unsigned short > *dyObj =
            dynamic_cast<sc_signal<unsigned short >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned short)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_signal<unsigned int > *dyObj =
            dynamic_cast<sc_signal<unsigned int >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned int)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_signal<unsigned long > *dyObj =
            dynamic_cast<sc_signal<unsigned long >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned long)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_signal<unsigned long long > *dyObj =
            dynamic_cast<sc_signal<unsigned long long>*>(m_obj);
        assert(dyObj);
        dyObj->write(v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_STR)) {
        //std::string
        sc_signal<std::string > *dyObj =
            dynamic_cast<sc_signal<std::string >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->sValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_LOGIC)) {
        sc_signal<sc_logic > *dyObj =
            dynamic_cast<sc_signal<sc_logic >*>(m_obj);
        assert(dyObj);
        dyObj->write((sc_logic)(v->sValue[0]));
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_signal<sc_bit > *dyObj =
            dynamic_cast<sc_signal<sc_bit >*>(m_obj);
        assert(dyObj);
        dyObj->write((sc_bit)(v->sValue[0]));
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_interface* interf = dynamic_cast<sc_interface*>(m_obj);
        assert(interf);
        interf->bsm_from_string(v->sValue);
    } else {
        return false;
    }
    return true;
}

bool bsm_sim_object_impl::WriteInoutPort(const bsm_object_value* v)
{
    assert(v);
    if(v == NULL) return false;
    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_inout<double > *dyObj = dynamic_cast<sc_inout<double >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->fValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_inout<float > *dyObj = dynamic_cast<sc_inout<float >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->fValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_inout<bool > *dyObj = dynamic_cast<sc_inout<bool >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_inout<char > *dyObj = dynamic_cast<sc_inout<char >*>(m_obj);
        assert(dyObj);
        dyObj->write((char)v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_inout<short > *dyObj = dynamic_cast<sc_inout<short >*>(m_obj);
        assert(dyObj);
        dyObj->write((short)v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_inout<int > *dyObj = dynamic_cast<sc_inout<int >*>(m_obj);
        assert(dyObj);
        dyObj->write((int)v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_inout<long > *dyObj = dynamic_cast<sc_inout<long >*>(m_obj);
        assert(dyObj);
        dyObj->write((long)v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_inout<long long > *dyObj =
            dynamic_cast<sc_inout<long long >*>(m_obj);
        assert(dyObj);
        dyObj->write(v->iValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_inout<unsigned char > *dyObj =
            dynamic_cast<sc_inout<unsigned char >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned char)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_inout<unsigned short > *dyObj =
            dynamic_cast<sc_inout<unsigned short >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned short)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_inout<unsigned int > *dyObj =
            dynamic_cast<sc_inout<unsigned int >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned int)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_inout<unsigned long > *dyObj =
            dynamic_cast<sc_inout<unsigned long >*>(m_obj);
        assert(dyObj);
        dyObj->write((unsigned long)v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_inout<unsigned long long > *dyObj =
            dynamic_cast<sc_inout<unsigned long long>*>(m_obj);
        assert(dyObj);
        dyObj->write(v->uValue);
    } else if(BSM_CHECK_TYPE(BSM_REG_STR)) {//std::string
        assert(false);
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_LOGIC)) {
        sc_inout<sc_logic > *dyObj =
            dynamic_cast<sc_inout<sc_logic >*>(m_obj);
        assert(dyObj);
        dyObj->write((sc_logic)(v->sValue[0]));
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_inout<sc_bit > *dyObj =
            dynamic_cast<sc_inout<sc_bit >*>(m_obj);
        assert(dyObj);
        dyObj->write((sc_bit)(v->sValue[0]));
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_port_base* interf = dynamic_cast<sc_port_base*>(m_obj);
        assert(interf);
        interf->bsm_from_string(v->sValue);
    } else {
        return false;
    }
    return true;
}
bool bsm_sim_object_impl::write(const bsm_object_value* val)
{
    if(!m_bInitialized) Initialize();

    if(!is_writable()) return false;

    bool bRtn = false;
    if(m_nSCType == BSM_SC_SIGNAL)
        bRtn = WriteSignal(val);
    else if(m_nSCType == BSM_SC_INOUT)
        bRtn = WriteInoutPort(val);
    return bRtn;
}

bool bsm_sim_object_impl::is_number()
{
    if(!m_bInitialized) Initialize();
    return m_nRegType == BSM_REG_DOUBLE ||
        m_nRegType == BSM_REG_FLOAT ||
        m_nRegType == BSM_REG_BOOL ||
        m_nRegType == BSM_REG_CHAR ||
        m_nRegType == BSM_REG_SHORT ||
        m_nRegType == BSM_REG_INT ||
        m_nRegType == BSM_REG_LONG ||
        m_nRegType == BSM_REG_INT64 ||
        m_nRegType == BSM_REG_UCHAR ||
        m_nRegType == BSM_REG_USHORT ||
        m_nRegType == BSM_REG_UINT ||
        m_nRegType == BSM_REG_ULONG ||
        m_nRegType == BSM_REG_UINT64 ||
        m_nRegType == BSM_REG_SC_LOGIC ||
        m_nRegType == BSM_REG_SC_BIT;
}

//////////////////////////////////////////////////////////////////////////////
bsm_sim_trace_file_impl::bsm_sim_trace_file_impl(const char* name, int nType)
    :m_trace(NULL)
{
    m_trace = new bsm_trace_file(name, nType);
    assert(m_trace);
}
bsm_sim_trace_file_impl::~bsm_sim_trace_file_impl()
{
    if(m_trace) delete m_trace;
}
void bsm_sim_trace_file_impl::enable(bool bEnable)
{
    m_trace->enable_bsm_trace(bEnable);
}
bool bsm_sim_trace_file_impl::is_enable()
{
    return m_trace->is_enable_bsm_trace();
}
void bsm_sim_trace_file_impl::set_print_type(unsigned int type)
{
    m_trace->set_bsm_print_type(type);
}
void bsm_sim_trace_file_impl::set_trace_type(int index, unsigned int nTrigger,
    unsigned int nTrace)
{
    m_trace->set_bsm_trace_type(index, nTrigger, nTrace);
}
//////////////////////////////////////////////////////////////////////////////
bsm_sim_trace_buf_impl::bsm_sim_trace_buf_impl(const char* name)
    :m_trace(NULL)
{
    m_trace = new bsm_trace_buf(name);
    assert(m_trace);
}
bsm_sim_trace_buf_impl::~bsm_sim_trace_buf_impl()
{
    if(m_trace) delete m_trace;
}
void bsm_sim_trace_buf_impl::enable(bool bEnable)
{
    m_trace->enable_bsm_trace(bEnable);
}
bool bsm_sim_trace_buf_impl::is_enable()
{
    return m_trace->is_enable_bsm_trace();
}
void bsm_sim_trace_buf_impl::set_trace_type(int index, unsigned int nTrigger,
    unsigned int nTrace)
{
    m_trace->set_bsm_trace_type(index, nTrigger, nTrace);
}
void bsm_sim_trace_buf_impl::set_buffer(bsm_buf_write_inf* buf)
{
    m_trace->set_bsm_buffer(buf);
}

//////////////////////////////////////////////////////////////////////////////
bsm_sim_context_impl::bsm_sim_context_impl(sc_module* top)
    :m_top(top)
    , m_sim(NULL)
    , m_strTimeStamp("")
{
    assert(top);
    if(m_top) m_sim = m_top->sc_get_curr_simcontext();
    assert(m_sim);
}
bsm_sim_context_impl::~bsm_sim_context_impl()
{
    sc_stop();
    m_sim = NULL;
    if(m_top) delete m_top;
    m_top = NULL;

    m_strTimeStamp = ("");
}
const char* bsm_sim_context_impl::sc_version()
{
    return sc_core::sc_version();
}
const char* bsm_sim_context_impl::sc_copyright()
{
    return sc_core::sc_copyright();
}
bsm_sim_object* bsm_sim_context_impl::first_object()
{
    sc_object* obj = m_sim->first_object();
    if(obj) {
        // the caller will be responsible to delete the object
        bsm_sim_object_impl* obj_impl = new bsm_sim_object_impl(obj);
        return obj_impl;
    }
    return NULL;
}
bsm_sim_object* bsm_sim_context_impl::next_object()
{
    sc_object* obj = m_sim->next_object();
    if(obj) {
        // the caller will be responsible to delete the object
        bsm_sim_object_impl* obj_impl = new bsm_sim_object_impl(obj);
        return obj_impl;
    }
    return NULL;
}
void bsm_sim_context_impl::start(double duration, int time_unit)
{
    sc_start(duration, sc_time_unit(time_unit));
}
void bsm_sim_context_impl::stop()
{
    sc_stop();
}
double bsm_sim_context_impl::time()
{
    if(m_sim) return m_sim->time_stamp().to_seconds();
    return 0.0;
}
double bsm_sim_context_impl::time(double time, int unit)
{
    sc_time scsimtime(time, (sc_time_unit)unit);
    return scsimtime.to_seconds();
}
const char* bsm_sim_context_impl::time_string()
{
    if(m_sim) m_strTimeStamp = m_sim->time_stamp().to_string();
    return m_strTimeStamp.c_str();
}
void bsm_sim_context_impl::set_callback(bsm_callback pCallBack)
{
    if(m_sim) m_sim->bsm_setcallback(pCallBack);
}

// trace
bsm_sim_trace_file* bsm_sim_context_impl::add_trace(const char* name, int type)
{
    if(m_sim == NULL) return NULL;
    // the caller is responsible to release the memory by calling remove_trace
    // type 0 -> vcd, 1 -> simple
    bsm_sim_trace_file_impl* tf_impl = new bsm_sim_trace_file_impl(name, type);
    m_sim->add_trace_bsm(tf_impl->m_trace);
    return tf_impl;
}
bool bsm_sim_context_impl::remove_trace(bsm_sim_trace_file* fp)
{
    if(m_sim == NULL) return false;

    bsm_sim_trace_file_impl* fp_impl = dynamic_cast<bsm_sim_trace_file_impl*>(fp);
    if(fp_impl) {
        m_sim->del_trace_bsm(fp_impl->m_trace);
        // release the memory
        delete fp_impl;
        return true;
    }
    return false;
}
bool bsm_sim_context_impl::trace(bsm_sim_trace_file*tf, bsm_sim_object*obj)
{
    if(m_sim == NULL) return false;

    assert(tf && obj);
    bsm_sim_trace_file_impl* fp_impl = dynamic_cast<bsm_sim_trace_file_impl*>(tf);
    bsm_sim_object_impl* obj_impl = dynamic_cast<bsm_sim_object_impl*>(obj);
    assert(fp_impl && obj_impl);
    if(obj_impl && fp_impl)
        return bsm_trace_object(fp_impl->m_trace, obj_impl->m_obj);
    return false;
}

// trace buffer
bsm_sim_trace_buf* bsm_sim_context_impl::add_trace_buf(const char* name)
{
    if(m_sim == NULL) return NULL;
    // the caller is responsible to release the memory by calling
    // remove_trace_buf
    bsm_sim_trace_buf_impl* tf_impl = new bsm_sim_trace_buf_impl(name);
    m_sim->add_trace_buf(tf_impl->m_trace);
    return tf_impl;
}
bool bsm_sim_context_impl::remove_trace_buf(bsm_sim_trace_buf*fp)
{
    if(m_sim == NULL) return false;

    bsm_sim_trace_buf_impl* fp_impl = dynamic_cast<bsm_sim_trace_buf_impl*>(fp);
    if(fp_impl) {
        m_sim->del_trace_buf(fp_impl->m_trace);
        delete fp_impl;
        return true;
    }
    return false;
}

bool bsm_sim_context_impl::trace_buf(bsm_sim_trace_buf*tf, bsm_sim_object*obj)
{
    if(m_sim == NULL) return false;

    assert(tf && obj);
    bsm_sim_trace_buf_impl* fp_impl = dynamic_cast<bsm_sim_trace_buf_impl*>(tf);
    bsm_sim_object_impl* obj_impl = dynamic_cast<bsm_sim_object_impl*>(obj);
    assert(fp_impl && obj_impl);
    if(obj_impl && fp_impl)
        return bsm_trace_buf_object(fp_impl->m_trace, obj_impl->m_obj);
    return false;
}
