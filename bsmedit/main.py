import multiprocessing
import wx
import click
from .mainframe import MainFrame
from .c2p import APP_ASSERT_DIALOG

class RunApp(wx.App):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        wx.Log.SetActiveTarget(wx.LogStderr())

        self.SetAssertMode(APP_ASSERT_DIALOG)

        frame = MainFrame(None, **self.kwargs)
        frame.Show(True)
        self.SetTopWindow(frame)
        self.frame = frame
        return True

@click.command()
@click.option('--config', '-c', default='bsmedit',
              help="Set configuration file name, default 'bsmedit'.")
@click.option('--path', '-p', multiple=True, type=click.Path(exists=True),
              help="Add external module path.")
@click.option('--ignore-perspective', '-i', is_flag=True,
              help="Do not load perspective.")
@click.option('--spawn', is_flag=True,
              help="Start a process with method 'spawn'.")
@click.argument('module', nargs=-1)
def main(config, path, ignore_perspective, spawn, module):
    if spawn and hasattr(multiprocessing, 'set_start_method'):
        multiprocessing.set_start_method('spawn')
    app = RunApp(config=config, ignore_perspective=ignore_perspective,
                 path=path, module=module)
    app.MainLoop()

if __name__ == '__main__':
    main()
