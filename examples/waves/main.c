#include <math.h>
#include <stdio.h>
#include <unistd.h>
extern "C" {
#include "waves.h"
}

void get_frame(wave_frame* frame) {
    static float initial_phase = 0;
    initial_phase += 2.*M_PI/100.0;
    if (initial_phase > 2.*M_PI)
        initial_phase -= 2.*M_PI;
    frame->rows = 30;
    frame->cols = 30;
    if (frame->max_frame_len < frame->rows*frame->cols)
        return;
    for (int i=0; i < 30; i++) {
        for (int j=0; j < 30; j++) {
            frame->frame[i*30+j] = cos(2*M_PI*i/30+initial_phase)*
                                   sin(2*M_PI*j/30+initial_phase);
        }
    }
}

void get_frames(wave_frame* frame) {
    while (1) {
        get_frame(frame);
        if (frame->callback) {
            if (!frame->callback(0)) {
                break;
            }
        }
        usleep(100000);
    }
}
