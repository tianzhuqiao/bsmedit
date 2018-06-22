#include "systemc.h"
extern "C" {
#include "bsm.h"
}
#include "top.h"

// define the interfaces to bsmedit
BSMEDIT_IMPLEMENT_MODULE(top,"top");
