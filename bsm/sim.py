import threading
import re
import json
import multiprocessing as mp
import Queue
from time import time as _time
import wx
import wx.py.dispatcher as dispatcher
from wx.lib.masked import NumCtrl
import graph
from _simxpm import module_xpm, switch_xpm, in_xpm, out_xpm, inout_xpm,\
                    module_grey_xpm, switch_grey_xpm, in_grey_xpm, out_grey_xpm,\
                    inout_grey_xpm, step_xpm, run_xpm, pause_xpm,\
                    step_grey_xpm, run_grey_xpm, pause_grey_xpm, setting_xpm,\
                    setting_grey_xpm
from simprocess import sim_process
from propgrid import bsmPropGrid
from simengine import *
from bsm._pymgr_helpers import Gcm
from autocomplete import AutocompleteTextCtrl
from _docstring import copy_docstring_raw

class ModuleTree(wx.TreeCtrl):
    ID_MP_DUMP = wx.NewId()
    ID_MP_TRACE_BUF = wx.NewId()
    ID_MP_ADD_TO_NEW_VIEWER = wx.NewId()
    ID_MP_ADD_TO_VIEWER_START = wx.NewId()
    def __init__(self, parent, style=wx.TR_DEFAULT_STYLE):
        wx.TreeCtrl.__init__(self, parent, style=style)
        imglist = wx.ImageList(16, 16, True, 10)
        imglist.Add(wx.BitmapFromXPMData(module_xpm))
        imglist.Add(wx.BitmapFromXPMData(switch_xpm))
        imglist.Add(wx.BitmapFromXPMData(in_xpm))
        imglist.Add(wx.BitmapFromXPMData(out_xpm))
        imglist.Add(wx.BitmapFromXPMData(inout_xpm))
        imglist.Add(wx.BitmapFromXPMData(module_grey_xpm))
        imglist.Add(wx.BitmapFromXPMData(switch_grey_xpm))
        imglist.Add(wx.BitmapFromXPMData(in_grey_xpm))
        imglist.Add(wx.BitmapFromXPMData(out_grey_xpm))
        imglist.Add(wx.BitmapFromXPMData(inout_grey_xpm))
        self.AssignImageList(imglist)
        self.objects = None
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnTreeItemExpanding)

    def OnTreeItemExpanding(self, event):
        """expand the item with children"""
        item = event.GetItem()
        if not item.IsOk():
            return
        self.FillNodes(item)

    def OnCompareItems(self, item1, item2):
        """compare the two items for sorting"""
        data1 = self.GetItemData(item1)
        data2 = self.GetItemData(item2)
        rtn = -2
        if data1 and data2:
            return self.SortByName(data1, data2)
        return rtn

    def SortByName(self, item1, item2):
        """compare the two items based on its type and name"""
        (obj1, type1) = item1.GetData()
        (obj2, type2) = item2.GetData()
        if type1 == type2:
            if obj1['name'] > obj2['name']:
                return 1
            else:
                return -1
        elif type1 > type2:
            return 1
        else:
            return -1

    def FillNodes(self, item):
        """fill the node with children"""
        (child, cookie) = self.GetFirstChild(item)
        if not child.IsOk():
            return False
        if self.GetItemText(child) != "...":
            return False
        # delete the '...'
        self.DeleteChildren(item)
        ext = self.GetExtendObj(item)
        for key, obj in self.objects.iteritems():
            # find all the children
            if obj['nkind'] != SC_OBJ_UNKNOWN and obj['parent'] == ext['name']:
                self.InsertScObj(item, obj)
        self.SortChildren(item)
        return True

    def Load(self, objects):
        """load the new simulation"""
        self.objects = objects
        self.FillTree()

    def FillTree(self):
        """fill the simulation objects tree"""
        #clear the tree control
        self.DeleteAllItems()
        if self.objects is None:
            return False

        # add the root item
        item = self.AddRoot("bsmedit")

        # go through all the objects, and only add the top level items for
        # speed. The items of other level will be populated once their parents
        # are expanded
        for key, obj in self.objects.iteritems():
            if obj['nkind'] != SC_OBJ_UNKNOWN and obj['parent'] == "":
                self.InsertScObj(item, obj)

        # any item? expand it
        (item, cookie) = self.GetFirstChild(item)
        if item.IsOk():
            self.Expand(item)

        self.SortChildren(item)
        return True

    def InsertScObj(self, item, obj):
        """insert a item with proper icon"""
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
        idx = self.AppendItem(item, obj['basename'], img[0], img[1],
                              wx.TreeItemData((obj, img)))
        # add the sign to append the children later
        if nkind in [SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY]:
            self.AppendItem(idx, '...', img[0], img[1], None)
        return idx

    def GetExtendObj(self, item):
        """return the extend object"""
        data = self.GetItemData(item)
        if data:
            (obj, img) = data.GetData()
            return obj
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

Gcs = Gcm()

class DumpDlg(wx.Dialog):
    def __init__(self, parent, objects, active, tracefile=True):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title="Dump...")

        self.objects = objects
        self.traceFile = tracefile

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)
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
        szConfirm.Add(self.btnOK, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.btnCancel = wx.Button(self, wx.ID_CANCEL, u"Cancel")
        szConfirm.Add(self.btnCancel, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
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
        objs = [n for n in self.objects if query in n]
        return objs, objs

    def OnBtnSelectFile(self, event):
        strWild = "BSM Files (*.bsm)|*.bsm|All Files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select BSM dump file", '', '', strWild,
                            style=wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.tcFile.SetValue(dlg.GetPath())

    def OnCheckVal(self, event):
        self.tcValid.Enable(self.cbTrigger.GetValue())

    def OnBtnOK(self, event):
        self.trace = {}
        if self.traceFile:
            self.trace['filename'] = self.tcFile.GetValue()
            self.trace['format'] = self.rbFormat.GetSelection()
        else:
            self.trace['size'] = self.spinSize.GetValue()
        self.trace['signal'] = self.tcSignal.GetValue()
        if self.cbTrigger.GetValue():
            self.trace['valid'] = self.tcValid.GetValue()
        else:
            self.trace['valid'] = None
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
        if num is not None and isinstance(num, int):
            self.num = num
        else:
            self.num = Gcs.get_next_num()
        self.colour = wx.Colour(178, 34, 34)
        Gcs.set_active(self)

        # the variable used to update the UI in idle()
        self.ui_timestamp = None
        self.ui_objs = None
        self.ui_buffers = None
        self.ui_update = 0
        self.tb = wx.ToolBar(self, style=wx.TB_FLAT|wx.TB_HORIZONTAL|wx.TB_NODIVIDER)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))

        self.tb.AddLabelTool(self.ID_SIM_STEP, "", wx.BitmapFromXPMData(step_xpm),
                             wx.BitmapFromXPMData(step_grey_xpm), wx.ITEM_NORMAL,
                             "Step", "Step the simulation")
        self.tb.AddLabelTool(self.ID_SIM_RUN, "", wx.BitmapFromXPMData(run_xpm),
                             wx.BitmapFromXPMData(run_grey_xpm), wx.ITEM_NORMAL,
                             "Run", "Run the simulation")
        self.tb.AddLabelTool(self.ID_SIM_PAUSE, "", wx.BitmapFromXPMData(pause_xpm),
                             wx.BitmapFromXPMData(pause_grey_xpm), wx.ITEM_NORMAL,
                             "Pause", "Pause the simulation")
        fStep = 1000.0
        fDuration = -1.0
        self.tb.AddSeparator()

        self.tcStep = NumCtrl(self.tb, wx.ID_ANY, "%g"%fStep, allowNegative=False, fractionWidth=0)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Step "))
        self.tb.AddControl(self.tcStep)
        self.cmbUnitStep = wx.ComboBox(self.tb, wx.ID_ANY, 'ns', size=(50, 20),
                                       choices=['fs', 'ps', 'ns', 'us', 'ms', 's'],
                                       style=wx.CB_READONLY)
        self.tb.AddControl(self.cmbUnitStep)
        self.tb.AddSeparator()

        self.tcTotal = NumCtrl(self.tb, wx.ID_ANY, "%g"%fDuration)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Total "))
        self.tb.AddControl(self.tcTotal)
        self.cmbUnitTotal = wx.ComboBox(self.tb, wx.ID_ANY, 'ns',
                                        size=(50, 20),
                                        choices=['fs', 'ps', 'ns', 'us', 'ms', 's'],
                                        style=wx.CB_READONLY)
        self.tb.AddControl(self.cmbUnitTotal)
        self.tb.AddSeparator()
        self.tb.AddStretchableSpace()
        self.tb.AddLabelTool(self.ID_SIM_SET, "", wx.BitmapFromXPMData(setting_xpm),
                             wx.BitmapFromXPMData(setting_grey_xpm),
                             wx.ITEM_DROPDOWN,
                             "Setting", "Configure the simulation")
        menu = wx.Menu()
        menu.Append(wx.ID_RESET, "&Reset")
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT, "&Exit")
        self.tb.SetDropdownMenu(self.ID_SIM_SET, menu)
        self.tb.Realize()

        self.tree = ModuleTree(self, style=wx.TR_DEFAULT_STYLE|
                               wx.TR_HAS_VARIABLE_ROW_HEIGHT|wx.TR_HIDE_ROOT|
                               wx.TR_MULTIPLE)
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(self.tree, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)
        self.Bind(EVT_SIM_NOTIFY, self.OnSimNotify)
        self.Bind(wx.EVT_TOOL, self.OnStep, id=self.ID_SIM_STEP)
        self.Bind(wx.EVT_TOOL, self.OnRun, id=self.ID_SIM_RUN)
        self.Bind(wx.EVT_TOOL, self.OnPause, id=self.ID_SIM_PAUSE)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self.OnTreeItemMenu)
        self.tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_MP_ADD_TO_NEW_VIEWER)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_MP_DUMP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_MP_TRACE_BUF)
        self.Bind(wx.EVT_MENU_RANGE, self.OnProcessCommand, id=wx.ID_FILE1, id2=wx.ID_FILE9)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=wx.ID_RESET)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.objects = None
        # the grid list used in context menu
        self.gridList = []

        # create the simulation kernel
        self.response = {}
        self._cmdId = 0
        self._cmdId_resp = -1
        self.qRespNotify = mp.Queue()

        self.qResp = None
        self.qCmd = None
        self.respThread = None
        self.simProcess = None
        self.lock = threading.Lock()
        self.waiting = 0
        self.busy = 0
        #
        if isinstance(filename, str) and filename is not None:
            self.load(filename)
        elif not silent:
            self.load_interactive()
        self.sim_filename = filename
        self.SetParameter()

    def __getitem__(self, key):
        return self.read(key)

    def __setitem__(self, key, value):
        if isinstance(key, str):
            return self.write({key:value})
        elif isinstance(key, list):
            return self.write(dict(zip(key, value)))
        else:
            raise ValueError()

    def OnClose(self, evt):
        self._stop()
        Gcs.destroy(self.num)

    def Destory(self, *args, **kwargs):
        self._stop()
        Gcs.destroy(self.num)
        return super(SimPanel, self).Destroy(*args, **kwargs)

    def SetColor(self, clr):
        self.color = clr

    def GetColor(self):
        return self.color

    def SendCommand(self, cmd, args={}, block=False):
        """send the command to the simulation process"""
        try:
            # always increase the command ID
            cid = self._cmdId
            self._cmdId += 1

            # return, if the previous call has not finished
            # it may happen when the previous command is waiting for response,
            # and another command is sent (by clicking a button)
            if self.qResp is None or self.qCmd is None or\
               self.simProcess is None or self.respThread is None:
                raise KeyboardInterrupt
            if not isinstance(args, dict):
                return False
            self.qCmd.put({'id':cid, 'block':block, 'cmd':cmd, 'arguments':args})
            #print 'block: ', block
            if block is True:
                # wait for the command to finish
                while True:
                    resp = self.qRespNotify.get()
                    #print resp
                    rtn = self.ProcessResponse(resp)
                    if resp.get('id', -1) == cid:
                        return rtn
            return True
        except:
            traceback.print_exc(file=sys.stdout)
        finally:
            pass

    def SetParameter(self, block=True):
        """set the simulation parameters with the values from GUI"""
        step = int(self.tcStep.GetValue())
        unitStep = int(self.cmbUnitStep.GetSelection())
        total = int(self.tcTotal.GetValue())
        unitTotal = int(self.cmbUnitTotal.GetSelection())
        self._set_parameter(step, unitStep, total, unitTotal, False, block)

    def set_parameter(self, step=None, total=None, more=False, block=True):
        """set the simulation parameters"""
        step, stepUnit = self.ParseTime(step)
        total, totalUnit = self.ParseTime(total)
        return self._set_parameter(step, stepUnit, total, totalUnit, more, block)

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
        return self.SendCommand('set_parameter', args, block)

    def start(self):
        """create an empty simulation"""
        self.stop()
        self.qResp = mp.Queue()
        self.qCmd = mp.Queue()
        self.respThread = RespThread(self, self.qResp, self.qRespNotify)
        self.respThread.start()
        self.simProcess = mp.Process(target=sim_process,
                                     args=(self.qResp, self.qCmd))
        self.simProcess.start()

    def load(self, filename, block=True):
        """load the simulation library (e.g., dll)"""
        self.start()
        return self.SendCommand('load', {'filename':filename}, block)

    def load_interactive(self):
        """show a file open dialog to select and open the simulation"""
        dlg = wx.FileDialog(self, "Choose a file", "", "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            self.load(filename)
        dlg.Destroy()

    def ParseTime(self, time):
        """
        parse the time in time+unit format

        For example,
            1) 1.5us will return (1.5, BSM_US)
            2) 100 will return (100, None), where unit is None (current one will
               be used)
        """
        if time:
            pattern = r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?:\s)*(fs|ps|ns|us|ms|s|)"
            x = re.match(pattern, str(time))
            if x:
                if x.group(2):
                    units = {'fs':BSM_FS, 'ps':BSM_PS, 'ns':BSM_NS, 'us':BSM_US,
                             'ms':BSM_MS, 's':BSM_SEC}
                    unit = units.get(x.group(2), None)
                    if unit is None:
                        raise ValueError("unknown time format: " + str(time))
                    return float(x.group(1)), unit
                else:
                    return float(x.group(1)), None
        return None, None

    def step(self, step=None, block=True):
        """
        proceed the simulation with one step

        The step is set with set_parameter(). The GUI components will be updated
        after the running.

        The breakpoints are checked at each delta cycle.
        """
        self.set_parameter(step=step, block=False)

        return self.SendCommand('step', {'running': False}, block)

    def run(self, to=None, more=None, block=True):
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
        return self.SendCommand('step', {'running': True}, block)

    def pause(self, block=True):
        """pause the simulation"""
        return self.SendCommand('pause', {}, block)

    def _stop(self):
        """destroy the simulation process"""
        if self.qResp is None or self.qCmd is None or\
            self.simProcess is None or self.respThread is None:
            return
        # stop the simulation kernel. No block operation allowed since
        # no response from the subprocess
        self.SendCommand('exit', {}, False)
        # stop the client
        self.qResp.put({'cmd':'exit'})
        self.simProcess.join()
        self.respThread.join()
        self.respThread = None
        self.simProcess = None
        dispatcher.send(signal='sim.unloaded', num=self.num)

    def stop(self):
        """destroy the simulation process and update the GUI"""
        self._stop()
        self.tree.Load(None)

    def reset(self):
        """reset the simulation"""
        if self.filename:
            self.load(self.filename)
        else:
            self.load_interactive()
    def time_stamp(self, inSecond=False, block=True):
        """return the simulation time elapsed as a string"""
        args = {}
        if inSecond:
            args['format'] = 'second'
        return self.SendCommand('time_stamp', args, block)

    def read(self, objects, block=True):
        """
        get the values of the registers

        If block == False, it will return after sending the command; otherwise, it
        will return the values.

        If objects only contains one register, its value will be returned if succeed;
        otherwise a dictionary is returned, where the keys are the items in objects.

        Example: read a single register
        >>> read('top.sig_bool', True)

        Example: read multiple registers from the same simulation
        >>> read(['top.sig_bool', 'top.sig_cos']
        """
        if isinstance(objects, str):
            objects = [objects]
        return self.SendCommand('read', {'objects':objects}, block)

    def write(self, objects, block=True):
        """
        write the value to the registers

        Objects should be a dictionary where the keys are the register name. Due to
        the two-step mechanism in SystemC, the value will be updated after the next
        delta cycle. That is, if a read() is called after write(), it will return
        the previous value.

        Example:
        >>> a = read('top.sig_int', True)
        >>> write({'top.sig_int': 100}, True)
        >>> b = read('top.sig_int', True) # a == b
        >>> step()
        >>> c = read('top.sig_int', True)
        """
        return self.SendCommand('write', {'objects':objects}, block)

    def trace_file(self, obj, ttype='bsm', valid=None,
                   trigger='posneg', block=True):
        """
        dump the values to a file

        obj:
            register name
        ttype:
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
        tTypeDict = {'bsm': BSM_TRACE_SIMPLE, 'vcd': BSM_TRACE_VCD}
        tTriggerDict = {'posneg': BSM_BOTHEDGE, 'pos': BSM_POSEDGE,
                        'neg': BSM_NEGEDGE, 'none': BSM_NONEEDGE}
        traceType = tTypeDict.get(ttype, None)
        traceTrigger = tTriggerDict.get(trigger, None)
        if not traceType:
            raise ValueError("Not supported trace type: " + str(ttype))
        if not traceTrigger:
            raise ValueError("Not supported trigger type: " + str(trigger))

        args = {'name':obj, 'type':traceType, 'valid':valid,
                'trigger':traceTrigger}
        return self.SendCommand('trace_file', args, block)

    def trace_buf(self, obj, size=256, valid=None, trigger='posneg',
                  block=True):
        """start dumping the register to a numpy.array"""
        if isinstance(obj, list):
            obj = obj[0]
        tTriggerDict = {'posneg': BSM_BOTHEDGE, 'pos': BSM_POSEDGE,
                        'neg': BSM_NEGEDGE, 'none': BSM_NONEEDGE}
        traceTrigger = tTriggerDict.get(trigger, None)
        if not traceTrigger:
            raise ValueError("Not supported trigger type: " + str(traceTrigger))

        args = {'name':obj, 'size':size, 'valid':valid, 'trigger':traceTrigger}
        return self.SendCommand('trace_buf', args, block)

    def read_buf(self, objects, block=True):
        """
        read the traced buffer to an numpy array

        If the buffer is previous traced by calling trace_buf, the array with
        previous defined size will return; otherwise the trace_buf will be
        called with default arguments first.
        """
        if isinstance(objects, str):
            objects = [objects]
        return self.SendCommand('read_buf', {'objects':objects}, block)

    def monitor_reg(self, objs, block=True):
        """
        monitor the register value

        At end of each step, the simulation process will report the value
        """
        if isinstance(objs, str):
            objs = [objs]
        return self.SendCommand('monitor_add', {'objects':objs}, block)

    def unmonitor_reg(self, objs, block=True):
        """stop monitoring the register"""
        if isinstance(objs, str):
            objs = [objs]
        return self.SendCommand('monitor_del', {'objects':objs}, block)

    def add_breakpoint(self, objs, block=True):
        """add the breakpoint (name, condition, hitcount)"""
        return self.SendCommand('breakpoint_add', {'objects':objs}, block)

    def del_breakpoint(self, objs, block=True):
        """delete the breakpoint"""
        return self.SendCommand('breakpoint_del', {'objects':objs}, block)

    def abs_object_name(self, obj):
        """generate the global name for simulation object (num.name)"""
        num, name = sim.get_object_name(obj)
        if num is not None:
            return obj
        return "%d."%self.num + obj

    def monitor(self, objects, grid = None, index=-1):
        """show the register in a propgrid window"""
        if not objects:
            return None
        if grid is None:
            grid = bsmPropGrid.GCM.get_active()
        if not grid:
            grid = sim.propgrid()
        if not grid:
            return
        if isinstance(objects, str):
            objects = [objects]
        props = []
        for name in objects:
            obj = self.objects.get(name, None)
            if obj is None:
                continue
            prop = grid.InsertProperty(self.abs_object_name(obj['name']),
                                       obj['basename'], obj['value'], index)
            prop.SetGripperColor(self.color)
            if not obj['readable'] and not obj['writable']:
                prop.SetReadOnly(True)
                prop.SetShowRadio(False)

            props.append(prop)
            if index != -1:
                index += 1
        if len(props) == 1:
            return props[0]
        return props

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
            wx.CallAfter(self.read, objects, True)

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
        for v in bsmPropGrid.GCM.get_all_managers():
            self.gridList.append(v)
            submenu.Append(nid, v.GetLabel())
            nid = nid + 1

        menu.AppendSubMenu(submenu, "Add to...")
        self.PopupMenu(menu)
        menu.Destroy()

    def OnTreeBeginDrag(self, event):
        if self.tree.objects is None:
            return

        ids = self.tree.GetSelections()
        objs = []
        objs_name = []
        for i in range(0, len(ids)):
            item = ids[i]
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
                    objchild.append(self.abs_object_name(ext2['name']))
                    objs_name.append(ext2['name'])
                    (child, cookie) = self.tree.GetNextChild(item, cookie)
                objs.append({'reg':self.abs_object_name(ext['name']), 'child':objchild})
            else:
                objs.append({'reg':self.abs_object_name(ext['name'])})
            objs_name.append(ext['name'])
        # need to explicitly allow drag
        # start drag operation
        data = wx.PyTextDataObject(json.dumps(objs))
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
        self.read(objs_name, False)
    def OnProcessCommand(self, event):
        """process the menu command"""
        eid = event.GetId()
        viewer = None
        if eid in [self.ID_MP_DUMP, self.ID_MP_TRACE_BUF]:
            objs = [o for o, v in self.objects.iteritems() if v['numeric'] and v['readable']]
            objs.sort()
            active = ''
            items = self.tree.GetSelections()
            if items:
                active = self.tree.GetExtendObj(items[0])['name']
            dlg = DumpDlg(self, objs, active, eid == self.ID_MP_DUMP)
            if dlg.ShowModal() == wx.ID_OK:
                t = dlg.GetTrace()
                if eid == self.ID_MP_DUMP:
                    self.trace_file(t['signal'], t['format'], t['valid'], t['trigger'])
                else:
                    self.trace_buf(t['signal'], t['size'], t['valid'], t['trigger'])
        elif eid == self.ID_MP_ADD_TO_NEW_VIEWER:
            viewer = sim.propgrid()
        elif eid >= wx.ID_FILE1 and eid <= wx.ID_FILE9:
            viewer = self.gridList[eid - wx.ID_FILE1]
        elif eid == wx.ID_EXIT:
            self.stop()
        elif eid == wx.ID_RESET:
            self.reset()
        if viewer:
            ids = self.tree.GetSelections()
            objs = []
            for i in range(0, len(ids)):
                item = ids[i]
                if item == self.tree.GetRootItem():
                    continue
                if not item.IsOk():
                    break
                ext = self.tree.GetExtendObj(item)
                nkind = ext['nkind']
                self.monitor(ext['name'],viewer)
                objs.append(ext['name'])
                if nkind == SC_OBJ_XSC_ARRAY:
                    (child, cookie) = self.tree.GetFirstChild(item)
                    if child.IsOk() and self.tree.GetItemText(child) == "...":
                        self.tree.Expand(item)
                    (child, cookie) = self.tree.GetFirstChild(item)
                    while child.IsOk():
                        ext2 = self.tree.GetExtendObj(child)
                        prop = self.monitor(ext2['name'], viewer)
                        objs.append(ext2['name'])
                        prop.SetIndent(1)
                        (child, cookie) = self.tree.GetNextChild(item, cookie)
            self.read(objs, False)
    def ProcessResponse(self, resp):
        try:
            self.waiting += 1;
            command = resp.get('cmd', '')
            cid = resp.get('id', -1)
            value = resp.get('value', False)
            args = resp.get('arguments', {})
            if command == 'load':
                self.objects = value
                self.tree.Load(self.objects)
                self.filename = args['filename']
                dispatcher.send(signal='sim.loaded', num=self.num)
                self.time_stamp(False, False)
                self.read([], False)
                self.read_buf([], False)
            elif command == 'step':
                if value:
                    if self.waiting > 1000:
                        self.waiting = 0
                        self.busy = True
                        self.set_parameter(step=self.tcStep.GetValue()*10, block=False)
                        print(self.tcStep.GetValue())
                    # simulation proceeds one step, update the values
                    if not args.get('running', False) or self.waiting < 20:
                        self.time_stamp(False, False)
                    if not args.get('running', False) or self.waiting < 100:
                        self.read([], False)
                        self.read_buf([], False)
            elif command == 'pause':
                pass
            elif command == 'monitor_add':
                objs = [self.abs_object_name(name) for name, v in value.iteritems() if v]
                dispatcher.send(signal='sim.monitor_added', objs=objs)
                objs = [name for name, v in value.iteritems() if v]
                self.read(objs, False)
            elif command == 'monitor_del':
                pass
            elif command == 'breakpoint_add':
                pass
            elif command == 'breakpoint_del':
                pass
            elif command == 'set_parameter':
                if value:
                    self.busy = False
                    args = resp['arguments']
                    step = self.tcStep.GetValue()
                    self.tcStep.SetValue(str(args.get('step', step)))
                    unitStep = self.cmbUnitStep.GetSelection()
                    self.cmbUnitStep.SetSelection(args.get('unitStep', unitStep))
                    total = self.tcTotal.GetValue()
                    self.tcTotal.SetValue(str(args.get('total', total)))
                    unitTotal = self.cmbUnitTotal.GetSelection()
                    self.cmbUnitTotal.SetSelection(args.get('unitTotal', unitTotal))
            elif command == 'get_parameter':
                pass
            elif command == 'read':
                self.ui_objs = {self.abs_object_name(name):v for name, v in value.iteritems()}
                if len(value) == 1:
                    value = value.values()[0]
            elif command == 'read_buf':
                self.ui_buffers = {self.abs_object_name(name):v for name, v in value.iteritems()}
                if len(value) == 1:
                    value = value.values()[0]
            elif command == 'write':
                pass
            elif command == 'time_stamp':
                if isinstance(value, str):
                    self.ui_timestamp = value
            elif command == 'trace_file':
                pass
            elif command == 'trace_buf':
                pass
            elif command == 'breakpoint_triggered':
                bp = value #[name, condition, hitcount, hitsofar]
                for grid in bsmPropGrid.GCM.get_all_managers():
                    if grid.triggerBreakPoint(self.abs_object_name(bp[0]), bp[1], bp[2]):
                        dispatcher.send(signal='frame.show_panel', panel=grid)
                        break
            elif command == 'writeOut':
                dispatcher.send(signal='shell.writeout', text=value)
            return value
        except:
            traceback.print_exc(file=sys.stdout)

    def OnSimNotify(self, evt):
        """process the response from the simulation process"""
        try:
            cmd = self.qRespNotify.get_nowait()
            while cmd:
                self.ProcessResponse(cmd)
                cmd = self.qRespNotify.get_nowait()
        except Queue.Empty:
            pass
    def OnIdle(self, event):
        """update the GUI"""
        self.waiting = 0 ;
        if (self.ui_timestamp is not None) and self.ui_update == 0:
            dispatcher.send(signal="frame.show_status_text", text=self.ui_timestamp)
            self.ui_timestamp = None
        elif (self.ui_objs is not None) and self.ui_update == 1:
            dispatcher.send(signal="grid.updateprop", objs=self.ui_objs)
            self.ui_objs = None
        elif (self.ui_buffers is not None) and self.ui_update == 2:
            # update the plot, it is time-consuming
            dispatcher.send(signal="sim.buffer_changed", bufs=self.ui_buffers)
            self.ui_buffers = None
        self.ui_update += 1
        self.ui_update %= 3

    def OnStep(self, event):
        self.SetParameter(False)
        self.step()

    def OnRun(self, event):
        self.SetParameter(False)
        self.run()

    def OnPause(self, event):
        self.pause()

bsmEVT_SIM_NOTIFY = wx.NewEventType()
EVT_SIM_NOTIFY = wx.PyEventBinder(bsmEVT_SIM_NOTIFY)
class SimEvent(wx.PyCommandEvent):
    def __init__(self):
        wx.PyCommandEvent.__init__(self, bsmEVT_SIM_NOTIFY)

class RespThread(threading.Thread):
    def __init__(self, frame, qResp, qRespNotify):
        threading.Thread.__init__(self)
        self.frame = frame
        self.qResp = qResp
        self.qRespNotify = qRespNotify
        self.lastTimeNotify = -1
    def run(self):
        while self.response():
            pass

    def response(self):
        command = self.qResp.get()
        command['waiting'] = self.qResp.qsize()
        if command['cmd'] == 'exit':
            return False
        if command.get('block', False):
            # always forward the response from blocking command, otherwise
            # the main thread may not be able to return
            self.qRespNotify.put(command)
        else:
            # TODO if the qRespNotify is not almost empty, maybe we send too
            # many responses (e.g., in running mode), and ignore the
            # unimportant response.
            #delta = _time() - self.lastTimeNotify
            #if delta > 0 or command.get('important', False):
            #    self.lastTimeNotify += delta
            self.qRespNotify.put(command)
            event = SimEvent()
            wx.PostEvent(self.frame, event)
        return True

class sim:
    frame = None
    ID_SIM_NEW = wx.NOT_FOUND
    def __init__(self):
        pass

    @classmethod
    def Initialize(cls, frame):
        cls.frame = frame

        dispatcher.send('frame.add_menu', path="View:Simulations",
                        rxsignal='', kind='Popup')
        resp = dispatcher.send(signal='frame.add_menu',
                               path='File:New:Simulation',
                               rxsignal='bsm.simulation')
        if resp:
            cls.ID_SIM_NEW = resp[0][1]

        dispatcher.connect(cls.ProcessCommand, signal='bsm.simulation')
        dispatcher.connect(receiver=cls.Uninitialize, signal='frame.exit')
        dispatcher.connect(receiver=cls.set_active, signal='frame.activate_panel')

        dispatcher.connect(receiver=cls.OnAddProp, signal='prop.insert')
        dispatcher.connect(receiver=cls.OnDelProp, signal='prop.delete')
        dispatcher.connect(receiver=cls.OnDropProp, signal='prop.drop')
        dispatcher.connect(receiver=cls.OnBPAdd, signal='prop.bp_add')
        dispatcher.connect(receiver=cls.OnBPDel, signal='prop.bp_del')
        dispatcher.connect(receiver=cls.OnValChanged, signal='prop.changed')
        dispatcher.connect(receiver=cls.OnPaneClosing, signal='frame.closing_pane')

    @classmethod
    def OnPaneClosing(cls, pane, force):
        if isinstance(pane, SimPanel):
            if force:
                pane.stop()
                return {'veto': False}
            for mgr in Gcs.get_all_managers():
                if mgr == pane:
                    return {'veto': True}

    @classmethod
    def OnValChanged(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            mgr.write({name: prop.GetValue()})

    @classmethod
    def OnBPAdd(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            cnd = prop.GetBPCondition()
            mgr.add_breakpoint([[name, cnd[0], cnd[1]]])

    @classmethod
    def OnBPDel(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            cnd = prop.GetBPCondition()
            mgr.del_breakpoint([[name, cnd[0], cnd[1]]])

    @classmethod
    def OnAddProp(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            mgr.monitor_reg(name)

    @classmethod
    def OnDelProp(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            mgr.unmonitor_reg(name)

    @classmethod
    def OnDropProp(cls, index, prop, grid):
        objs = json.loads(prop)
        for obj in objs:
            reg = obj['reg']
            num, name = cls.get_object_name(str(reg))
            mgr = Gcs.get_manager(num)
            if mgr is None:
                continue
            p = mgr.monitor(name, grid, index)
            if index != -1:
                index = index + 1
            for c in obj.get('child', []):
                num, name = cls.get_object_name(str(c))
                mgr = Gcs.get_manager(num)
                if mgr is None: continue
                p = mgr.monitor(name, grid, index)
                p.SetIndent(1)
                if index != -1:
                    index = index + 1

    @classmethod
    def set_active(cls, pane):
        if pane and isinstance(pane, SimPanel):
            Gcs.set_active(pane)
        if pane and isinstance(pane, bsmPropGrid):
            bsmPropGrid.GCM.set_active(pane)

    @classmethod
    def Uninitialize(cls):
        for mgr in Gcs.get_all_managers():
            mgr.stop()
            dispatcher.send('frame.close_panel', panel=mgr)
        dispatcher.send('frame.del_menu', path="View:Simulations")
        dispatcher.send('frame.del_menu', path="File:New:Simulation",
                                        id = cls.ID_SIM_NEW)

    @classmethod
    def ProcessCommand(cls, command):
        if command == cls.ID_SIM_NEW:
            cls.simulation()

    @classmethod
    def get_object_name(cls, name):
        """return the object name"""
        x = re.match(r'^(\d)+\.(.*)', name)
        if x is None:
            return (None, name)
        else:
            return (int(x.group(1)), x.group(2))

    @classmethod
    def MakeBitmap(cls, red, green, blue, alpha=128):
        # Create the bitmap that we will stuff pixel values into using
        # the raw bitmap access classes.
        bmp = wx.EmptyBitmap(16, 16, 32)

        # Create an object that facilitates access to the bitmap's
        # pixel buffer
        pixelData = wx.AlphaPixelData(bmp)
        if not pixelData:
            raise RuntimeError("Failed to gain raw access to bitmap data.")

        # We have two ways to access each pixel, first we'll use an
        # iterator to set every pixel to the colour and alpha values
        # passed in.
        for pixel in pixelData:
            pixel.Set(red, green, blue, alpha)

        # Next we'll use the pixel accessor to set the border pixels
        # to be fully opaque
        pixels = pixelData.GetPixels()
        for x in xrange(16):
            pixels.MoveTo(pixelData, x, 0)
            pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
            pixels.MoveTo(pixelData, x, 16-1)
            pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
        for y in xrange(16):
            pixels.MoveTo(pixelData, 0, y)
            pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
            pixels.MoveTo(pixelData, 16-1, y)
            pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)

        return bmp

    @classmethod
    def GetColorByNum(cls, num):
        color = ['green', 'red', 'blue', 'black', 'cyan', 'yellow', 'magenta', 'cyan']
        return wx.NamedColour(color[num%len(color)])

    @classmethod
    def simulation(cls, num=None, filename=None, silent=False, create=True,
                   activate=False):
        """
        create a simulation

        If the simulation exists, return its handler; otherwise, create it if
        create == True.
        """
        manager = Gcs.get_manager(num)
        if manager is None and create:
            manager = SimPanel(sim.frame, num, filename, silent)
            clr = cls.GetColorByNum(manager.num)
            clr.Set(clr.red, clr.green, clr.blue, 128)
            manager.SetColor(clr)
            page_bmp = cls.MakeBitmap(clr.red, clr.green, clr.blue)#178,  34,  34)
            title = "Simulation-%d"%manager.num
            dispatcher.send(signal="frame.add_panel", panel=manager,
                            title=title, target="History",
                            icon=page_bmp, showhidemenu="View:Simulations:%s"%title)
        # activate the manager
        elif manager and activate:
            dispatcher.send(signal='frame.show_panel', panel=manager)

        return manager

    @classmethod
    def propgrid(cls, num=None, create=True, activate=False):
        """
        get the propgrid manager by its number

        If the manager exists, return its handler; otherwise, it will be created.
        """
        manager = bsmPropGrid.GCM.get_manager(num)
        if not manager and create:
            manager = bsmPropGrid(cls.frame)
            manager.SetLabel("Propgrid-%d"%manager.num)
            dispatcher.send(signal="frame.add_panel", panel=manager,
                            title=manager.GetLabel())
        elif manager and activate:
            # activate the manager
            dispatcher.send(signal='frame.show_panel', panel=manager)
        return manager

    @classmethod
    def get_sim_from_signal(cls, name):
        num, n = cls.get_object_name(name)
        if not num:
            return Gcs.get_active()
        return Gcs.get_manager(num)
    @classmethod
    def plot_trace(cls, x=None, y=None, autorelim=True, *args, **kwargs):
        """
        plot the trace

        The trace will be automatically updated after each simulation step.
        """
        if not graph.initialized:
            print "Matplotlib is not installed correctly!"
            return
        if y is None:
            return
        s = cls.get_sim_from_signal(y)
        if s is None:
            return
        dy = s.read_buf(cls.get_object_name(y), True)
        y = {s.abs_object_name(y):dy}
        if x is not None:
            s = cls.get_sim_from_signal(x)
            if s is None:
                return
            dx = s.read_buf(cls.get_object_name(x), True)
            x = {s.abs_object_name(x):dx}
        mgr = graph.plt.get_current_fig_manager()
        mgr.plot_trace(x, y, autorelim, *args, **kwargs)

def bsm_Initialize(frame):
    sim.Initialize(frame)
    dispatcher.send(signal='shell.run',
                    command='from bsm.pysim import *',
                    prompt=False, verbose=False, history=False)

