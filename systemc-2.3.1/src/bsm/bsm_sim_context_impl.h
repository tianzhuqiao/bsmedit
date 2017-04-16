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

#ifndef _BSM_SIM_CONTEXT_IMPL_H_
#define _BSM_SIM_CONTEXT_IMPL_H_
using namespace sc_core;
#include "bsm_sim_context.h"
class bsm_sim_object_impl:public bsm_object_impl<bsm_sim_object>
{
    enum{BSM_REG_UNKNOWN,BSM_REG_DOUBLE,BSM_REG_FLOAT,BSM_REG_BOOL,
        BSM_REG_CHAR,BSM_REG_SHORT,BSM_REG_INT,BSM_REG_LONG,BSM_REG_INT64,
        BSM_REG_UCHAR,BSM_REG_USHORT,BSM_REG_UINT,BSM_REG_ULONG,BSM_REG_UINT64
        ,BSM_REG_STR,BSM_REG_SC_LOGIC,BSM_REG_SC_BIT,BSM_REG_TEMPL};
    enum{BSM_SC_UNKNOWN,BSM_SC_SIGNAL,BSM_SC_IN,BSM_SC_INOUT};
public:
    bsm_sim_object_impl(sc_object* obj);
    virtual~bsm_sim_object_impl();
public:
    virtual const char* name(); 
    virtual const char* basename();
    virtual const char* kind();
    virtual const char* read();
    virtual bool write(const char*);
    virtual bool is_writable();
    virtual bool is_readable();
    virtual bool is_number();
    virtual const char* get_fx_disp(bool,int,int,int,int,int);
protected:
    void check_kind();
    void Initialize();
    void CheckSignalType();
    void CheckInputType();
    void CheckOutputType();
    void Read_Signal();
    void Read_Port();
    void Read_Port2();
    bool Write_Signal(const char* val);
    bool Write_Port2(const char* val);
public:
    sc_object* m_obj;
    std::string m_value;
    std::string m_disp;
    bool m_bInitialized;
    int m_nKind;
    std::string m_strBSMType;
    int m_nRegType;
    int m_nSCType;
};
class bsm_sim_trace_file_impl:public bsm_object_impl<bsm_sim_trace_file>
{
public:
    bsm_sim_trace_file_impl(const char* name,int nType);
    virtual~bsm_sim_trace_file_impl();
public:
    virtual void enable(bool);
    virtual bool is_enable();
    virtual void set_print_type(unsigned int);
    virtual void set_trace_type(int,unsigned int,unsigned int);
public:
    bsm_trace_file* m_trace;
};

class bsm_sim_trace_buf_impl:public bsm_object_impl<bsm_sim_trace_buf>
{
public:
    bsm_sim_trace_buf_impl(const char* name);
    virtual~bsm_sim_trace_buf_impl();
public:
    virtual void enable(bool) ;
    virtual bool is_enable();
    virtual void set_trace_type(int,unsigned int,unsigned int);
    virtual void set_buffer(bsm_buf_write_inf*);
public:
    bsm_trace_buf* m_trace;
};

class bsm_sim_context_impl:public bsm_object_impl<bsm_sim_context>
{
public:
    bsm_sim_context_impl(sc_module* top);
    virtual~bsm_sim_context_impl();

public:
    virtual const char* sc_version();
    virtual const char* sc_copyright();

    virtual bsm_sim_object* first_object();
    virtual bsm_sim_object* next_object();
    virtual void start(double duration,int time_unit);
    virtual void stop();
    virtual double time();
    virtual double time(double time, int unit);
    virtual const char* time_string();
    
    void set_callback(bsm_callback pCallBack);

    //trace
    virtual bsm_sim_trace_file* add_trace(const char* name,int nType);
    virtual bool remove_trace(bsm_sim_trace_file* );
    virtual bool trace(bsm_sim_trace_file*,bsm_sim_object*);
    //trace buffer
    virtual bsm_sim_trace_buf* add_trace_buf(const char* name);
    virtual bool remove_trace_buf(bsm_sim_trace_buf*);
    virtual bool trace_buf(bsm_sim_trace_buf*,bsm_sim_object*);
public:
    sc_module* m_top;
    sc_simcontext* m_sim;
    std::string m_strTimeStamp;
};

#endif //!defined(_BSM_SIM_CONTEXT_IMPL_H_)

/* 
 *History:
 *
 * $Log$
 *
 */
