import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wxagg import FigureCanvasAgg
from matplotlib.backend_bases import ResizeEvent

class FigureCanvas(FigureCanvasWxAgg):

    def _update_device_pixel_ratio(self, *args, **kwargs):
        # We need to be careful in cases with mixed resolution displays if
        # device_pixel_ratio changes.
        if self._set_device_pixel_ratio(self.GetDPIScaleFactor()):
            self.draw()

    def _on_size(self, event):
        """
        Called when wxEventSize is generated.

        In this application we attempt to resize to fit the window, so it
        is better to take the performance hit and redraw the whole window.
        """
        self._update_device_pixel_ratio()
        sz = self.GetParent().GetSizer()
        if sz:
            si = sz.GetItem(self)
        if sz and si and not si.Proportion and not si.Flag & wx.EXPAND:
            # managed by a sizer, but with a fixed size
            size = self.GetMinSize()
        else:
            # variable size
            size = self.GetClientSize()
            # Do not allow size to become smaller than MinSize
            size.IncTo(self.GetMinSize())
        if getattr(self, "_width", None):
            if size == (self._width, self._height):
                # no change in size
                return
        self._width, self._height = size
        self._isDrawn = False

        if self._width <= 1 or self._height <= 1:
            return  # Empty figure

        # Create a new, correctly sized bitmap
        dpival = self.figure.dpi
        if not wx.Platform == '__WXMSW__':
            scale = self.GetDPIScaleFactor()
            dpival /= scale
        winch = self._width / dpival
        hinch = self._height / dpival
        self.figure.set_size_inches(winch, hinch, forward=False)

        # Rendering will happen on the associated paint event
        # so no need to do anything here except to make sure
        # the whole background is repainted.
        self.Refresh(eraseBackground=False)
        ResizeEvent("resize_event", self)._process()
        self.draw_idle()

    def _mpl_coords(self, pos=None):
        """
        Convert a wx position, defaulting to the current cursor position, to
        Matplotlib coordinates.
        """
        if pos is None:
            pos = wx.GetMouseState()
            x, y = self.ScreenToClient(pos.X, pos.Y)
        else:
            x, y = pos.X, pos.Y
        # flip y so y=0 is bottom of canvas
        if not wx.Platform == '__WXMSW__':
            scale = self.GetDPIScaleFactor()
            return x*scale, self.figure.bbox.height - y*scale
        else:
            return x, self.figure.bbox.height - y

    def draw(self, drawDC=None):
        """
        Render the figure using agg.
        """
        FigureCanvasAgg.draw(self)
        self.bitmap = self._create_bitmap()
        self._isDrawn = True
        self.gui_repaint(drawDC=drawDC)

    def blit(self, bbox=None):
        # docstring inherited
        bitmap = self._create_bitmap()
        if bbox is None:
            self.bitmap = bitmap
        else:
            srcDC = wx.MemoryDC(bitmap)
            destDC = wx.MemoryDC(self.bitmap)
            x = int(bbox.x0)
            y = int(self.bitmap.GetHeight() - bbox.y1)
            destDC.Blit(x, y, int(bbox.width), int(bbox.height), srcDC, x, y)
            destDC.SelectObject(wx.NullBitmap)
            srcDC.SelectObject(wx.NullBitmap)
        self.gui_repaint()

    def _create_bitmap(self):
        """Create a wx.Bitmap from the renderer RGBA buffer"""
        rgba = self.get_renderer().buffer_rgba()
        h, w, _ = rgba.shape
        bitmap = wx.Bitmap.FromBufferRGBA(w, h, rgba)
        bitmap.SetScaleFactor(self.GetDPIScaleFactor())
        return bitmap
