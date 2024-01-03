#include <math.h>
#include "top.h"
#ifndef M_PI
#define M_PI       3.14159265358979323846
#endif

top::~top() {
}

void top::Action() {
    sig_sin.write(sin(m_phase));
    sig_cos.write(cos(m_phase));
    int steps = sig_steps.read();
    if (steps < 256) {
        steps = 256;
        sig_steps.write(256);
    }
    m_phase = m_phase + M_PI / steps;
    if (m_phase > 2 * M_PI) m_phase -= 2 * M_PI;
}
