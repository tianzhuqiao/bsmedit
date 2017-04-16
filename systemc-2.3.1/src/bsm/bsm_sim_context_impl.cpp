/**
 *BSMEdit-Systemc Simulation Module Controling
 *Copyright (C) 2009 Tianzhu Qiao <ben.qiao@gmail.com>
 *http://bsmedit.sourceforge.net/
 *http://www.feiyilin.com/
 *
 *This program is free software; you can redistribute it and/or modify
 *it under the terms of the GNU General Public License as published by
 *the Free Software Foundation; either version 2 of the License, or
 *(at your option) any later version.
 *                                    
 *This program is distributed in the hope that it will be useful,
 *but WITHOUT ANY WARRANTY; without even the implied warranty of
 *MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *GNU General Public License for more details.
 *                                    
 *You should have received a copy of the GNU General Public License along
 *with this program; if not, write to the Free Software Foundation, Inc.,
 *51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 *http://www.gnu.org/copyleft/gpl.html
 **/
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>

#include "sysc/kernel/sc_object.h"
#include "bsm/sc_bsm_trace.h"
#include "bsm/sc_bsm_trace_buf.h"
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
,m_value("NaN")
,m_disp("")
,m_bInitialized(false)
,m_nKind(SC_OBJ_UNKNOWN)
,m_strBSMType("Unknown")
,m_nRegType(BSM_REG_UNKNOWN)
,m_nSCType(BSM_SC_UNKNOWN)
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
    if(strKind.compare("sc_signal")==0)
        nKind = SC_OBJ_SIGNAL;
    else if(strKind.compare("sc_in")==0)
        nKind = SC_OBJ_INPUT;
    else if( strKind.compare("sc_out")==0)
        nKind = SC_OBJ_OUTPUT;
    else if( strKind.compare("sc_in_out")==0)
        nKind = SC_OBJ_INOUT;
    else if(strKind.compare("sc_clock")==0)
        nKind = SC_OBJ_CLOCK;
    else if(strKind.compare("xsc_property")==0) {
        nKind = SC_OBJ_XSC_PROP;
        std::string strname = name();
        if( strname.find("[")!=std::string::npos &&
            strname.find("]")!=std::string::npos )
            nKind = SC_OBJ_XSC_ARRAY_ITEM;
    }
    else if(strKind.compare("sc_module")==0)
        nKind = SC_OBJ_MODULE;
    else if( strKind.compare("xsc_array")==0)
        nKind = SC_OBJ_XSC_ARRAY;
   
   m_nKind     = nKind;
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
        m_nKind == SC_OBJ_XSC_ARRAY_ITEM)
    {          
        m_nSCType = BSM_SC_SIGNAL;
        sc_interface* interf = dynamic_cast<sc_interface* >(m_obj);
        assert(interf);
        if(interf) {
            m_strBSMType = interf->bsm_type();
            if(m_strBSMType.compare("Generic") == 0)
                CheckSignalType();
        }
    } else if(m_nKind == SC_OBJ_INPUT) {
        m_nSCType = BSM_SC_IN;
        sc_port_base* interf = dynamic_cast<sc_port_base* >(m_obj);
        assert(interf);
        if(interf) {
            m_strBSMType = interf->bsm_type();
            if(m_strBSMType.compare("Generic")==0)
                CheckInputType();
        }
    } else if(m_nKind == SC_OBJ_OUTPUT || m_nKind == SC_OBJ_INOUT) {
        m_nSCType = BSM_SC_INOUT;
        sc_port_base* interf = dynamic_cast<sc_port_base* >(m_obj);
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
        m_strBSMType.compare("sc_lv") == 0)
    {
        m_nRegType = BSM_REG_TEMPL;
    }
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
void bsm_sim_object_impl::Read_Signal()
{
    const int buf_len = 128;
    static char value[buf_len];
    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_signal<double > *dyObj =
            dynamic_cast<sc_signal<double >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%.14g", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_signal<float > *dyObj = dynamic_cast<sc_signal<float >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%.14g", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE (BSM_REG_BOOL)) {
        sc_signal<bool > *dyObj = dynamic_cast< sc_signal<bool >* >(m_obj);
        assert(dyObj);
        m_value = dyObj->read() == 1 ? '1' : '0';
        return;
    } else if(BSM_CHECK_TYPE (BSM_REG_CHAR)) {
        sc_signal<char > *dyObj = dynamic_cast< sc_signal<char >* >(m_obj);
        assert(dyObj);
        char chr = dyObj->read();
        m_value = chr;
        return;        
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_signal<short > *dyObj = dynamic_cast<sc_signal<short >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%hi", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_signal<int > *dyObj = dynamic_cast<sc_signal<int >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%i", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_signal<long > *dyObj = dynamic_cast<sc_signal<long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%li", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_signal<long long > *dyObj =
            dynamic_cast<sc_signal<long long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%li", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_signal<unsigned char > *dyObj =
            dynamic_cast<sc_signal<unsigned char >*>(m_obj);
        assert(dyObj);
        unsigned char chr = dyObj->read();
        m_value = value;
        return;
    } else if (BSM_CHECK_TYPE (BSM_REG_USHORT)) {
        sc_signal<unsigned short > *dyObj = 
            dynamic_cast< sc_signal<unsigned short >* >(m_obj);
        assert(dyObj);
        sprintf(value,"%hu",dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_signal<unsigned int > *dyObj =
            dynamic_cast<sc_signal<unsigned int >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%u", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_signal<unsigned long > *dyObj =
            dynamic_cast<sc_signal<unsigned long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%lu", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_signal<unsigned long long > *dyObj =
            dynamic_cast<sc_signal<unsigned long long>*>(m_obj);
        assert(dyObj);
        sprintf(value, "%lu", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_LOGIC)) {
        sc_signal<sc_logic > *dyObj =
            dynamic_cast<sc_signal<sc_logic >*>(m_obj);
        assert(dyObj);
        m_value = dyObj->read().to_char();
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_signal<sc_bit > *dyObj = 
            dynamic_cast< sc_signal<sc_bit >* >(m_obj);
        assert(dyObj);        
        m_value = dyObj->read().to_char();
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_STR)) {
        sc_signal<std::string > *dyObj =
            dynamic_cast<sc_signal<std::string >*>(m_obj);
        assert(dyObj);
        m_value = dyObj->read();
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_interface* interf = dynamic_cast<sc_interface*>(m_obj);
        assert(interf);
        int nlen = 0;
        if(interf->bsm_to_string(0, nlen)) {
            char *buf = NULL;
            if(nlen >= buf_len)
                buf = new char[nlen + 1];
            else
                buf = value;
            interf->bsm_to_string(buf, nlen);
            buf[nlen] = '\0';
            m_value = buf;
            if(nlen >= buf_len)
                delete[] buf;
            return;
        }
    }
    m_value = ("NaN");
}

void bsm_sim_object_impl::Read_Port()
{
    const int buf_len = 128;
    static char value[buf_len];
    if(BSM_CHECK_TYPE (BSM_REG_DOUBLE)) {
        sc_in<double > *dyObj = 
            dynamic_cast< sc_in<double >* >(m_obj);
        assert(dyObj);
        sprintf(value,"%.14g",dyObj->read());
        m_value = value;       
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_in<float > *dyObj = dynamic_cast<sc_in<float >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%.14g", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_in<bool > *dyObj = dynamic_cast<sc_in<bool >*>(m_obj);
        assert(dyObj);
        m_value = dyObj->read() == 1 ? '1' : '0';
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_in<char > *dyObj = dynamic_cast<sc_in<char >*>(m_obj);
        assert(dyObj);
        char chr = dyObj->read();
        m_value = chr;
        return;        
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_in<short > *dyObj = dynamic_cast<sc_in<short >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%hi", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_in<int > *dyObj = dynamic_cast<sc_in<int >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%i", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_in<long > *dyObj = dynamic_cast<sc_in<long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%li", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_in<long long > *dyObj =
            dynamic_cast<sc_in<long long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%li", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_in<unsigned char > *dyObj =
            dynamic_cast<sc_in<unsigned char >*>(m_obj);
        assert(dyObj);
        unsigned char chr = dyObj->read();
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_in<unsigned short > *dyObj =
            dynamic_cast<sc_in<unsigned short >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%hu", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_in<unsigned int > *dyObj =
            dynamic_cast<sc_in<unsigned int >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%u", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_in<unsigned long > *dyObj =
            dynamic_cast<sc_in<unsigned long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%lu", dyObj->read());
        m_value = value;
        return;
    } else if (BSM_CHECK_TYPE (BSM_REG_UINT64)) {
         sc_in<unsigned long long > *dyObj = 
            dynamic_cast< sc_in<unsigned long long>* >(m_obj);
        assert(dyObj);
        sprintf(value,"%lu",dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE (BSM_REG_SC_LOGIC)) {
        sc_in<sc_logic > *dyObj = dynamic_cast< sc_in<sc_logic >* >(m_obj);
        assert(dyObj);
        m_value = dyObj->read().to_char();
        return;
    } else if(BSM_CHECK_TYPE (BSM_REG_SC_BIT)) {
        sc_in<sc_bit > *dyObj = dynamic_cast< sc_in<sc_bit >* >(m_obj);
        assert(dyObj);
        m_value = dyObj->read().to_char();
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_port_base* port = dynamic_cast<sc_port_base* >(m_obj);
        assert(port);
        int nlen=0;
        if(port->bsm_to_string(0,nlen)) {
            char *buf = NULL;
            if(nlen >= buf_len) buf = new char[nlen + 1];
            else buf = value;
            port->bsm_to_string(buf, nlen);
            buf[nlen] = '\0';
            m_value = buf;
            if(nlen >= buf_len) delete[] buf;
            return;
        }
    }
    m_value = ("NaN");
}


void bsm_sim_object_impl::Read_Port2()
{
    const int buf_len = 128;
    static char value[buf_len];
    if(BSM_CHECK_TYPE (BSM_REG_DOUBLE)) {
        sc_inout<double > *dyObj = 
            dynamic_cast< sc_inout<double >* >(m_obj);
        assert(dyObj);
        sprintf(value, "%.14g", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_inout<float > *dyObj = dynamic_cast<sc_inout<float >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%.14g", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_inout<bool > *dyObj = dynamic_cast<sc_inout<bool >*>(m_obj);
        assert(dyObj);
        m_value = dyObj->read() == 1 ? '1' : '0';
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_inout<char > *dyObj = dynamic_cast<sc_inout<char >*>(m_obj);
        assert(dyObj);
        char chr = dyObj->read();
        m_value = chr;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_inout<short > *dyObj = dynamic_cast<sc_inout<short >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%hi", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_inout<int > *dyObj = dynamic_cast<sc_inout<int >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%i", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_inout<long > *dyObj = dynamic_cast<sc_inout<long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%li", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_inout<long long > *dyObj =
            dynamic_cast<sc_inout<long long >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%li", dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_inout<unsigned char > *dyObj =
            dynamic_cast<sc_inout<unsigned char >*>(m_obj);
        assert(dyObj);
        unsigned char chr = dyObj->read();
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_inout<unsigned short > *dyObj =
            dynamic_cast<sc_inout<unsigned short >*>(m_obj);
        assert(dyObj);
        sprintf(value, "%hu", dyObj->read());
        m_value = value;
        return;
    } else if (BSM_CHECK_TYPE (BSM_REG_UINT)) {
        sc_inout<unsigned int > *dyObj = 
            dynamic_cast< sc_inout<unsigned int >* >(m_obj);
        assert(dyObj);
        sprintf(value,"%u",dyObj->read());
        m_value = value;
        return;
    } else if (BSM_CHECK_TYPE (BSM_REG_ULONG)) {
        sc_inout<unsigned long > *dyObj = 
            dynamic_cast< sc_inout<unsigned long >* >(m_obj);
        assert(dyObj);
        sprintf(value,"%lu",dyObj->read());
        m_value = value;
        return;
    } else if (BSM_CHECK_TYPE (BSM_REG_UINT64)) {
        sc_inout<unsigned long long > *dyObj = 
            dynamic_cast< sc_inout<unsigned long long>* >(m_obj);
        assert(dyObj);
        sprintf(value,"%lu",dyObj->read());
        m_value = value;
        return;
    } else if(BSM_CHECK_TYPE (BSM_REG_SC_LOGIC)) {
        sc_inout<sc_logic > *dyObj = dynamic_cast< sc_inout<sc_logic >* >(m_obj);
        assert(dyObj);
        m_value = dyObj->read().to_char();
        return;
    } else if(BSM_CHECK_TYPE (BSM_REG_SC_BIT)) {
        sc_inout<sc_bit > *dyObj = dynamic_cast< sc_inout<sc_bit >* >(m_obj);
        assert(dyObj);
        m_value = dyObj->read().to_char();
        return;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_port_base* port = dynamic_cast<sc_port_base*>(m_obj);

        int nlen = 0;
        if(port->bsm_to_string(0, nlen)) {
            char *buf = NULL;
            if(nlen>=buf_len) buf  = new char[nlen+1];
            else buf = value;            
            port->bsm_to_string(buf,nlen);
            buf[nlen] = '\0';
            m_value = buf;
            if(nlen>=buf_len)
                delete[] buf;
            return ;
        }
    }
    m_value =("NaN");
}
const char* bsm_sim_object_impl::read()
{
    if(!m_bInitialized) Initialize();
    if(!is_readable()) {
        if(m_obj) return kind();//not readable ,return the kind
        return ("NaN");  
    }
    if(m_nSCType == BSM_SC_SIGNAL)
        Read_Signal();
    else if(m_nSCType == BSM_SC_IN)
        Read_Port();
    else if(m_nSCType == BSM_SC_INOUT)
        Read_Port2();
    return m_value.c_str();
}

bool bsm_sim_object_impl::Write_Signal(const char* val)
{
    if(val == NULL) return false;

    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_signal<double > *dyObj =
            dynamic_cast<sc_signal<double >*>(m_obj);
        assert(dyObj);
        char* end;
        double value = strtod(val, &end);

        dyObj->write(value);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_signal<float > *dyObj = dynamic_cast<sc_signal<float >*>(m_obj);
        assert(dyObj);
        char* end;
        double value = strtod(val, &end);
        dyObj->write((float)value);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_signal<bool > *dyObj = dynamic_cast<sc_signal<bool >*>(m_obj);
        assert(dyObj);
        int value = atoi(val);
        dyObj->write(value==1);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_signal<char > *dyObj = dynamic_cast<sc_signal<char >*>(m_obj);
        assert(dyObj);
        char chr = val[0];
        dyObj->write(chr);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_signal<short > *dyObj = dynamic_cast< sc_signal<short >* >(m_obj);
        assert(dyObj);
        short value = 0;
        if(sscanf(val, "%hi", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return  false;
    } else if (BSM_CHECK_TYPE (BSM_REG_INT)) {
        sc_signal<int > *dyObj = dynamic_cast< sc_signal<int >* >(m_obj);
        assert(dyObj);
        int value = 0;
        if(sscanf(val, "%i", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_signal<long > *dyObj = dynamic_cast<sc_signal<long >*>(m_obj);
        assert(dyObj);
        long value = 0;
        if(sscanf(val, "%li", &value) == 1) {
            dyObj->write((long)value);
            return true;
        }
        return false; 
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_signal<long long > *dyObj =
            dynamic_cast<sc_signal<long long >*>(m_obj);
        assert(dyObj);

        long value = 0;
        if(sscanf(val, "%li", &value) == 1) {
            dyObj->write((long long)value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_signal<unsigned char > *dyObj =
            dynamic_cast<sc_signal<unsigned char >*>(m_obj);
        assert(dyObj);
        unsigned char chr = (unsigned char)val[0];
        dyObj->write(chr);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_signal<unsigned short > *dyObj =
            dynamic_cast<sc_signal<unsigned short >*>(m_obj);
        assert(dyObj);
        unsigned short value = 0;
        if(sscanf(val, "%hu", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_signal<unsigned int > *dyObj =
            dynamic_cast<sc_signal<unsigned int >*>(m_obj);
        assert(dyObj);
        unsigned int value = 0;
        if(sscanf(val, "%u", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_signal<unsigned long > *dyObj =
            dynamic_cast<sc_signal<unsigned long >*>(m_obj);
        assert(dyObj);
        unsigned long value = 0;
        if(sscanf(val, "%lu", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_signal<unsigned long long > *dyObj =
            dynamic_cast<sc_signal<unsigned long long>*>(m_obj);
        assert(dyObj);
        unsigned long value = 0;
        if(sscanf(val, "%lu", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE (BSM_REG_STR)){
        //std::string
        sc_signal<std::string > *dyObj = 
            dynamic_cast< sc_signal<std::string >* >(m_obj); 
        assert(dyObj);
        std::string str = val;
        dyObj->write(str);
        return true;
    } else if(BSM_CHECK_TYPE (BSM_REG_SC_LOGIC)) {
        sc_signal<sc_logic > *dyObj =
            dynamic_cast< sc_signal<sc_logic >* >(m_obj);
        assert(dyObj);
        char chr= val[0];
        dyObj->write(sc_logic(chr));
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_signal<sc_bit > *dyObj =
            dynamic_cast<sc_signal<sc_bit >*>(m_obj);
        assert(dyObj);
        char chr = val[0];
        dyObj->write(sc_bit(chr));
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_interface* interf = dynamic_cast<sc_interface*>(m_obj);
        assert(interf);
        if(interf->bsm_from_string(val))
            return true;
    }
    return false;
}

bool bsm_sim_object_impl::Write_Port2(const char* val)
{
    if(val == NULL) return false;

    if(BSM_CHECK_TYPE(BSM_REG_DOUBLE)) {
        sc_inout<double > *dyObj =
            dynamic_cast<sc_inout<double >*>(m_obj);
        assert(dyObj);
        char* end;
        double value = strtod(val, &end);

        dyObj->write(value);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_FLOAT)) {
        sc_inout<float > *dyObj = dynamic_cast<sc_inout<float >*>(m_obj);
        assert(dyObj);
        char* end;
        double value = strtod(val, &end);
        dyObj->write((float)value);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_BOOL)) {
        sc_inout<bool > *dyObj = dynamic_cast< sc_inout<bool >* >(m_obj);
        assert(dyObj);
        int value = atoi(val);
        dyObj->write(value==1);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_CHAR)) {
        sc_inout<char > *dyObj = dynamic_cast<sc_inout<char >*>(m_obj);
        assert(dyObj);
        char chr = val[0];
        dyObj->write(chr);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_SHORT)) {
        sc_inout<short > *dyObj = dynamic_cast<sc_inout<short >*>(m_obj);
        assert(dyObj);
        int value = atoi(val);
        dyObj->write((short)value);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT)) {
        sc_inout<int > *dyObj = dynamic_cast< sc_inout<int >* >(m_obj);
        assert(dyObj);
        int value = atoi(val);
        dyObj->write(value);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_LONG)) {
        sc_inout<long > *dyObj = dynamic_cast<sc_inout<long >*>(m_obj);
        assert(dyObj);
        long value = 0;
        if(sscanf(val, "%li", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_INT64)) {
        sc_inout<long long > *dyObj =
            dynamic_cast<sc_inout<long long >*>(m_obj);
        assert(dyObj);
        long value = 0;
        if(sscanf(val, "%li", &value) == 1) {
            dyObj->write((long long)value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_UCHAR)) {
        sc_inout<unsigned char > *dyObj =
            dynamic_cast<sc_inout<unsigned char >*>(m_obj);
        assert(dyObj);
        unsigned char chr = (unsigned char)val[0];
        dyObj->write(chr);
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_USHORT)) {
        sc_inout<unsigned short > *dyObj =
            dynamic_cast<sc_inout<unsigned short >*>(m_obj);
        assert(dyObj);
        unsigned short value = 0;
        if(sscanf(val, "%hu", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT)) {
        sc_inout<unsigned int > *dyObj =
            dynamic_cast<sc_inout<unsigned int >*>(m_obj);
        assert(dyObj);
        unsigned int value = 0;
        if(sscanf(val, "%u", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_ULONG)) {
        sc_inout<unsigned long > *dyObj =
            dynamic_cast<sc_inout<unsigned long >*>(m_obj);
        assert(dyObj);
        unsigned long value = 0;
        if(sscanf(val, "%lu", &value) == 1) {
            dyObj->write(value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE(BSM_REG_UINT64)) {
        sc_inout<unsigned long long > *dyObj =
            dynamic_cast<sc_inout<unsigned long long>*>(m_obj);
        assert(dyObj);
        unsigned long value = 0;
        if(sscanf(val, "%lu", &value) == 1) {
            dyObj->write((unsigned long long)value);
            return true;
        }
        return false;
    } else if(BSM_CHECK_TYPE (BSM_REG_STR)) {//std::string
        assert(false);
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_LOGIC)) {
        sc_inout<sc_logic > *dyObj =
            dynamic_cast<sc_inout<sc_logic >*>(m_obj);
        assert(dyObj);
        char chr = val[0];
        dyObj->write(sc_logic(chr));
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_SC_BIT)) {
        sc_inout<sc_bit > *dyObj =
            dynamic_cast<sc_inout<sc_bit >*>(m_obj);
        assert(dyObj);
        char chr = val[0];
        dyObj->write(sc_bit(chr));
        return true;
    } else if(BSM_CHECK_TYPE(BSM_REG_TEMPL)) {
        sc_port_base* interf = dynamic_cast<sc_port_base*>(m_obj);
        assert(interf);
        if(interf->bsm_from_string(val))
            return true;
    }
    return false;
}
bool bsm_sim_object_impl::write(const char* val)
{
    if(!m_bInitialized) Initialize();

    if(!is_writable()) return false;

    bool bRtn = false;
    if(m_nSCType == BSM_SC_SIGNAL)
        return Write_Signal(val);
    else if(m_nSCType == BSM_SC_INOUT)
        return Write_Port2(val);
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
const char* bsm_sim_object_impl::get_fx_disp(bool bSigned, int nWL, int nIWL,
                                             int nQM, int nOM, int nNR)
{
    try {
        m_disp = m_value;
        if(m_value.compare("NaN") != 0) {
            if(bSigned) {
                sc_fix_fast Inputa(nWL, nIWL, (sc_q_mode)nQM, (sc_o_mode)nOM);
                Inputa = m_value.c_str();
                m_disp = Inputa.to_string((sc_numrep)nNR);
            } else {
                sc_ufix_fast Inputa(nWL, nIWL, (sc_q_mode)nQM, (sc_o_mode)nOM);
                Inputa = m_value.c_str();
                m_disp = Inputa.to_string((sc_numrep)nNR);
            }
        }
    }
    catch(...)  {
        m_disp = m_value;
    }
    return m_disp.c_str();
}
//////////////////////////////////////////////////////////////////////////////
bsm_sim_trace_file_impl::bsm_sim_trace_file_impl(const char* name,int nType)
:m_trace(NULL)
{
    m_trace = new bsm_trace_file(name,nType);
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
    m_trace->set_bsm_trace_type(index,nTrigger,nTrace);
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
    m_trace->set_bsm_trace_type(index,nTrigger,nTrace);
}
void bsm_sim_trace_buf_impl::set_buffer(bsm_buf_write_inf* buf)
{
    m_trace->set_bsm_buffer(buf);
}

//////////////////////////////////////////////////////////////////////////////
bsm_sim_context_impl::bsm_sim_context_impl(sc_module* top)
:m_top(top)
,m_sim(NULL)
,m_strTimeStamp("")
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
        // the caller will be responsible to delte the object
        bsm_sim_object_impl* obj_impl = new bsm_sim_object_impl(obj);
        return obj_impl;
    }
    return NULL;
}
bsm_sim_object* bsm_sim_context_impl::next_object()
{
    sc_object* obj = m_sim->next_object();
    if(obj) {
        // the caller will be responsible to delte the object
        bsm_sim_object_impl* obj_impl = new bsm_sim_object_impl(obj);
        return obj_impl;
    }
    return NULL;
}
void bsm_sim_context_impl::start(double duration,int time_unit)
{
    sc_start(duration,sc_time_unit(time_unit));
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
bsm_sim_trace_file* bsm_sim_context_impl::add_trace(const char* name,int type)
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
    if(m_sim == NULL) return NULL;

    bsm_sim_trace_file_impl* fp_impl = dynamic_cast<bsm_sim_trace_file_impl*>(fp);
    if(fp_impl) {
        m_sim->del_trace_bsm(fp_impl->m_trace);
        // release the memory
        delete fp_impl;
        return true;
    }
    return false;
}
bool bsm_sim_context_impl::trace(bsm_sim_trace_file*tf ,bsm_sim_object*obj)
{
    if(m_sim == NULL) return NULL;

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
    if(m_sim==NULL) return NULL;

    bsm_sim_trace_buf_impl* fp_impl = dynamic_cast<bsm_sim_trace_buf_impl*>(fp);
    if(fp_impl) {
        m_sim->del_trace_buf(fp_impl->m_trace);
        delete fp_impl;
        return true;
    }
    return false;
}

bool bsm_sim_context_impl::trace_buf(bsm_sim_trace_buf*tf ,bsm_sim_object*obj)
{
    if(m_sim==NULL) return NULL;

    assert(tf && obj);
    bsm_sim_trace_buf_impl* fp_impl = dynamic_cast<bsm_sim_trace_buf_impl*>(tf);
    bsm_sim_object_impl* obj_impl = dynamic_cast<bsm_sim_object_impl*>(obj);
    assert(fp_impl && obj_impl);
    if(obj_impl && fp_impl)
        return bsm_trace_buf_object(fp_impl->m_trace, obj_impl->m_obj);
    return false;
}
