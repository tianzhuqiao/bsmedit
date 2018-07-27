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
import wx.lib.agw.aui as aui
from ..auibarpopup import AuiToolBarPopupArt
from . import graph
from .bsmxpm import module_xpm, switch_xpm, in_xpm, out_xpm, inout_xpm,\
                    module_grey_xpm, switch_grey_xpm, in_grey_xpm,\
                    out_grey_xpm, inout_grey_xpm, step_xpm, run_xpm, \
                    pause_xpm, setting_xpm
from .simprocess import *
from .. import propgrid as pg
from .pymgr_helpers import Gcm
from .autocomplete import AutocompleteTextCtrl
from .utility import MakeBitmap, FastLoadTreeCtrl, PopupMenu
from .. import c2p

Gcs = Gcm()
class Simulation(object):
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
        self.qresp = None
        self.qcmd = None
        self.sim_process = None
        self.status = {'running':False, 'valid':False}
        self._interfaces = {}

    def release(self):
        """destroy simulation"""
        self.frame = None
        self.stop()
        Gcs.destroy(self.num)

    def __getitem__(self, obj):
        """read the object"""
        return self.read(objects=obj)

    def __setitem__(self, obj, value):
        """write the value to the object"""
        if isinstance(obj, six.string_types):
            return self.write({obj:value})
        elif isinstance(obj, (list, tuple)):
            return self.write(dict(zip(obj, value)))
        else:
            raise ValueError()

    def _send_command(self, cmd, **kwargs):
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
            if self.qresp is None or self.qcmd is None or self.sim_process is None:
                raise KeyboardInterrupt
            block = kwargs.get('block', True)

            if not kwargs.get('silent', True):
                print(cmd, cid, kwargs)

            self.qcmd.put({'id':cid, 'cmd':cmd, 'arguments':kwargs})
            if block is True:
                # wait for the command to finish
                while True:
                    resp = self.qresp.get()
                    rtn = self._process_response(resp)
                    if resp.get('id', -1) == cid:
                        return rtn
            return True
        except:
            traceback.print_exc(file=sys.stdout)

    def is_valid(self):
        return self.status['valid']

    def is_running(self):
        return self.status['running']

    def wait_until_simulation_paused(self, timeout=None):
        """
        wait for the simulation to pause

        return: It will not return until the simulation has paused.
                True: the simulation is valid and paused;
                False: otherwise.
        timeout: the maximum waiting period (in second)
        """
        # return if the simulation is not valid
        if self.qresp is None or self.qcmd is None or self.sim_process is None:
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

    def start(self):
        """create an empty simulation"""
        self.stop()
        self.qresp = mp.Queue()
        self.qcmd = mp.Queue()
        self.sim_process = mp.Process(target=sim_process,
                                      args=(self.qresp, self.qcmd))
        self.sim_process.start()
        self._interfaces = self._send_command('get_interfaces')
        if self._set_interfaces:
            self._set_interfaces(self._interfaces)

    def _set_interfaces(self, interfaces):
        for item in interfaces:
            if hasattr(self, item):
                continue
            def wrapper(cmd, **kwargs):
                return self._send_command(cmd, **kwargs)
            formatted_args = interfaces[item]['args']
            formatted_args = formatted_args.lstrip('(').rstrip(')')
            formatted_args2 = []
            for arg in formatted_args.split(','):
                if '=' in arg:
                    # remove the default value
                    arg = arg[:arg.find('=')]
                    arg = "{0}={0}".format(arg)
                formatted_args2.append(arg)

            fndef = 'lambda %s: wrapper("%s", %s)'%(formatted_args, item,
                                                    ','.join(formatted_args2))
            fake_fn = eval(fndef, {'wrapper': wrapper, 'item': item})
            fake_fn.__doc__ = interfaces[item]['doc']
            setattr(self, item, fake_fn)

    def load(self, filename=None, block=True):
        """
        load the simulation library (e.g., dll)

        if filename is None, show a file open dialog to select and open the
        simulation
        """
        if filename is None:
            style = c2p.FD_OPEN | c2p.FD_FILE_MUST_EXIST
            dlg = wx.FileDialog(self.frame, "Choose a file", "", "", "*.*", style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
            dlg.Destroy()

        if filename is None:
            return False

        self.start()
        self.filename = filename
        self._send_command('load', block=block, filename=filename)
        return self.get_status()

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
        return self.step(running=True, block=block)

    def stop(self):
        """destroy the simulation"""
        if self.qresp is None or self.qcmd is None or self.sim_process is None:
            return
        # stop the simulation kernel. No block operation allowed since
        # no response from the subprocess
        self._send_command('exit', block=False)
        while not self.qresp.empty():
            self.qresp.get_nowait()
        self.sim_process.join()
        self.sim_process = None
        # stop the client
        self._process_response({'cmd':'exit'})

    def reset(self):
        """reset the simulation"""
        if self.filename:
            return self.load(self.filename)
        return False

    def _object_list(self, objs):
        """help function to generate object list"""
        if isinstance(objs, six.string_types):
            return [objs]
        elif isinstance(objs, (list, tuple)):
            return objs
        else:
            raise ValueError()

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
            grid = SimPropGrid.GCM.get_active()
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
            prop.SetReadonly(not obj['writable'])
            prop.SetShowCheck(obj['readable'])
            props.append(prop)
            if index != -1:
                index += 1
        if len(props) == 1:
            return props[0]
        return props

    def _process_response(self, resp):
        """process the response from the simulation core"""
        try:
            wx.CallAfter(dp.send, signal='sim.response', sender=self, resp=resp)
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
            elif command == 'get_status':
                self.status.update(value)
            return value
        except:
            traceback.print_exc(file=sys.stdout)

    def process_response(self):
        if not self.qresp:
            return None
        try:
            # process the response
            resp = self.qresp.get_nowait()
            if resp:
                return self._process_response(resp)
        except Queue.Empty:
            pass

        if self.status['running'] and self.qresp.empty() and self.qcmd.empty():
            # if the queues are almost empty, retrieve the data
            self.time_stamp(insecond=False, block=False)
            self.read(objects=[], block=False)
            self.read_buf([], block=False)

        return None

class ModuleTree(FastLoadTreeCtrl):
    """the tree control to show the hierarchy of the objects in the simulation"""
    def __init__(self, parent, style=wx.TR_DEFAULT_STYLE):
        style = style | wx.TR_HAS_VARIABLE_ROW_HEIGHT | wx.TR_HIDE_ROOT |\
                wx.TR_MULTIPLE | wx.TR_LINES_AT_ROOT
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
        self.toolbarart = AuiToolBarPopupArt(self)
        self.tb = aui.AuiToolBar(self, -1, agwStyle=aui.AUI_TB_OVERFLOW|
                                 aui.AUI_TB_PLAIN_BACKGROUND)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))
        xpm2bmp = c2p.BitmapFromXPM
        self.tb.AddSimpleTool(self.ID_SIM_STEP, "Step", xpm2bmp(step_xpm),
                              "Step the simulation")
        self.tb.AddSimpleTool(self.ID_SIM_RUN, "Run", xpm2bmp(run_xpm),
                              "Run the simulation")
        self.tb.AddSimpleTool(self.ID_SIM_PAUSE, "Pause", xpm2bmp(pause_xpm),
                              "Pause the simulation")

        self.tb.AddSeparator()

        self.tcStep = wx.SpinCtrlDouble(self.tb, value='1000', size=(150, -1),
                                        min=0, max=1e9, inc=1)
        self.tcStep.SetDigits(4)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Step "))
        self.tb.AddControl(self.tcStep)
        units = ['fs', 'ps', 'ns', 'us', 'ms', 's']
        self.cmbUnitStep = wx.Choice(self.tb, wx.ID_ANY, size=(50, -1),
                                     choices=units)
        self.cmbUnitStep.SetSelection(2)
        self.tb.AddControl(self.cmbUnitStep)
        self.tb.AddSeparator()

        self.tcTotal = wx.SpinCtrlDouble(self.tb, value='-1', size=(150, -1),
                                         min=-1, max=1e9, inc=1)
        self.tcTotal.SetDigits(4)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Total "))
        self.tb.AddControl(self.tcTotal)
        self.cmbUnitTotal = wx.Choice(self.tb, wx.ID_ANY, size=(50, -1),
                                      choices=units)
        self.cmbUnitTotal.SetSelection(2)
        self.tb.AddControl(self.cmbUnitTotal)
        self.tb.AddStretchSpacer()
        self.tb.AddSimpleTool(self.ID_SIM_SET, "Setting", xpm2bmp(setting_xpm),
                              "Configure the simulation")

        self.tb.SetToolDropDown(self.ID_SIM_SET, True)
        self.tb.SetArtProvider(self.toolbarart)
        self.tb.Realize()
        self.tree = ModuleTree(self)
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(self.tree, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.Bind(wx.EVT_TOOL, self.OnProcessCommand)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCmdUI)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self.OnTreeItemMenu)
        self.tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)
        self.Bind(aui.EVT_AUITOOLBAR_TOOL_DROPDOWN, self.OnMenuDropDown,
                  id=self.ID_SIM_SET)
        # simulation
        self.sim = Simulation(self, num)
        if filename is not None or not silent:
            self.sim.load(filename)
            self.SetParameter()

        dp.connect(receiver=self._process_response, signal='sim.response',
                   sender=self.sim)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.timer.Start(5)

    def OnTimer(self, event):
        try:
            # process the response
            self.sim.process_response()
        except:
            traceback.print_exc(file=sys.stdout)

    def OnMenuDropDown(self, event):
        if event.IsDropDownClicked():
            menu = wx.Menu()
            menu.Append(wx.ID_RESET, "&Reset")
            menu.AppendSeparator()
            menu.Append(wx.ID_EXIT, "&Exit")

            # line up our menu with the button
            tb = event.GetEventObject()
            tb.SetToolSticky(event.GetId(), True)
            rect = tb.GetToolRect(event.GetId())
            pt = tb.ClientToScreen(rect.GetBottomLeft())
            pt = self.ScreenToClient(pt)

            self.PopupMenu(menu, pt)

            # make sure the button is "un-stuck"
            tb.SetToolSticky(event.GetId(), False)

    def Destroy(self):
        """
        Destroy the simulation properly before close the pane.
        """
        dp.disconnect(receiver=self._process_response, signal='sim.response',
                      sender=self.sim)
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
        if not self.sim or not self.sim.is_valid():
            return

        step = self.tcStep.GetValue()
        unitStep = self.cmbUnitStep.GetString(self.cmbUnitStep.GetSelection())
        step = "%f%s"%(step, unitStep)
        total = self.tcTotal.GetValue()
        unitTotal = self.cmbUnitTotal.GetString(self.cmbUnitTotal.GetSelection())
        total = "%f%s"%(total, unitTotal)
        self.sim.set_parameter(step=step, total=total, more=False, block=block)

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
            wx.CallAfter(self.sim.read, objects, block=True)

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
        nid = wx.ID_HIGHEST
        grids = []
        for mag in SimPropGrid.GCM.get_all_managers():
            grids.append(mag)
            submenu.Append(nid, mag.GetLabel())
            nid += 1

        menu.AppendSubMenu(submenu, "Add to...")
        cmd = PopupMenu(self, menu)
        if cmd in [self.ID_MP_DUMP, self.ID_MP_TRACE_BUF]:
            objs = [o for o, v in six.iteritems(self.sim.objects) if \
                    v['numeric'] and v['readable']]
            objs.sort()
            active = ''
            items = self.tree.GetSelections()
            if items:
                active = self.tree.GetExtendObj(items[0])['name']
            dlg = DumpDlg(self, objs, active, cmd == self.ID_MP_DUMP)
            if dlg.ShowModal() == wx.ID_OK:
                t = dlg.GetTrace()
                if cmd == self.ID_MP_DUMP:
                    self.sim.trace_file(t['filename'], t['signal'], t['format'],
                                        t['valid'], t['trigger'], block=False)
                else:
                    self.sim.trace_buf(t['signal'], t['size'], t['valid'],
                                       t['trigger'], block=False)
        elif cmd == self.ID_MP_ADD_TO_NEW_VIEWER:
            self.AddSelectedToGrid(sim.propgrid())
        else:
            idx = cmd - wx.ID_HIGHEST
            if idx >= 0 and idx < len(grids):
                self.AddSelectedToGrid(grids[idx])

    def AddSelectedToGrid(self, grid):
        if not grid:
            return
        ids = self.tree.GetSelections()
        objs = []
        for item in ids:
            if item == self.tree.GetRootItem():
                continue
            if not item.IsOk():
                break
            ext = self.tree.GetExtendObj(item)
            nkind = ext['nkind']
            self.sim.monitor(ext['name'], grid)
            objs.append(ext['name'])
            if nkind == SC_OBJ_XSC_ARRAY:
                (child, cookie) = self.tree.GetFirstChild(item)
                if child.IsOk() and self.tree.GetItemText(child) == "...":
                    self.tree.Expand(item)
                (child, cookie) = self.tree.GetFirstChild(item)
                while child.IsOk():
                    ext2 = self.tree.GetExtendObj(child)
                    prop = self.sim.monitor(ext2['name'], grid)
                    objs.append(ext2['name'])
                    prop.SetIndent(1)
                    (child, cookie) = self.tree.GetNextChild(item, cookie)
        self.sim.read(objects=objs, block=False)


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
        self.sim.read(objects=objs_name, block=False)

    def OnUpdateCmdUI(self, event):
        eid = event.GetId()
        if eid in [self.ID_SIM_STEP, self.ID_SIM_RUN]:
            event.Enable(self.sim and not self.sim.is_running())
        elif eid == self.ID_SIM_PAUSE:
            event.Enable(self.sim and self.sim.is_running())

    def OnProcessCommand(self, event):
        """process the menu command"""
        eid = event.GetId()
        if eid == wx.ID_EXIT:
            self.sim.stop()
            # delay destroy the simulation window so AuiToolBar can finish
            # processing the dropdown event.
            wx.CallAfter(dp.send, signal='frame.delete_panel', panel=self)
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

    def _process_response(self, resp):
        if self.is_destroying:
            return
        try:
            command = resp.get('cmd', '')
            value = resp.get('value', False)
            if command == 'load':
                self.tree.Load(self.sim.objects)
            elif command == 'exit':
                self.tree.Load(None)
                dp.send('sim.unloaded', num=self.sim.num)
            elif command == 'monitor_signal':
                objs = [name for name, v in six.iteritems(value) if v]
                self.sim.read(objects=objs, block=False)
            elif command == 'set_parameter':
                if value:
                    step = self.tcStep.GetValue()
                    self.tcStep.SetValue(value.get('step', step))
                    unitStep = self.cmbUnitStep.GetSelection()
                    self.cmbUnitStep.SetSelection(value.get('step_unit', unitStep))
                    total = self.tcTotal.GetValue()
                    self.tcTotal.SetValue(value.get('total', total))
                    unitTotal = self.cmbUnitTotal.GetSelection()
                    self.cmbUnitTotal.SetSelection(value.get('total_unit', unitTotal))
            elif command == 'read':
                gname = self.sim.global_object_name
                ui_objs = {gname(name):v for name, v in six.iteritems(value)}
                dp.send(signal="sim.update", objs=ui_objs)
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
                for grid in SimPropGrid.GCM.get_all_managers():
                    if grid.TriggerBreakPoint(gname(bp[0]), bp[1], bp[2]):
                        dp.send(signal='frame.show_panel', panel=grid)
                        break
                else:
                    txt = "Breakpoint triggered: %s\n"%(json.dumps(bp))
                    dp.send(signal='shell.write_out', text=txt)
            elif command == 'write_out':
                dp.send(signal='shell.write_out', text=value)

            if command in ['load', 'step'] and value:
                self.sim.time_stamp(insecond=False, block=False)
                self.sim.read(objects=[], block=False)
                self.sim.read_buf(objects=[], block=False)
        except:
            traceback.print_exc(file=sys.stdout)

class SimPropGrid(pg.PropGrid):
    GCM = Gcm()
    ID_PROP_BREAKPOINT = wx.NewId()
    ID_PROP_BREAKPOINT_CLEAR = wx.NewId()
    def __init__(self, parent, num=None):
        pg.PropGrid.__init__(self, parent)

        # if num is not defined or is occupied, generate a new one
        if num is None or num in SimPropGrid.GCM.get_nums():
            num = SimPropGrid.GCM.get_next_num()
        self.num = num
        SimPropGrid.GCM.set_active(self)

        dp.connect(self.OnSimLoad, 'sim.loaded')
        dp.connect(self.OnSimUnload, 'sim.unloaded')
        dp.connect(self.OnSimUpdate, 'sim.update')

    def Destroy(self):
        dp.disconnect(self.simLoad, 'sim.loaded')
        dp.disconnect(self.simUnload, 'sim.unloaded')
        dp.disconnect(self.OnSimUpdate, 'sim.update')
        self.DeleteAllProperties()
        SimPropGrid.GCM.destroy_mgr(self)
        super(SimPropGrid, self).Destroy()

    def OnSimUpdate(self, objs):
        for name, v in six.iteritems(objs):
            p = self.GetProperty(name)
            if isinstance(p, list):
                for prop in p:
                    prop.SetValue(v)
            elif isinstance(p, pg.Property):
                p.SetValue(v)

    def OnSimLoad(self, num):
        """try reconnecting registers when the simulation is loaded."""
        objs = []
        s = str(num) + '.'
        objs = [n for n in six.iterkeys(self.PropDict) if name.startswith(s)]
        if objs:
            # tell the simulation to monitor signals
            resp = dp.send('sim.monitor_reg', objects=objs)
            if not resp:
                return
            status = resp[0][1]
            if status == False:
                return
            for obj in objs:
                # enable props that is monitored successfully
                if isinstance(status, dict) and not status.get(obj, False):
                    continue
                p = self.GetProperty(obj)
                if not p:
                    continue
                if isinstance(p, pg.Property):
                    p = [p]
                for prop in p:
                    prop.Italic(False)
                    prop.SetReadonly(False)
                    prop.Enable(True)

    def OnSimUnload(self, num):
        # disable all props from the simulation with id 'num'
        s = str(num) + '.'
        for p in self.PropList:
            name = p.GetName()
            if not name.startswith(s):
                continue
            p.Italic(True)
            p.SetReadonly(True)
            p.Enable(False)

    def GetContextMenu(self, prop):
        menu = super(SimPropGrid, self).GetContextMenu(prop)
        if not menu:
            menu = wx.Menu()
        else:
            menu.AppendSeparator()
        if prop:
            menu.Append(self.ID_PROP_BREAKPOINT, "Breakpoint Condition")
            menu.Enable(self.ID_PROP_BREAKPOINT, prop.IsChecked())
        menu.Append(self.ID_PROP_BREAKPOINT_CLEAR, "Clear all Breakpoints")
        return menu

    def OnPropEventsHandler(self, evt):
        if not super(SimPropGrid, self).OnPropEventsHandler(evt):
            return False

        prop = evt.GetProperty()
        eid = evt.GetEventType()
        if eid == pg.wxEVT_PROP_CLICK_CHECK:
            # turn on/off breakpoint
            if prop.IsChecked():
                dp.send('prop.bp_add', prop=prop)
            else:
                dp.send('prop.bp_del', prop=prop)
        elif eid == pg.wxEVT_PROP_CHANGED:
            # the value changed, notify the parent
            dp.send('prop.changed', prop=prop)

    def OnProcessCommand(self, eid, prop):
        """process the context menu command"""
        if eid == self.ID_PROP_BREAKPOINT:
            if not prop:
                return
            condition = prop.GetData()
            if condition is None:
                self.bp_condition = ('', '')
            dlg = BreakpointSettingsDlg(self, condition[0], condition[1])
            if dlg.ShowModal() == wx.ID_OK:
                prop.SetData(dlg.GetCondition())
        elif eid == self.ID_PROP_BREAKPOINT_CLEAR:
            self.ClearBreakPoints()
        else:
            super(SimPropGrid, self).OnProcessCommand(eid, prop)

    def ClearBreakPoints(self):
        """clear all the breakpoints"""
        for prop in self._props:
            if prop and prop.IsChecked():
                prop.SetChecked(False)

    def TriggerBreakPoint(self, name, cond, hitcount):
        """check whether the breakpoints are triggered"""
        for prop in self._props:
            if name == prop.GetName():
                if (cond, hitcount) == prop.GetData():
                    self.EnsureVisible(prop)
                    self.SelectProperty(prop)
                    return True



class BreakpointSettingsDlg(wx.Dialog):
    def __init__(self, parent, condition='', hitcount=''):
        wx.Dialog.__init__(self, parent, title="Breakpoint Condition",
                           size=wx.Size(431, 289),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        szAll = wx.BoxSizer(wx.VERTICAL)
        label = ("At the end of each delta cycle, the expression is evaluated "
                 "and the breakpoint is hit only if the expression is true or "
                 "the register value has changed")
        self.stInfo = wx.StaticText(self, label=label)
        self.stInfo.Wrap(400)
        szAll.Add(self.stInfo, 1, wx.ALL, 5)

        szCnd = wx.BoxSizer(wx.HORIZONTAL)

        szCond = wx.BoxSizer(wx.VERTICAL)

        self.rbChanged = wx.RadioButton(self, label="Has changed", style=wx.RB_GROUP)
        szCond.Add(self.rbChanged, 5, wx.ALL|wx.EXPAND, 5)

        label = "Is true (value: $; for example, $==10)"
        self.rbCond = wx.RadioButton(self, label=label)
        szCond.Add(self.rbCond, 0, wx.ALL|wx.EXPAND, 5)

        self.tcCond = wx.TextCtrl(self)
        szCond.Add(self.tcCond, 0, wx.ALL|wx.EXPAND, 5)

        label = "Hit count (hit count: #; for example, #>10"
        self.cbHitCount = wx.CheckBox(self, label=label)
        szCond.Add(self.cbHitCount, 0, wx.ALL, 5)

        self.tcHitCount = wx.TextCtrl(self)
        szCond.Add(self.tcHitCount, 0, wx.ALL|wx.EXPAND, 5)

        szCnd.Add(szCond, 1, wx.EXPAND, 5)

        szAll.Add(szCnd, 1, wx.EXPAND, 5)

        self.stLine = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        szAll.Add(self.stLine, 0, wx.EXPAND |wx.ALL, 5)

        szConfirm = wx.BoxSizer(wx.HORIZONTAL)

        self.btnOK = wx.Button(self, wx.ID_OK, u"OK")
        szConfirm.Add(self.btnOK, 0, wx.ALL, 5)

        self.btnCancel = wx.Button(self, wx.ID_CANCEL, u"Cancel")
        szConfirm.Add(self.btnCancel, 0, wx.ALL, 5)

        szAll.Add(szConfirm, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(szAll)
        self.Layout()

        # initialize the controls
        self.condition = condition
        self.hitcount = hitcount
        if self.condition == '':
            self.rbChanged.SetValue(True)
            self.tcCond.Disable()
        else:
            self.rbChanged.SetValue(False)
            self.rbCond.SetValue(True)
        self.tcCond.SetValue(self.condition)
        if self.hitcount == '':
            self.cbHitCount.SetValue(False)
            self.tcHitCount.Disable()
        else:
            self.cbHitCount.SetValue(True)
        self.tcHitCount.SetValue(self.hitcount)
        # Connect Events
        self.rbChanged.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.rbCond.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.cbHitCount.Bind(wx.EVT_CHECKBOX, self.OnRadioButton)
        self.btnOK.Bind(wx.EVT_BUTTON, self.OnBtnOK)

    def OnRadioButton(self, event):
        if self.rbChanged.GetValue():
            self.tcCond.Disable()
        else:
            self.tcCond.Enable()
        if self.cbHitCount.GetValue():
            self.tcHitCount.Enable()
        else:
            self.tcHitCount.Disable()
        event.Skip()
    def OnBtnOK(self, event):
        # set condition to empty string to indicate the breakpoint will be
        # triggered when the value is changed
        if self.rbChanged.GetValue():
            self.condition = ''
        else:
            self.condition = self.tcCond.GetValue()
        if self.cbHitCount.GetValue():
            self.hitcount = self.tcHitCount.GetValue()
        else:
            self.hitcount = ""
        event.Skip()

    def GetCondition(self):
        return (self.condition, self.hitcount)

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
            cnd = prop.GetData()
            if cnd is None:
                cnd = ("", "")
            mgr.add_breakpoint(name, cnd[0], cnd[1])

    @classmethod
    def _prop_bp_del(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            cnd = prop.GetData()
            if cnd is None:
                cnd = ("", "")
            mgr.del_breakpoint(name, cnd[0], cnd[1])

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
        if pane and isinstance(pane, SimPropGrid):
            SimPropGrid.GCM.set_active(pane)

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
        mgr = SimPropGrid.GCM.get_manager(num)
        if not mgr and create:
            mgr = SimPropGrid(cls.frame)
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

        dy = sy.read_buf(y, block=True)
        y = {sy.global_object_name(y):dy}
        if sx:
            dx = sx.read_buf(x, block=True)
            x = {sx.global_object_name(x):dx}
        mgr = graph.plt.get_current_fig_manager()
        autorelim = kwargs.pop("relim", True)
        mgr.plot_trace(x, y, autorelim, *args, **kwargs)

def bsm_initialize(frame, **kwargs):
    sim.initialize(frame)
