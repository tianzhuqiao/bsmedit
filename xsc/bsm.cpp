/**
*BSMEdit-Systemc Simulation Module Controling
*Copyright (C) 2009~2015 Tianzhu Qiao <ben.qiao@gmail.com>
*http://bsmedit.feiyilin.com/
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

#include <vector>
#include <assert.h>
#include <stdlib.h>
#include "bsm.h"
#ifdef WIN32
#define BSMEDIT_EXPORT __declspec( dllexport )
#else
#define BSMEDIT_EXPORT
#endif

bsm_buffer_impl::bsm_buffer_impl(int size)
: m_nRead(0)
, m_nWrite(0)
{
    resize(size);
}
bsm_buffer_impl::~bsm_buffer_impl()
{
}

//bsm_buf_read_inf
int bsm_buffer_impl::size()
{
    return m_buffer.size();
}
double bsm_buffer_impl::read(int n) const
{
    if(m_buffer.size() > 0) {
        n = (n + m_nWrite) % m_buffer.size();
        return m_buffer[n];
    }
    return 0.0;
}
//bsm_buf_write_inf
bool bsm_buffer_impl::append(double value)
{
    if(m_buffer.size() > 0) {
        assert(m_nWrite < (int)m_buffer.size() && m_nWrite >= 0);
        m_buffer[m_nWrite] = value;
        m_nWrite++;
        m_nWrite = m_nWrite%m_buffer.size();
        return true;
    }
    return false;
}

bool bsm_buffer_impl::write(double value, int n)
{
    if(n < (int)m_buffer.size() && n >= 0) {
        n = (n + m_nWrite) % m_buffer.size();
        m_buffer[n] = value;
        return true;
    }
    return false;
}

bool bsm_buffer_impl::resize(int nSize)
{
    if(nSize < 0) return false;
    m_buffer.resize(nSize);
    m_nRead = m_nWrite = 0;
    return true;
}

bool bsm_buffer_impl::retrive(double* buf, int size)
{
    int count = (int)(size < this->size() ? size : this->size());
    if(m_nWrite >= count)
        std::copy(m_buffer.begin() + m_nWrite - count, m_buffer.begin() + m_nWrite, buf);
    else {
        int sz = count - m_nWrite;
        std::copy(m_buffer.begin() + (this->size() - sz), m_buffer.begin() + this->size(), buf);
        std::copy(m_buffer.begin(), m_buffer.begin() + m_nWrite, buf + sz);
    }

    return true;
}
sim_context context;
extern "C"{
    BSMEDIT_EXPORT bool ctx_first_object(sim_object* obj)
    {
        bsm_sim_object* simobj = context.m_sim->first_object();
        if(simobj) {
            obj->m_obj = simobj;
            strcpy(obj->name, simobj->name());
            strcpy(obj->basename, simobj->basename());
            strcpy(obj->kind, simobj->kind());
            obj->writable = simobj->is_writable();
            obj->readable = simobj->is_readable();
            obj->numeric = simobj->is_number();
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT bool ctx_next_object(sim_object* obj)
    {
        bsm_sim_object* simobj = context.m_sim->next_object();
        if(simobj) {
            obj->m_obj = simobj;
            strcpy(obj->name, simobj->name());
            strcpy(obj->basename, simobj->basename());
            strcpy(obj->kind, simobj->kind());
            obj->writable = simobj->is_writable();
            obj->readable = simobj->is_readable();
            obj->numeric = simobj->is_number();
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT bool ctx_del_object(sim_object* obj)
    {
        if(obj) {
            delete obj->m_obj;
            obj->m_obj = NULL;
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT bool ctx_read(sim_object* obj)
    {
        if(obj) {
            strcpy(obj->value, obj->m_obj->read());
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT bool ctx_write(sim_object* obj)
    {
        if(obj) {
            obj->m_obj->write(obj->value);
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT void ctx_start(int duration, int unit)
    {
        context.m_sim->start(duration, unit);
    }

    BSMEDIT_EXPORT void ctx_stop()
    {
        context.m_sim->stop();
        delete context.m_sim;
        context.m_sim = NULL;
    }

    BSMEDIT_EXPORT double ctx_time()
    {
        return context.m_sim->time();
    }

    BSMEDIT_EXPORT double ctx_time_sec(double time, int unit)
    {
        return context.m_sim->time(time, unit);
    }

    BSMEDIT_EXPORT bool ctx_time_str(char* time)
    {
        if(time){
            strcpy(time, context.m_sim->time_string());
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT void ctx_set_callback(bsm_sim_context::bsm_callback fun)
    {
        context.m_sim->set_callback(fun);
    }

    BSMEDIT_EXPORT bool ctx_add_trace_file(sim_trace_file* t)
    {
        bsm_sim_trace_file* obj = context.m_sim->add_trace(t->name, t->type);
        if(obj) {
            t->m_obj = obj;
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT bool ctx_remove_trace_file(sim_trace_file* t)
    {
        if(context.m_sim->remove_trace(t->m_obj)) {
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT bool ctx_trace_file(sim_trace_file* t, sim_object* obj, sim_object* val, int trigger)
    {
        if(val) {
            //ugly code, to be updated
            context.m_sim->trace(t->m_obj, val->m_obj);
            t->m_obj->set_trace_type(-1, trigger, 1);
            context.m_sim->trace(t->m_obj, obj->m_obj);
            t->m_obj->set_trace_type(-1, 4, 0);
        } else {
            context.m_sim->trace(t->m_obj, obj->m_obj);
            t->m_obj->set_trace_type(-1, trigger, 0);
        }
        return context.m_sim->trace(t->m_obj, obj->m_obj);
    }

    BSMEDIT_EXPORT bool ctx_add_trace_buf(sim_trace_buf* t)
    {
        bsm_sim_trace_buf* obj = context.m_sim->add_trace_buf(t->name);
        if(obj) {
            t->m_obj = obj;
            bsm_buffer_impl* buf = new bsm_buffer_impl(t->size);
            obj->set_buffer(buf);
            t->m_buf = buf;
            return true;
        }
        return false;
    }

    BSMEDIT_EXPORT bool ctx_remove_trace_buf(sim_trace_buf* t)
    {
        return context.m_sim->remove_trace_buf(t->m_obj);
    }

    BSMEDIT_EXPORT bool ctx_trace_buf(sim_trace_buf* t, sim_object* obj, sim_object* val, int trigger)
    {
        if(val) {    
            //ugly code, to be updated
            context.m_sim->trace_buf(t->m_obj, val->m_obj);
            t->m_obj->set_trace_type(-1, trigger, 1);
            context.m_sim->trace_buf(t->m_obj, obj->m_obj);
            t->m_obj->set_trace_type(-1, 4, 0);
        } else {
            context.m_sim->trace_buf(t->m_obj, obj->m_obj);
            t->m_obj->set_trace_type(-1, trigger, 0);
        }
        return true;
    }

    BSMEDIT_EXPORT bool ctx_read_trace_buf(sim_trace_buf* t)
    {
        return t->m_buf->retrive(t->buffer, t->size);
    }

    BSMEDIT_EXPORT bool ctx_resize_trace_buf(sim_trace_buf* t)
    {
        return t->m_buf->resize(t->size);
    }
}