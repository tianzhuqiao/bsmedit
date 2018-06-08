#include <math.h>
extern "C" {
#include "wave.h"
}

void get_frame(wave_frame* frame)
{
    frame->rows = 30;
    frame->cols = 30;
    if(frame->max_frame_len < frame->rows*frame->cols)
        return;
    for(int i=0; i<30; i++) {
        for(int j=0; j<30; j++) {
            frame->frame[i*30+j] = cos(2*M_PI*i/30)*sin(2*M_PI*j/30);
        }
    }
}
