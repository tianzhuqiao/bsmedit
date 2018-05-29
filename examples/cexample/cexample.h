#ifndef _CEXAMPLE_H_
#define _CEXAMPLE_H_
typedef struct ce_frame {
    int rows;
    int cols;
    int* frame;
    int max_frame_len;
} ce_frame;

void get_frame(ce_frame* frame);
#endif // #ifndef _CEXAMPLE_H_
