extern "C" {
#include "cexample.h"
}
void get_frame(ce_frame* frame)
{
    frame->rows = 10;
    frame->cols = 10;
    if(frame->max_frame_len < frame->rows*frame->cols)
        return;
    for(int i=0; i<10; i++) {
        for(int j=0; j<10; j++) {
            frame->frame[i*10+j] = i*10+j;
        }
    }

}
