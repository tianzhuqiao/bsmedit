import wx
import wx.py.dispatcher as dp
from bsmutility.shell import Shell
from bsmutility.bsminterface import Interface
from ..version import __version__


class SHELL(Interface):
    shell = None
    @classmethod
    def initialize(cls, frame, **kwargs):
        super().initialize(frame, **kwargs)

        cls.debug = kwargs.get('debug', False)
        ns = {}
        ns['wx'] = wx
        ns['app'] = wx.GetApp()
        ns['frame'] = cls.frame
        intro = f'Welcome To {cls.frame.GetLabel()} ' + __version__
        cls.shell = Shell(cls.frame, introText=intro, locals=ns)
        active = kwargs.get('active', True)
        direction = kwargs.get('direction', 'top')
        dp.send(signal="frame.add_panel",
                panel=cls.shell,
                active=active,
                title="Shell",
                direction=direction,
                name='shell')

    @classmethod
    def initialized(cls):
        super().initialized()
        if cls.shell and not cls.debug:
            # not redirect if in debug mode
            redirect = True
            resp = dp.send('frame.get_config', group='shell', key='redirect_stdout')
            if resp and resp[0][1] is not None:
                redirect = resp[0][1]
            cls.shell.redirectStdout(redirect)

            redirect = True
            resp = dp.send('frame.get_config', group='shell', key='redirect_stderr')
            if resp and resp[0][1] is not None:
                redirect = resp[0][1]
            cls.shell.redirectStderr(redirect)

    @classmethod
    def uninitialized(cls):
        super().uninitialized()
        if cls.shell:
            cls.shell.redirectStdout(False)
            cls.shell.redirectStderr(False)
            dp.send('frame.delete_panel', panel=cls.shell)
            cls.shell = None

def bsm_initialize(frame, **kwargs):
    SHELL.initialize(frame, **kwargs)
