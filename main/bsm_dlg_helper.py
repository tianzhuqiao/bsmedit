# -*- coding: utf-8 -*- 

###########################################################################
## Python code generated with wxFormBuilder (version Sep  8 2010)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

from frameplus import framePlus
import wx

###########################################################################
## Class mainFrame
###########################################################################

class mainFrame ( framePlus ):
	
	def __init__( self, parent ):
		framePlus.__init__( self, parent, id = wx.ID_ANY, title = u"BSMEdit", pos = wx.DefaultPosition, size = wx.Size( 800,600 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		
		self.menubar = wx.MenuBar( 0 )
		self.menuFile = wx.Menu()
		self.menuNew = wx.Menu()
		#self.menuNewPythonScript = wx.MenuItem( self.menuNew, wx.ID_ANY, u"Python Script"+ u"\t" + u"Ctrl+N", wx.EmptyString, wx.ITEM_NORMAL )
		#self.menuNew.AppendItem( self.menuNewPythonScript )
		
		self.menuFile.AppendSubMenu( self.menuNew, u"New" )
		
		self.menuOpen = wx.Menu()
		#self.menuOpenPythonScript = wx.MenuItem( self.menuOpen, wx.ID_ANY, u"Python Script"+ u"\t" + u"Ctrl+O", wx.EmptyString, wx.ITEM_NORMAL )
		#self.menuOpen.AppendItem( self.menuOpenPythonScript )
		
		self.menuFile.AppendSubMenu( self.menuOpen, u"Open" )
		
		self.menuFile.AppendSeparator()
		
		self.menuLoadPrj = wx.MenuItem( self.menuFile, wx.ID_ANY, u"&Open project"+ u"\t" + u"Ctrl-L", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuFile.AppendItem( self.menuLoadPrj )
		
		self.menuFile.AppendSeparator()
		
		self.menuCloseSim = wx.MenuItem( self.menuFile, wx.ID_ANY, u"&Close Project", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuFile.AppendItem( self.menuCloseSim )
		
		self.menuFile.AppendSeparator()
		
		self.menuSave = wx.MenuItem( self.menuFile, wx.ID_ANY, u"&Save Project", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuFile.AppendItem( self.menuSave )
		
		self.menuSaveAs = wx.MenuItem( self.menuFile, wx.ID_ANY, u"Save Project &As", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuFile.AppendItem( self.menuSaveAs )
		
		self.menuFile.AppendSeparator()
		
		self.menuRecentFiles = wx.Menu()
		self.menuFile.AppendSubMenu( self.menuRecentFiles, u"Recent Files" )
		
		self.menuRecentPrj = wx.Menu()
		self.menuFile.AppendSubMenu( self.menuRecentPrj, u"&Recent Projects" )
		
		self.menuFile.AppendSeparator()
		
		self.menuQuit = wx.MenuItem( self.menuFile, wx.ID_CLOSE, u"&Quit", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuFile.AppendItem( self.menuQuit )
		
		self.menubar.Append( self.menuFile, u"&File" ) 
		
		self.menuView = wx.Menu()
		self.menuLayout = wx.Menu()
		
		self.menuSaveCurLayout = wx.MenuItem( self.menuLayout, wx.ID_ANY, u"&Save current ", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuLayout.AppendItem( self.menuSaveCurLayout )
		
		self.menuDelLayout = wx.MenuItem( self.menuLayout, wx.ID_ANY, u"&Delete layout", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuLayout.AppendItem( self.menuDelLayout )
		self.menuLayout.AppendSeparator()
		
		self.menuView.AppendSubMenu( self.menuLayout, u"&Layout" )
		
		self.menuToolbar = wx.Menu()
		self.menuToolbarStd = wx.MenuItem( self.menuToolbar, wx.ID_ANY, u"&Standard toolbar", wx.EmptyString, wx.ITEM_CHECK )
		self.menuToolbar.AppendItem( self.menuToolbarStd )
		
		self.menuToolbar.AppendSeparator()
		
		self.menuView.AppendSubMenu( self.menuToolbar, u"&Toolbars" )
		
		self.menuView.AppendSeparator()
		
		self.menuPanes = wx.Menu()
		self.menuView.AppendSubMenu( self.menuPanes, u"Panels" )
		
		self.menubar.Append( self.menuView, u"&View" ) 
		
		self.menuTool = wx.Menu()
		self.menuProperties = wx.MenuItem( self.menuTool, wx.ID_ANY, u"&Properties", u"Show/hide the project panel", wx.ITEM_NORMAL )
		self.menuTool.AppendItem( self.menuProperties )
		
		self.menubar.Append( self.menuTool, u"&Tools" ) 
		
		self.menuPLugins = wx.Menu()
		self.menuMagPlugins = wx.MenuItem( self.menuPLugins, wx.ID_ANY, u"&Manage plugins", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuPLugins.AppendItem( self.menuMagPlugins )
		
		self.menuPLugins.AppendSeparator()
		
		self.menubar.Append( self.menuPLugins, u"&Plugins" ) 
		
		self.menuHelp = wx.Menu()
		self.menuHome = wx.MenuItem( self.menuHelp, wx.ID_ANY, u"&Home", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuHelp.AppendItem( self.menuHome )
		
		self.menuContact = wx.MenuItem( self.menuHelp, wx.ID_ANY, u"&Contact", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuHelp.AppendItem( self.menuContact )
		
		self.menuHelp.AppendSeparator()
		
		self.menuAbout = wx.MenuItem( self.menuHelp, wx.ID_ABOUT, u"&About", wx.EmptyString, wx.ITEM_NORMAL )
		self.menuHelp.AppendItem( self.menuAbout )
		
		self.menubar.Append( self.menuHelp, u"&Help" ) 
		
		self.SetMenuBar( self.menubar )
		
		
		# Connect Events
		self.Bind( wx.EVT_CLOSE, self.OnClose )
		#self.Bind( wx.EVT_MENU, self.OnNewPythonScript, id = self.menuNewPythonScript.GetId() )
		#self.Bind( wx.EVT_MENU, self.OnOpenPythonScript, id = self.menuOpenPythonScript.GetId() )
		self.Bind( wx.EVT_MENU, self.OnFileLoadProject, id = self.menuLoadPrj.GetId() )
		self.Bind( wx.EVT_MENU, self.OnFileCloseProject, id = self.menuCloseSim.GetId() )
		self.Bind( wx.EVT_MENU, self.OnFileSaveProject, id = self.menuSave.GetId() )
		self.Bind( wx.EVT_MENU, self.OnFileSaveProjectAs, id = self.menuSaveAs.GetId() )
		self.Bind( wx.EVT_MENU, self.OnFileQuit, id = self.menuQuit.GetId() )
		self.Bind( wx.EVT_MENU, self.OnViewSaveLayout, id = self.menuSaveCurLayout.GetId() )
		self.Bind( wx.EVT_MENU, self.OnViewDeleteLayout, id = self.menuDelLayout.GetId() )
		self.Bind( wx.EVT_MENU, self.OnViewToggleBar, id = self.menuToolbarStd.GetId() )
		self.Bind( wx.EVT_UPDATE_UI, self.OnUpdateViewToggleBar, id = self.menuToolbarStd.GetId() )
		self.Bind( wx.EVT_MENU, self.OnToolsProperties, id = self.menuProperties.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPluginsManage, id = self.menuMagPlugins.GetId() )
		self.Bind( wx.EVT_MENU, self.OnHelpHome, id = self.menuHome.GetId() )
		self.Bind( wx.EVT_MENU, self.OnHelpContact, id = self.menuContact.GetId() )
		self.Bind( wx.EVT_MENU, self.OnHelpAbout, id = self.menuAbout.GetId() )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnClose( self, event ):
		event.Skip()
	
	def OnNewPythonScript( self, event ):
		event.Skip()
	
	def OnOpenPythonScript( self, event ):
		event.Skip()
	
	def OnFileLoadProject( self, event ):
		event.Skip()
	
	def OnFileCloseProject( self, event ):
		event.Skip()
	
	def OnFileSaveProject( self, event ):
		event.Skip()
	
	def OnFileSaveProjectAs( self, event ):
		event.Skip()
	
	def OnFileQuit( self, event ):
		event.Skip()
	
	def OnViewSaveLayout( self, event ):
		event.Skip()
	
	def OnViewDeleteLayout( self, event ):
		event.Skip()
	
	def OnViewToggleBar( self, event ):
		event.Skip()
	
	def OnUpdateViewToggleBar( self, event ):
		event.Skip()
	
	def OnToolsProperties( self, event ):
		event.Skip()
	
	def OnPluginsManage( self, event ):
		event.Skip()
	
	def OnHelpHome( self, event ):
		event.Skip()
	
	def OnHelpContact( self, event ):
		event.Skip()
	
	def OnHelpAbout( self, event ):
		event.Skip()
	

###########################################################################
## Class panelConfig
###########################################################################

class panelConfig ( wx.Panel ):
	
	def __init__( self, parent ):
		wx.Panel.__init__ ( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.TAB_TRAVERSAL )
		
		bSizer1 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_toolBar = wx.ToolBar( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TB_FLAT ) 
		self.m_toolBar.AddLabelTool( wx.ID_ANY, u"Enable", wx.Bitmap( u"res/accept.xpm", wx.BITMAP_TYPE_ANY ), wx.NullBitmap, wx.ITEM_NORMAL, u"Enable", wx.EmptyString ) 
		self.m_toolBar.AddLabelTool( wx.ID_ANY, u"Disable", wx.Bitmap( u"res/cancel.xpm", wx.BITMAP_TYPE_ANY ), wx.NullBitmap, wx.ITEM_NORMAL, u"Disable", wx.EmptyString ) 
		self.m_toolBar.AddSeparator()
		self.m_toolBar.AddLabelTool( wx.ID_ANY, u"Config", wx.Bitmap( u"res/cog.xpm", wx.BITMAP_TYPE_ANY ), wx.NullBitmap, wx.ITEM_NORMAL, u"Config", wx.EmptyString ) 
		self.m_toolBar.Realize()
		
		bSizer1.Add( self.m_toolBar, 0, wx.EXPAND, 5 )
		
		self.m_splitter = wx.SplitterWindow( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.SP_NOBORDER )
		self.m_splitter.Bind( wx.EVT_IDLE, self.m_splitterOnIdle )
		
		self.m_panelPlugin = wx.Panel( self.m_splitter, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		bSizer2 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_listPlugin = wx.ListCtrl( self.m_panelPlugin, wx.ID_ANY, wx.DefaultPosition, wx.Size( 400,200 ), wx.LC_HRULES|wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_SORT_ASCENDING|wx.LC_VRULES )
		bSizer2.Add( self.m_listPlugin, 1, wx.ALL|wx.EXPAND, 0 )
		
		self.m_panelPlugin.SetSizer( bSizer2 )
		self.m_panelPlugin.Layout()
		bSizer2.Fit( self.m_panelPlugin )
		self.m_panelInfo = wx.Panel( self.m_splitter, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		bSizer3 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_tcInfo = wx.TextCtrl( self.m_panelInfo, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,150 ), wx.TE_AUTO_URL|wx.TE_MULTILINE|wx.TE_RICH )
		bSizer3.Add( self.m_tcInfo, 1, wx.ALL|wx.EXPAND, 0 )
		
		self.m_panelInfo.SetSizer( bSizer3 )
		self.m_panelInfo.Layout()
		bSizer3.Fit( self.m_panelInfo )
		self.m_splitter.SplitHorizontally( self.m_panelPlugin, self.m_panelInfo, 0 )
		bSizer1.Add( self.m_splitter, 1, wx.EXPAND, 5 )
		
		self.SetSizer( bSizer1 )
		self.Layout()
		
		# Connect Events
		self.Bind( wx.EVT_TOOL, self.OnToolEnable, id = wx.ID_ANY )
		self.Bind( wx.EVT_UPDATE_UI, self.OnUpdateToolEnable, id = wx.ID_ANY )
		self.Bind( wx.EVT_TOOL, self.OnToolDisable, id = wx.ID_ANY )
		self.Bind( wx.EVT_UPDATE_UI, self.OnUpdateToolDisable, id = wx.ID_ANY )
		self.Bind( wx.EVT_TOOL, self.OnToolConfig, id = wx.ID_ANY )
		self.Bind( wx.EVT_UPDATE_UI, self.OnUpdateToolConfig, id = wx.ID_ANY )
		self.m_listPlugin.Bind( wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelected )
		self.m_tcInfo.Bind( wx.EVT_TEXT_URL, self.OnTextURL )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnToolEnable( self, event ):
		event.Skip()
	
	def OnUpdateToolEnable( self, event ):
		event.Skip()
	
	def OnToolDisable( self, event ):
		event.Skip()
	
	def OnUpdateToolDisable( self, event ):
		event.Skip()
	
	def OnToolConfig( self, event ):
		event.Skip()
	
	def OnUpdateToolConfig( self, event ):
		event.Skip()
	
	def OnListItemSelected( self, event ):
		event.Skip()
	
	def OnTextURL( self, event ):
		event.Skip()
	
	def m_splitterOnIdle( self, event ):
		self.m_splitter.SetSashPosition( 0 )
		self.m_splitter.Unbind( wx.EVT_IDLE )
	

###########################################################################
## Class dlgTopSettings
###########################################################################

class dlgTopSettings ( wx.Dialog ):
	
	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"BSMEdit Settings", pos = wx.DefaultPosition, size = wx.Size( 480,360 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )
		
		self.SetSizeHintsSz( wx.Size( 480,360 ), wx.DefaultSize )
		
		bSizer1 = wx.BoxSizer( wx.VERTICAL )
		
		self.notebook = wx.Notebook( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )
		
		bSizer1.Add( self.notebook, 1, wx.EXPAND |wx.ALL, 5 )
		
		bSizer10 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.btnOK = wx.Button( self, wx.ID_OK, u"OK", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer10.Add( self.btnOK, 0, wx.ALL, 5 )
		
		self.btnCancel = wx.Button( self, wx.ID_CANCEL, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer10.Add( self.btnCancel, 0, wx.ALL, 5 )
		
		bSizer1.Add( bSizer10, 0, wx.ALIGN_RIGHT|wx.RIGHT, 5 )
		
		self.SetSizer( bSizer1 )
		self.Layout()
		
		# Connect Events
		self.btnOK.Bind( wx.EVT_BUTTON, self.OnBtnOK )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnBtnOK( self, event ):
		event.Skip()
	

###########################################################################
## Class panelGeneral
###########################################################################

class panelGeneral ( wx.Panel ):
	
	def __init__( self, parent ):
		wx.Panel.__init__ ( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( -1,-1 ), style = wx.TAB_TRAVERSAL )
		
		bSizer1 = wx.BoxSizer( wx.VERTICAL )
		
		bSizer2 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.stcPlugin = wx.StaticText( self, wx.ID_ANY, u"Plugin Path", wx.DefaultPosition, wx.Size( 80,-1 ), 0 )
		self.stcPlugin.Wrap( -1 )
		bSizer2.Add( self.stcPlugin, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )
		
		self.m_tcPlugin = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer2.Add( self.m_tcPlugin, 1, wx.ALL, 5 )
		
		self.btnPlugin = wx.Button( self, wx.ID_ANY, u"...", wx.DefaultPosition, wx.Size( 25,-1 ), 0 )
		bSizer2.Add( self.btnPlugin, 0, wx.ALL, 5 )
		
		bSizer1.Add( bSizer2, 0, wx.EXPAND, 5 )
		
		bSizer3 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.stcData = wx.StaticText( self, wx.ID_ANY, u"Data Path", wx.DefaultPosition, wx.Size( 80,-1 ), 0 )
		self.stcData.Wrap( -1 )
		bSizer3.Add( self.stcData, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )
		
		self.m_tcData = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_tcData.SetToolTipString( u"The folder to store the data" )
		
		bSizer3.Add( self.m_tcData, 1, wx.ALL, 5 )
		
		self.btnData = wx.Button( self, wx.ID_ANY, u"...", wx.DefaultPosition, wx.Size( 25,-1 ), 0 )
		bSizer3.Add( self.btnData, 0, wx.ALL, 5 )
		
		bSizer1.Add( bSizer3, 0, wx.EXPAND, 5 )
		
		self.m_cbConsole = wx.CheckBox( self, wx.ID_ANY, u"Create a console terminal (windows only)", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.m_cbConsole, 0, wx.ALL, 5 )
		
		self.SetSizer( bSizer1 )
		self.Layout()
		bSizer1.Fit( self )
		
		# Connect Events
		self.btnPlugin.Bind( wx.EVT_BUTTON, self.OnBtnPluginPath )
		self.btnData.Bind( wx.EVT_BUTTON, self.OnBtnDataPath )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnBtnPluginPath( self, event ):
		event.Skip()
	
	def OnBtnDataPath( self, event ):
		event.Skip()
	

###########################################################################
## Class dlgAbout
###########################################################################

class dlgAbout ( wx.Dialog ):
	
	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"About", pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		
		bSizer2 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_panel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		self.m_panel.SetBackgroundColour( wx.Colour( 255, 255, 255 ) )
		
		bSizer20 = wx.BoxSizer( wx.VERTICAL )
		
		bSizer21 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_bitmap = wx.StaticBitmap( self.m_panel, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer21.Add( self.m_bitmap, 0, wx.ALL|wx.EXPAND, 0 )
		
		self.m_stTitle = wx.StaticText( self.m_panel, wx.ID_ANY, u"BSMEdit 2.1", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_stTitle.Wrap( -1 )
		self.m_stTitle.SetFont( wx.Font( 28, 74, 90, 92, False, "Arial" ) )
		self.m_stTitle.SetForegroundColour( wx.Colour( 255, 128, 64 ) )
		
		bSizer21.Add( self.m_stTitle, 0, wx.ALL, 5 )
		
		self.m_stVersion = wx.StaticText( self.m_panel, wx.ID_ANY, u"Version", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_stVersion.Wrap( -1 )
		self.m_stVersion.SetFont( wx.Font( 8, 74, 90, 90, False, "Arial" ) )
		self.m_stVersion.SetForegroundColour( wx.Colour( 120, 120, 120 ) )
		
		bSizer21.Add( self.m_stVersion, 0, wx.ALL, 5 )
		
		self.m_stCopyright = wx.StaticText( self.m_panel, wx.ID_ANY, u"Copyright", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_stCopyright.Wrap( -1 )
		self.m_stCopyright.SetFont( wx.Font( 8, 74, 90, 90, False, "Arial" ) )
		
		bSizer21.Add( self.m_stCopyright, 0, wx.ALL, 5 )
		
		self.m_stBuildinfo = wx.StaticText( self.m_panel, wx.ID_ANY, u"Buildinfo", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_stBuildinfo.Wrap( -1 )
		self.m_stBuildinfo.SetFont( wx.Font( 8, 74, 90, 90, False, "Arial" ) )
		
		bSizer21.Add( self.m_stBuildinfo, 0, wx.ALL|wx.EXPAND, 5 )
		
		bSizer20.Add( bSizer21, 0, wx.EXPAND, 5 )
		
		self.m_staticline3 = wx.StaticLine( self.m_panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		bSizer20.Add( self.m_staticline3, 0, wx.EXPAND |wx.ALL, 0 )
		
		self.m_panel.SetSizer( bSizer20 )
		self.m_panel.Layout()
		bSizer20.Fit( self.m_panel )
		bSizer2.Add( self.m_panel, 1, wx.EXPAND |wx.ALL, 0 )
		
		bSizer22 = wx.BoxSizer( wx.VERTICAL )
		
		self.btnOk = wx.Button( self, wx.ID_OK, u"Ok", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer22.Add( self.btnOk, 0, wx.ALIGN_RIGHT|wx.ALL, 5 )
		
		bSizer2.Add( bSizer22, 0, wx.EXPAND, 5 )
		
		self.SetSizer( bSizer2 )
		self.Layout()
		bSizer2.Fit( self )
	
	def __del__( self ):
		pass
	

