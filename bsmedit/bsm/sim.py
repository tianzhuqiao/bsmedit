import re
import json
import multiprocessing as mp
import time
import traceback
import sys
import six
import six.moves.queue as Queue
import wx
import wx.py.dispatcher as dp
from wx.lib.masked import NumCtrl

from . import graph
from ._simxpm import *
from .simprocess import sim_process
from .propgrid import bsmPropGrid
from .simengine import *
from ._pymgr_helpers import Gcm
from .autocomplete import AutocompleteTextCtrl
from ._utility import MakeBitmap, FastLoadTreeCtrl
from .. import c2p

Gcs = Gcm()
class Simulation(object):
    trigger_type = {'posneg': BSM_BOTHEDGE, 'pos': BSM_POSEDGE,
                    'neg': BSM_NEGEDGE, 'none': BSM_NONEEDGE,
                    BSM_BOTHEDGE:BSM_BOTHEDGE, BSM_POSEDGE:BSM_PS,
                    BSM_NEGEDGE:BSM_NEGEDGE, BSM_NONEEDGE:BSM_NONEEDGE}
    sim_units = {'fs':BSM_FS, 'ps':BSM_PS, 'ns':BSM_NS, 'us':BSM_US,
                 'ms':BSM_MS, 's':BSM_SEC}
    def __init__(self, parent, num=None):
        if num is not None and isinstance(num, int) and \
           num not in Gcs.get_all_managers():
            self.num = num
        else:
            self.num = Gcs.get_next_num()
        Gcs.set_active(self)
        self.frame = parent
        # simulation filename
        self.filename = ""
        # the dict holds all the objects from the simulation
        self.objects = None
        # create the simulation kernel
        self._cmd_id = 0
        self.qResp = None
        self.qCmd = None
        self.simProcess = None

    def release(self):
        """destroy simulation"""
        self.frame = None
        self._stop()
        Gcs.destroy(self.num)

    def __getitem__(self, obj):
        """read the object"""
        return self.read(obj)

    def __setitem__(self, obj, value):
        """write the value to the object"""
        if isinstance(obj, six.string_types):
            return self.write({obj:value})
        elif isinstance(obj, (list, tuple)):
            return self.write(dict(zip(obj, value)))
        else:
            raise ValueError()

    def _send_command(self, cmd, args=None, block=True):
        """
        send the command to the simulation process

        don't call this function directly unless you know what it is doing.
        """
        try:
            # always increase the command ID
            cid = self._cmd_id
            self._cmd_id += 1

            # return, if the previous call has not finished
            # it may happen when the previous command is waiting for response,
            # and another command is sent (by clicking a button)
            if self.qResp is None or self.qCmd is None or\
               self.simProcess is None:
                raise KeyboardInterrupt
            if args and not isinstance(args, dict):
                return False
            if not args:
                args = {}
            self.qCmd.put({'id':cid, 'block':block, 'cmd':cmd, 'arguments':args})
            if block is True:
                # wait for the command to finish
                while True:
                    resp = self.qResp.get()
                    rtn = self._process_response(resp)
                    if resp.get('id', -1) == cid:
                        return rtn
            return True
        except:
            traceback.print_exc(file=sys.stdout)

    def wait_until_simulation_paused(self, timeout=None):
        """
        wait for the simulation to pause

        return: It will not return until the simulation has paused.
                True: the simulation is valid and paused;
                False: otherwise.
        timeout: the maximum waiting period (in second)
        """
        # return if the simulation is not valid
        if self.qResp is None or self.qCmd is None or self.simProcess is None:
            return False
        start = -1
        if timeout is not None:
            start = time.time()
        while True:
            resp = self.get_status()
            if not resp['running']:
                return True
            wx.YieldIfNeeded()
            time.sleep(0.1)
            if start > 0 and time.time()-start > timeout:
                return False
        return False

    def get_status(self):
        """
        get the simulation status.

        return the dict showing the simulation status
        """
        return self._send_command('get_status', None, block=True)

    def set_parameter(self, step=None, total=None, more=False, block=True):
        """set the simulation parameters"""
        step, step_unit = self._parse_time(step)
        total, total_unit = self._parse_time(total)
        return self._set_parameter(step, step_unit, total, total_unit, more, block)

    def _set_parameter(self, step=None, unitStep=None, total=None,
                       unitTotal=None, more=False, block=True):
        """
        set the simulation parameters

        If more is True, total is additional to the current simulation time.
        """
        args = {'more':more}
        if step is not None:
            args['step'] = step
        if unitStep is not None:
            args['unitStep'] = unitStep
        if total is not None:
            args['total'] = total
        if unitTotal is not None:
            args['unitTotal'] = unitTotal
        return self._send_command('set_parameter', args, block)

    def start(self):
        """create an empty simulation"""
        self.stop()
        self.qResp = mp.Queue()
        self.qCmd = mp.Queue()
        self.simProcess = mp.Process(target=sim_process,
                                     args=(self.qResp, self.qCmd))
        self.simProcess.start()

    def load(self, filename, block=True):
        """load the simulation library (e.g., dll)"""
        self.start()
        self.filename = filename
        return self._send_command('load', {'filename':filename}, block)

    def load_interactive(self):
        """show a file open dialog to select and open the simulation"""
        style = c2p.FD_OPEN | c2p.FD_FILE_MUST_EXIST
        dlg = wx.FileDialog(self.frame, "Choose a file", "", "", "*.*", style)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            self.load(filename)
        dlg.Destroy()

    def _parse_time(self, t):
        """
        parse the time in time+unit format

        For example,
            1) 1.5us will return (1.5, BSM_US)
            2) 100 will return (100, None), where unit is None (current one will
               be used)
        """
        pattern = r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?:\s)*(fs|ps|ns|us|ms|s|)"
        x = re.match(pattern, str(t))
        if x:
            if x.group(2):
                unit = self.sim_units.get(x.group(2), None)
                if unit is None:
                    raise ValueError("unknown time format: " + str(time))
                return float(x.group(1)), unit
            else:
                return float(x.group(1)), None
        return None, None

    def step(self, step=None, block=False):
        """
        proceed the simulation with one step

        The step is set with set_parameter(). The GUI components will be updated
        after the running.

        The breakpoints are checked at each delta cycle.
        """
        self.set_parameter(step=step, block=False)
        return self._send_command('step', {'running': False}, block)

    def run(self, to=None, more=None, block=False):
        """
        keep running the simulation

        The simulation is executed step by step. After each step, the simulation
        'server' will notify the 'client' to update the GUI.
        """
        total = None
        if to:
            total, ismore = to, False
        elif more:
            total, ismore = more, True
        else:
            # run with the current settings
            total, ismore = None, False
        self.set_parameter(total=total, more=ismore, block=False)
        return self._send_command('step', {'running': True}, block)

    def pause(self, block=True):
        """pause the simulation"""
        return self._send_command('pause', {}, block)

    def _stop(self):
        """destroy the simulation process"""
        if self.qResp is None or self.qCmd is None or self.simProcess is None:
            return
        # stop the simulation kernel. No block operation allowed since
        # no response from the subprocess
        self._send_command('exit', {}, False)
        while not self.qResp.empty():
            self.qResp.get_nowait()
        self.simProcess.join()
        self.simProcess = None
        # stop the client
        self._process_response({'cmd':'exit'})

    def stop(self):
        """destroy the simulation process and update the GUI"""
        self._stop()

    def reset(self):
        """reset the simulation"""
        if self.filename:
            return self.load(self.filename)
        return False

    def time_stamp(self, in_second=False, block=True):
        """return the simulation time elapsed as a string"""
        args = {}
        if in_second:
            args['format'] = 'second'
        return self._send_command('time_stamp', args, block)

    def read(self, objs, block=True):
        """
        get the values of the registers

        If block == False, it will return after sending the command; otherwise,
        it will return the values.

        If objects only contains one register, its value will be returned if
        succeed; otherwise a dictionary is returned, where the keys are the
        items in objects.

        Example: read a single register
        >>> read('top.sig_bool', True)

        Example: read multiple registers from the same simulation
        >>> read(['top.sig_bool', 'top.sig_cos']
        """
        objs = self._object_list(objs)
        return self._send_command('read', {'objects':objs}, block)

    def write(self, objs, block=True):
        """
        write the value to the registers

        objs should be a dictionary where the keys are the register name.
        Due to the two-step mechanism in SystemC, the value will be updated
        after the next delta cycle. That is, if a read() is called after
        write(), it will return the previous value.

        Example:
        >>> a = read('top.sig_int', True)
        >>> write({'top.sig_int': 100}, True)
        >>> b = read('top.sig_int', True) # a == b
        >>> step()
        >>> c = read('top.sig_int', True)
        """
        if not isinstance(objs, dict):
            raise ValueError("Not supported objs type, expect a dict")
        return self._send_command('write', {'objects':objs}, block)

    def trace_file(self, obj, fmt='bsm', valid=None, trigger='posneg',
                   block=True):
        """
        dump object values to a file

        obj:
            register name
        fmt:
            'bsm': only output the register value, one per line (Default)
            'vcd': output the SystemC VCD format data
        valid:
            the trigger signal. If it is none, the write-operation will be
            triggered by the register itself
        trigger:
            'posneg': trigger on both rising and falling edges
            'pos': trigger on rising edge
            'neg': trigger on falling edge
            'none': no triggering
        """
        if isinstance(obj, list):
            obj = obj[0]
        fmts = {'bsm': BSM_TRACE_SIMPLE, 'vcd': BSM_TRACE_VCD,
                BSM_TRACE_SIMPLE: BSM_TRACE_SIMPLE, BSM_TRACE_VCD: BSM_TRACE_VCD}

        tfmt = fmts.get(fmt, None)
        trig = self.trigger_type.get(trigger, None)
        if tfmt is None:
            raise ValueError("Not supported trace type: " + str(fmt))
        if trig is None:
            raise ValueError("Not supported trigger type: " + str(trigger))

        args = {'name':obj, 'type':tfmt, 'valid':valid, 'trigger':trig}
        return self._send_command('trace_file', args, block)

    def trace_buf(self, obj, size=256, valid=None, trigger='posneg',
                  block=True):
        """start dumping the register to a numpy array"""
        if isinstance(obj, list):
            obj = obj[0]
        trig = self.trigger_type.get(trigger, None)
        if trig is None:
            raise ValueError("Not supported trigger type: " + str(trigger))

        args = {'name':obj, 'size':size, 'valid':valid, 'trigger':trig}
        return self._send_command('trace_buf', args, block)

    def _object_list(self, objs):
        """help function to generate object list"""
        if isinstance(objs, six.string_types):
            return [objs]
        elif isinstance(objs, (list, tuple)):
            return objs
        else:
            raise ValueError()

    def read_buf(self, objects, block=True):
        """
        read the traced buffer to an numpy array

        If the buffer is previous traced by calling trace_buf, the array with
        previous defined size will return; otherwise the trace_buf will be
        called with default arguments first.
        """
        objs = self._object_list(objects)
        return self._send_command('read_buf', {'objects':objs}, block)

    def monitor_signal(self, objects, block=True):
        """
        monitor the register value

        At end of each step, the simulation process will report the value
        """
        objs = self._object_list(objects)
        return self._send_command('monitor_signal', {'objects':objs}, block)

    def unmonitor_signal(self, objects, block=True):
        """stop monitoring the register"""
        objs = self._object_list(objects)
        return self._send_command('unmonitor_signal', {'objects':objs}, block)

    def get_monitored_signal(self, block=True):
        """get the list of the monitored signals"""
        return self._send_command('get_monitored_singal', block=block)

    def add_breakpoint(self, bp, block=True):
        """
        add the breakpoint

        bp = (name, condition, hitcount) or name
        """
        if isinstance(bp[0], six.string_types):
            bp = [bp, None, None]
        return self._send_command('add_breakpoint', {'objects':bp}, block)

    def del_breakpoint(self, bp, block=True):
        """delete the breakpoint"""
        if isinstance(bp[0], six.string_types):
            bp = [bp, None, None]
        return self._send_command('del_breakpoint', {'objects':bp}, block)

    def get_breakpoint(self, block=True):
        """get all the breakpoints"""
        return self._send_command('get_breakpoint', block=block)

    def global_object_name(self, obj):
        """generate the global name for simulation object (num.name)"""
        if obj in self.objects:
            return "%d."%self.num + obj
        return None

    def monitor(self, objects, grid=None, index=-1):
        """
        show the register in a propgrid window

        grid: If the grid is None, the objects will be added to the active propgrid
        window. If the active propgrid window is also None, it will create one.

        index: the index of the object in the propgrid window. -1 to append.
        """
        if not objects:
            return None
        if grid is None:
            grid = bsmPropGrid.GCM.get_active()
        if not grid:
            grid = sim.propgrid()
        if not grid:
            return None
        props = []
        for name in self._object_list(objects):
            obj = self.objects.get(name, None)
            # ignore the invalid object
            if obj is None:
                print("invalid object: ", obj)
                continue
            prop = grid.InsertProperty(self.global_object_name(obj['name']),
                                       obj['basename'], obj['value'], index)
            prop.SetGripperColor(self.frame.GetColor())
            prop.SetReadOnly(not obj['writable'])
            prop.SetShowRadio(obj['readable'])
            props.append(prop)
            if index != -1:
                index += 1
        if len(props) == 1:
            return props[0]
        return props

    def _process_response(self, resp):
        """process the response from the simulation core"""
        try:
            wx.CallAfter(self.frame.ProcessResponse, resp)
            command = resp.get('cmd', '')
            value = resp.get('value', False)
            args = resp.get('arguments', {})
            if command == 'load':
                self.objects = value
                self.filename = args['filename']
            elif command in ['read', 'read_buf', 'write']:
                # single value, return the value, not the dict
                if len(value) == 1:
                    value = list(value.values())[0]
            return value
        except:
            traceback.print_exc(file=sys.stdout)

class ModuleTree(FastLoadTreeCtrl):
    """the tree control shows the hierarchy of the objects in the simulation"""
    ID_MP_DUMP = wx.NewId()
    ID_MP_TRACE_BUF = wx.NewId()
    ID_MP_ADD_TO_NEW_VIEWER = wx.NewId()
    ID_MP_ADD_TO_VIEWER_START = wx.NewId()
    def __init__(self, parent, style=wx.TR_DEFAULT_STYLE):
        style = style | wx.TR_HAS_VARIABLE_ROW_HEIGHT | \
                wx.TR_HIDE_ROOT| wx.TR_MULTIPLE | wx.TR_LINES_AT_ROOT
        FastLoadTreeCtrl.__init__(self, parent, self.get_children, style=style)
        imglist = wx.ImageList(16, 16, True, 10)
        for xpm in [module_xpm, switch_xpm, in_xpm, out_xpm, inout_xpm,
                    module_grey_xpm, switch_grey_xpm, in_grey_xpm,
                    out_grey_xpm, inout_grey_xpm]:
            imglist.Add(c2p.BitmapFromXPM(xpm))
        self.AssignImageList(imglist)
        self.objects = None

    def get_children(self, item):
        """ callback function to return the children of item """
        if item == self.GetRootItem():
            parent = ""
        else:
            ext = self.GetExtendObj(item)
            parent = ext['name']
        children = []
        for key, obj in six.iteritems(self.objects):
            if obj['nkind'] != SC_OBJ_UNKNOWN and obj['parent'] == parent:
                child = {'label':obj['basename']}
                nkind = obj['nkind']
                img = [-1, -1]
                if nkind == SC_OBJ_MODULE:
                    img = [0, 0]
                elif nkind in [SC_OBJ_SIGNAL, SC_OBJ_CLOCK, SC_OBJ_XSC_PROP,
                               SC_OBJ_XSC_ARRAY, SC_OBJ_XSC_ARRAY_ITEM]:
                    img = [1, 1]
                elif nkind == SC_OBJ_INPUT:
                    img = [2, 2]
                elif nkind == SC_OBJ_OUTPUT:
                    img = [3, 3]
                elif nkind == SC_OBJ_INOUT:
                    img = [4, 4]
                else:
                    raise ValueError('Invalid object type')
                child['img'] = img[0]
                child['imgsel'] = img[1]
                child['data'] = key
                # add the sign to append the children later
                child['is_folder'] = nkind in [SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY]
                children.append(child)
        return children

    def OnCompareItems(self, item1, item2):
        """compare the two items for sorting"""
        def SortByName(obj1, obj2):
            """compare the two items based on its type and name"""
            type1 = obj1['nkind'] in [SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY]
            type2 = obj2['nkind'] in [SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY]
            if type1 == type2:
                if obj1['name'] > obj2['name']:
                    return 1
            elif type1 < type2:
                return 1
            return -1

        data1 = self.GetExtendObj(item1)
        data2 = self.GetExtendObj(item2)
        rtn = -2
        if data1 and data2:
            return SortByName(data1, data2)
        return rtn

    def Load(self, objects):
        """load the new simulation"""
        self.objects = objects
        self.FillTree()

    def FillTree(self):
        """fill the simulation objects tree"""
        #clear the tree control
        self.DeleteAllItems()
        if self.objects is None:
            return

        # add the root item
        item = self.AddRoot("bsmedit")
        # fill the top level item
        self.FillChildren(item)
        # any item? expand it
        item, _ = self.GetFirstChild(item)
        if item.IsOk():
            self.Expand(item)

    def GetExtendObj(self, item):
        """return the extend object"""
        data = self.GetItemData(item)
        if data:
            if not c2p.bsm_is_phoenix:
                data = data.GetData()
            return self.objects.get(data, None)
        return None

    def FindItem(self, parent, name):
        """find the first child of parent by its name"""
        (child, cookie) = self.GetFirstChild(parent)
        while child:
            ext = self.GetExtendObj(child)
            if name == ext['name']:
                return child
            if self.ItemHasChildren(child):
                self.FillNodes(child)
                grandchild = self.FindItem(child, name)
                if grandchild.IsOk():
                    return grandchild
            (child, cookie) = self.GetNextChild(parent, cookie)
        return wx.TreeItemId()

    def SetActiveNode(self, name):
        """select the item by its name"""
        item = self.GetRootItem()
        child = self.FindItem(item, name)
        if child.IsOk():
            self.EnsureVisible(child)
            self.UnselectAll()
            self.SelectItem(child)

class DumpDlg(wx.Dialog):
    def __init__(self, parent, objects, active, tracefile=True):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title="Dump...")

        self.objects = objects
        self.traceFile = tracefile

        szAll = wx.BoxSizer(wx.VERTICAL)

        if self.traceFile:
            sbox = wx.StaticBox(self, label="&File name")
            szFile = wx.StaticBoxSizer(sbox, wx.HORIZONTAL)
            self.tcFile = wx.TextCtrl(sbox, value=active)
            self.tcFile.SetMaxLength(0)
            szFile.Add(self.tcFile, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            self.btnSelectFile = wx.Button(sbox, label="...", size=(25, -1))
            szFile.Add(self.btnSelectFile, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            szAll.Add(szFile, 0, wx.ALL|wx.EXPAND, 5)

        sbox = wx.StaticBox(self, wx.ID_ANY, "&Signal")
        szSignal = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        self.tcSignal = AutocompleteTextCtrl(sbox, value=active,
                                             completer=self.Completer)
        szSignal.Add(self.tcSignal, 0, wx.ALL|wx.EXPAND, 5)
        self.cbTrigger = wx.CheckBox(sbox, label="Use Trigger Signal")
        szSignal.Add(self.cbTrigger, 0, wx.ALL, 5)
        self.tcValid = AutocompleteTextCtrl(sbox, completer=self.Completer)
        szSignal.Add(self.tcValid, 0, wx.ALL|wx.EXPAND, 5)
        rbTriggerChoices = ["&Pos Edge", "&Neg Edge", "Both Edge"]
        self.rbTrigger = wx.RadioBox(sbox, label="Trigger",
                                     choices=rbTriggerChoices)
        self.rbTrigger.SetSelection(2)
        szSignal.Add(self.rbTrigger, 0, wx.ALL|wx.EXPAND, 5)
        szAll.Add(szSignal, 1, wx.ALL|wx.EXPAND, 5)

        if self.traceFile:
            rbFormatChoices = [u"&VCD", u"&BSM"]
            self.rbFormat = wx.RadioBox(self, label="&Format",
                                        choices=rbFormatChoices)
            self.rbFormat.SetSelection(1)
            szAll.Add(self.rbFormat, 0, wx.ALL|wx.EXPAND, 5)
        else:
            szSize = wx.BoxSizer(wx.HORIZONTAL)
            szSize.Add(wx.StaticText(self, wx.ID_ANY, "Size"), 0, wx.ALL, 5)
            self.spinSize = wx.SpinCtrl(self, style=wx.SP_ARROW_KEYS, min=1,
                                        max=2**31-1, initial=256)
            szSize.Add(self.spinSize, 1, wx.EXPAND | wx.ALL, 5)
            szAll.Add(szSize, 0, wx.ALL|wx.EXPAND, 5)

        self.m_staticline1 = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        szAll.Add(self.m_staticline1, 0, wx.EXPAND |wx.ALL, 5)

        szConfirm = wx.BoxSizer(wx.HORIZONTAL)
        self.btnOK = wx.Button(self, wx.ID_OK, u"OK")
        szConfirm.Add(self.btnOK, 0, wx.ALL, 5)
        self.btnCancel = wx.Button(self, wx.ID_CANCEL, u"Cancel")
        szConfirm.Add(self.btnCancel, 0, wx.ALL, 5)
        szAll.Add(szConfirm, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(szAll)
        self.Layout()
        szAll.Fit(self)

        self.tcValid.Enable(self.cbTrigger.GetValue())
        # Connect Events
        if self.traceFile:
            self.btnSelectFile.Bind(wx.EVT_BUTTON, self.OnBtnSelectFile)
        self.cbTrigger.Bind(wx.EVT_CHECKBOX, self.OnCheckVal)
        self.btnOK.Bind(wx.EVT_BUTTON, self.OnBtnOK)

        self.trace = {}

    def Completer(self, query):
        """return all the simulation object for auto complete"""
        root = query
        if query.find('.'):
            root = query[0:query.rfind('.')+1]
        # only report the direct children of 'query', for example
        # query = 'top.si'
        # will return all the children of top, whose name starts with 'si'
        objs = []
        for obj in self.objects:
            if obj.startswith(query):
                item = obj[len(root):]
                if item.find('.') != -1:
                    item = item[:item.find('.')]
                objs.append(item)
        if objs:
            objs = list(set(objs))
            objs.sort()
        return objs, objs, len(query)-len(root)

    def OnBtnSelectFile(self, event):
        wildcard = "BSM Files (*.bsm)|*.bsm|All Files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select BSM dump file", '', '', wildcard,
                            style=c2p.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.tcFile.SetValue(dlg.GetPath())

    def OnCheckVal(self, event):
        self.tcValid.Enable(self.cbTrigger.GetValue())

    def OnBtnOK(self, event):
        self.trace = {}
        if self.traceFile:
            # trace file
            self.trace['filename'] = self.tcFile.GetValue()
            self.trace['format'] = self.rbFormat.GetSelection()
        else:
            # trace buffer
            self.trace['size'] = self.spinSize.GetValue()
        self.trace['signal'] = self.tcSignal.GetValue()
        self.trace['valid'] = None
        if self.cbTrigger.GetValue():
            self.trace['valid'] = self.tcValid.GetValue()
        self.trace['trigger'] = self.rbTrigger.GetSelection()
        event.Skip()

    def GetTrace(self):
        return self.trace

class SimPanel(wx.Panel):
    ID_GOTO_PARENT = wx.NewId()
    ID_GOTO_HOME = wx.NewId()
    ID_SIM_STEP = wx.NewId()
    ID_SIM_RUN = wx.NewId()
    ID_SIM_PAUSE = wx.NewId()
    ID_SIM_SET = wx.NewId()
    ID_MP_DUMP = wx.NewId()
    ID_MP_TRACE_BUF = wx.NewId()
    ID_MP_ADD_TO_NEW_VIEWER = wx.NewId()
    ID_MP_ADD_TO_VIEWER_START = wx.NewId()
    def __init__(self, parent, num=None, filename=None, silent=False):
        wx.Panel.__init__(self, parent)

        self.is_destroying = False
        self._color = wx.Colour(178, 34, 34)
        # the variable used to update the UI in idle()
        self.gridList = []
        self.tb = wx.ToolBar(self, style=wx.TB_FLAT|wx.TB_HORIZONTAL|wx.TB_NODIVIDER)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))
        xpm2bmp = c2p.BitmapFromXPM
        c2p.tbAddTool(self.tb, self.ID_SIM_STEP, "", xpm2bmp(step_xpm),
                      xpm2bmp(step_grey_xpm), wx.ITEM_NORMAL, "Step",
                      "Step the simulation")
        c2p.tbAddTool(self.tb, self.ID_SIM_RUN, "", xpm2bmp(run_xpm),
                      xpm2bmp(run_grey_xpm), wx.ITEM_NORMAL, "Run",
                      "Run the simulation")
        c2p.tbAddTool(self.tb, self.ID_SIM_PAUSE, "", xpm2bmp(pause_xpm),
                      xpm2bmp(pause_grey_xpm), wx.ITEM_NORMAL, "Pause",
                      "Pause the simulation")

        self.tb.AddSeparator()

        self.tcStep = NumCtrl(self.tb, wx.ID_ANY, "1000",
                              allowNegative=False, fractionWidth=0)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Step "))
        self.tb.AddControl(self.tcStep)
        units = ['fs', 'ps', 'ns', 'us', 'ms', 's']
        self.cmbUnitStep = wx.ComboBox(self.tb, wx.ID_ANY, 'ns',
                                       size=(50, -1), choices=units,
                                       style=wx.CB_READONLY)
        self.tb.AddControl(self.cmbUnitStep)
        self.tb.AddSeparator()

        self.tcTotal = NumCtrl(self.tb, wx.ID_ANY, "-1",
                               allowNegative=True, fractionWidth=0)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Total "))
        self.tb.AddControl(self.tcTotal)
        self.cmbUnitTotal = wx.ComboBox(self.tb, wx.ID_ANY, 'ns',
                                        size=(50, -1), choices=units,
                                        style=wx.CB_READONLY)
        self.tb.AddControl(self.cmbUnitTotal)
        self.tb.AddSeparator()
        self.tb.AddStretchableSpace()
        c2p.tbAddTool(self.tb, self.ID_SIM_SET, "", xpm2bmp(setting_xpm),
                      xpm2bmp(setting_grey_xpm), wx.ITEM_DROPDOWN,
                      "Setting", "Configure the simulation")
        menu = wx.Menu()
        menu.Append(wx.ID_RESET, "&Reset")
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT, "&Exit")
        self.tb_set_menu = menu
        self.tb.SetDropdownMenu(self.ID_SIM_SET, self.tb_set_menu)
        self.tb.Realize()
        self.tree = ModuleTree(self)
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(self.tree, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.running = False
        self.Bind(wx.EVT_TOOL, self.OnProcessCommand)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCmdUI)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self.OnTreeItemMenu)
        self.tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)

        self.sim = Simulation(self, num)
        if isinstance(filename, six.string_types):
            self.sim.load(filename)
        elif not silent:
            self.sim.load_interactive()
        self.SetParameter()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.timer.Start(5)

    def OnTimer(self, event):
        if not self.sim or not self.sim.qResp or not self.sim.qCmd:
            return
        if self.running and self.sim.qResp.empty() and self.sim.qCmd.empty():
            # if the queues are almost empty, retrieve the data
            self.sim.time_stamp(False, False)
            self.sim.read([], False)
            self.sim.read_buf([], False)
        try:
            # process the response
            resp = self.sim.qResp.get_nowait()
            if resp:
                self.ProcessResponse(resp)
        except Queue.Empty:
            pass

    def Destroy(self):
        """
        Destroy the simulation properly before close the pane.
        """
        self.timer.Stop()
        self.is_destroying = True
        self.sim.release()
        self.sim = None
        super(SimPanel, self).Destroy()

    def SetColor(self, clr):
        self._color = clr

    def GetColor(self):
        return self._color

    def SetParameter(self, block=True):
        """set the simulation parameters with the values from GUI"""
        step = int(self.tcStep.GetValue())
        unitStep = int(self.cmbUnitStep.GetSelection())
        total = int(self.tcTotal.GetValue())
        unitTotal = int(self.cmbUnitTotal.GetSelection())
        self.sim._set_parameter(step, unitStep, total, unitTotal, False, block)

    def OnTreeSelChanged(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        # pre-read the prop value
        objects = []
        items = self.tree.GetSelections()
        for item in items:
            obj = self.tree.GetExtendObj(item)
            objects.append(obj['name'])
        if objects:
            wx.CallAfter(self.sim.read, objects, True)

    def OnTreeItemMenu(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        menu = wx.Menu()
        menu.Append(self.ID_MP_DUMP, "&Dump file")
        menu.AppendSeparator()
        menu.Append(self.ID_MP_TRACE_BUF, "&Trace buffer")
        menu.AppendSeparator()
        submenu = wx.Menu()
        submenu.Append(self.ID_MP_ADD_TO_NEW_VIEWER, "&Add to new propgrid")
        submenu.AppendSeparator()
        nid = wx.ID_FILE1
        self.gridList = []
        for mag in bsmPropGrid.GCM.get_all_managers():
            self.gridList.append(mag)
            submenu.Append(nid, mag.GetLabel())
            nid += 1

        menu.AppendSubMenu(submenu, "Add to...")
        self.PopupMenu(menu)
        menu.Destroy()

    def OnTreeBeginDrag(self, event):
        if self.tree.objects is None:
            return

        ids = self.tree.GetSelections()
        objs = []
        objs_name = []
        gname = self.sim.global_object_name
        for item in ids:
            if item == self.tree.GetRootItem():
                continue
            if not item.IsOk():
                break
            ext = self.tree.GetExtendObj(item)
            nkind = ext['nkind']
            if nkind == SC_OBJ_XSC_ARRAY:
                (child, cookie) = self.tree.GetFirstChild(item)
                if child.IsOk() and self.tree.GetItemText(child) == "...":
                    # item has children, but haven't been expanded
                    self.tree.Expand(item)
                (child, cookie) = self.tree.GetFirstChild(item)
                objchild = []
                while child.IsOk():
                    ext2 = self.tree.GetExtendObj(child)
                    objchild.append(gname(ext2['name']))
                    objs_name.append(ext2['name'])
                    (child, cookie) = self.tree.GetNextChild(item, cookie)
                objs.append({'reg':gname(ext['name']), 'child':objchild})
            else:
                objs.append({'reg':gname(ext['name'])})
            objs_name.append(ext['name'])
        # need to explicitly allow drag
        # start drag operation
        data = c2p.PyTextDataObject(json.dumps(objs))
        source = wx.DropSource(self.tree)
        source.SetData(data)
        rtn = source.DoDragDrop(True)
        if rtn == wx.DragError:
            wx.LogError("An error occurred during drag and drop operation")
        elif rtn == wx.DragNone:
            pass
        elif rtn == wx.DragCopy:
            pass
        elif rtn == wx.DragMove:
            pass
        elif rtn == wx.DragCancel:
            pass
        self.sim.read(objs_name, False)

    def OnUpdateCmdUI(self, event):
        eid = event.GetId()
        if eid in [self.ID_SIM_STEP, self.ID_SIM_RUN]:
            event.Enable(not self.running)
        elif eid == self.ID_SIM_PAUSE:
            event.Enable(self.running)

    def OnProcessCommand(self, event):
        """process the menu command"""
        eid = event.GetId()
        viewer = None
        if eid in [self.ID_MP_DUMP, self.ID_MP_TRACE_BUF]:
            objs = [o for o, v in six.iteritems(self.sim.objects) if v['numeric'] and v['readable']]
            objs.sort()
            active = ''
            items = self.tree.GetSelections()
            if items:
                active = self.tree.GetExtendObj(items[0])['name']
            dlg = DumpDlg(self, objs, active, eid == self.ID_MP_DUMP)
            if dlg.ShowModal() == wx.ID_OK:
                t = dlg.GetTrace()
                if eid == self.ID_MP_DUMP:
                    self.sim.trace_file(t['signal'], t['format'], t['valid'], t['trigger'])
                else:
                    self.sim.trace_buf(t['signal'], t['size'], t['valid'], t['trigger'])
        elif eid == self.ID_MP_ADD_TO_NEW_VIEWER:
            viewer = sim.propgrid()
        elif eid >= wx.ID_FILE1 and eid <= wx.ID_FILE9:
            viewer = self.gridList[eid - wx.ID_FILE1]
        elif eid == wx.ID_EXIT:
            self.sim.stop()
            dp.send(signal='frame.delete_panel', panel=self)
        elif eid == wx.ID_RESET:
            self.sim.reset()
        elif eid == self.ID_SIM_STEP:
            self.SetParameter(False)
            self.sim.step()
        elif eid == self.ID_SIM_RUN:
            self.SetParameter(False)
            self.sim.run()
        elif eid == self.ID_SIM_PAUSE:
            self.sim.pause()
        if viewer:
            ids = self.tree.GetSelections()
            objs = []
            for item in ids:
                if item == self.tree.GetRootItem():
                    continue
                if not item.IsOk():
                    break
                ext = self.tree.GetExtendObj(item)
                nkind = ext['nkind']
                self.sim.monitor(ext['name'], viewer)
                objs.append(ext['name'])
                if nkind == SC_OBJ_XSC_ARRAY:
                    (child, cookie) = self.tree.GetFirstChild(item)
                    if child.IsOk() and self.tree.GetItemText(child) == "...":
                        self.tree.Expand(item)
                    (child, cookie) = self.tree.GetFirstChild(item)
                    while child.IsOk():
                        ext2 = self.tree.GetExtendObj(child)
                        prop = self.sim.monitor(ext2['name'], viewer)
                        objs.append(ext2['name'])
                        prop.SetIndent(1)
                        (child, cookie) = self.tree.GetNextChild(item, cookie)
            self.sim.read(objs, False)

    def ProcessResponse(self, resp):
        if self.is_destroying:
            return
        try:
            command = resp.get('cmd', '')
            value = resp.get('value', False)
            args = resp.get('arguments', {})
            if command == 'load':
                self.tree.Load(self.sim.objects)
                self.sim.time_stamp(False, False)
                self.sim.read([], False)
                self.sim.read_buf([], False)
            elif command == 'exit':
                self.tree.Load(None)
                dp.send('sim.unloaded', num=self.sim.num)
            elif command == 'step':
                if value:
                    self.sim.time_stamp(False, False)
                    self.sim.read([], False)
                    self.sim.read_buf([], False)
            elif command == 'get_status':
                self.running = value.get('running', False)
            elif command == 'monitor_add':
                objs = [name for name, v in six.iteritems(value) if v]
                self.sim.read(objs, False)
            elif command == 'set_parameter':
                if value:
                    args = resp['arguments']
                    step = self.tcStep.GetValue()
                    self.tcStep.SetValue(args.get('step', step))
                    unitStep = self.cmbUnitStep.GetSelection()
                    self.cmbUnitStep.SetSelection(args.get('unitStep', unitStep))
                    total = self.tcTotal.GetValue()
                    self.tcTotal.SetValue(args.get('total', total))
                    unitTotal = self.cmbUnitTotal.GetSelection()
                    self.cmbUnitTotal.SetSelection(args.get('unitTotal', unitTotal))
            elif command == 'read':
                gname = self.sim.global_object_name
                ui_objs = {gname(name):v for name, v in six.iteritems(value)}
                dp.send(signal="grid.updateprop", objs=ui_objs)
            elif command == 'read_buf':
                gname = self.sim.global_object_name
                ui_buffers = {gname(name):v for name, v in six.iteritems(value)}
                dp.send(signal="sim.buffer_changed", bufs=ui_buffers)
            elif command == 'time_stamp':
                if isinstance(value, six.string_types):
                    dp.send(signal="frame.show_status_text", text=value)
            elif command == 'breakpoint_triggered':
                bp = value #[name, condition, hitcount, hitsofar]
                gname = self.sim.global_object_name
                for grid in bsmPropGrid.GCM.get_all_managers():
                    if grid.triggerBreakPoint(gname(bp[0]), bp[1], bp[2]):
                        dp.send(signal='frame.show_panel', panel=grid)
                        break
                else:
                    txt = "Breakpoint triggered: %s\n"%(json.dumps(bp))
                    dp.send(signal='shell.write_out', text=txt)
            elif command == 'write_out':
                dp.send(signal='shell.write_out', text=value)
        except:
            traceback.print_exc(file=sys.stdout)

class sim(object):
    frame = None
    ID_SIM_NEW = wx.NOT_FOUND
    ID_PROP_NEW = wx.NOT_FOUND
    @classmethod
    def initialize(cls, frame):
        cls.frame = frame

        resp = dp.send(signal='frame.add_menu', path='File:New:Simulation',
                       rxsignal='bsm.simulation')
        if resp:
            cls.ID_SIM_NEW = resp[0][1]
        resp = dp.send(signal='frame.add_menu', path='File:New:PropGrid',
                       rxsignal='bsm.simulation')
        if resp:
            cls.ID_PROP_NEW = resp[0][1]

        dp.connect(cls._process_command, signal='bsm.simulation')
        dp.connect(receiver=cls._frame_set_active, signal='frame.activate_panel')
        dp.connect(receiver=cls._frame_uninitialize, signal='frame.exit')
        dp.connect(receiver=cls.initialized, signal='frame.initialized')
        dp.connect(receiver=cls._prop_insert, signal='prop.insert')
        dp.connect(receiver=cls._prop_delete, signal='prop.delete')
        dp.connect(receiver=cls._prop_drop, signal='prop.drop')
        dp.connect(receiver=cls._prop_bp_add, signal='prop.bp_add')
        dp.connect(receiver=cls._prop_bp_del, signal='prop.bp_del')
        dp.connect(receiver=cls._prop_changed, signal='prop.changed')

    @classmethod
    def initialized(cls):
        dp.send(signal='shell.run', command='from bsmedit.bsm.pysim import *',
                prompt=False, verbose=False, history=False)

    @classmethod
    def _prop_changed(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            mgr.write({name: prop.GetValue()})

    @classmethod
    def _prop_bp_add(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            cnd = prop.GetBPCondition()
            mgr.add_breakpoint([[name, cnd[0], cnd[1]]])

    @classmethod
    def _prop_bp_del(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            cnd = prop.GetBPCondition()
            mgr.del_breakpoint([[name, cnd[0], cnd[1]]])

    @classmethod
    def _prop_insert(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            mgr.monitor_signal(name)

    @classmethod
    def _prop_delete(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            mgr.unmonitor_signal(name)

    @classmethod
    def _prop_drop(cls, index, prop, grid):
        objs = json.loads(prop)
        for obj in objs:
            reg = obj['reg']
            mgr, name = cls._find_object(str(reg))
            if not mgr:
                continue
            p = mgr.monitor(name, grid, index)
            if index != -1:
                index = index + 1
            for c in obj.get('child', []):
                mgr, name = cls._find_object(str(c))
                if not mgr:
                    continue
                p = mgr.monitor(name, grid, index)
                p.SetIndent(1)
                if index != -1:
                    index = index + 1

    @classmethod
    def _frame_set_active(cls, pane):
        if pane and isinstance(pane, SimPanel):
            Gcs.set_active(pane.sim)
        if pane and isinstance(pane, bsmPropGrid):
            bsmPropGrid.GCM.set_active(pane)

    @classmethod
    def _frame_uninitialize(cls):
        for mgr in Gcs.get_all_managers():
            mgr.stop()
            dp.send('frame.delete_panel', panel=mgr.frame)
        dp.send('frame.delete_menu', path="View:Simulations")
        dp.send('frame.delete_menu', path="File:New:Simulation", id=cls.ID_SIM_NEW)
        dp.send('frame.delete_menu', path="File:New:PropGrid", id=cls.ID_PROP_NEW)

    @classmethod
    def _process_command(cls, command):
        if command == cls.ID_SIM_NEW:
            style = c2p.FD_OPEN | c2p.FD_FILE_MUST_EXIST
            dlg = wx.FileDialog(cls.frame, "Choose a file", "", "", "*.*", style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                cls.simulation(filename=filename)
            dlg.Destroy()
        if command == cls.ID_PROP_NEW:
            cls.propgrid()

    @classmethod
    def _find_object(cls, name):
        """
        Find the object in simulations by its name, for example
            '1.top.sig_cos' -> find the object with name 'top.sig_cos' in
                               simulation 1
            'top.sig_cos' -> find the object with name 'top.sig_cos' in
                             the active simulation, the active simulation is
                             the simulation that is currently active or most
                             recently active.
        """
        x = re.match(r'^(\d)+\.(.*)', name)
        if x:
            num, obj = (int(x.group(1)), x.group(2))
        else:
            num, obj = None, name
        if num is None:
            mgr = Gcs.get_active()
        else:
            mgr = Gcs.get_manager(num)
        if not mgr or obj not in mgr.objects:
            return None, None
        return mgr, obj

    @classmethod
    def simulation(cls, num=None, filename=None, silent=False, create=True,
                   activate=False):
        """
        create a simulation

        If the simulation exists, return its handler; otherwise, create it if
        create == True.
        """
        def GetColorByNum(num):
            color = ['green', 'red', 'blue', 'black', 'cyan', 'yellow',
                     'magenta', 'cyan']
            return c2p.NamedColour(color[num%len(color)])
        manager = Gcs.get_manager(num)
        if manager is None and create:
            manager = SimPanel(sim.frame, num, filename, silent)
            clr = GetColorByNum(manager.sim.num)
            clr.Set(clr.red, clr.green, clr.blue, 128)
            manager.SetColor(clr)
            page_bmp = MakeBitmap(clr.red, clr.green, clr.blue)#178,  34,  34)
            title = "Simulation-%d"%manager.sim.num
            dp.send(signal="frame.add_panel", panel=manager, title=title,
                    target="History", icon=page_bmp,
                    showhidemenu="View:Simulations:%s"%title)
            return manager.sim
        # activate the manager
        elif manager and activate:
            dp.send(signal='frame.show_panel', panel=manager)

        return manager

    @classmethod
    def propgrid(cls, num=None, create=True, activate=False):
        """
        get the propgrid handle by its number

        If the propgrid exists, return its handler; otherwise, it will be created.
        """
        mgr = bsmPropGrid.GCM.get_manager(num)
        if not mgr and create:
            mgr = bsmPropGrid(cls.frame)
            mgr.SetLabel("Propgrid-%d"%mgr.num)
            dp.send(signal="frame.add_panel", panel=mgr, title=mgr.GetLabel())
        elif mgr and activate:
            # activate the window
            dp.send(signal='frame.show_panel', panel=mgr)
        return mgr

    @classmethod
    def plot_trace(cls, *args, **kwargs):
        """
        plot the trace

        The trace will be automatically updated after each simulation step.
        """
        if args and isinstance(args[0], six.string_types):
            s1, obj1 = cls._find_object(args[0])
            if not s1 or not obj1:
                print("unknown sim object:", args[0])
                return
            s2, obj2 = None, None
            if len(args) > 1 and isinstance(args[1], six.string_types):
                s2, obj2 = cls._find_object(args[1])

        if obj2:
            args = args[2:]
            sx, x, sy, y = s1, obj1, s2, obj2
        else:
            args = args[1:]
            sx, x, sy, y = None, None, s1, obj1

        dy = sy.read_buf(y, True)
        y = {sy.global_object_name(y):dy}
        if sx:
            dx = sx.read_buf(x, True)
            x = {sx.global_object_name(x):dx}
        mgr = graph.plt.get_current_fig_manager()
        autorelim = kwargs.pop("relim", True)
        mgr.plot_trace(x, y, autorelim, *args, **kwargs)

def bsm_initialize(frame):
    sim.initialize(frame)
