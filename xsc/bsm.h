#ifndef _BSM_H
#define _BSM_H

#ifdef WIN32
#define BSMEDIT_EXPORT __declspec(dllexport)
#else
#define BSMEDIT_EXPORT
#endif
#define MAX_NAME_LEN 256

#ifdef BSM_SYSTEMC_INTERFACE
#include "systemc.h"
#endif  // BSM_SYSTEMC_INTERFACE

typedef struct sim_object {
    char name[MAX_NAME_LEN];
    char basename[MAX_NAME_LEN];
    char kind[MAX_NAME_LEN];
#ifdef BSM_SYSTEMC_INTERFACE
    bsm_sim_object::bsm_object_value value;
#else
    struct bsm_object_value {
        char sValue[256];
        double fValue;
        unsigned long long uValue;
        long long iValue;
        int type;
    } value;
#endif  // BSM_SYSTEMC_INTERFACE
    bool writable;
    bool readable;
    bool numeric;
}sim_object;

typedef struct sim_trace_file {
    char name[MAX_NAME_LEN];
    int type;
}sim_trace_file;

typedef struct sim_trace_buf {
    char name[MAX_NAME_LEN];
    double* buffer;
    int size;
}sim_trace_buf;

typedef struct sim_context {
    char version[MAX_NAME_LEN];
    char copyright[MAX_NAME_LEN];
}sim_context;

#define BSMEDIT_IMPLEMENT_MODULE(T, name) extern "C"\
{\
    BSMEDIT_EXPORT void bsm_sim_top(sim_context *context)\
    {\
        extern bsm_sim_context* sim;\
        sim = new bsm_sim_context_impl(new T(name));\
        snprintf(context->copyright, MAX_NAME_LEN, "%s", sim->sc_copyright());\
        snprintf(context->version, MAX_NAME_LEN, ""%s, sim->sc_version());\
    }\
}
void bsm_sim_top(sim_context *context);
bool ctx_read(sim_object* obj);
bool ctx_write(sim_object* obj);
bool ctx_first_object(sim_object* obj);
bool ctx_next_object(sim_object* obj);
bool ctx_free_object(sim_object* obj);
void ctx_start(double duration, int unit);
void ctx_stop();
double ctx_time();
bool ctx_time_str(char* time);
#ifdef BSM_SYSTEMC_INTERFACE
void ctx_set_callback(bsm_sim_context::bsm_callback fun);
#else
typedef int(*bsm_callback)(int);
void ctx_set_callback(bsm_callback fun);
#endif  // BSM_SYSTEMC_INTERFACE
bool ctx_create_trace_file(sim_trace_file* t);
bool ctx_close_trace_file(sim_trace_file* t);
bool ctx_trace_file(sim_trace_file* t, sim_object* obj, sim_object* val, int trigger);
bool ctx_create_trace_buf(sim_trace_buf* t);
bool ctx_close_trace_buf(sim_trace_buf* t);
bool ctx_trace_buf(sim_trace_buf* t, sim_object* obj, sim_object* val, int trigger);
bool ctx_read_trace_buf(sim_trace_buf* t);
bool ctx_resize_trace_buf(sim_trace_buf* t);
#endif  // _BSM_H
