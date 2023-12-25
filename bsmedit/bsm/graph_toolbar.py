import logging
import pathlib
import wx
import numpy as np
import PIL
import matplotlib as mpl
from matplotlib.backends.backend_wx import NavigationToolbar2
from matplotlib import cbook
from  ..aui import aui

_log = logging.getLogger(__name__)

class GraphToolbar(NavigationToolbar2, aui.AuiToolBar):
    def __init__(self, canvas, coordinates=True, *, style=0,
                 agwStyle=aui.AUI_TB_OVERFLOW, **kwargs):
        aui.AuiToolBar.__init__(self, canvas.GetParent(), -1, style=style,
                                agwStyle=agwStyle, **kwargs)


        if 'wxMac' in wx.PlatformInfo:
            self.SetToolBitmapSize((24, 24))
        self.wx_ids = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.AddSeparator()
                continue
            self.wx_ids[text] = (
                self.AddTool(
                    -1,
                    bitmap=self._icon(f"{image_file}.png"),
                    disabled_bitmap=wx.NullBitmap,
                    label=text, short_help_string=tooltip_text,
                    kind=(wx.ITEM_CHECK if text in ["Pan", "Zoom"]
                          else wx.ITEM_NORMAL))
                .GetId())
            self.Bind(wx.EVT_TOOL, getattr(self, callback),
                      id=self.wx_ids[text])

        self._coordinates = coordinates
        if self._coordinates:
            self.AddStretchSpacer()
            self._label_text = wx.StaticText(self, style=wx.ALIGN_RIGHT)
            self.AddControl(self._label_text)

        self.Realize()

        NavigationToolbar2.__init__(self, canvas)

    @staticmethod
    def _icon(name):
        """
        Construct a `wx.Bitmap` suitable for use as icon from an image file
        *name*, including the extension and relative to Matplotlib's "images"
        data directory.
        """
        image = np.array(PIL.Image.open(cbook._get_data_path("images", name)))
        try:
            dark = wx.SystemSettings.GetAppearance().IsDark()
        except AttributeError:  # wxpython < 4.1
            # copied from wx's IsUsingDarkBackground / GetLuminance.
            bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
            fg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            # See wx.Colour.GetLuminance.
            bg_lum = (.299 * bg.red + .587 * bg.green + .114 * bg.blue) / 255
            fg_lum = (.299 * fg.red + .587 * fg.green + .114 * fg.blue) / 255
            dark = fg_lum - bg_lum > .2
        if dark:
            fg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            black_mask = (image[..., :3] == 0).all(axis=-1)
            image[black_mask, :3] = (fg.Red(), fg.Green(), fg.Blue())
        return wx.Bitmap.FromBufferRGBA(
            image.shape[1], image.shape[0], image.tobytes())

    def _update_buttons_checked(self):
        if "Pan" in self.wx_ids:
            self.ToggleTool(self.wx_ids["Pan"], self.mode.name == "PAN")
        if "Zoom" in self.wx_ids:
            self.ToggleTool(self.wx_ids["Zoom"], self.mode.name == "ZOOM")

    def zoom(self, *args):
        super().zoom(*args)
        self._update_buttons_checked()

    def pan(self, *args):
        super().pan(*args)
        self._update_buttons_checked()

    def save_figure(self, *args):
        # Fetch the required filename and file type.
        filetypes, exts, filter_index = self.canvas._get_imagesave_wildcards()
        default_file = self.canvas.get_default_filename()
        dialog = wx.FileDialog(
            self.canvas.GetParent(), "Save to file",
            mpl.rcParams["savefig.directory"], default_file, filetypes,
            wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        dialog.SetFilterIndex(filter_index)
        if dialog.ShowModal() == wx.ID_OK:
            path = pathlib.Path(dialog.GetPath())
            _log.debug('%s - Save file path: %s', type(self), path)
            fmt = exts[dialog.GetFilterIndex()]
            ext = path.suffix[1:]
            if ext in self.canvas.get_supported_filetypes() and fmt != ext:
                # looks like they forgot to set the image type drop
                # down, going with the extension.
                _log.warning('extension %s did not match the selected '
                             'image type %s; going with %s',
                             ext, fmt, ext)
                fmt = ext
            # Save dir for next time, unless empty str (which means use cwd).
            if mpl.rcParams["savefig.directory"]:
                mpl.rcParams["savefig.directory"] = str(path.parent)
            try:
                self.canvas.figure.savefig(path, format=fmt)
            except Exception as e:
                dialog = wx.MessageDialog(
                    parent=self.canvas.GetParent(), message=str(e),
                    caption='Matplotlib error')
                dialog.ShowModal()
                dialog.Destroy()

    def draw_rubberband(self, event, x0, y0, x1, y1):
        height = self.canvas.figure.bbox.height
        self.canvas._rubberband_rect = (x0, height - y0, x1, height - y1)
        self.canvas.Refresh()

    def remove_rubberband(self):
        self.canvas._rubberband_rect = None
        self.canvas.Refresh()

    def set_message(self, s):
        if self._coordinates:
            self._label_text.SetLabel(s)

    def set_history_buttons(self):
        can_backward = self._nav_stack._pos > 0
        can_forward = self._nav_stack._pos < len(self._nav_stack._elements) - 1
        if 'Back' in self.wx_ids:
            self.EnableTool(self.wx_ids['Back'], can_backward)
        if 'Forward' in self.wx_ids:
            self.EnableTool(self.wx_ids['Forward'], can_forward)
        self.Refresh(False)
        self.Update()
