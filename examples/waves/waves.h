#ifndef _WAVE_H_
#define _WAVE_H_
typedef struct wave_frame {
    int rows;
    int cols;
    float* frame;
    int max_frame_len;
} wave_frame;

void get_frame(wave_frame* frame);
#endif // _WAVE_H_
