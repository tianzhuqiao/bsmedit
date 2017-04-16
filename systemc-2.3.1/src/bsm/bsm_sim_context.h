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

#ifndef _BSM_SIM_CONTEXT_H_
#define _BSM_SIM_CONTEXT_H_
#include "bsm_object.h"
#include "bsm_buffer_intf.h"
class bsm_sim_object:public bsm_object_base
{
public:
    bsm_sim_object(){};
    virtual~bsm_sim_object(){};
public:
    virtual const char* name()=0; 
    virtual const char* basename()=0;
    virtual const char* kind()=0;
    virtual const char* read()=0;
    virtual bool write(const char*)=0;
    virtual bool is_writable()=0 ;
    virtual bool is_readable()=0;
    virtual bool is_number()=0;
    virtual const char* get_fx_disp(bool,int,int,int,int,int)=0;
};
class bsm_sim_trace_file: public bsm_object_base
{
public:
    bsm_sim_trace_file(){};
    virtual~bsm_sim_trace_file(){};
public:
    virtual void enable(bool) = 0;
    virtual bool is_enable() = 0;
    virtual void set_print_type(unsigned int) = 0;
    virtual void set_trace_type(int,unsigned int,unsigned int) = 0;
};

class bsm_sim_trace_buf:public bsm_object_base
{
public:
    bsm_sim_trace_buf(){};
    virtual~bsm_sim_trace_buf(){};
public:
    virtual void enable(bool) = 0;
    virtual bool is_enable() = 0;
    virtual void set_trace_type(int,unsigned int,unsigned int) = 0;
    virtual void set_buffer(bsm_buf_write_inf*)=0;
};
enum {SC_OBJ_UNKNOWN,SC_OBJ_SIGNAL,SC_OBJ_CLOCK,SC_OBJ_INPUT,SC_OBJ_OUTPUT,SC_OBJ_INOUT,
SC_OBJ_MODULE,SC_OBJ_XSC_PROP,SC_OBJ_XSC_ARRAY,SC_OBJ_XSC_ARRAY_ITEM};
class bsm_sim_context:public bsm_object_base
{
public:
    bsm_sim_context(){};
    virtual~bsm_sim_context(){};

public:
    virtual const char* sc_version()=0;
    virtual const char* sc_copyright()=0;

    virtual bsm_sim_object* first_object()=0;
    virtual bsm_sim_object* next_object()=0;
    virtual void start(double duration,int time_unit)=0;
    virtual void stop()=0;
    //virtual void destroy()=0;

    virtual double time()=0;
    virtual double time(double time, int unit)=0;
    virtual const char* time_string()=0;
    typedef  int(*bsm_callback)(int);
    virtual void set_callback(bsm_callback pCallBack)=0;
    //trace
    virtual bsm_sim_trace_file* add_trace(const char* name,int nType)=0;
    virtual bool remove_trace(bsm_sim_trace_file* )=0;
    virtual bool trace(bsm_sim_trace_file*,bsm_sim_object*)=0;
    //trace buffer
    virtual bsm_sim_trace_buf* add_trace_buf(const char* name)=0;
    virtual bool remove_trace_buf(bsm_sim_trace_buf*)=0;
    virtual bool trace_buf(bsm_sim_trace_buf*,bsm_sim_object*)=0;
};

#endif //!defined(_BSM_SIM_CONTEXT_H_)

/* 
 *History:
 *
 * $Log$
 *
 */
