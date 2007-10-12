

from wnd.controls import menu
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class ExplMenu(menu.Menu):
	
	def __init__(self, main):
		menu.Menu.__init__(self)
		self.Main= main

		p= self.Popup('&File', IDM_FILE)
		p.Item('Exit', IDM_FILE_QUIT)

		p= self.Popup('&Mark', IDM_MARK)
		p.Item('&Select Group...', IDM_MARK_SELECTGROUP, 'disabled') # not impl

		p= self.Popup('&panes', IDM_PANES)
		p.Item('Pane1   Allow navigate', IDM_PANES_ALLOWNAVIGATE_1)
		p.Item('              Show Folders', IDM_PANES_SHOWFOLDERS_1)
		
		p.Separator(0)
		
		p.Item('Pane 2   Allow navigate', IDM_PANES_ALLOWNAVIGATE_2)
		p.Item('               Show Folders', IDM_PANES_SHOWFOLDERS_2)
		

		

	def handle_menu_msg(self, hwnd, msg, wp, lp):
				
		
		if msg=='menu popup':
			panes= self.GetPopup(IDM_PANES)
						
			if wp== panes.handle:
				
				##
				if self.Main.DirList1.IsNavigateAllowed():
					self.Check(IDM_PANES_ALLOWNAVIGATE_1)
				else:
					self.Uncheck(IDM_PANES_ALLOWNAVIGATE_1)

				if self.Main.DirList1.AreFoldersVisible():
					self.Check(IDM_PANES_SHOWFOLDERS_1)
				else:
					self.Uncheck(IDM_PANES_SHOWFOLDERS_1)



								
				##
				if self.Main.DirList2.IsNavigateAllowed():
					self.Check(IDM_PANES_ALLOWNAVIGATE_2)
				else:
					self.Uncheck(IDM_PANES_ALLOWNAVIGATE_2)
				
				if self.Main.DirList2.AreFoldersVisible():
					self.Check(IDM_PANES_SHOWFOLDERS_2)
				else:
					self.Uncheck(IDM_PANES_SHOWFOLDERS_2)
			

		
		elif msg=='menu choice':
			if lp[0]== IDM_FILE_QUIT:
				self.Main.Close()


			elif lp[0]==IDM_PANES_ALLOWNAVIGATE_1:
				self.CheckUncheck(lp[0])
				self.Main.DirList1.AllowNavigate(self.IsChecked(lp[0]))
								
			elif lp[0]==IDM_PANES_ALLOWNAVIGATE_2:
				self.CheckUncheck(lp[0])
				self.Main.DirList2.AllowNavigate(self.IsChecked(lp[0]))
								
			elif lp[0]==IDM_PANES_SHOWFOLDERS_1:
				self.CheckUncheck(lp[0])
				self.Main.DirList1.ShowFolders(self.IsChecked(lp[0]))
			
			elif lp[0]==IDM_PANES_SHOWFOLDERS_2:
				self.CheckUncheck(lp[0])
				self.Main.DirList2.ShowFolders(self.IsChecked(lp[0]))

		
			
			
IDM_FILE= 1000
IDM_FILE_QUIT= IDM_FILE +1

IDM_MARK= 2000
IDM_MARK_SELECTGROUP= IDM_MARK +1

IDM_VIEW= 3000

IDM_PANES= 4000
IDM_PANES_ALLOWNAVIGATE_1= IDM_PANES +1
IDM_PANES_ALLOWNAVIGATE_2= IDM_PANES +2
IDM_PANES_SHOWFOLDERS_1= IDM_PANES +3
IDM_PANES_SHOWFOLDERS_2= IDM_PANES +4



#****************************************************************************
#****************************************************************************
