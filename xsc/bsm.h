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

#ifndef _BSM_H
#define _BSM_H
#include "systemc.h"

#ifdef WIN32
    #define BSMEDIT_EXPORT __declspec( dllexport )
#else
    #define BSMEDIT_EXPORT
#endif
#define MAX_NAME_LEN 255
class bsm_buffer_impl : public bsm_buf_read_inf, public bsm_buf_write_inf
{
public:
    bsm_buffer_impl(int size = 256);
    virtual ~bsm_buffer_impl();

public:
    //bsm_buf_read_inf
    virtual int size();
    virtual double read(int n) const;

    //bsm_buf_write_inf
    virtual bool write(double value, int n);
    virtual bool append(double value);
    virtual bool resize(int nSize);

    bool retrive(double* buf, int size);
protected:
    std::vector<double> m_buffer;
    int m_nRead;
    int m_nWrite;
};

typedef struct sim_context {
    char version[MAX_NAME_LEN];
    char copyright[MAX_NAME_LEN];

    bsm_sim_context* m_sim;
}sim_context;

typedef struct sim_object {
    char name[MAX_NAME_LEN];
    char basename[MAX_NAME_LEN];
    char kind[MAX_NAME_LEN];
    char value[MAX_NAME_LEN];
    bool writable;
    bool readable;
    bool numeric;

    bsm_sim_object* m_obj;
}sim_object;

typedef struct sim_trace_file {
    char name[MAX_NAME_LEN];
    int type;

    bsm_sim_trace_file* m_obj;
}sim_trace_file;

typedef struct sim_trace_buf {
    char name[MAX_NAME_LEN];
    double* buffer;
    int size;

    bsm_sim_trace_buf* m_obj;
    bsm_buffer_impl* m_buf;
}sim_trace_buf;
extern sim_context context;
#define BSMEDIT_DECLARE_MODULE   extern "C"\
{\
    BSMEDIT_EXPORT bsm_sim_context* bsm_sim_top_create(); \
    BSMEDIT_EXPORT void bsm_sim_run(double duration, int time_unit); \
    BSMEDIT_EXPORT sim_context* bsm_sim_top(); \
}
#define BSMEDIT_IMPLEMENT_MODULE(T,name) bsm_sim_context* bsm_sim_top_create()\
{\
    return  new bsm_sim_context_impl(new T(name)); \
}\
\
void bsm_sim_run(double duration, int time_unit)\
{\
    sc_start(duration, (sc_time_unit)time_unit); \
}\
sim_context* bsm_sim_top()\
{\
    context.m_sim = new bsm_sim_context_impl(new T(name));\
    strcpy(context.copyright, context.m_sim->sc_copyright());\
    strcpy(context.version, context.m_sim->sc_version());\
    return &context;\
}

#endif //!define _BSM_H
