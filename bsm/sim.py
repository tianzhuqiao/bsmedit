import wx
import os
import threading
from simxpm import *
from sim_process import *
from bsmprop import *
from bsmpropgrid import *
from multiprocessing import Process, Queue
import threading
from sim_engine import *
from _pymgr_helpers import Gcm
import time
import matplotlib.pyplot as plt
import re
from wx.lib.masked import NumCtrl
import json
class ModuleTreeItemData(wx.TreeItemData):
    def __init__(self, obj, nType):
        wx.TreeItemData.__init__(self, None)
        self.scobj = obj
        self.m_nType = nType
    def GetObj(self):
        return scobj
    def GetType(self):
        return m_nType

class ModuleTree(wx.TreeCtrl):
    ID_MP_DUMP = wx.NewId()
    ID_MP_TRACE_BUF = wx.NewId()
    ID_MP_ADD_TO_NEW_VIEWER = wx.NewId()
    ID_MP_ADD_TO_VIEWER_START = wx.NewId()
    def __init__(self, parent,  style = wx.TR_DEFAULT_STYLE):
        wx.TreeCtrl.__init__(self, parent, style = style)
        imglist = wx.ImageList(16,16,True,10)
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
        self.sortfun = self.sortByTitle
        self.Bind( wx.EVT_TREE_ITEM_EXPANDING, self.OnTreeItemExpanding)
        self.Bind( wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated)
        
    def OnTreeItemActivated(self, event):
        pass
    
    def OnTreeItemExpanding(self, event):
        hParent = event.GetItem()
        if not hParent.IsOk():
            return
        self.FillNodes(hParent)

    def OnCompareItems(self, item1, item2):
        pItemData1 = self.GetItemData(item1)
        pItemData2 = self.GetItemData(item2)
        rtn = -2
        if self.sortfun and pItemData1 and pItemData2:
            return self.sortfun(pItemData1,pItemData2)
        else:#if rtn>1 and rtn<-1:
            return super(ModuleTree, self).OnCompareItems(item1, item2)
   
        return rtn
    def sortByTitle(self, item1, item2):
        (obj1, nType1) = item1.GetData()
        (obj2, nType2) = item2.GetData()
        if nType1 == nType2:
            if obj1['name'] > obj2['name']:
                return 1
            else:
                return -1
        if nType1 > nType2:
            return 1
        elif nType1 < nType2:
            return -1
        else:
            return 0

    def FillNodes(self, hParent):
        (hChild, cookie) = self.GetFirstChild(hParent)
        if not hChild.IsOk():
            return False
        if self.GetItemText(hChild) ==  "...":
            self.DeleteChildren(hParent)
            ext = self.GetExtendObj(hParent)
            for key, obj in self.objects.iteritems():
                if obj['nkind'] != SC_OBJ_UNKNOWN and \
                        obj['parent'] == ext['name']:
                    self.InsertScObj(hParent, obj)
        self.SortChildren(hParent)
        return True
    def Load(self, objects):
        self.objects = objects
        self.FillTree()
    def FillTree(self):
        #clear the tree control
        self.DeleteAllItems()
        assert (self.GetCount() == 0)
    
        if self.objects == None:
            return False
    
        # add the root item
        hRoot = self.AddRoot("BSMEdit")

        hParent = hRoot 
    
        # go through all the objects, and only add the top level item
        for key, obj in self.objects.iteritems():
            if obj['nkind'] != SC_OBJ_UNKNOWN and obj['parent'] == "":
                self.InsertScObj(hParent,obj)
    
        #any item? expand it
        (item, cookie) = self.GetFirstChild(hRoot)
        if item.IsOk():
            self.Expand(item)
    
        self.SortChildren(hParent)
        return True
    
    def InsertScObj(self, hParent, obj):
        nKind = obj['nkind']
        img  = -1
        img2 = -1
        if nKind == SC_OBJ_MODULE:
            img  = 0
            img2 = 0
        elif nKind in [SC_OBJ_SIGNAL, SC_OBJ_CLOCK, SC_OBJ_XSC_PROP, 
                       SC_OBJ_XSC_ARRAY, SC_OBJ_XSC_ARRAY_ITEM]:
            img  = 1
            img2 = 1
        elif nKind == SC_OBJ_INPUT:
            img  = 2
            img2 = 2
        elif nKind == SC_OBJ_OUTPUT:
            img  = 3
            img2 = 3
        elif nKind == SC_OBJ_INOUT:
            img  = 4
            img2 = 4
        id = self.AppendItem(hParent,obj['basename'],img,img2, wx.TreeItemData((obj,img)))
        #add the sign to append the children later
        if nKind == SC_OBJ_MODULE or nKind == SC_OBJ_XSC_ARRAY:
            self.AppendItem(id, ("..."),img,img2, None)
        return id
    
    def GetExtendObj(self, hItem):
        ext = self.GetItemData(hItem)
        if ext:
            (obj, img) = ext.GetData() 
            return obj
        return None
    
    def finditem(self, hParent, strName):
        (hChild, cookie) = self.GetFirstChild(hParent)
        while(hChild):
            ext = self.GetExtendObj(hChild)
            if strName == ext['name']:
                return hChild
            if HasChildren(hChild):
                FillNodes(hChild)
                hChild2 = self.finditem(hChild,strName)
                if hChild2.IsOk():
                    return hChild2
            (hChild, cookie) = self.GetNextChild(hParent,cookie)
        return wx.TreeItemId()

    def SetActiveNode(self, strName):
        hItem = Self.GetRootItem()
        hChild = finditem(hItem,strName)
        if hChild.IsOk():
            self.EnsureVisible(hChild)
            self.UnselectAll()
            self.SelectItem(hChild)

Gcs = Gcm()
class PseudoSimEvent():
    def __init__(self, eng=None):
        self._set = False
        self._waiting = False
    def set(self):
        self._set = True

    def clear(self):
        self._set = False

    def wait(self):
        self._waiting = True
        while (self._set is False):
            wx.YieldIfNeeded()
            time.sleep(0.05)
        self._waiting = False
    def isWaiting(self):
        return self._waiting

class ModulePanel(wx.Panel):
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
    def __init__(self, parent, num = None, filename = None, silent = False):
        wx.Panel.__init__(self, parent)
        if num is not None and isinstance(num, int):
            self.num =  num
        else:
            self.num =  Gcs.get_next_num()
        Gcs.set_active(self)

        # event for 'block' operations
        self._resume_event = PseudoSimEvent()
        # the variable used to update the UI in idle()
        self.ui_timestamp = None
        self.ui_objs = None
        self.ui_buffers = None
        self.ui_update = 0
        self.tb = wx.ToolBar(self, style = wx.TB_FLAT | wx.TB_HORIZONTAL | wx.TB_NODIVIDER)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))

        self.tb.AddLabelTool(self.ID_SIM_STEP, "", wx.BitmapFromXPMData(step_xpm),
                          wx.BitmapFromXPMData(step_grey_xpm),wx.ITEM_NORMAL, "Step", "Step the simulation")
        self.tb.AddLabelTool(self.ID_SIM_RUN, "", wx.BitmapFromXPMData(run_xpm),
                          wx.BitmapFromXPMData(run_grey_xpm), wx.ITEM_NORMAL, "Run", "Run the simulation")
        self.tb.AddLabelTool(self.ID_SIM_PAUSE, "", wx.BitmapFromXPMData(pause_xpm),
                          wx.BitmapFromXPMData(pause_grey_xpm),wx.ITEM_NORMAL, "Pause", "Pause the simulation")
        fStep = 1000.0
        fDuration = -1.0
        nUnit = BSM_NS
        self.tb.AddSeparator()
        
        self.tcStep = NumCtrl(self.tb, wx.ID_ANY, ("%g"%fStep), allowNegative=False, fractionWidth = 0)
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Step "))
        self.tb.AddControl(self.tcStep)
        self.cmbUnitStep = wx.ComboBox(self.tb, wx.ID_ANY, 'ns',
                        wx.DefaultPosition,wx.Size(50,20), ['fs', 'ps', 'ns', 'us', 'ms', 's'], wx.CB_READONLY)
        self.tb.AddControl(self.cmbUnitStep)
        self.tb.AddSeparator()

        self.tcTotal = NumCtrl(self.tb, wx.ID_ANY, ("%g"%fDuration))
        self.tb.AddControl(wx.StaticText(self.tb, wx.ID_ANY, "Total "))
        self.tb.AddControl(self.tcTotal)
        self.cmbUnitTotal = wx.ComboBox(self.tb, wx.ID_ANY, 'ns',
                        wx.DefaultPosition,wx.Size(50,20), ['fs', 'ps', 'ns', 'us', 'ms', 's'], wx.CB_READONLY)
        self.tb.AddControl(self.cmbUnitTotal)
        self.tb.AddSeparator()
        self.tb.AddStretchableSpace()
        self.tb.AddLabelTool(self.ID_SIM_SET, "", wx.BitmapFromXPMData(setting_xpm),
                          wx.BitmapFromXPMData(setting_grey_xpm),wx.ITEM_DROPDOWN, "Setting", "Configure the simulation")
        menu = wx.Menu()
        menu.Append(wx.ID_ANY, "&Reset")
        menu.AppendSeparator()
        menu.Append(wx.ID_ANY, "&Exit")
        self.tb.SetDropdownMenu(self.ID_SIM_SET, menu)
        self.tb.Realize()

        self.tree  =ModuleTree(self,
                style=wx.TR_DEFAULT_STYLE
                | wx.TR_HAS_VARIABLE_ROW_HEIGHT | wx.TR_HIDE_ROOT | wx.TR_MULTIPLE)
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
        self.tree.Bind( wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_MP_ADD_TO_NEW_VIEWER)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_MP_DUMP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_MP_TRACE_BUF)
        self.Bind(wx.EVT_MENU_RANGE, self.OnProcessCommand, id = wx.ID_FILE1, id2 = wx.ID_FILE9)
        self.Bind (wx.EVT_IDLE, self.OnIdle)
        self.objects = None
        # create the simulation kernel
        self.qResp = None
        self.qCmd = None
        self.thread = None
        self.p = None
        self.start()
        self.lock = threading.Lock()
        #
        if isinstance(filename, str) and filename is not None:
            self.load(filename)
        elif not silent:
            self.load_interactive()
        self.SetParameter()

    def __del__(self):
        # stop() will involve some gui operations, it should not be called in
        # __del__()
        self._stop()
        Gcs.destroy(self.num)

    def sendCommand(self, cmd, args, block = False):
        try:
            # return, if the previous call has not finished
            # it may happen when the previous command is waiting for response, 
            # and another command is sent (by clicking a button)
            if self._resume_event.isWaiting():
                block = False

            if self.qResp is None or self.qCmd is None or\
               self.p is None or self.thread is None:
                raise KeyboardInterrupt
            self._resume_event.clear()
            if not isinstance(args, dict):
                return False
            self.qCmd.put([{'cmd':cmd, 'arguments':args}])
            if block: 
                self._resume_event.wait()
                return self.response
            return True
        except:
            traceback.print_exc(file=sys.stdout)
        finally:
            pass

    def SetParameter(self):
        step = int(self.tcStep.GetValue())
        unitStep = int(self.cmbUnitStep.GetSelection())
        total = int(self.tcTotal.GetValue())
        unitTotal = int(self.cmbUnitTotal.GetSelection())
        self.set_parameter(step, unitStep, total, unitTotal)

    def set_parameter(self, step, unitStep, total, unitTotal, block = False):
        args = {'unitStep': unitStep, 'step': step, 'total': total, 'unitTotal': unitTotal}
        self.sendCommand('set_parameter', args, block)

    def start(self):
        self.stop()
        self.qResp = Queue()
        self.qCmd = Queue()
        self.thread = simThread(self, self.qResp)
        self.thread.start()
        self.p = Process(target=sim_process, args=(self.qResp, self.qCmd))
        self.p.start()

    def load(self, filename, block = True):
        self.sendCommand('load', {'filename':filename}, block)
    
    def load_interactive(self):
        dlg = wx.FileDialog(self, "Choose a file", "", "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            self.sendCommand('load', {'filename':filename}, True)
        dlg.Destroy()

    def step(self, block = True):
        self.sendCommand('step', {'running': False}, block)

    def run(self, block = True):
        self.sendCommand('step', {'running': True}, block)

    def pause(self, block = True):
        self.sendCommand('pause', {}, block)

    def _stop(self):
        if self.qResp is None or self.qCmd is None or\
            self.p is None or self.thread is None:
            return
        # stop the simulation kernel. No block operation allowed since
        # no response from the subprocess
        self.sendCommand('exit', {}, False)
        # stop the client
        self.qResp.put([{'resp':'exit'}])
        self.p.join()
        self.thread.join()
        self.thread = None
        self.p = None
        wx.py.dispatcher.send(signal='sim.unload', num=self.num)

    def stop(self):
        self._stop()
        self.tree.Load(None)

    def reset(self):
        self.start()

    def time_stamp(self, block = False):
        return self.sendCommand('timestamp', {}, block)

    def time_stamp_sec(self, block = False):
        return self.sendCommand('timestamp', {'format':'second'}, block)

    def read(self, objects, block = False):
        if isinstance(objects, str):
            objects = [objects]
        return self.sendCommand('read', {'objects':objects}, block)

    def write(self, objects, block = False):
        return self.sendCommand('write', {'objects':objects}, block)
    
    def trace_file(self, obj, trace_type = BSM_TRACE_SIMPLE, valid = None, trigger = BSM_BOTHEDGE, block = False):
        return self.sendCommand('tracefile', {'name': obj, 'type': trace_type, 'valid':valid, 'trigger':trigger}, block)

    def trace_buf(self, obj, size, valid = None, trigger = BSM_BOTHEDGE, block = False):
        return self.sendCommand('tracebuf', {'name': obj, 'size': size, 'valid': valid, 'trigger': trigger}, block)

    def read_buf(self, objects, block = False):
        if isinstance(objects, str):
            objects = [objects]
        return self.sendCommand('readbuf', {'objects':objects}, block)
    def _abs_object_name(self, obj):
        num, name = sim.get_object_name(obj)
        if num is not None:
            return obj
        return "%d."%self.num + obj
    def show_prop(self, grid, objects, index = -1):
        if grid is None or objects is None:
            return None
        if isinstance(objects, str):
            objects = [objects]
        prop = []
        for name in objects:
            obj = self.objects.get(name, None)
            if obj == None: continue
            p = grid.InsertProperty(self._abs_object_name(obj['name']), obj['basename'], obj['value'], index)
            if not obj['readable'] and not obj['writable']:
                p.SetReadOnly(True)
                p.SetShowRadio(False)

            prop.append(p)
            if index!=-1: index += 1
        if len(prop)==1:
            return prop[0]
        return prop
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
            self.read(objects)

    def OnTreeItemMenu(self, event):
        itemId = event.GetItem()
        if not itemId.IsOk():
             return
        strReg = self.tree.GetItemText(itemId)
        menu = wx.Menu()
        menu.Append(self.ID_MP_DUMP, "&Dump file")
        menu.AppendSeparator()
        menu.Append(self.ID_MP_TRACE_BUF, "&New Tracing buffer")
        menu.AppendSeparator()
        submenu = wx.Menu()
        submenu.Append(self.ID_MP_ADD_TO_NEW_VIEWER, "&Add to a new viewer")
        submenu.AppendSeparator()
        id = wx.ID_FILE1
        self.viewer = []
        for v in bsmPropGrid.GCM.get_all_managers():
            self.viewer.append(v)
            submenu.Append(id, v.GetLabel())
            id = id + 1
        
        menu.AppendSubMenu(submenu, "Add to...")
        self.PopupMenu(menu)
        menu.Destroy()

    def OnTreeBeginDrag(self, event):
        if self.tree.objects == None:
            return

        ids = self.tree.GetSelections()
        objs = []
        for i in range(0, len(ids)):
            hItem = ids[i]
            if hItem == self.tree.GetRootItem():
                continue
            if not hItem.IsOk():
                break
            ext = self.tree.GetExtendObj(hItem)
            nKind = ext['nkind']
            if nKind == SC_OBJ_XSC_ARRAY:
                (hChild, cookie) = self.tree.GetFirstChild(hItem)
                if hChild.IsOk() and self.tree.GetItemText(hChild)== "...":
                    self.tree.Expand(hItem)
                (hChild, cookie) = self.tree.GetFirstChild(hItem)
                objchild = []
                while hChild.IsOk():
                    ext2 = self.tree.GetExtendObj(hChild)
                    objchild.append(self._abs_object_name(ext2['name']))
                    (hChild, cookie) = self.tree.GetNextChild(hItem,cookie)
                objs.append({'reg':self._abs_object_name(ext['name']),'child':objchild})
            else:
                objs.append({'reg':self._abs_object_name(ext['name'])})
        # need to explicitly allow drag
        # start drag operation
        propData = wx.PyTextDataObject(json.dumps(objs))

        source = wx.DropSource(self.tree)
        source.SetData(propData)
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

    def OnProcessCommand(self, event):
        eid = event.GetId()
        viewer = None
        if eid == self.ID_MP_DUMP:
            pass
        elif eid == self.ID_MP_TRACE_BUF:
            pass
        elif eid == self.ID_MP_ADD_TO_NEW_VIEWER:
            viewer = sim.propgrid()
        elif eid >= wx.ID_FILE1 and eid <= wx.ID_FILE9:
            viewer =  self.viewer[eid - wx.ID_FILE1]
        if viewer:
            #items = self.tree.GetSelections()
            #for item in items:
            #    obj = self.tree.GetExtendObj(item)
            #    self.show_prop(viewer, obj['name'])
            ids = self.tree.GetSelections()
            objs = []
            for i in range(0, len(ids)):
                hItem = ids[i]
                if hItem == self.tree.GetRootItem():
                    continue
                if not hItem.IsOk():
                    break
                ext = self.tree.GetExtendObj(hItem)
                nKind = ext['nkind']
                self.show_prop(viewer, ext['name'])
                if nKind == SC_OBJ_XSC_ARRAY:
                    (hChild, cookie) = self.tree.GetFirstChild(hItem)
                    if hChild.IsOk() and self.tree.GetItemText(hChild)== "...":
                        self.tree.Expand(hItem)
                    (hChild, cookie) = self.tree.GetFirstChild(hItem)
                    objchild = []
                    while hChild.IsOk():
                        ext2 = self.tree.GetExtendObj(hChild)
                        prop = self.show_prop(viewer, ext2['name'])
                        prop.SetIndent(1)
                        (hChild, cookie) = self.tree.GetNextChild(hItem,cookie)

    def monitor_add(self, objs, block=True):
        if isinstance(objs, str):
            objs = [objs]
        return self.sendCommand('monitor_add', {'objects':objs}, block)
    
    def monitor_del(self, objs, block=True):
        if isinstance(objs, str):
            objs = [objs]
        return self.sendCommand('monitor_del', {'objects':objs}, block)
   
    def bp_add(self, objs, block=False):
        return self.sendCommand('breakpoint_add', {'objects':objs}, block)
    
    def bp_del(self, objs, block=False):
        return self.sendCommand('breakpoint_del', {'objects':objs}, block)

    def OnSimNotify(self, e):
        command = e.GetVal()
        for cmd in command:
            command = cmd['resp']
            value = cmd['value']
            self.response = value
            if command == 'load':
                self.objects = value
                self.tree.Load(self.objects)
                wx.CallAfter(wx.py.dispatcher.send, signal='sim.load', num=self.num)

            elif command == 'monitor':
                objs = value
                self.ui_objs = {self._abs_object_name(name):v for name, v in objs.iteritems()}

            elif command == 'monitor_add':
                objs = [self._abs_object_name(name) for name, v in value.iteritems() if v]
                wx.CallAfter(wx.py.dispatcher.send, signal='sim.monitor_added', objs = objs)

            elif command == 'read':
                for name, obj in value.iteritems():
                    o = self.objects.get(name, None)
                    if o is None: continue
                    o['value'] = obj
                if len(value) == 1:
                    value = value.values()[0]

            elif command == 'timestamp':
                if isinstance(value, str):
                    self.ui_timestamp = value

            elif command == 'readbuf':
                self.ui_buffers = {self._abs_object_name(name):v for name, v in value.iteritems()}
                if len(value) == 1:
                    value = value.values()[0]

            elif command == 'triggered':
                bp = value #[name, condition, hitcount, hitsofar]
                for grid in bsmPropGrid.get_instances():
                    if grid.triggerBreakPoint(self._abs_object_name(bp[0]), bp[1], bp[2]):
                        wx.py.dispatcher.send(signal = 'frame.showpanel', panel = grid)
                        break

            elif command == 'ack':
                pass

            elif command == 'writeOut':
                wx.py.dispatcher.send(signal = 'shell.writeout', text = value)

        self.response = value
        self._resume_event.set()

    def OnIdle(self, event):
        if (self.ui_timestamp is not None) and self.ui_update == 0:
            wx.py.dispatcher.send(signal="frame.setstatustext", text = self.ui_timestamp)
            self.ui_timestamp = None
        elif (self.ui_objs is not None) and self.ui_update == 1:
            wx.py.dispatcher.send(signal="grid.updateprop", objs = self.ui_objs)
            self.ui_objs = None
        elif (self.ui_buffers is not None) and self.ui_update == 2:
            # update the plot, it is time-consuming
           wx.py.dispatcher.send(signal="sim.buffer_changed", bufs = self.ui_buffers)
           self.ui_buffers = None
        self.ui_update += 1 
        self.ui_update %= 3 

    def OnStep(self, e):
        self.SetParameter()
        self.step()

    def OnRun(self, e):
        self.SetParameter()
        self.run()

    def OnPause(self, e):
        self.pause()

class clientCommand:
    def __init__(self, frame, q):
        self.q = q
        self.frame = frame

    def command(self):
        command = self.q.get()
        for cmd in command:
            if cmd['resp'] == 'exit':
                return False
        Event = simEvent(bsmEVT_SIM_NOTIFY)
        Event.SetVal(command)
        wx.PostEvent(self.frame, Event)
        return True

bsmEVT_SIM_NOTIFY = wx.NewEventType()
EVT_SIM_NOTIFY = wx.PyEventBinder(bsmEVT_SIM_NOTIFY)
class simEvent(wx.PyCommandEvent):
    def __init__(self, evtType):
        wx.PyCommandEvent.__init__(self, evtType)
        self.val = None
    def SetVal(self, val):
        self.val = val
    def GetVal(self):
        return self.val

class simThread(threading.Thread):
    def __init__(self, frame, q):
        threading.Thread.__init__(self)
        self.frame=frame
        self.q = q
    def run(self):
        cmd = clientCommand(self.frame, self.q)
        while cmd.command():
            pass

class sim:
    frame = None
    ID_SIM_NEW = wx.NOT_FOUND
    def __init__(self):     
      pass
    @classmethod
    def Initialize(cls, frame):
        cls.frame = frame

        response = wx.py.dispatcher.send(signal='frame.addmenu',
                            path='File:New:Simulation', rxsignal='bsm.simulation')
        if response:
            cls.ID_SIM_NEW = response[0][1]
        
        wx.py.dispatcher.connect(cls.ProcessCommand, signal='bsm.simulation')
        wx.py.dispatcher.connect(receiver=cls.Uninitialize, signal='frame.exit')
        wx.py.dispatcher.connect(receiver=cls.set_active, signal='frame.activatepane')
        
        wx.py.dispatcher.connect(receiver = cls.OnAddProp, signal='prop.insert')
        wx.py.dispatcher.connect(receiver = cls.OnDelProp, signal='prop.delete')
        wx.py.dispatcher.connect(receiver = cls.OnDropProp, signal='prop.drop')
        wx.py.dispatcher.connect(receiver = cls.OnBPAdd, signal='prop.bp_add')
        wx.py.dispatcher.connect(receiver = cls.OnBPDel, signal='prop.bp_del')
        wx.py.dispatcher.connect(receiver = cls.OnValChanged, signal='prop.changed')
        wx.py.dispatcher.connect(receiver = cls.monitor_add, signal='sim.monitor_add')
        wx.py.dispatcher.connect(receiver = cls.monitor_del, signal='sim.monitor_del')
        wx.py.dispatcher.connect(receiver = cls.trace_buf, signal='sim.trace_buf')
    @classmethod
    def parse_objs(cls, objs):
        s = Gcs.get_active()
        if not s: return
        d = {}
        for obj in objs:
            num, name = cls.get_object_name(obj)
            if num is None:
                num = s.num
            if num in d.keys():
                d[num].append(name)
            else:
                d[num]=[name]
        return d
    @classmethod
    def monitor_add(cls, objs):
        d = cls.parse_objs(objs)
        for num, obj in d.iteritems():
            mgr = Gcs.get_manager(num)
            if mgr:
                mgr.monitor_add(obj)
    @classmethod
    def monitor_del(cls, objs):
        d = cls.parse_objs(objs)
        for num, obj in d.iteritems():
            mgr = Gcs.get_manager(num)
            if mgr:
                mgr.monitor_del(obj)
    @classmethod
    def trace_buf(cls, objs, size, valid = None, trigger = BSM_BOTHEDGE):
        d = cls.parse_objs(objs)
        for num, obj in d.iteritems():
            mgr = Gcs.get_manager(num)
            if mgr:
                mgr.trace_buf(obj, size, valid, trigger)
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
            mgr.bp_add([[name, cnd[0], cnd[1] ]])
    @classmethod
    def OnBPDel(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            cnd = prop.GetBPCondition()
            mgr.bp_del([[name, cnd[0], cnd[1]]])
    @classmethod
    def OnAddProp(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            mgr.monitor_add(name)
    @classmethod
    def OnDelProp(cls, prop):
        num, name = cls.get_object_name(prop.GetName())
        mgr = Gcs.get_manager(num)
        if mgr:
            mgr.monitor_del(name)
    @classmethod 
    def OnDropProp(cls, index, prop, grid):
        objs = json.loads(prop)
        for obj in objs:
            reg = obj['reg']
            num, name = cls.get_object_name(str(reg))
            mgr = Gcs.get_manager(num)
            if mgr is None: continue
            p = mgr.show_prop(grid, name, index)
            if index!=-1:
                index = index + 1
            for c in obj.get('child', []):
                num, name = cls.get_object_name(str(c))
                mgr = Gcs.get_manager(num)
                if mgr is None: continue
                p = mgr.show_prop(grid, name, index)
                p.SetIndent(1)
                if index!=-1:
                    index = index + 1

    @classmethod
    def set_active(cls, pane, force=False, notify=False):
        if pane and isinstance(pane, ModulePanel):
            Gcs.set_active(pane)
        if pane and isinstance(pane, bsmPropGrid):
            bsmPropGrid.GCM.set_active(pane)
    @classmethod
    def Uninitialize(cls):
        pass

    @classmethod
    def ProcessCommand(cls, command):
        if command == cls.ID_SIM_NEW:
              simulation() 
    @classmethod 
    def propgrid(cls, num = None, create = True, activate = False):
        """
        get the propgrid manager by its number

        If the manager exists, return its handler; otherwise, it will be created.
        """
        manager = bsmPropGrid.GCM.get_manager(num)
        if not manager and create:
            manager = bsmPropGrid(cls.frame)
            manager.SetLabel("Propgrid-%d"%manager.num)
            wx.py.dispatcher.send(signal="frame.addpanel", panel=manager, 
                                                          title=manager.GetLabel())
        elif manager and activate:
            # activate the manager
            wx.py.dispatcher.send(signal = 'frame.showpanel', panel = manager)
        return manager
    @classmethod
    def get_object_name(cls, name):
        x = re.match('^(\d)+\.(.*)', name)
        if x is None:
            return (None, name)
        else:
            return (int(x.group(1)), x.group(2))

def bsm_Initialize(frame):
    sim.Initialize(frame)

