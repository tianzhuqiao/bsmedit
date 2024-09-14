import os
import re
import json
import multiprocessing as mp
import time
import traceback
import sys
import six.moves.queue as Queue
import six
import wx
import wx.py.dispatcher as dp
import aui2 as aui
import propgrid as pg
from bsmutility.pymgr_helpers import Gcm
from bsmutility.autocomplete import AutocompleteTextCtrl
from bsmutility.utility import MakeBitmap, FastLoadTreeCtrl
from bsmutility.utility import svg_to_bitmap
from bsmutility.utility import get_file_finder_name, show_file_in_finder
from bsmutility.bsmxpm import module_svg, signal_svg, input_svg, output_svg, inout_svg,\
                    step_svg, step_grey_svg, run_svg, run_grey_svg, \
                    pause_svg, pause_grey_svg, setting_svg, radio_disabled_svg, \
                    radio_activated_svg, radio_checked_svg, radio_unchecked_svg
from . import graph
from .simprocess import sim_process, SC_OBJ_UNKNOWN, SC_OBJ_SIGNAL, SC_OBJ_INPUT,\
                        SC_OBJ_OUTPUT, SC_OBJ_INOUT, SC_OBJ_CLOCK, SC_OBJ_XSC_PROP,\
                        SC_OBJ_XSC_ARRAY_ITEM, SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY
from .. import to_byte

Gcs = Gcm()


class Simulation():
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
        self.status = {'running': False, 'valid': False}
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
            v = self.write({obj: value})
            print(v)
        elif isinstance(obj, (list, tuple)):
            v = self.write(dict(zip(obj, value)))
            print(v)
        else:
            raise ValueError()

    def _send_command(self, cmd, **kwargs):
        """
        send the command to the simulation process

        don't call this function directly unless you know what it is doing.
        """
        try:
            if not self.sim_process or not self.sim_process.is_alive():
                print("The simulation has not started or is not alive!")
                return False
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

            self.qcmd.put({'id': cid, 'cmd': cmd, 'arguments': kwargs})
            if block is True:
                # wait for the command to finish
                while self.sim_process.is_alive():
                    try:
                        resp = self.qresp.get(timeout=0.3)
                    except Queue.Empty:
                        continue
                    rtn = self._process_response(resp)
                    if resp.get('id', -1) == cid:
                        return rtn
            return self.sim_process.is_alive()
        except:
            traceback.print_exc(file=sys.stdout)

        return False

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
            if start > 0 and time.time() - start > timeout:
                return False
        return False

    def start(self):
        """create an empty simulation"""
        self.stop()
        self.qresp = mp.Queue()
        self.qcmd = mp.Queue()
        self.sim_process = mp.Process(target=sim_process,
                                      args=(self.qresp, self.qcmd, sim.debug))
        self.sim_process.start()
        self._interfaces = self._send_command('get_interfaces')
        if self._interfaces:
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
                    arg = arg[:arg.find('=')].strip()
                    arg = f"{arg}={arg}"
                formatted_args2.append(arg)
            fndef = 'lambda %s: wrapper("%s", %s)' % (
                formatted_args, item, ','.join(formatted_args2))
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
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            dlg = wx.FileDialog(self.frame, "Choose a file", "", "", "*.*",
                                style)
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
        self.set_parameter(to=to, more=more, block=False)
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
        self._process_response({'cmd': 'exit'})

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
            return f"{self.num}.{obj}"
        return None

    def monitor(self, objects, grid=None, index=-1, style='Text', **kwargs):
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
                print("invalid object: ", name)
                continue
            if obj['kind'] == 'sc_module':
                prop = PropSim('Separator', label=obj['basename'], **kwargs)
                prop.Name(self.global_object_name(obj['name']))
                # call insert after set the name as "Insert" will trigger
                # the monitor_signal command
                prop = grid.Insert(prop, index)
            else:
                prop = PropSim(style, label=obj['basename'], **kwargs)
                prop.Name(self.global_object_name(obj['name'])).Value(obj['value'])
                prop.SetGripperColor(self.frame.GetColor())
                prop = grid.Insert(prop, index)
                if not obj['writable']:
                    prop.Editing(False)
                prop.SetShowCheck(obj['readable'])
                # set value invalid since obj['value'] may have garbage value
                # (not read the actual value from simulation yet.);
                # will set it to true once the value is updated.
                prop.SetValueValid(False)
            props.append(prop)
            if index != -1:
                index += 1
        if len(props) == 1:
            return props[0]
        return props

    def _process_response(self, resp):
        """process the response from the simulation core"""
        try:
            wx.CallAfter(dp.send,
                         signal='sim.response',
                         sender=self,
                         resp=resp)
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
                running = self.status['running']
                if running and not value.get('running', running):
                    # if the queues are almost empty, retrieve the data
                    self.time_stamp(insecond=False, block=False)
                    self.read(objects=[], block=False)
                    self.read_buf([], block=False)
                self.status.update(value)
            return value
        except:
            traceback.print_exc(file=sys.stdout)

        return None

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
        for svg in [
                module_svg, signal_svg, input_svg, output_svg, inout_svg,
        ]:
            imglist.Add(svg_to_bitmap(svg, size=(16, 16), win=self))
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
                child = {'label': obj['basename']}
                nkind = obj['nkind']
                img = [-1, -1]
                if nkind == SC_OBJ_MODULE:
                    img = [0, 0]
                elif nkind in [
                        SC_OBJ_SIGNAL, SC_OBJ_CLOCK, SC_OBJ_XSC_PROP,
                        SC_OBJ_XSC_ARRAY, SC_OBJ_XSC_ARRAY_ITEM
                ]:
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
            type1 = obj1['nkind']# in [SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY]
            type2 = obj2['nkind']# in [SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY]
            order = [SC_OBJ_MODULE, SC_OBJ_XSC_ARRAY, SC_OBJ_CLOCK, SC_OBJ_INPUT,
                     SC_OBJ_INOUT, SC_OBJ_OUTPUT, SC_OBJ_SIGNAL, SC_OBJ_XSC_PROP,
                     SC_OBJ_XSC_ARRAY_ITEM, SC_OBJ_UNKNOWN]
            type1_order = len(order)
            type2_order = len(order)
            if type1 in order:
                type1_order = order.index(type1)
            if type2 in order:
                type2_order = order.index(type2)

            if type1_order == type2_order and obj1['name'] == obj2['name']:
                return 0
            if type1_order == type2_order:
                return 1 if obj1['name'] > obj2['name'] else -1

            return 1 if type1_order > type2_order else -1

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
            szFile.Add(self.tcFile, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            self.btnSelectFile = wx.Button(sbox, label="...", size=(25, -1))
            szFile.Add(self.btnSelectFile, 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            szAll.Add(szFile, 0, wx.ALL | wx.EXPAND, 5)

        sbox = wx.StaticBox(self, wx.ID_ANY, "&Signal")
        szSignal = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        self.tcSignal = AutocompleteTextCtrl(sbox,
                                             value=active,
                                             completer=self.Completer)
        szSignal.Add(self.tcSignal, 0, wx.ALL | wx.EXPAND, 5)
        self.cbTrigger = wx.CheckBox(sbox, label="Use Trigger Signal")
        szSignal.Add(self.cbTrigger, 0, wx.ALL, 5)
        self.tcValid = AutocompleteTextCtrl(sbox, completer=self.Completer)
        szSignal.Add(self.tcValid, 0, wx.ALL | wx.EXPAND, 5)
        rbTriggerChoices = ["&Pos Edge", "&Neg Edge", "Both Edge"]
        self.rbTrigger = wx.RadioBox(sbox,
                                     label="Trigger",
                                     choices=rbTriggerChoices)
        self.rbTrigger.SetSelection(2)
        szSignal.Add(self.rbTrigger, 0, wx.ALL | wx.EXPAND, 5)
        szAll.Add(szSignal, 1, wx.ALL | wx.EXPAND, 5)

        if self.traceFile:
            rbFormatChoices = [u"&VCD", u"&BSM"]
            self.rbFormat = wx.RadioBox(self,
                                        label="&Format",
                                        choices=rbFormatChoices)
            self.rbFormat.SetSelection(1)
            szAll.Add(self.rbFormat, 0, wx.ALL | wx.EXPAND, 5)
        else:
            szSize = wx.BoxSizer(wx.HORIZONTAL)
            szSize.Add(wx.StaticText(self, wx.ID_ANY, "Size"), 0, wx.ALL, 5)
            self.spinSize = wx.SpinCtrl(self,
                                        style=wx.SP_ARROW_KEYS,
                                        min=1,
                                        max=2**31 - 1,
                                        initial=256)
            szSize.Add(self.spinSize, 1, wx.EXPAND | wx.ALL, 5)
            szAll.Add(szSize, 0, wx.ALL | wx.EXPAND, 5)

        self.m_staticline1 = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        szAll.Add(self.m_staticline1, 0, wx.EXPAND | wx.ALL, 5)

        btnsizer = wx.StdDialogButtonSizer()

        self.btnOK = wx.Button(self, wx.ID_OK)
        self.btnOK.SetDefault()
        btnsizer.AddButton(self.btnOK)

        self.btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(self.btnCancel)
        btnsizer.Realize()

        szAll.Add(btnsizer, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

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
            root = query[0:query.rfind('.') + 1]
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
        return objs, objs, len(query) - len(root)

    def OnBtnSelectFile(self, event):
        wildcard = "BSM Files (*.bsm)|*.bsm|All Files (*.*)|*.*"
        dlg = wx.FileDialog(self,
                            "Select BSM dump file",
                            '',
                            '',
                            wildcard,
                            style=wx.FD_OPEN)
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

class DumpManageDlg(wx.Dialog):
    ID_MP_DUMP_STOP = wx.NewIdRef()
    def __init__(self, sim, parent, id=-1, title='Manage dump files',
                 size=wx.DefaultSize, pos=wx.DefaultPosition,
                 style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER):
        wx.Dialog.__init__(self)
        self.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        self.Create(parent, id, title, pos, size, style)

        self.propgrid = pg.PropGrid(self)
        g = self.propgrid
        g.Draggable(False)
        g.Configurable(False)
        self.sim = sim

        dumps = sim.get_trace_files()
        for f, opt in dumps.items():
            g.Insert(pg.PropSeparator(f)).Expand(False)
            for o in opt:
                desc = self.GetDumpDescription(o)
                g.Insert(pg.PropText(desc[0][1])).Value(desc[0][1]).Editing(False).Indent(1)
                for name, value in desc[1:]:
                    g.Insert(pg.PropText(name)).Value(value).Editing(False).Indent(2)

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(g, 1, wx.EXPAND|wx.ALL, 1)

        # ok/cancel button
        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.AddStretchSpacer(1)

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALL|wx.EXPAND, 5)

        self.SetSizer(sizer)

        g.Bind(pg.EVT_PROP_RIGHT_CLICK, self.OnPropEventsHandler)

    def OnPropEventsHandler(self, event):
        prop = event.GetProp()
        if isinstance(prop, pg.PropSeparator):
            menu = wx.Menu()
            menu.Append(self.ID_MP_DUMP_STOP, 'Stop dumpping file')
            cmd = self.GetPopupMenuSelectionFromUser(menu)
            if cmd == wx.ID_NONE:
                return

            if cmd == self.ID_MP_DUMP_STOP:
                filename = prop.GetLabel()
                msg = f"Do you want to stop dumping {filename}?"
                dlg = wx.MessageDialog(self, msg, 'bsmedit', wx.YES_NO)
                result = dlg.ShowModal() == wx.ID_YES
                dlg.Destroy()
                if result:
                    if self.sim.close_trace_file(filename):
                        prop.SetEnable(False)

    def GetDumpDescription(self, dump):
        formats = {0: 'VCD', 1:'BSM'}
        edge = {0:"pos edge", 1: "neg edge", 2:"both edge"}
        trigger = dump[3]
        if trigger is None:
            trigger = ''
        info = [['signal', dump[1]],
                ['trigger', f'{trigger} @ {edge.get(dump[4], "unknown edge")}'],
                ['format', formats.get(dump[2], 'unknown')]
                ]
        return info

class SimPanel(wx.Panel):
    ID_SIM_STEP = wx.NewIdRef()
    ID_SIM_RUN = wx.NewIdRef()
    ID_SIM_PAUSE = wx.NewIdRef()
    ID_SIM_SET = wx.NewIdRef()
    ID_MP_DUMP = wx.NewIdRef()
    ID_MP_TRACE_BUF = wx.NewIdRef()
    ID_MP_ADD_TO_NEW_VIEWER = wx.NewIdRef()
    ID_MP_ADD_TO_VIEWER_START = wx.NewIdRef()
    ID_MP_DUMP_MANAGE = wx.NewIdRef()

    def __init__(self, parent, num=None, filename=None, silent=False):
        wx.Panel.__init__(self, parent)

        self.is_destroying = False
        self._color = wx.Colour(178, 34, 34)
        self.tb = aui.AuiToolBar(self, -1, agwStyle=aui.AUI_TB_OVERFLOW)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))
        self.tb.AddTool(self.ID_SIM_STEP, "Step", svg_to_bitmap(step_svg, win=self),
                        svg_to_bitmap(step_grey_svg, win=self), wx.ITEM_NORMAL,
                        "Step the simulation")
        self.tb.AddTool(self.ID_SIM_RUN, "Run", svg_to_bitmap(run_svg, win=self),
                        svg_to_bitmap(run_grey_svg, win=self), wx.ITEM_NORMAL,
                        "Run the simulation")
        self.tb.AddTool(self.ID_SIM_PAUSE, "Pause", svg_to_bitmap(pause_svg, win=self),
                        svg_to_bitmap(pause_grey_svg, win=self), wx.ITEM_NORMAL,
                        "Pause the simulation")

        self.tb.AddSeparator()

        self.tcStep = wx.SpinCtrlDouble(self.tb,
                                        value='1000',
                                        size=(150, -1),
                                        min=0,
                                        max=1e9,
                                        inc=1)
        self.tcStep.SetDigits(4)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Step "))
        self.tb.AddControl(self.tcStep)
        units = ['fs', 'ps', 'ns', 'us', 'ms', 's']
        self.cmbUnitStep = wx.Choice(self.tb,
                                     wx.ID_ANY,
                                     size=(50, -1),
                                     choices=units)
        self.cmbUnitStep.SetSelection(2)
        self.tb.AddControl(self.cmbUnitStep)
        self.tb.AddSeparator()

        self.tcTotal = wx.SpinCtrlDouble(self.tb,
                                         value='-1',
                                         size=(150, -1),
                                         min=-1,
                                         max=1e9,
                                         inc=1)
        self.tcTotal.SetDigits(4)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Total "))
        self.tb.AddControl(self.tcTotal)
        self.cmbUnitTotal = wx.Choice(self.tb,
                                      wx.ID_ANY,
                                      size=(50, -1),
                                      choices=units)
        self.cmbUnitTotal.SetSelection(2)
        self.tb.AddControl(self.cmbUnitTotal)
        self.tb.AddStretchSpacer()
        self.tb.AddSimpleTool(self.ID_SIM_SET, "Setting", svg_to_bitmap(setting_svg, win=self),
                              "Configure the simulation")

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
        # simulation
        self.sim = Simulation(self, num)
        if filename is not None or not silent:
            self.sim.load(filename, block=True)
            self.SetParameter()

        self.filename = filename or ""

        dp.connect(receiver=self._process_response,
                   signal='sim.response',
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

    def Destroy(self):
        """
        Destroy the simulation properly before close the pane.
        """
        dp.disconnect(receiver=self._process_response,
                      signal='sim.response',
                      sender=self.sim)
        self.timer.Stop()
        self.is_destroying = True
        self.sim.release()
        self.sim = None
        super().Destroy()

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
        step = "%f%s" % (step, unitStep)
        total = self.tcTotal.GetValue()
        unitTotal = self.cmbUnitTotal.GetString(
            self.cmbUnitTotal.GetSelection())
        total = f"%f%s" % (total, unitTotal)
        self.sim.set_parameter(step=step, total=total, block=block)

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
        menu.Append(self.ID_MP_DUMP, "&Dump to file")
        menu.AppendSeparator()
        menu.Append(self.ID_MP_TRACE_BUF, "&Trace to buffer")
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
        cmd = self.GetPopupMenuSelectionFromUser(menu)
        if cmd == wx.ID_NONE:
            return
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
                    self.sim.trace_file(name=t['signal'],
                                        filename=t['filename'],
                                        fmt=t['format'],
                                        valid=t['valid'],
                                        trigger=t['trigger'],
                                        block=False)
                else:
                    self.sim.trace_buf(name=t['signal'],
                                       size=t['size'],
                                       valid=t['valid'],
                                       trigger=t['trigger'],
                                       block=False)
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
                objs.append({'reg': gname(ext['name']), 'child': objchild})
            else:
                objs.append({'reg': gname(ext['name'])})
            objs_name.append(ext['name'])
        # need to explicitly allow drag
        # start drag operation
        data = wx.TextDataObject(json.dumps(objs))
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

    def _exit_sim(self):
        msg = f'Do you want to kill {self.GetLabel()}?'
        # use top level frame as parent, otherwise it may crash when
        # it is called in Destroy()
        dlg = wx.MessageDialog(self.GetTopLevelParent(), msg, 'bsmedit', wx.YES_NO)
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        if result:
            self.sim.stop()
            wx.CallAfter(dp.send, signal='frame.delete_panel', panel=self)

    def OnProcessCommand(self, event):
        """process the menu command"""
        eid = event.GetId()
        if eid == wx.ID_EXIT:
            # delay destroy the simulation window so AuiToolBar can finish
            # processing the dropdown event.
            wx.CallAfter(self._exit_sim)
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
        elif eid == self.ID_MP_DUMP_MANAGE:
            dlg = DumpManageDlg(self.sim, self, size=(600, 480))
            # this does not return until the dialog is closed.
            val = dlg.ShowModal()
        elif eid == self.ID_SIM_SET:
            menu = wx.Menu()
            item = menu.Append(self.ID_MP_DUMP_MANAGE, "&Manage dump files")
            if not self.sim.is_valid() or not self.sim.get_trace_files():
                item.Enable(False)
            menu.AppendSeparator()
            menu.Append(wx.ID_RESET, "&Reset")
            menu.AppendSeparator()
            menu.Append(wx.ID_EXIT, "&Exit")

            self.PopupMenu(menu)

    def _process_response(self, resp):
        if self.is_destroying:
            return
        try:
            command = resp.get('cmd', '')
            value = resp.get('value', False)
            if command == 'load':
                self.tree.Load(self.sim.objects)
                dp.send('sim.loaded', num=self.sim.num)
            elif command == 'exit':
                self.tree.Load(None)
                dp.send('sim.unloaded', num=self.sim.num)
                if Gcs.get_active() == self.sim:
                    dp.send(signal="frame.show_status_text", text="")
            elif command == 'monitor_signal':
                objs = [name for name, v in six.iteritems(value) if v]
                self.sim.read(objects=objs, block=False)
            elif command == 'set_parameter':
                if value:
                    step = self.tcStep.GetValue()
                    self.tcStep.SetValue(value.get('step', step))
                    unitStep = self.cmbUnitStep.GetSelection()
                    self.cmbUnitStep.SetSelection(
                        value.get('step_unit', unitStep))
                    total = self.tcTotal.GetValue()
                    self.tcTotal.SetValue(value.get('total', total))
                    unitTotal = self.cmbUnitTotal.GetSelection()
                    self.cmbUnitTotal.SetSelection(
                        value.get('total_unit', unitTotal))
            elif command == 'read':
                gname = self.sim.global_object_name
                ui_objs = {gname(name): v for name, v in six.iteritems(value)}
                dp.send(signal="sim.update", objs=ui_objs)
            elif command == 'read_buf':
                gname = self.sim.global_object_name
                ui_buffers = {
                    gname(name): v
                    for name, v in six.iteritems(value)
                }
                dp.send(signal="sim.buffer_changed", bufs=ui_buffers)
            elif command == 'time_stamp':
                if isinstance(value, six.string_types):
                    dp.send(signal="frame.show_status_text", text=value)
            elif command == 'breakpoint_triggered':
                SimPropGrid.ClearAllTrigger()
                bp = value  #[name, condition, hitcount, hitsofar]
                gname = self.sim.global_object_name
                for grid in SimPropGrid.GCM.get_all_managers():
                    if grid.TriggerBreakPoint(gname(bp[0]), bp[1], bp[2]):
                        dp.send(signal='frame.show_panel', panel=grid)
                        break
                else:
                    txt = f"Breakpoint triggered: {json.dumps(bp)}\n"
                    dp.send(signal='shell.write_out', text=txt)
            elif command == 'write_out':
                dp.send(signal='shell.write_out', text=value)

            if command in ['load', 'step'] and value:
                self.sim.time_stamp(insecond=False, block=False)
                self.sim.read(objects=[], block=False)
                self.sim.read_buf(objects=[], block=False)
        except:
            traceback.print_exc(file=sys.stdout)


wxEVT_PROP_CLICK_CHECK = wx.NewEventType()
EVT_PROP_CLICK_CHECK = wx.PyEventBinder(wxEVT_PROP_CLICK_CHECK, 1)


class PropSim(pg.PropBase):
    def __init__(self, style='Text', *args, **kwargs):
        self.prop = None
        self.SetControlStyle(style, *args, **kwargs)

    def all_subclasses(self):
        def _sub_classes(cls):
            return set(cls.__subclasses__()).union(
                    [s for c in cls.__subclasses__() for s in _sub_classes(c)])
        sub =  _sub_classes(pg.PropBase)
        return {s.__name__.lower(): s for s in sub if sub != PropSim}

    def __getattr__(self, name):
        return getattr(self.prop, name)

    def SetControlStyle(self, style, *args, **kwargs):
        sub = self.all_subclasses()
        style = style.lower()
        cls = sub.get(style, None)
        if cls is None:
            cls = sub.get(f'Prop{style}'.lower(), None)
        if cls is None:
            return False

        if isinstance(self.prop, cls):
            return True
        prop = cls(*args, **kwargs)
        if self.prop:
            prop.copy(self.prop)
        self.prop = prop
        if self.GetGrid():
            self.GetGrid().UpdateGrid()
        return True

    def duplicate(self):
        p = PropSim()
        if self.prop:
            p.prop = self.prop.duplicate()
        return p

def PropGenericUdpate():
    pg.PropGeneric.gripper_clr = wx.RED
    pg.PropGeneric.show_check = True
    pg.PropGeneric.checked = False
    pg.PropGeneric.condition = ("", "")
    pg.PropGeneric.triggered = False
    def SetGripperColor(self, clr=None):
        self.gripper_clr = clr
    pg.PropGeneric.SetGripperColor = SetGripperColor

    def GetGripperColor(self):
        return self.gripper_clr
    pg.PropGeneric.GetGripperColor = GetGripperColor

    def SetShowCheck(self, show=True, silent=True):
        """show/hide radio button"""
        if self.show_check == show:
            return
        self.show_check = show
        if not silent:
            self.Refresh()
    pg.PropGeneric.SetShowCheck = SetShowCheck

    def IsShowCheck(self):
        """return whether the icon is shown"""
        return self.show_check
    pg.PropGeneric.IsShowCheck = IsShowCheck

    def SetChecked(self, check=True, silent=False):
        """check/uncheck the radio button"""
        if check != self.IsChecked():
            self.checked = check
            if not self.SendPropEvent(wxEVT_PROP_CLICK_CHECK):
                self.checked = not check
            if not silent:
                self.Refresh()

    pg.PropGeneric.SetChecked = SetChecked

    def IsChecked(self):
        """return true if the radio button is checked"""
        return self.checked

    pg.PropGeneric.IsChecked = IsChecked

    def OnMouseUp(self, pt):
        ht = self.HitTest(pt)
        if self.IsEnabled():
            # click on the check icon? change the state
            if self.IsShowCheck() and ht == 'check':
                checked = self.IsChecked()
                self.SetChecked(not checked)
        return ht
    pg.PropGeneric.OnMouseUp = OnMouseUp

    def SetBpCondition(self, cond, hitcount):
        self.condition = (cond, hitcount)
    pg.PropGeneric.SetBpCondition = SetBpCondition

    def GetBpCondition(self):
        return self.condition
    pg.PropGeneric.GetBpCondition = GetBpCondition

    def SetTriggered(self, triggered):
        self.triggered = triggered
    pg.PropGeneric.SetTriggered = SetTriggered

    def IsTriggered(self):
        return self.triggered
    pg.PropGeneric.IsTriggered = IsTriggered

    pg.PropGeneric._copy_orig = pg.PropGeneric.copy
    def copy(self, prop):
        self._copy_orig(prop)
        self.gripper_clr = prop.gripper_clr
        self.show_check = prop.show_check
        self.checked = prop.checked
        self.condition = prop.condition
        self.triggered = prop.triggered

    pg.PropGeneric.copy = copy

class SimPropArt(pg.PropArtNative):
    def __init__(self, win=None):
        super().__init__()
        self.gripper_width = 6
        if wx.Platform == '__WXMSW__':
            self.img_expand = wx.ImageList(12, 12, True, 2)
            self.img_expand.Add(wx.Bitmap(to_byte(pg.tree_xpm)))
            self.expansion_width = 12
        self.check_width = 16
        size = (16, 16)
        self.img_check = wx.ImageList(size[0], size[1], True, 4)
        self.img_check.Add(svg_to_bitmap(radio_unchecked_svg, size=size, win=win))
        self.img_check.Add(svg_to_bitmap(radio_disabled_svg, size=size, win=win))
        self.img_check.Add(svg_to_bitmap(radio_checked_svg, size=size, win=win))
        self.img_check.Add(svg_to_bitmap(radio_activated_svg, size=size, win=win))

    def PrepareDrawRect(self, p):
        """calculate the rect for each section"""
        mx = self.gap_x
        irc = p.GetRect()
        irc.SetLeft(irc.GetLeft() + self.margin['left'])
        irc.SetRight(irc.GetRight() + self.margin['right'])
        irc.SetTop(irc.GetTop() + self.margin['top'])
        irc.SetBottom(irc.GetBottom() + self.margin['bottom'])
        x = irc.x
        x = x + mx * 2 + p.indent * self.indent_width
        # gripper
        rc = wx.Rect(*irc)
        rc.x += self.gap_x
        rc.SetWidth(self.gripper_width)
        p.regions['gripper'] = rc

        if self.expansion_width > 0 and p.HasChildren():
            # expander icon
            rc = wx.Rect(*irc)
            rc.x = x + mx * 2
            rc.SetWidth(self.expansion_width)
            p.regions['expander'] = rc
            x = rc.right

        if self.check_width > 0 and p.IsShowCheck():
            # radio/check icon
            rc = wx.Rect(*irc)
            rc.x = x + mx
            rc.SetWidth(self.check_width + 2)
            p.regions['check'] = rc
            x = rc.right

        # label
        p.regions['label'] = wx.Rect(*irc)
        p.regions['label'].x = x + mx * 2

        if not p.IsSeparator():
            title_width = p.title_width
            if title_width < 0:
                title_width = self.title_width
            p.regions['label'].SetRight(title_width)
            x = p.regions['label'].right

            rc = wx.Rect(*irc)
            rc.x = x + mx
            rc.SetWidth(self.splitter_width)
            p.regions['splitter'] = rc
            x = rc.right

            rc = wx.Rect(*irc)
            rc.x = x
            rc.SetWidth(irc.right - x)
            p.regions['value'] = rc
        else:
            # separator does not have splitter & value
            p.regions['label'].SetWidth(p.regions['label'].GetWidth() +
                                        irc.right - x)
            p.regions['splitter'] = wx.Rect(irc.right, irc.top, 0, 0)
            p.regions['value'] = wx.Rect(irc.right, irc.top, 0, 0)

    def DrawGripper(self, dc, p):
        # draw gripper
        if p.gripper_clr:
            pen = wx.Pen(wx.BLACK, 1, wx.PENSTYLE_TRANSPARENT)
            dc.SetPen(pen)

            dc.SetBrush(wx.Brush(p.gripper_clr))
            rc = p.regions['gripper']
            dc.DrawRectangle(rc.x, rc.y + 1, 3, rc.height - 1)

    def DrawCheckNative(self, dc, p):
        # draw radio button
        if self.check_width > 0 and p.IsShowCheck():
            render = wx.RendererNative.Get()
            state = 0
            if not p.IsEnabled():
                state |= wx.CONTROL_DISABLED
            if p.IsChecked():
                state |= wx.CONTROL_CHECKED
            if p.IsActivated():
                state |= wx.CONTROL_FOCUSED

            w, h = self.check_width, self.check_width
            rc = p.regions['check']
            x = rc.x + (rc.width - w) // 2
            y = rc.y + (rc.height - h) // 2 + 1
            render.DrawRadioBitmap(p.grid, dc, (x, y, w, h), state)

    def DrawCheck(self, dc, p):
        if self.check_width > 0 and p.IsShowCheck():
            state = 0
            if not p.IsEnabled():
                state = 1
            elif p.IsChecked():
                state = 2
                if p.IsTriggered():
                    state = 3

            if self.img_check.GetImageCount() == 4:
                (w, h) = self.img_check.GetSize(0)
                rc = p.regions['check']
                x = rc.x + (rc.width - w) // 2
                y = rc.y + (rc.height - h) // 2 + 1
                self.img_check.Draw(state, dc, x, y,
                                    wx.IMAGELIST_DRAW_TRANSPARENT)
            else:
                self.DrawCheckNative(dc, p)

    def DrawExpansion(self, dc, p):
        if p.HasChildren():
            if hasattr(self, 'img_expand') and self.img_expand.GetImageCount() == 2:
                (w, h) = self.img_expand.GetSize(0)
                rc = p.regions['expander']
                x = rc.x + (rc.width - w) // 2
                y = rc.y + (rc.height - h) // 2 + 1
                idx = 0
                if not p.IsExpanded():
                    idx = 1
                self.img_expand.Draw(idx, dc, x, y,
                                     wx.IMAGELIST_DRAW_TRANSPARENT)
            else:
                super().DrawExpansion(dc, p)

    def DrawItem(self, dc, p):
        super().DrawItem(dc, p)
        self.DrawGripper(dc, p)
        self.DrawCheck(dc, p)


class SimPropGrid(pg.PropGrid):
    GCM = Gcm()
    ID_PROP_BREAKPOINT = wx.NewIdRef()
    ID_PROP_BREAKPOINT_CLEAR = wx.NewIdRef()

    def __init__(self, parent, num=None):
        pg.PropGrid.__init__(self, parent)

        # if num is not defined or is occupied, generate a new one
        if num is None or num in SimPropGrid.GCM.get_nums():
            num = SimPropGrid.GCM.get_next_num()
        self.num = num
        SimPropGrid.GCM.set_active(self)
        self.SetArtProvider(SimPropArt(self))
        self.Bind(EVT_PROP_CLICK_CHECK, self.OnPropEventsHandler)

        dp.connect(self.OnSimLoad, 'sim.loaded')
        dp.connect(self.OnSimUnload, 'sim.unloaded')
        dp.connect(self.OnSimUpdate, 'sim.update')

    def Destroy(self):
        dp.disconnect(self.OnSimLoad, 'sim.loaded')
        dp.disconnect(self.OnSimUnload, 'sim.unloaded')
        dp.disconnect(self.OnSimUpdate, 'sim.update')
        self.DeleteAll()
        SimPropGrid.GCM.destroy_mgr(self)
        super().Destroy()

    def OnSimUpdate(self, objs):
        for name, v in six.iteritems(objs):
            p = self.Get(name)
            if isinstance(p, list):
                for prop in p:
                    prop.SetValue(v)
                    prop.SetValueValid(True)
            elif isinstance(p, pg.PropBase):
                p.SetValue(v)
                p.SetValueValid(True)

    def OnSimLoad(self, num):
        """try reconnecting registers when the simulation is loaded."""
        s = str(num) + '.'
        sl = len(s)
        objs = []
        for p in self._props:
            name = p.GetName()
            if name.startswith(s):
                objs.append(name[sl:])
        if objs:
            # tell the simulation to monitor signals
            resp = dp.send('sim.command',
                           num=num,
                           command='monitor_signal',
                           objects=objs)
            if not resp:
                return
            status = resp[0][1]
            if status is False:
                return
            for obj in objs:
                # enable props that is monitored successfully
                if isinstance(status, dict) and not status.get(obj, False):
                    continue
                p = self.Get(s + obj)
                if not p:
                    continue
                if isinstance(p, pg.PropBase):
                    p = [p]
                for prop in p:
                    prop.SetReadonly(False)
                    prop.Enable(True)

    def OnSimUnload(self, num):
        # disable all props from the simulation with id 'num'
        s = str(num) + '.'
        for p in self._props:
            name = p.GetName()
            if not name.startswith(s):
                continue
            p.SetReadonly(True)
            p.Enable(False)

    def GetContextMenu(self, prop):
        menu = super().GetContextMenu(prop)
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
        if not super().OnPropEventsHandler(evt):
            return False

        prop = evt.GetProp()
        eid = evt.GetEventType()
        if eid == wxEVT_PROP_CLICK_CHECK:
            # turn on/off breakpoint
            if prop.IsChecked():
                dp.send('prop.bp_add', prop=prop)
            else:
                dp.send('prop.bp_del', prop=prop)
        elif eid == pg.wxEVT_PROP_CHANGED:
            # the value changed, notify the parent
            dp.send('prop.changed', prop=prop)
        return True

    def OnProcessCommand(self, eid, prop):
        """process the context menu command"""
        if eid == self.ID_PROP_BREAKPOINT:
            if not prop:
                return
            condition = prop.GetBpCondition()
            dlg = BreakpointSettingsDlg(self, condition[0], condition[1])
            if dlg.ShowModal() == wx.ID_OK:
                if prop.IsChecked():
                    # delete current breakpoint
                    prop.SetChecked(False)
                    prop.SetBpCondition(*dlg.GetCondition())
                    # add breakpoint to make the condition valid
                    prop.SetChecked(True)
                else:
                    prop.SetBpCondition(*dlg.GetCondition())

        elif eid == self.ID_PROP_BREAKPOINT_CLEAR:
            self.ClearBreakPoints()
        else:
            super().OnProcessCommand(eid, prop)

    def ClearBreakPoints(self):
        """clear all the breakpoints"""
        for prop in self._props:
            if prop and prop.IsChecked():
                prop.SetChecked(False)
    @classmethod
    def ClearAllTrigger(cls):
        for grid in SimPropGrid.GCM.get_all_managers():
            grid.ClearTrigger()

    def ClearTrigger(self):
        for prop in self._props:
            prop.SetTriggered(False)

    def TriggerBreakPoint(self, name, cond, hitcount):
        """check whether the breakpoints are triggered"""
        for prop in self._props:
            if prop.IsChecked() and name == prop.GetName():
                if (cond, hitcount) == prop.GetBpCondition():
                    prop.SetTriggered(True)
                    self.EnsureVisible(prop)
                    self.SetSelection(prop)
                    return True
        return False

    def Index(self, prop):
        """return the index of prop, or -1 if not found"""
        if isinstance(prop, pg.PropBase) and not isinstance(prop, PropSim):
            for i, p in enumerate(self._props):
                if prop == p or (isinstance(p, PropSim) and prop == p.prop):
                    return i
            return -1

        return super().Index(prop)

class BreakpointSettingsDlg(wx.Dialog):
    def __init__(self, parent, condition='', hitcount=''):
        wx.Dialog.__init__(self,
                           parent,
                           title="Breakpoint Condition",
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        szAll = wx.BoxSizer(wx.VERTICAL)
        label = ("At the end of each delta cycle, the expression is evaluated "
                 "and the breakpoint is hit only if the expression is true or "
                 "the register value has changed")
        self.stInfo = wx.StaticText(self, label=label)
        self.stInfo.Wrap(400)
        szAll.Add(self.stInfo, 0, wx.ALL, 5)

        szCond = wx.BoxSizer(wx.VERTICAL)

        self.rbChanged = wx.RadioButton(self,
                                        label="Has changed",
                                        style=wx.RB_GROUP)
        szCond.Add(self.rbChanged, 0, wx.ALL | wx.EXPAND, 5)

        label = "Is true (value: $; for example, $==10)"
        self.rbCond = wx.RadioButton(self, label=label)
        szCond.Add(self.rbCond, 0, wx.ALL | wx.EXPAND, 5)

        self.tcCond = wx.TextCtrl(self)
        szCond.Add(self.tcCond, 0, wx.ALL | wx.EXPAND, 5)

        label = "Hit count (hit count: #; for example, #>10"
        self.cbHitCount = wx.CheckBox(self, label=label)
        szCond.Add(self.cbHitCount, 0, wx.ALL, 5)

        self.tcHitCount = wx.TextCtrl(self)
        szCond.Add(self.tcHitCount, 0, wx.ALL | wx.EXPAND, 5)

        szAll.Add(szCond, 0, wx.EXPAND, 5)

        self.stLine = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        szAll.Add(self.stLine, 0, wx.EXPAND | wx.ALL, 5)

        btnsizer = wx.StdDialogButtonSizer()

        self.btnOK = wx.Button(self, wx.ID_OK)
        self.btnOK.SetDefault()
        btnsizer.AddButton(self.btnOK)

        self.btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(self.btnCancel)
        btnsizer.Realize()

        szAll.Add(btnsizer, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.SetSizer(szAll)
        self.Layout()
        self.Fit()

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


class sim:
    frame = None
    ID_SIM_NEW = wx.NOT_FOUND
    ID_PROP_NEW = wx.NOT_FOUND
    ID_PANE_COPY_PATH = wx.NewIdRef()
    ID_PANE_COPY_PATH_REL = wx.NewIdRef()
    ID_PANE_SHOW_IN_FINDER = wx.NewIdRef()
    ID_PANE_SHOW_IN_BROWSING = wx.NewIdRef()

    @classmethod
    def initialize(cls, frame, **kwargs):
        PropGenericUdpate()
        cls.frame = frame
        cls.debug = kwargs.get('debug', False)

        resp = dp.send(signal='frame.add_menu',
                       path='File:New:Simulation',
                       rxsignal='bsm.simulation')
        if resp:
            cls.ID_SIM_NEW = resp[0][1]
        resp = dp.send(signal='frame.add_menu',
                       path='File:New:PropGrid',
                       rxsignal='bsm.simulation')
        if resp:
            cls.ID_PROP_NEW = resp[0][1]

        dp.connect(cls._process_command, signal='bsm.simulation')
        dp.connect(cls._sim_command, signal='sim.command')
        dp.connect(receiver=cls._frame_set_active,
                   signal='frame.activate_panel')
        dp.connect(receiver=cls._frame_uninitialize, signal='frame.exiting')
        dp.connect(receiver=cls.initialized, signal='frame.initialized')
        dp.connect(receiver=cls._prop_insert, signal='prop.insert')
        dp.connect(receiver=cls._prop_delete, signal='prop.delete')
        dp.connect(receiver=cls._prop_drop, signal='prop.drop')
        dp.connect(receiver=cls._prop_bp_add, signal='prop.bp_add')
        dp.connect(receiver=cls._prop_bp_del, signal='prop.bp_del')
        dp.connect(receiver=cls._prop_changed, signal='prop.changed')
        dp.connect(cls.PaneMenu, 'bsm.sim.pane_menu')

    @classmethod
    def initialized(cls):
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.pysim import *',
                prompt=False,
                verbose=False,
                history=False)
        dp.send(signal='shell.run',
                command='import six',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def _sim_command(cls, num, command, **kwargs):
        mgr = Gcs.get_manager(num)
        kwargs.pop("signal", None)
        kwargs.pop("sender", None)
        if mgr and hasattr(mgr, command) and command in mgr._interfaces:
            fun = getattr(mgr, command)
            if fun:
                return fun(**kwargs)
        return False

    @classmethod
    def _prop_changed(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            mgr.write({name: prop.GetValue()})

    @classmethod
    def _prop_bp_add(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            cnd = prop.GetBpCondition()
            if cnd is None:
                cnd = ["", ""]
            mgr.add_breakpoint(name, cnd[0], cnd[1])

    @classmethod
    def _prop_bp_del(cls, prop):
        mgr, name = cls._find_object(prop.GetName())
        if mgr:
            cnd = prop.GetBpCondition()
            if cnd is None:
                cnd = ("", "")
            mgr.del_breakpoint(name, cnd[0], cnd[1])

    @classmethod
    def _prop_insert(cls, prop):
        if not isinstance(prop, PropSim):
            return
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
            if Gcs.get_active() == pane.sim:
                return
            Gcs.set_active(pane.sim)
            if pane.sim.is_valid() and not pane.sim.is_running():
                # update the time stamp on the status bar
                pane.sim.time_stamp(insecond=False, block=False)
        if pane and isinstance(pane, SimPropGrid):
            SimPropGrid.GCM.set_active(pane)

    @classmethod
    def _frame_uninitialize(cls):
        for mgr in Gcs.get_all_managers():
            mgr.stop()
            dp.send('frame.delete_panel', panel=mgr.frame)
        for mgr in SimPropGrid.GCM.get_all_managers():
            dp.send('frame.delete_panel', panel=mgr)

        dp.send('frame.delete_menu', path="View:Simulations")
        dp.send('frame.delete_menu',
                path="File:New:Simulation",
                id=cls.ID_SIM_NEW)
        dp.send('frame.delete_menu',
                path="File:New:PropGrid",
                id=cls.ID_PROP_NEW)

    @classmethod
    def _process_command(cls, command):
        if command == cls.ID_SIM_NEW:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            dlg = wx.FileDialog(cls.frame, "Choose a file", "", "", "*.*",
                                style)
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
    def simulation(cls,
                   num=None,
                   filename=None,
                   silent=False,
                   create=True,
                   activate=False):
        """
        create a simulation

        If the simulation exists, return its handler; otherwise, create it if
        create == True.
        """
        def GetColorByNum(num):
            color = [
                'green', 'red', 'blue', 'black', 'cyan', 'yellow', 'magenta',
                'cyan'
            ]
            return wx.Colour(color[num % len(color)])

        manager = Gcs.get_manager(num)
        if manager is None and create:
            manager = SimPanel(sim.frame, num, filename, silent)
            clr = GetColorByNum(manager.sim.num)
            clr.Set(clr.red, clr.green, clr.blue, 128)
            manager.SetColor(clr)
            scale_factor = 1#manager.GetContentScaleFactor()
            page_bmp = MakeBitmap(clr.red, clr.green,
                                  clr.blue, scale_factor=scale_factor)
            (_, filename) = os.path.split(manager.filename)
            title = f"{filename} (sim-{manager.sim.num})"
            dp.send(signal="frame.add_panel",
                    panel=manager,
                    title=title,
                    target="History",
                    icon=page_bmp,
                    showhidemenu=f"View:Simulations:{title}",
                    pane_menu={'rxsignal': 'bsm.sim.pane_menu',
                           'menu': [
                               {'id':cls.ID_PANE_COPY_PATH, 'label':'Copy Path\tAlt+Ctrl+C'},
                               {'id':cls.ID_PANE_COPY_PATH_REL, 'label':'Copy Relative Path\tAlt+Shift+Ctrl+C'},
                               {'type': wx.ITEM_SEPARATOR},
                               {'id': cls.ID_PANE_SHOW_IN_FINDER, 'label':f'Reveal in  {get_file_finder_name()}\tAlt+Ctrl+R'},
                               {'id': cls.ID_PANE_SHOW_IN_BROWSING, 'label':'Reveal in Browsing panel'},
                               ]},
                    tooltip=manager.filename or "",
                    name=manager.filename or "")
            return manager.sim
        # activate the manager
        elif manager and activate:
            dp.send(signal='frame.show_panel', panel=manager)

        return manager

    @classmethod
    def PaneMenu(cls, pane, command):
        if not pane or not isinstance(pane, SimPanel):
            return
        if command in [cls.ID_PANE_COPY_PATH, cls.ID_PANE_COPY_PATH_REL]:
            if wx.TheClipboard.Open():
                filepath = pane.filename
                if command == cls.ID_PANE_COPY_PATH_REL:
                    filepath = os.path.relpath(filepath, os.getcwd())
                wx.TheClipboard.SetData(wx.TextDataObject(filepath))
                wx.TheClipboard.Close()
        elif command == cls.ID_PANE_SHOW_IN_FINDER:
            show_file_in_finder(pane.filename)
        elif command == cls.ID_PANE_SHOW_IN_BROWSING:
            dp.send(signal='dirpanel.goto', filepath=pane.filename, show=True)

    @classmethod
    def propgrid(cls, num=None, create=True, activate=False):
        """
        get the propgrid handle by its number

        If the propgrid exists, return its handler; otherwise, it will be created.
        """
        mgr = SimPropGrid.GCM.get_manager(num)
        if not mgr and create:
            mgr = SimPropGrid(cls.frame)
            mgr.SetLabel(f"Propgrid-{mgr.num}")
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
        s1, obj1, s2, obj2 = None, None, None, None
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
        y = {sy.global_object_name(y): dy}
        if sx:
            dx = sx.read_buf(x, block=True)
            x = {sx.global_object_name(x): dx}
        # since matplotlib 3.1.0, get_current_fig_manager returns an instance
        # of FigureManagerBase, and its frame is our panel
        mgr = graph.plt.get_current_fig_manager()
        if not isinstance(mgr, graph.MatplotPanel) and hasattr(mgr, 'frame'):
            mgr = mgr.frame
        if not mgr.IsShownOnScreen():
            dp.send('frame.show_panel', panel=mgr)
        autorelim = kwargs.pop("relim", True)
        mgr.plot_trace(x, y, autorelim, *args, **kwargs)


def bsm_initialize(frame, **kwargs):
    sim.initialize(frame, **kwargs)
