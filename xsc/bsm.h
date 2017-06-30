#ifndef _BSM_H
#define _BSM_H
#include "systemc.h"

#ifdef WIN32
#define BSMEDIT_EXPORT __declspec( dllexport )
#else
#define BSMEDIT_EXPORT
#endif
#define MAX_NAME_LEN 256
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

typedef struct sim_object {
    char name[MAX_NAME_LEN];
    char basename[MAX_NAME_LEN];
    char kind[MAX_NAME_LEN];
    bsm_sim_object::bsm_object_value value;
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

typedef struct sim_context {
    char version[MAX_NAME_LEN];
    char copyright[MAX_NAME_LEN];

    bsm_sim_context* m_sim;
}sim_context;

extern sim_context context;

#define BSMEDIT_IMPLEMENT_MODULE(T, name) extern "C"\
{\
    BSMEDIT_EXPORT sim_context* bsm_sim_top(); \
}\
sim_context* bsm_sim_top()\
{\
    context.m_sim = new bsm_sim_context_impl(new T(name));\
    strcpy(context.copyright, context.m_sim->sc_copyright());\
    strcpy(context.version, context.m_sim->sc_version());\
    return &context;\
}

#endif //!define _BSM_H
