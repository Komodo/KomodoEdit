
import wnd
from wnd.controls.button import Button
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class MyWindow(wnd.Window):
	def __init__(self):
		wnd.Window.__init__(self, 'hello World', 'Hello World!', 50, 50, 180, 100, 'sysmenu')
		
		self.button1=Button(self, 'Hello', 20, 20, 60, 30)
		self.button1.onMSG=self.on_button
		self.button2=Button(self, 'Quit', 85, 20, 60, 30)
		self.button2.onMSG=self.on_button
		
	def on_button(self, hwnd, msg, wp, lp):
		if msg=="command":
			if hwnd==self.button1.Hwnd:
				print 'Hello World !'
			elif hwnd==self.button2.Hwnd:
				self.Close()



w = MyWindow()
w.Run()