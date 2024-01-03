#include "systemc.h"
extern "C" {
#include "sysc/bsm/bsm.h"
}
#include "top.h"

// define the interfaces to bsmedit
BSMEDIT_IMPLEMENT_MODULE(top, "top");
