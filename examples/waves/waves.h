#ifndef _WAVE_H_
#define _WAVE_H_
typedef int (*pyCallback)(int);
typedef struct wave_frame {
    int rows;
    int cols;
    float* frame;
    int max_frame_len;
    pyCallback callback;
} wave_frame;

void get_frame(wave_frame* frame);
void get_frames(wave_frame* frame);
#endif // _WAVE_H_
