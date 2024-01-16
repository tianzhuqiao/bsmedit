#ifndef SRC_SYSC_BSM_BSM_H_
#define SRC_SYSC_BSM_BSM_H_

#ifdef WIN32
#define BSMEDIT_EXPORT __declspec(dllexport)
#else
#define BSMEDIT_EXPORT
#endif
#define MAX_NAME_LEN 256

typedef struct bsm_object_value {
        char sValue[MAX_NAME_LEN];
        double fValue;
        unsigned long long uValue;
        long long iValue;
        int type;
}bsm_object_value;
typedef struct sim_object {
    char name[MAX_NAME_LEN];
    char basename[MAX_NAME_LEN];
    char kind[MAX_NAME_LEN];
    bsm_object_value value;
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

#define BSMEDIT_IMPLEMENT_MODULE(T, name) extern bsm_sim_context* g_sim;\
extern "C"\
{\
    BSMEDIT_EXPORT void bsm_sim_top(sim_context *context)\
    {\
        g_sim = bsm_create_sim_context(new T(name));\
        snprintf(context->copyright, MAX_NAME_LEN, "%s", g_sim->sc_copyright());\
        snprintf(context->version, MAX_NAME_LEN, "%s", g_sim->sc_version());\
    }\
}
BSMEDIT_EXPORT void bsm_sim_top(sim_context *context);
BSMEDIT_EXPORT bool ctx_read(sim_object* obj);
BSMEDIT_EXPORT bool ctx_write(sim_object* obj);
BSMEDIT_EXPORT bool ctx_first_object(sim_object* obj);
BSMEDIT_EXPORT bool ctx_next_object(sim_object* obj);
BSMEDIT_EXPORT bool ctx_free_object(sim_object* obj);
BSMEDIT_EXPORT void ctx_start(double duration, int unit);
BSMEDIT_EXPORT void ctx_stop();
BSMEDIT_EXPORT double ctx_time();
BSMEDIT_EXPORT bool ctx_time_str(char* time);
BSMEDIT_EXPORT typedef int(*bsm_callback)(int);
BSMEDIT_EXPORT void ctx_set_callback(bsm_callback fun);
BSMEDIT_EXPORT bool ctx_create_trace_file(sim_trace_file* t);
BSMEDIT_EXPORT bool ctx_close_trace_file(sim_trace_file* t);
BSMEDIT_EXPORT bool ctx_trace_file(sim_trace_file* t, sim_object* obj,
                                   sim_object* val, int trigger);
BSMEDIT_EXPORT bool ctx_create_trace_buf(sim_trace_buf* t);
BSMEDIT_EXPORT bool ctx_close_trace_buf(sim_trace_buf* t);
BSMEDIT_EXPORT bool ctx_trace_buf(sim_trace_buf* t, sim_object* obj,
                                  sim_object* val, int trigger);
BSMEDIT_EXPORT bool ctx_read_trace_buf(sim_trace_buf* t);
BSMEDIT_EXPORT bool ctx_resize_trace_buf(sim_trace_buf* t);
#endif  // SRC_SYSC_BSM_BSM_H_

