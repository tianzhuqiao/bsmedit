from bsmutility.debugtool import DebugTool


def bsm_initialize(frame, **kwargs):
    """module initialization"""
    DebugTool.initialize(frame, **kwargs)
