#ifndef TOP_H_
#define TOP_H_

#include "systemc.h"

class top : public sc_module {
 public:
    SC_HAS_PROCESS(top);
    top(sc_module_name name_):
    sc_module(name_)
        , m_phase(0.0)
        , clock("CLOCK", 10, 0.5, 0.0)
        , sig_sin("sig_sin")
        , sig_cos("sig_cos")
        , sig_steps("sig_steps", 256) {
        SC_METHOD(Action);
        sensitive_pos << clock;
    }
    virtual ~top();

 private:
    void Action();

 private:
    double m_phase;
    // signal
    sc_clock clock;
    sc_signal<double> sig_sin;
    sc_signal<double> sig_cos;
    sc_signal<int> sig_steps;
};

#endif  // #ifndef TOP_H_
