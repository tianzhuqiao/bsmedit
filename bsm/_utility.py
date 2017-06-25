"""define some utility functions"""
import wx
def MakeBitmap(red, green, blue, alpha=128):
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

