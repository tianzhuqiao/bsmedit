#include <vector>
#include <assert.h>
#include <stdlib.h>
#include <map>
#include "systemc.h"

extern "C" {
#include "bsm.h"
}

class bsm_buffer_impl : public bsm_buf_read_inf, public bsm_buf_write_inf
{
public:
    bsm_buffer_impl(int size=256);
    virtual ~bsm_buffer_impl();

public:
    // bsm_buf_read_inf
    virtual int size();
    virtual double read(int n) const;

    // bsm_buf_write_inf
    virtual bool write(double value, int n);
    virtual bool append(double value);
    virtual bool resize(int nSize);

    bool retrive(double* buf, int size);
protected:
    std::vector<double> m_buffer;
    int m_nRead;
    int m_nWrite;
};

static std::map<std::string, bsm_sim_object*> sim_objs;
static std::map<std::string, bsm_sim_trace_file*> sim_tfiles;
static std::map<std::string, bsm_sim_trace_buf*> sim_tbufs;
static std::map<std::string, bsm_buffer_impl*> sim_bufs;

bsm_buffer_impl::bsm_buffer_impl(int size)
    : m_nRead(0)
    , m_nWrite(0)
{
    resize(size);
}

bsm_buffer_impl::~bsm_buffer_impl()
{
}

// bsm_buf_read_inf
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

// bsm_buf_write_inf
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
    if(m_nWrite >= count) {
        std::copy(m_buffer.begin()+m_nWrite-count, m_buffer.begin()+m_nWrite, buf);
    } else {
        int sz = count - m_nWrite;
        std::copy(m_buffer.begin()+(this->size()-sz), m_buffer.begin()+this->size(), buf);
        std::copy(m_buffer.begin(), m_buffer.begin()+m_nWrite, buf+sz);
    }

    return true;
}

bsm_sim_context* g_sim = NULL;
BSMEDIT_EXPORT bool ctx_read(sim_object* obj)
{
    if(obj && obj->readable) {
        return sim_objs[obj->name]->read((bsm_sim_object::bsm_object_value*)&obj->value);
    }
    return false;
}

BSMEDIT_EXPORT bool ctx_write(sim_object* obj)
{
    if(obj && obj->writable) {
        return sim_objs[obj->name]->write((bsm_sim_object::bsm_object_value*)&obj->value);
    }
    return false;
}

void copy_simobject(sim_object* obj, bsm_sim_object* simobj)
{
    snprintf(obj->name, MAX_NAME_LEN, "%s", simobj->name());
    snprintf(obj->basename, MAX_NAME_LEN, "%s", simobj->basename());
    snprintf(obj->kind, MAX_NAME_LEN, "%s", simobj->kind());
    obj->writable = simobj->is_writable();
    obj->readable = simobj->is_readable();
    obj->numeric = simobj->is_number();
    sim_objs[obj->name] = simobj;
    ctx_read(obj);
}

BSMEDIT_EXPORT bool ctx_first_object(sim_object* obj)
{
    bsm_sim_object* simobj = g_sim->first_object();
    if(obj && simobj) {
        copy_simobject(obj, simobj);
        return true;
    }
    return false;
}

BSMEDIT_EXPORT bool ctx_next_object(sim_object* obj)
{
    bsm_sim_object* simobj = g_sim->next_object();
    if(obj && simobj) {
        copy_simobject(obj, simobj);
        return true;
    }
    return false;
}

BSMEDIT_EXPORT bool ctx_free_object(sim_object* obj)
{
    if(obj) {
        delete sim_objs[obj->name];
        sim_objs.erase(obj->name);
        return true;
    }
    return false;
}

BSMEDIT_EXPORT void ctx_start(double duration, int unit)
{
	g_sim->start(duration, unit);
}

BSMEDIT_EXPORT void ctx_stop()
{
	g_sim->stop();
    delete g_sim;
    g_sim = NULL;
}

BSMEDIT_EXPORT double ctx_time()
{
    return g_sim->time();
}

BSMEDIT_EXPORT bool ctx_time_str(char* time)
{
    if(time) {
        snprintf(time, MAX_NAME_LEN, "%s", g_sim->time_string());
        return true;
    }
    return false;
}

BSMEDIT_EXPORT void ctx_set_callback(bsm_sim_context::bsm_callback fun)
{
	g_sim->set_callback(fun);
}

BSMEDIT_EXPORT bool ctx_create_trace_file(sim_trace_file* t)
{
    bsm_sim_trace_file* obj = g_sim->add_trace(t->name, t->type);
    if(obj) {
        sim_tfiles[t->name] = obj;
        return true;
    }
    return false;
}

BSMEDIT_EXPORT bool ctx_close_trace_file(sim_trace_file* t)
{
    if(g_sim->remove_trace(sim_tfiles[t->name])) {
        sim_tfiles.erase(t->name);
        return true;
    }
    return false;
}

BSMEDIT_EXPORT bool ctx_trace_file(sim_trace_file* t, sim_object* obj,
    sim_object* val, int trigger)
{
    if(!t || ! obj) {
        return false;
    }
    if(val) {
        // ugly code, to be updated
		g_sim->trace(sim_tfiles[t->name], sim_objs[val->name]);
        sim_tfiles[t->name]->set_trace_type(-1, trigger, 1);
		g_sim->trace(sim_tfiles[t->name], sim_objs[obj->name]);
        sim_tfiles[t->name]->set_trace_type(-1, 4, 0);
    } else {
		g_sim->trace(sim_tfiles[t->name], sim_objs[obj->name]);
        sim_tfiles[t->name]->set_trace_type(-1, trigger, 0);
    }
    return true;
}

BSMEDIT_EXPORT bool ctx_create_trace_buf(sim_trace_buf* t)
{
    bsm_sim_trace_buf* obj = g_sim->add_trace_buf(t->name);
    if(obj) {
        sim_tbufs[t->name] = obj;
        bsm_buffer_impl* buf = new bsm_buffer_impl(t->size);
        obj->set_buffer(buf);
        sim_bufs[t->name] = buf;
        return true;
    }
    return false;
}

BSMEDIT_EXPORT bool ctx_close_trace_buf(sim_trace_buf* t)
{
    if(sim_tbufs.find(t->name) != sim_tbufs.end())
        return g_sim->remove_trace_buf(sim_tbufs[t->name]);
    return false;
}

BSMEDIT_EXPORT bool ctx_trace_buf(sim_trace_buf* t, sim_object* obj,
    sim_object* val, int trigger)
{
    if(val) {
        // ugly code, to be updated
		g_sim->trace_buf(sim_tbufs[t->name], sim_objs[val->name]);
        sim_tbufs[t->name]->set_trace_type(-1, trigger, 1);
		g_sim->trace_buf(sim_tbufs[t->name], sim_objs[obj->name]);
        sim_tbufs[t->name]->set_trace_type(-1, 4, 0);
    } else {
		g_sim->trace_buf(sim_tbufs[t->name], sim_objs[obj->name]);
        sim_tbufs[t->name]->set_trace_type(-1, trigger, 0);
    }
    return true;
}

BSMEDIT_EXPORT bool ctx_read_trace_buf(sim_trace_buf* t)
{
    return sim_bufs[t->name]->retrive(t->buffer, t->size);
}

BSMEDIT_EXPORT bool ctx_resize_trace_buf(sim_trace_buf* t)
{
    return sim_bufs[t->name]->resize(t->size);
}

