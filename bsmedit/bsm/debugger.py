"""
The code is based on PythonTookit (http://pythontoolkit.sourceforge.net/)
"""
import time
import inspect #for debugger frame inpsection
import sys #for set_trace etc
import six.moves._thread as thread #for keyboard interrupt
import os.path #for absolute filename conversions
import ctypes #for pythonapi calls
from codeop import _maybe_compile, Compile
import traceback #for formatting errors
import wx
import wx.py.dispatcher as dp
from .. import c2p

help_msg = """
\"\"\"
#help | #h:
    - show this text.
#step | #s:
    - step to the next line.
#stepin | #si:
    - step into a new code block call.
#stepout | #so:
    - step out of the current code block.
#resume | #r:
    - resume running the code.
#setscope [L] | #ss [L]:
    - set the active scope level L (default: 0 for the main user namespace).
#line | #l:
    - print the current line of source (if available).
#end | #e:
    - quit the debugger.
#stop:
    - interrupt the execution
\"\"\"
"""
class PseudoEvent(object):
    """
    An object with the same interface as a threading.Event for the internal
    engine. This prevents the readline/readlines and debugger from blocking
    when waiting for user input.

    This calls the doyield function and sleeps until the event is set.
    """
    def __init__(self):
        self._set = False

    def set(self):
        self._set = True

    def clear(self):
        self._set = False

    def wait(self, timeout=None):
        if timeout is not None:
            raise NotImplementedError('Timeout not implemented')
        while self._set is False: #and (self._eng._stop is False):
            wx.YieldIfNeeded()
            # send the EVT_UPDATE_UI events so the UI status has a chance to
            # update (e.g., menubar, toolbar)
            if c2p.bsm_is_phoenix:
                wx.EventLoop.GetActive().ProcessIdle()
            else:
                wx.GetApp().ProcessIdle()
            time.sleep(0.05)

class EngineDebugger(object):
    bpnum = 0
    def __init__(self):
        self.compiler = EngineCompiler()
        #debugger state
        self._paused = False #is paused.
        self._can_stepin = False #debugger is about to enter a new scope
        self._can_stepout = False #debugger can be stepped out of a scope

        #debugger command flags
        self._resume = False #debugging was resumed.
        self._end = False #stop debugging, finish running code
        self._stop = False #stop running code
        self._stepin = False #debugger step in to scope
        self._stepout = False #debugger step out of scope

        #event used to wake the trace function when paused
        self._resume_event = PseudoEvent()

        #user commands to execute when the debugger is paused
        #this is check in the trace function and executed in the active scope.
        self._cmd = None

        #debugger scopes:
        #keep track of the different scopes available for tools to query
        self._scopes = [] #list of scope (function) names
        self._frames = [] #list of scope frames
        self._active_scope = 0 #the current scope level used for exec/eval/commands
        self._paused_active_scope = 0
        #internal variable used to keep track of where wer started debugging
        self._bottom_frame = None

        #files to look for when tracing...
        self._fncache = {} #absolute filename cache
        self._block_files = [] #list of filepaths not to trace in (or any further)

        #prevent trace in all engine module files to avoid locks blocking comms threads.
        self.set_block_file(os.path.dirname(__file__)+os.sep+'*.*')

        # break points - info on breakpoints is stored in an DictList instance
        # which allows items (the breakpoint data dict) to be retrieved by
        #filename or id. The key tcount is the breakpoint counters for hits,
        # and is reset before each user command.
        self.bpoints = DictList()
        self._bp_hcount = {} # hit counter {id: hcount}
        self._bp_tcount = {} # trigger counter {id: tcount}

        #Register message handlers for the debugger
        dp.connect(self.pause, 'debugger.pause')
        dp.connect(self.resume, 'debugger.resume')
        dp.connect(self.stop_code, 'debugger.stop')
        dp.connect(self.end, 'debugger.end')
        dp.connect(self.step, 'debugger.step')
        dp.connect(self.step_in, 'debugger.step_into')
        dp.connect(self.step_out, 'debugger.step_out')
        dp.connect(self.set_scope, 'debugger.set_scope')
        dp.connect(self.set_breakpoint, 'debugger.set_breakpoint')
        dp.connect(self.clear_breakpoint, 'debugger.clear_breakpoint')
        dp.connect(self.edit_breakpoint, 'debugger.edit_breakpoint')
        dp.connect(self.get_breakpoint, 'debugger.get_breakpoint')
        dp.connect(self.get_status, 'debugger.get_status')

    def release(self):
        self.compiler.release()
        dp.disconnect(self.pause, 'debugger.pause')
        dp.disconnect(self.resume, 'debugger.resume')
        dp.disconnect(self.stop_code, 'debugger.stop')
        dp.disconnect(self.end, 'debugger.end')
        dp.disconnect(self.step, 'debugger.step')
        dp.disconnect(self.step_in, 'debugger.step_into')
        dp.disconnect(self.step_out, 'debugger.step_out')
        dp.disconnect(self.set_scope, 'debugger.set_scope')
        dp.disconnect(self.set_breakpoint, 'debugger.set_breakpoint')
        dp.disconnect(self.clear_breakpoint, 'debugger.clear_breakpoint')
        dp.disconnect(self.edit_breakpoint, 'debugger.edit_breakpoint')
        dp.disconnect(self.get_breakpoint, 'debugger.get_breakpoint')
        dp.disconnect(self.get_status, 'debugger.get_status')

    # Interface methods
    def reset(self):
        """Reset the debugger internal state"""
        self._paused = False
        self._can_stepin = False
        self._can_stepout = False

        self._resume = False
        self._end = False
        self._stop = False
        self._stepin = False
        self._stepout = False

        self._resume_event.clear()

        self._scopes = []
        self._frames = []
        self._active_scope = 0

        self._bottom_frame = None

        #resest breakpoint counters
        for d in self.bpoints.items():
            d['tcount'] = 0

    def stop_code(self):
        """
        Attempt to stop the running code by raising a keyboard interrupt in
        the main thread
        """
        self._stop = True #stops the code if paused
        if self._paused is True:
            self.prompt()

        self._resume_event.set()

        #try a keyboard interrupt - this will not work for the internal engine
        # as the error is raised here instead of the running code, hence put in
        #try clause.
        try:
            thread.interrupt_main()
        except:
            pass

        # send the notification, the debugger may stop after the notification
        dp.send('debugger.ended')

    def end(self):
        """ End the debugging and finish running the code """
        #set the end flag and wake the traceback function
        #if necessary
        self._end = True
        self._resume = True
        self._resume_event.set()

        # send the notification, the debugger may stop after the notification
        dp.send('debugger.ended')
        return True

    def pause(self, flag=True):
        """ Pause currently running code - returns success """
        if flag is False:
            return not self.resume()

        #already paused do nothing.
        if self._paused is True:
            return True

        #set the paused flag to pause at next oppertunity
        self._paused = True
        return True

    def resume(self):
        """ Unpause currently running code """
        #not paused - so cannot resume
        if self._paused is False:
            return False
        #set flag to false
        self._resume = True
        #set resume event to wake the traceback function
        self._resume_event.set()
        return True

    def step(self):
        """
        Step to the next line of code when the debugger is paused
        """
        #not paused - cannot step
        if self._paused is False:
            return False
        #make sure the step_in flag is False, so we don't step into a new scope
        #but rather step 'over' it.
        self._stepin = False
        #set the event so the trace function can resume - but don't change the
        #paused flag so the code will pause again after the next line.
        self._resume_event.set()
        return True

    def step_in(self):
        """
        Step into the new scope (function/callable).
        This is only available if the next line is a 'call' event
        """
        #not paused or not at a call event
        if (self._paused is False) or (self._can_stepin) is False:
            return False

        #set the step in flag and wake the traceback function
        self._stepin = True
        self._resume_event.set()
        return True

    def step_out(self):
        """
        Step out of a scope (function/callable).
        This is only available if the debugger is currently in a scope other
        than the main user namespace.
        """
        #check if we can step out
        if (self._paused is False) or (self._can_stepout is False):
            return False

        #set the step out flag and wake the traceback function
        #this will turn the traceback off for the current scope by returning
        #None, as the new local trace function.
        self._can_stepout = False
        self._stepout = True
        self._resume_event.set()
        return True

    #breakpoints
    def set_breakpoint(self, bpdata):
        """
        Set a break point
        bpdata = {id, filename, lineno, condition, ignore_count, trigger_count}
        where id should be a unique identifier for this breakpoint
        """
        #check if the id to use already exists.
        if self.bpoints.filter(('id',), (id,)):
            return False

        #check bpdata
        keys = list(bpdata.keys())
        if 'id' not in keys:
            bpdata['id'] = EngineDebugger.bpnum
            EngineDebugger.bpnum += 1
        elif 'filename' not in keys:
            return False
        elif 'lineno' not in keys:
            return False
        if 'condition' not in keys:
            bpdata['condition'] = ""
        if 'hitcount' not in keys:
            bpdata['hitcount'] = ""

        bpdata['tcount'] = 0

        #create new breakpoint
        bpdata['filename'] = self._abs_filename(bpdata['filename'])
        self.bpoints.append(bpdata)
        dp.send('debugger.breakpoint_added', bpdata=bpdata)
        return True

    def get_breakpoint(self, filename, lineno):
        """
        Return the break point according to the (filename, lineno),
        if not found, return None
        """
        bps = self.bpoints.filter(('filename', 'lineno'),
                                  (self._abs_filename(filename), lineno))
        if bps:
            return bps[0]
        return None

    def clear_breakpoint(self, id):
        """
        Clear the debugger breakpoint with the id given.
        If id is None all breakpoints will be cleared.
        """
        if id is None:
            self.bpoints.clear()
            return True

        #check if the id to clear exists.
        bps = self.bpoints.filter(('id',), (id,))
        if not bps:
            return False

        #remove the breakpoint
        bp = bps[0]
        self.bpoints.remove(bp)
        dp.send('debugger.breakpoint_cleared', bpdata=bp)
        return True

    def edit_breakpoint(self, id, **kwargs):
        """
        Edit a breakpoint.

        Only modify the keywords given (from filename, lineno, condition,
        trigger_count and ignore_count).

        e.g. edit_breakpoint(id=1, filename='test.py', lineno=23) will modify
        the breakpoint filename and lineno.
        """
        #check if the id to clear exists.
        bps = self.bpoints.filter(('id',), (id,))
        if not bps:
            return False

        bpdata = bps[0]
        if 'filename' in kwargs:
            kwargs['filename'] = self._abs_filename(kwargs['filename'])
        bpdata.update(kwargs)
        return True

    #debugger command/interogration interface
    def get_scope(self, level=None):
        """
        Get the scope name,frame, globals and locals dictionaries for the scope at the
        level given (None=current scope, 0=user namespace dictionary).

        Note: To make any changes permanent you should call
        _update_frame_locals(frame), with the frame.
        """
        #Note see http://utcc.utoronto.ca/~cks/space/blog/python/FLocalsAndTraceFunctions for possible problem!
        #Confirmed this issue - making a change to an existing variable will not
        #'stick' if the locals/globals are retrieved again before the next line
        #is executed.

        #To get round this either:
        #1)Keep a cache of the scopes globals/locals
        #to only fetch the dictionary once, after the next line the changes will
        #stick - but only to the top frame!
        #
        #2)Or using the python c api call that is called after the trace function
        #returns to make the changes stick immediately. This is done in the
        #function _update_frame_locals(frame)
        if level is None:
            level = self._active_scope
        if level > len(self._scopes) or level < 0:
            raise Exception('Level out of range: '+str(level))
        #get the scope name
        name = self._scopes[level]
        frame = self._frames[level]
        return name, frame, frame.f_globals, frame.f_locals

    def set_scope(self, level, silent=False):
        """
        Set the scope level to use for interogration when paused. This will be
        reset at the next pause (i.e. after stepping).
        """
        #check level is an int
        if isinstance(level, int) is False:
            return False
        #check level is in range
        if level > (len(self._scopes)-1):
            return False
        #check if already in this level
        if level == self._active_scope:
            return True
        self._active_scope = level

        #send scope change message
        if not silent:
            dp.send('debugger.update_scopes')
        return True

    def get_status(self):
        """return the current status"""
        if self._active_scope < 0 or self._active_scope >= len(self._frames):
            return None
        frame = self._frames[self._active_scope]
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        lineno = frame.f_lineno
        name = frame.f_code.co_name
        return {'name':name, 'filename':self._abs_filename(filename),
                'lineno':lineno, 'scopes':self._scopes,
                'active_scope':self._active_scope, 'paused': self._paused,
                'can_stepin':self._can_stepin,
                'can_stepout':self._can_stepout,
                'frames': self._frames}

    def push_line(self, line):
        """
        A debugger commands to run - this is called from the engine when a
        line is pushed and we are debugging and paused, so store internally and
        wake the debugger.
        """
        #not paused so not expecting any commands???
        if self._paused is False:
            return
        #have some code to execute so call run_user_command to do something with it
        #this wakes the resume event and runs the code in the mainthread
        self._cmd = line
        self._resume_event.set()
    #filepaths
    def set_block_file(self, filepath):
        """
        Set a filepath to block from tracing.
        use path* to include multiple files.
        """
        filepath = self._abs_filename(filepath)
        self._block_files.append(filepath)

    def get_block_files(self):
        """
        Get the filepaths that are currently blocked from tracing
        """
        return self._block_files

    #engine like interfaces
    def evaluate(self, expression, level=None):
        """
        Evaluate expression in the active debugger scope and return result
        (like builtin eval)

        It is intened to be used to provide functionality to the GUI, so commands
        should be fairly quick to process to avoid blocking.

        The optional level argument controls the scope that will be used.
        scope=None uses the current debugger scope and scope=0 is the top level
        scope (the usernamespace).

        Returns None on errors
        """
        #get the scope locals/globals
        _, frame, g, l = self.get_scope(level)

        #try to evaluate the expression
        try:
            result = eval(expression, g, l)
        except:
            result = None

        #update the locals
        self._update_frame_locals(frame)
        return result

    def execute(self, expression, level=None):
        """
        Execute expression in engine (like builtin exec)

        It is intened to be used to provide functionality to the GUI interface,
        so commands should be fairly quick to process to avoid blocking the
        communications thread.

        The optional level argument controls the scope that will be used.
        scope=None uses the current debugger scope and scope=0 is the top level
        scope (the usernamespace).
        """
        #get the scope locals/globals
        _, frame, g, l = self.get_scope(level)

        #execute the expression
        try:
            exec(expression, g, l)
        except:
            pass

        #update the locals
        self._update_frame_locals(frame)

    # trace methods
    #Trace every line - why?
    #1) It allows step out to work from a breakpoint in a nested scope
    #2) It makes the code easier to follow
    #3) It allows running code to be paused anywhere rather than just in traced scopes
    #The downside is speed, with every line now causing a call into python code
    def __call__(self, frame, event, arg):
        """ This trace function is called only once when debugging starts."""
        #store the first frame so we know where user code starts
        self._bottom_frame = frame
        #set the new global trace function
        sys.settrace(self._trace_global)

        #update the scope list
        self._update_scopes(frame)

        #return the local trace function for the first call
        return self._trace_global(frame, event, arg)

    def _trace_global(self, frame, event, arg):
        """The main trace function called on call events """
        #Prepause
        #check if the engine wants to stop running code
        if self._stop is True:
            raise KeyboardInterrupt
        #check if the debugger want to end debugging.
        if self._end is True:
            sys.settrace(None)
            #use a blank trace function as returning None doesn't work
            return self._trace_off

        #file and name of scope being called.
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        lineno = frame.f_lineno

        #if the file is on the block list do not trace
        #this is mainly engine/message bus files and prevents the user pausing and
        #locking the engine communications.
        if self._check_files(filename, self._block_files):
            return None
        #if the calling frame is also blocked return None
        if frame.f_back.f_trace is None and frame != self._bottom_frame:
            return None

        #if trace_stepout is the parent frames trace function then do not pause
        #here unless there is a breakpoint set, just return the stepout trace function
        #which only checks for breakpoints and exits.
        elif (frame.f_back.f_trace) == (self._trace_stepout):
            return self._trace_stepout

        #check for breakpoints
        filename = self._abs_filename(filename)
        bps = self.bpoints.filter(('filename', 'lineno'), (filename, lineno))
        for bpdata in bps:
            paused = self._hit_bp(bpdata, frame)
            if paused is True:
                break
        #Pause
        ##pause at this line?
        if self._paused is True:
            #This pauses until stepped/resumed
            self._trace_pause(frame, event, arg)

        #After pause
        #if paused and stepping in print a message
        if self._paused:
            if self._stepin is True:
                local_trace = self._trace_local
            else:
                #not stepping in so use the stepout function
                local_trace = self._trace_stepout
        #not paused so carry on with the normal trace function
        else:
            local_trace = self._trace_local

        #reset the can step in flags
        self._can_stepin = False
        self._stepin = False

        return local_trace

    def _trace_local(self, frame, event, arg):
        """
        The local trace function
        - the main local trace function checks for breakpoints and pause requests
        - used for all traced scopes unless stepping out, or ending debugging.
        """
        #check if the engine wants to stop running code
        if self._stop is True:
            raise KeyboardInterrupt

        #check if the debugger want to end debugging.
        if self._end is True:
            sys.settrace(None)
            #use a blank trace function as returning None doesn't work
            #this is a python bug (as of python2.7 01/2011)
            return self._trace_off

        #file and name of scope being called.
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        lineno = frame.f_lineno

        #check for breakpoints
        filename = self._abs_filename(filename)
        bps = self.bpoints.filter(('filename', 'lineno'), (filename, lineno))
        for bpdata in bps:
            paused = self._hit_bp(bpdata, frame)
            if paused is True:
                break

        #Need to pause/already paused here
        if self._paused is True:
            #This pauses until stepped/resumed
            self._trace_pause(frame, event, arg)

        #check for step out
        if self._stepout is True:
            #set the previous frame to use the local trace function incase it is
            #not using it already
            frame.f_back.f_trace = self._trace_local
            #and use the stepout function from now on - _trace_local will only be
            #called again when a new breakpoint is encountered or if we are back
            #in the frame above (frame.f_back)
            self._stepout = False
            return self._trace_stepout

        return self._trace_local

    def _trace_stepout(self, frame, event, arg):
        """
        A minimial local trace function used when stepping out of a scope.
        - it will only pause if a breakpoint is encountered (it passes control back to trace_local)
        """
        #check if the engine wants to stop running code
        if self._stop is True:
            raise KeyboardInterrupt
        #check if the debugger want to end debugging.
        if self._end is True:
            sys.settrace(None)
            #use a blank trace function as returning None doesn't work
            return self._trace_off

        #file and name of scope being called.
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        lineno = frame.f_lineno

        #check for breakpoints
        filename = self._abs_filename(filename)
        bps = self.bpoints.filter(('filename', 'lineno'), (filename, lineno))
        for bpdata in bps:
            will_break = self._check_bp(bpdata, frame)
            if will_break is True:
                #do not bother to continue checking
                #pass to the full trace function.
                return self._trace_local(frame, event, arg)
        return self._trace_stepout

    def _trace_pause(self, frame, event, arg):
        """
        A function called from within the local trace
        function to handle a pauses at this event
        """
        #update the scope list
        self._update_scopes(frame)
        #if self._paused_active_scope != self._active_scope:
        #    return
        if event == 'call':
            self._can_stepout = False
            self._can_stepin = True
        elif len(self._scopes) > 1:
            self._can_stepout = True
            self._can_stepin = True
        else:
            self._can_stepout = False
            self._can_stepin = True
        if event == 'call' and not self._stepin:
            return

        # do not stop inside the system files
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        for f in sys.path+['<input>', '<string>']:
            if filename.startswith(f):
                return

        #send a paused message to the console
        #(it will publish an ENGINE_DEBUG_PAUSED message after updating internal
        #state)
        dp.send('debugger.paused')
        #The user can then select whether to resume, step, step-in, step-out
        #cancel the code or stop debugging.

        #Make the console prompt for debugger commands at this pause.
        self.prompt()
        ##Paused loop - waiting for user instructions
        loop = True
        while loop:
            self._resume_event.wait()
            self._resume_event.clear()

            #check if the engine wants to stop running code
            if self._stop is True:
                raise KeyboardInterrupt

            #check if there is user code the execute
            if self._cmd is None:
                #turn console debug mode off -Note: None to turn off, True/False
                #is line continuation
                #need to step or resume so exit this while block
                #self.prompt()
                loop = False

            #user command to process.
            else:
                line = self._cmd
                self._cmd = None
                #check for debugger commands
                handled = self._process_dbg_command(line)
                if handled is False:
                    #not a command so execute as python source
                    self._process_dbg_source(line)

        #reset stepin flag
        self._can_stepin = False

        ##Debugger will run next line
        #check if we have resumed (will not pause again until a breakpoint/pause request)
        if self._resume is True:
            self._paused = False
            self._resume = False
            self._active_scope = 0

    def _trace_off(self, frame, event, arg):
        """
        A dummy tracing function used when ending tracing as returning None
        doesn't work (python bug v2.7 as of 01/2011)
        """
        return None

    # Internal methods
    def _check_bp(self, bpdata, frame):
        """
        Decide whether to break at the bpdata given.
        The frame is used to evaluate any conditons.
        """
        trigger = False
        #check if there is an expression to evaluate
        condition = bpdata['condition']
        if condition == "":
            hit = True
        else:
            try:
                hit = eval(condition, frame.f_globals, frame.f_locals)
            except:
                #fail safe - so trigger anyway.
                traceback.print_exc(file=sys.stdout)
                hit = True
                trigger = True

        if not trigger and hit:
            ht = bpdata['hitcount']
            if ht == "":
                trigger = True
            else:
                ht = ht.replace('#', str(bpdata['tcount']))
                try:
                    trigger = eval(ht, frame.f_globals, frame.f_locals)
                except:
                    #fail safe - so trigger anyway.
                    traceback.print_exc(file=sys.stdout)
                    trigger = True

        return trigger

    def _hit_bp(self, bpdata, frame):
        """
        Decide whether to break at the bpdata given and update internal counters
        and pause if necesary. The frame is used to evaluate any conditons.

        _hit_bp (this method) will check, update counters and pause if necessary
        _check_bp will only check - not pause or update counters.
        """
        trigger = False
        #checkif there is an expression to evaluate
        condition = bpdata['condition']
        if condition == "":
            #no condition triggering... increment tcount
            hit = True
        else:
            #evaluate it
            try:
                hit = eval(condition, frame.f_globals, frame.f_locals)
            except:
                #fail safe - so trigger anyway.
                traceback.print_exc(file=sys.stdout)
                hit = True
                trigger = True

        if not trigger and hit:
            bpdata['tcount'] += 1
            ht = bpdata['hitcount']
            if ht == "":
                trigger = True
            else:
                ht = ht.replace('#', str(bpdata['tcount']))
                try:
                    trigger = eval(ht, frame.f_globals, frame.f_locals)
                except:
                    #fail safe - so trigger anyway.
                    traceback.print_exc(file=sys.stdout)
                    trigger = True

        # pause if triggered
        if trigger is True:
            self._paused = True
            self._paused_active_scope = self._active_scope

        return trigger

    def _update_scopes(self, frame):
        scopes = []
        frames = []
        #loop backwards through frames until the bottom frame and generate lists
        #of scope names and frames.
        while frame is not None:
            name = frame.f_code.co_name
            if name == '<module>':
                filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
                if filename == '<input>':
                    name = 'Main'
            scopes.append(name)
            frames.append(frame)

            #check the next frame back
            if frame == self._bottom_frame:
                frame = None
            else:
                frame = frame.f_back

        #store to internals
        scopes.reverse()
        frames.reverse()
        self._scopes = scopes
        self._frames = frames

        #set current scope
        level = len(self._scopes)-1
        if self._active_scope != level:
            self.set_scope(level, True)

    def _update_frame_locals(self, frame):
        """
        Ensures changes to a frames locals are stored so they are not lost.
        """
        # For explanation see get_scope and the following pages:
        # http://bugs.python.org/issue1654367#
        # http://www.gossamer-threads.com/lists/python/dev/546183
        #use PyFrame_LocalsToFast(f, 1) to save changes back into c array.
        func = ctypes.pythonapi.PyFrame_LocalsToFast
        func.restype = None
        func(ctypes.py_object(frame), 1)

    def _abs_filename(self, filename):
        """
        Internal method to return the absolute filepath form.
        """
        #change filename provided to absolute form
        #This is done using code from the bdb.BdB.canonic() method
        if filename == "<" + filename[1:-1] + ">":
            #file name is a special case - do not modify
            fname = filename
        else:
            #check in cache of filenames already done.
            fname = self._fncache.get(filename, None)
            if not fname:
                #not in cache, get the absolute path
                fname = os.path.abspath(filename)
                fname = os.path.normcase(fname)
                self._fncache[filename] = fname
        return fname

    def _check_files(self, filename, filelist):
        """
        Internal method to check if the file is included in the list (or included
        by a wildcard *).Returns True/False.
        """
        #get absolute filepath form
        fname = self._abs_filename(filename)

        #loop over filelist entries checking each one - return on first positive.
        for f in filelist:
            #a wildcard - check if fname startswith the path upto the *
            if f.endswith('*'):
                if fname.startswith(f[:-1]):
                    return True
            #a normal path - check if fname is this path.
            elif fname == f:
                return True
        return False

    def _process_dbg_command(self, line):
        """
        Check for, and perform user debugger commands.
        Returns handled=True/False
        """
        ##Check for debugger comment commands:
        if line.startswith('#') is False:
            return False

        cmd = line.rstrip('\n') #remove the trailing newline for this check
        parts = cmd.split(' ') #split into command and arguments
        cmd = parts[0]
        args = parts[1:]
        cmd = cmd.lower() #convert to all lower case:

        #step
        if cmd in ['#step', '#s']:
            res = self.step()
            if res is False:
                self.write_debug('Cannot step here')
            else:
                #no need to prompt as stepping
                return True
        #step in
        elif cmd in ['#stepin', '#si']:
            res = self.step_in()
            if res is False:
                self.write_debug('Cannot step in here')
            else:
                #no need to prompt as stepping
                return True
        #stepout
        elif cmd in ['#stepout', '#so']:
            res = self.step_out()
            if res is False:
                self.write_debug('Cannot step out here')
            else:
                #no need to prompt as stepping
                return True

        #set scope
        elif cmd in ['#setscope', '#ss']:
            if len(args) != 1:
                level = 0
            try:
                level = int(args[0])
            except:
                level = args[0]
            res = self.set_scope(level)
            if res is False:
                msg = 'Usage: #setscope level (0 to %d)'%(len(self._scopes)-1)
                self.write_debug(msg)
        #resume
        elif cmd in ['#resume', '#r']:
            res = self.resume()
            if res is False:
                self.write_debug('Cannot resume here')
            else:
                #no need to prompt as resuming
                return True
            return True
        #end debugging
        elif cmd in ['#end', '#e']:
            self.end()
            return True
        #help
        elif cmd in ['#help', '#h']:
            self.write_debug(help_msg)

        elif cmd in ['#line', '#l']:
            frame = self._frames[self._active_scope]
            tb = inspect.getframeinfo(frame)
            if tb.code_context is None:
                self.write_debug('Source line unavailable')
            else:
                self.write_debug(tb.code_context[tb.index])
        elif cmd in ['#stop']:
            self.stop_code()
            return True
        else:
            return False

        #Prompt for a new command and return
        self.prompt()
        return True

    def _process_dbg_source(self, line):
        """
        Process a line of user input as python source to execute in the active
        scope
        """
        ##line is user python command compile it
        ismore, code, err = self.compiler.compile(line)

        #need more
        #   - tell the console to prompt for more
        if ismore:
            self.prompt(ismore=True)
            return

        #syntax error
        #   - compiler will output the error
        #   - tell the console to prompt for new command
        if err:
            self.prompt(iserr=True)
            return

        #no code object - could be a blank line
        if code is None:
            self.prompt()
            return

        ##run the code in the active scope
        _, frame, g, l = self.get_scope(self._active_scope)
        try:
            exec(code, g, l)
        except SystemExit:
            self.write_debug('Blocking system exit')
        except KeyboardInterrupt:
            self._paused = False
            raise KeyboardInterrupt
        except:
            #engine wanted to stop anyway - probably wxPython keyboard interrupt error
            if self._stop is True:
                self._paused = False
                raise KeyboardInterrupt

            #error in user code.
            self.compiler.show_traceback()

        #update the locals
        self._update_frame_locals(frame)

        ##Finsihed running the code - prompt for a new command
        # add the command to history
        dp.send('shell.addToHistory', command=line)
        self.prompt()
    def write_debug(self, string):
        """
        Write a debugger message to the controlling console
        """
        print(string)

    def prompt(self, ismore=False, iserr=False):
        dp.send('shell.prompt', ismore=ismore, iserr=iserr)

"""
Engine misc.

Various engine utility functions/classes
"""
# A general purpose list type object used for storing dictionaries these can
# then be filtered by key.
# Used to store breakpoints in both the engine debugger (engine process) and
# engine manager(gui process) where breakpoints are stored as dictionaries
class DictList(object):
    def __init__(self, dicts=None, default=None):
        """
        Create a list like container object for dictionaries with the ability to
        look up dicts by key value or by index.

        dicts - is a sequence of dictionaries to populate the DictList with.
        default - a defualt dictionary to use to create a new dictionary in the
        list.

        Example.

        >>> person1 = {'Name':'John', 'Age':53}
        >>> person2 = {'Name':'Bob', 'Age':53}
        >>> person3 = {'Name':'Sally', 'Age':31}
        >>> default = {'Name':'', 'Age':0}
        >>> dlist = DictList((person1,person2,person3),default)

        >>> #Filter by age
        >>> dlist.filter(keys=('Age',),values=(53,))
        [{'Age': 53, 'Name': 'John'}, {'Age': 53, 'Name': 'Bob'}]

        >>> #Filter by age and name
        >>> dlist.filter(keys=('Age','Name'),values=(53,'John'))
        [{'Age': 53, 'Name': 'John'}]

        >>> #Add a new dictionary
        >>> dlist.new()
        {'Age': 0, 'Name': ''}
        """
        if dicts is None:
            dicts = []
        if default is None:
            default = {}
        self._dicts = []
        for d in dicts:
            self._dicts.append(d)
        self._default = default

    def clear(self):
        """Remove all items"""
        self._dicts = []

    def index(self, d):
        """Find the index of a dictionary in the list"""
        return self._dicts.index(d)

    def pop(self, index):
        """Remove the dictionary at the index given"""
        return self._dicts.pop(index)

    def items(self, key=None):
        """
        Return a list of all dictionaries in the list. If the optional key is
        given it will returns a list of the values of all dicts which have that
        key.
        """
        if key is None:
            return self._dicts

        #get the key values
        dicts = []
        for d in self._dicts:
            if key in d:
                dicts.append(d[key])
        return dicts

    def filter(self, keys=(), values=()):
        """
        Filter the dictionaries in the list to return only those
        with all matching key value pairs.
        """
        dicts = self._dicts
        #filter for each key,value in
        for key, value in zip(keys, values):
            self._fkey = key
            self._fvalue = value
            dicts = list(filter(self._filter, dicts))
            self._fkey = None
            self._fvalue = None
        return dicts

    def values(self, key):
        """
        Return a list of all values a given key has in the dictionarys.
        """
        values = []
        for i in self.items():
            value = i[key]
            if value not in values:
                values.append(value)
        return values

    def append(self, d):
        """
        Append a dictionary to the list.
        """
        #check item
        if isinstance(d, dict) is False:
            raise ValueError('Expected a dictionary')
        self._dicts.append(d)

    def new(self):
        """
        Create and append a new dictionary to the list. If a default dictionary
        has been set a shallow copy will made. The new dictionary is returned.
        """
        d = self._default.copy()
        self.append(d)
        return d

    def remove(self, d):
        """
        Remove the dictionary from the list and return it.
        """
        n = self.index(d)
        return self.pop(n)

    def set_default(self, d):
        if isinstance(d, dict) is False:
            raise ValueError('Default should be a dictionary')

    def _filter(self, d):
        """internal method to find matching items"""
        #d is the dictionary to check for a match
        #self._fkey, self._fvalue are stored before calling this function and
        #are the key:value to match
        if self._fkey in d:
            return d[self._fkey] == self._fvalue
        return False

    def __len__(self):
        return len(self._dicts)

    def __iter__(self):
        return self._dicts.__iter__()

    def __getitem__(self, index):
        return self._dicts[index]

    def __setitem__(self, index, d):
        #index store new item
        if isinstance(d, dict) is False:
            raise ValueError('Expected a dictionary')
        self._dicts[index] = d

    def __repr__(self):
        s = 'DictList('+self._dicts.__repr__()+')'
        return s

"""
Engine Compiler

Handles the compilation of source and formating exceptions and tracebacks for
the engine.
"""
class EngineCompiler(Compile):
    def __init__(self):
        Compile.__init__(self)

        #the number of lines to remove from the traceback line count,
        #for multi line hack in compilation stage
        self._lineadjust = 0

        #source buffer to get print line of source in exception
        self._buffer = ''

        #register message handlers
        dp.connect(self.future_flag, 'debugger.futureflag')

    def release(self):
        dp.disconnect(self.future_flag, 'debugger.futureflag')

    # Interface methods
    def set_compiler_flag(self, flag, is_set=True):
        """
        Set or unset a __future__ compiler flag
        """
        if is_set:
            self.flags |= flag
        else:
            self.flags &= ~flag

    def compile(self, source):
        """
        Compile source.
        Returns (more,code,err) where:

        more        -   Bool indicating whether more is expected
        code        -   the compiled code object if any
        err         -   True if syntax error, false otherwise
        """
        ##to enable more lines when the current code is ok but not finished we
        ##remove the final \n, this means the line must have \n\n to be complete.
        #if source[-1]=='\n':
        #    source = source[:-1]
        # Check for source consisting of only blank lines and comments
        for line in source.split("\n"):
            line = line.strip()
            if line and line[0] != '#':
                break               # Leave it alone
        else:
            source = ""
        ##check that the line is not empty
        if source.lstrip() == '':
            return False, None, False

        ##to enable multiple lines to be compiled at once we use a cheat...
        ##everything is enclosed in if True: block so that it will compile as a
        ##single line, but need to check that there is no indentation error...
        if source[0] != ' ': #check for first line indentation error
            self._lineadjust = -1
            lastline = source.split('\n')[-1]
            source = "if True:\n " + source.replace('\n', '\n ')
            #the old source ended with a '\n' no more to come so add '\n'
            #so that it compiles
            if source.endswith('\n '):
                source = source+'\n'
            #also if the last line is zero indent add a \n as the block is also
            #complete
            if (len(lastline)-len(lastline.lstrip())) == 0:
                source = source+'\n'
        else:
            self._lineadjust = 0

        #store source in buffer
        self._buffer = source

        ##now compile as usual.
        filename = "<Engine input>"
        symbol = "single"
        try:
            code = _maybe_compile(self, source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1 - syntax error
            self.show_syntaxerror()
            return False, None, True

        if code is None:
            # Case 2 - more needed
            return True, None, False

        # Case 3 - compile to code
        return False, code, False

    def show_syntaxerror(self):
        """
        Display the syntax error that just occurred.
        This doesn't display a stack trace because there isn't one.

        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).

        taken from: code.InteractiveInterpreter
        """
        filename = "<Engine input>"

        errtype, value, sys.last_traceback = sys.exc_info()
        sys.last_type = errtype
        sys.last_value = value

        try:
            msg, (dummy_filename, lineno, offset, line) = value
        except:
            # Not the format we expect; leave it alone
            pass
        else:
            if dummy_filename == filename:
                #(lineno-1 due to multiline hack in compile source)
                value = errtype(msg, (filename, lineno+self._lineadjust, offset, line))
            else:
                value = errtype(msg, (dummy_filename, lineno, offset, line))
            sys.last_value = value
        err = traceback.format_exception_only(errtype, value)
        map(sys.stderr.write, err)

    def show_traceback(self):
        """
        Display the exception that just occurred.
        We remove the first stack item because it is our own code and adjust the
        line numbers for any engine inputs.
        modified from: code.InteractiveInterpreter
        """
        try:
            typ, value, sys.last_traceback = sys.exc_info()
            sys.last_type = typ
            sys.last_value = value
            tblist = traceback.extract_tb(sys.last_traceback)
            del tblist[:1] #in our code so remove

            for n in range(0, len(tblist)):
                filename, lineno, offset, line = tblist[n]
                if filename == "<Engine input>":
                    #alter line number
                    tblist[n] = (filename, lineno+self._lineadjust, offset, line)
                lst = traceback.format_list(tblist)
                if lst:
                    lst.insert(0, "Traceback (most recent call last):\n")
                lst[len(lst):] = traceback.format_exception_only(typ, value)
            map(sys.stderr.write, lst)
        except:
            pass
    # Message handlers
    def future_flag(self, msg):
        """enable or disable a __future__ feature using flags"""
        flag, is_set = msg.get_data()
        self.set_compiler_flag(flag, is_set)
