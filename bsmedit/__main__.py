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
@click.option('--ignore-perspective', '-i', is_flag=True,
              help="Do not load perspective.")
@click.option('--path', '-p', multiple=True, type=click.Path(exists=True),
              help="Add external module path.")
@click.argument('module', nargs=-1)
def main(config, ignore_perspective, path, module):
    app = RunApp(config=config, ignore_perspective=ignore_perspective,
                 path=path, module=module)
    app.MainLoop()

if __name__ == '__main__':
    main()
