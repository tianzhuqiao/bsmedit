#include "systemc.h"

#include "top.h"
#include "bsm.h"

#ifdef BSM_DLL_SIM
// for compability with v2
BSMEDIT_DECLARE_MODULE
BSMEDIT_IMPLEMENT_MODULE(top,"top");
#else
int sc_main(int ac, char* av[])
{
    top sctop("top");
    bsm_sim_context_impl* m_sim = new bsm_sim_context_impl(&sctop);
    cout << m_sim->time(1, SC_SEC) << endl;
	sc_trace_file *fpvcd;                          // Declare FilePointer fp
	fpvcd=sc_create_vcd_trace_file("wave");        // Open the VCD file, create wave.vcd file
    sc_trace(fpvcd,sctop.sig_int,  "sig_int");                 // Add signals to trace file

	sc_start(15000);
    sc_start(15000);

	sc_close_vcd_trace_file(fpvcd);                // close(fp)
    sc_time scsimtime(1, SC_SEC);
    cout << scsimtime.to_seconds() << endl;
    return 0;
}
#endif
