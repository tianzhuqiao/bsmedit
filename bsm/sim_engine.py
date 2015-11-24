import ctypes as ct
import traceback

SC_OBJ_UNKNOWN        = 0
SC_OBJ_SIGNAL         = 1
SC_OBJ_INPUT          = 2
SC_OBJ_OUTPUT         = 3
SC_OBJ_INOUT          = 4
SC_OBJ_CLOCK          = 5
SC_OBJ_XSC_PROP       = 6
SC_OBJ_XSC_ARRAY_ITEM = 7
SC_OBJ_MODULE         = 8
SC_OBJ_XSC_ARRAY      = 9

BSM_FS  = 0
BSM_PS  = 1
BSM_NS  = 2
BSM_US  = 3
BSM_MS  = 4
BSM_SEC = 5

BSM_POSEDGE  = 0
BSM_NEGEDGE  = 1
BSM_BOTHEDGE = 2
BSM_NONEEDGE = 3

BSM_TRACE_VCD    = 0
BSM_TRACE_SIMPLE = 1

class simObj(ct.Structure):
    _fields_ = [('name', ct.c_char*255),
                ('basename', ct.c_char*255),
                ('kind', ct.c_char*255),
                ('value', ct.c_char*255),
                ('writable', ct.c_bool),
                ('readable', ct.c_bool),
                ('numeric', ct.c_bool),
                ('obj', ct.c_voidp),
                ('parent', ct.c_char*255),
                ('nkind', ct.c_int),
                ('register', ct.c_bool)]
                
class simTraceFile(ct.Structure):
    _fields_ = [('name', ct.c_char*255),
                ('type', ct.c_int),
                ('obj', ct.c_voidp)]
 
class simTraceBuf(ct.Structure):
    _fields_ = [('name', ct.c_char*255),
                ('buffer', ct.POINTER(ct.c_double)),
                ('size', ct.c_int),
                ('obj', ct.c_voidp),
                ('buf', ct.c_voidp)]

class SimContext(ct.Structure):
    _fields_ = [('version', ct.c_char*255),
                ('copyright', ct.c_char*255),
                ]
                
def sim_callback(i):
    # return 1 to stop the simulation
    return 0

class sim_engine:
    DOUBLE = ct.c_double
    PDOUBLE = ct.POINTER(DOUBLE)
    PPDOUBLE = ct.POINTER(PDOUBLE)
    INT = ct.c_int
    SIM_CALLBACK = ct.CFUNCTYPE(ct.c_int, ct.c_int)
    def __init__(self, dll, frame = None):
        self.frame = frame
        self.dll = ""
        self.valid = self.load(dll)

    def __del__(self):
        #ctx_del_object = self.interface("ctx_del_object", (ct.POINTER(simObj),), ct.c_bool)
        #for name, obj in self.sim_objects.iteritems():
        #    ctx_del_object(obj)
        pass
    def load(self, dll):
        self.dll = dll
        try:
            self.cdll = ct.cdll.LoadLibrary(dll)
            bsm_sim_top = self.interface("bsm_sim_top",None, ct.POINTER(SimContext))
            self.ctx = bsm_sim_top().contents
            
            self.ctx_read_helper = self.interface("ctx_read", (ct.POINTER(simObj),), ct.c_bool)
            self.ctx_write_helper = self.interface("ctx_write", (ct.POINTER(simObj),), ct.c_bool)
            ctx_first_object = self.interface("ctx_first_object", (ct.POINTER(simObj),), ct.c_bool)
            ctx_next_object = self.interface("ctx_next_object", (ct.POINTER(simObj),), ct.c_bool)

            obj = simObj()
            rtn = ctx_first_object(obj)
            self.sim_objects = {}
            while rtn:
                self.CheckObject(obj)
                if obj.readable:
                    self.ctx_read(obj)
                self.sim_objects[obj.name] = obj
                obj = simObj()
                rtn = ctx_next_object(obj)
                
            
            self.ctx_start = self.interface("ctx_start", (ct.c_int, ct.c_int), None)
            self.ctx_stop = self.interface("ctx_stop", None, None)
            self.ctx_time = self.interface("ctx_time", None, ct.c_double)
            self.ctx_time_sec = self.interface("ctx_time_sec", (ct.c_double, ct.c_int), ct.c_double)
            self.ctx_time_str_helper = self.interface("ctx_time_str", (ct.c_char*255, ), ct.c_bool)
            self.ctx_set_callback_helper = self.interface("ctx_set_callback", (self.SIM_CALLBACK, ), None)
     
            self.ctx_add_trace_file = self.interface("ctx_add_trace_file", (ct.POINTER(simTraceFile),), ct.c_bool)
            self.ctx_remove_trace_file = self.interface("ctx_remove_trace_file", (ct.POINTER(simTraceFile),), ct.c_bool)
            self.ctx_trace_file = self.interface("ctx_trace_file", (ct.POINTER(simTraceFile),ct.POINTER(simObj), ct.POINTER(simObj), ct.c_int), ct.c_bool)
            
            self.ctx_add_trace_buf = self.interface("ctx_add_trace_buf", (ct.POINTER(simTraceBuf),), ct.c_bool)
            self.ctx_remove_trace_buf = self.interface("ctx_remove_trace_buf", (ct.POINTER(simTraceBuf),), ct.c_bool)
            self.ctx_trace_buf = self.interface("ctx_trace_buf", (ct.POINTER(simTraceBuf),ct.POINTER(simObj),ct.POINTER(simObj), ct.c_int), ct.c_bool)
            self.ctx_read_trace_buf = self.interface("ctx_read_trace_buf", (ct.POINTER(simTraceBuf),), ct.c_bool)
            self.ctx_resize_trace_buf = self.interface("ctx_resize_trace_buf", (ct.POINTER(simTraceBuf),), ct.c_bool)
        except:
            traceback.print_exc(file=sys.stdout)
            return False

        return True


    def sim_objects(self):
        return self.sim_objects

    def CheckObject(self, obj):
        assert(obj);
        if obj == None:
            return;
        strKind = obj.kind;
        nKind = SC_OBJ_UNKNOWN;
        if strKind == "sc_signal":
            nKind = SC_OBJ_SIGNAL;
        elif strKind == "sc_in":
            nKind = SC_OBJ_INPUT;
        elif strKind == "sc_out":
            nKind = SC_OBJ_OUTPUT;
        elif strKind == "sc_in_out":
            nKind = SC_OBJ_INOUT;
        elif strKind == "sc_clock":
            nKind = SC_OBJ_CLOCK;
        elif strKind == "xsc_property":
            nKind = SC_OBJ_XSC_PROP;
            if obj.name.find("[")!=-1 and  obj.name.find("]")!=-1:
                nKind = SC_OBJ_XSC_ARRAY_ITEM;
        elif strKind == "sc_module":
            nKind = SC_OBJ_MODULE;
        elif strKind == "xsc_array":
            nKind = SC_OBJ_XSC_ARRAY;

        obj.nkind = nKind;
        obj.register = (nKind in [SC_OBJ_SIGNAL, SC_OBJ_INPUT,
            SC_OBJ_OUTPUT, SC_OBJ_INOUT, SC_OBJ_CLOCK,
            SC_OBJ_XSC_PROP, SC_OBJ_XSC_ARRAY_ITEM])
        name = obj.name
        idx = name.rfind('.')
        if nKind == SC_OBJ_XSC_ARRAY_ITEM:
            idx = name.rfind('[')
        obj.parent = ""
        if idx!=-1:
            name = name[0:idx]
            obj.parent = name
    
    def ctx_read(self, simObj):
        if not simObj: return ""
        if self.ctx_read_helper(simObj):
            return simObj.value
        return ""
    
    def ctx_write(self, simObj, value):
        if not simObj: return False
        simObj.value = str(value)
        return self.ctx_write_helper(simObj)
    
    def ctx_time_str(self):
        buf = ct.create_string_buffer(255)
        self.ctx_time_str_helper(buf)
        return buf.value
    
    def ctx_set_callback(self, fun):
        self.ctx_callback = self.SIM_CALLBACK(fun)
        self.ctx_set_callback_helper(self.ctx_callback)
        
    def interface(self, fun, arg = None, res=None):
        f = getattr(self.cdll, fun)
        f.argtypes = arg
        f.restype = res
        return f
