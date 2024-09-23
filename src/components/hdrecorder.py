#encoding: latin-1

# Neil
# Modular Sequencer
# Copyright (C) 2006,2007,2008 The Neil Development Team
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""
Provides dialog class for hd recorder control.
"""

from gi.repository import Gtk
from gi.repository import GObject
import neil.utils as utils, os, stat
from neil.utils import new_stock_image_toggle_button, ObjectHandlerGroup
import neil.common as common
import neil.com as com
import zzub
from neil.common import MARGIN, MARGIN2, MARGIN3

class HDRecorderDialog(Gtk.Dialog):
	"""
	This Dialog shows the HD recorder, which allows recording
	the audio output to a wave file.
	"""

	__neil__ = dict(
		id = 'neil.core.hdrecorder',
		singleton = True,
		categories = [
			'viewdialog',
			'view',
		]
	)
	
	__view__ = dict(
			label = "Hard Disk Recorder",
			order = 0,
			toggle = True,
	)
	
	def __init__(self):
		"""
		Initializer.
		"""
		Gtk.Dialog.__init__(self, 
			"Hard Disk Recorder")
		self.connect('delete-event', self.hide_on_delete)
		#self.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
		#self.set_size_request(250,-1)
		self.set_resizable(False)
		btnsaveas = Gtk.Button(stock=Gtk.STOCK_SAVE_AS)
		btnsaveas.connect("clicked", self.on_saveas)
		textposition = Gtk.Label("")
		self.hgroup = ObjectHandlerGroup()
		self.btnrecord = new_stock_image_toggle_button(Gtk.STOCK_MEDIA_RECORD)
		self.hgroup.connect(self.btnrecord, 'clicked', self.on_toggle_record)
		chkauto = Gtk.CheckButton("_Auto start/stop")
		chkauto.connect("toggled", self.on_autostartstop)
		self.btnsaveas = btnsaveas
		self.textposition = textposition
		self.chkauto = chkauto
		# 0.3: DEAD
		#self.chkauto.set_active(self.master.get_auto_write())
		sizer = Gtk.VBox(False, MARGIN)		
		sizer.pack_start(btnsaveas, False, True, 0)
		sizer.pack_start(textposition, False, True, 0)
		sizer2 = Gtk.HBox(False,MARGIN)
		sizer3 = Gtk.HButtonBox()
		sizer3.set_spacing(MARGIN)
		sizer3.set_layout(Gtk.ButtonBoxStyle.START)
		sizer3.pack_start(self.btnrecord, False, True, 0)
		sizer2.pack_start(sizer3, False, True, 0)
		sizer2.pack_start(chkauto, False, True, 0)
		sizer.pack_start(sizer2, True, True, 0)
		sizer.set_border_width(MARGIN)
		self.vbox.add(sizer)
		self.filename = ''
		GObject.timeout_add(100, self.on_timer)
		eventbus = com.get('neil.core.eventbus')
		eventbus.zzub_parameter_changed += self.on_zzub_parameter_changed
		self.update_label()
		self.update_rec_button()
		
	def on_zzub_parameter_changed(self,plugin,group,track,param,value):
		player = com.get('neil.core.player')
		recorder = player.get_stream_recorder()
		if plugin == recorder:
			if (group,track,param) == (zzub.zzub_parameter_group_global,0,0):
				self.update_label()
			elif (group,track,param) == (zzub.zzub_parameter_group_global,0,1):
				self.update_rec_button(value)
				
	def update_rec_button(self, value=None):
		block = self.hgroup.autoblock()
		player = com.get('neil.core.player')
		recorder = player.get_stream_recorder()
		if value == None:
			value = recorder.get_parameter_value(zzub.zzub_parameter_group_global, 0, 1)
		self.btnrecord.set_active(value)
		self.chkauto.set_active(not recorder.get_attribute_value(0))
			
	def update_label(self):
		player = com.get('neil.core.player')
		recorder = player.get_stream_recorder()
		self.btnsaveas.set_label(recorder.describe_value(zzub.zzub_parameter_group_global, 0, 0))
		
	def on_autostartstop(self, widget):
		"""
		Handles clicks on the auto start/stop checkbox. Updates the masters
		auto_write property.
		
		@param event: Command event.
		@type event: wx.CommandEvent
		"""
		player = com.get('neil.core.player')
		recorder = player.get_stream_recorder()
		recorder.set_attribute_value(0, not widget.get_active())
		player.history_flush()
		
	def on_timer(self):
		"""
		Called by timer event. Updates controls according to current
		state of recording.
		"""
		if self.get_parent_window() and self.get_parent_window().is_visible():
			player = com.get('neil.core.player')
			master = player.get_plugin(0)		
			bpm = master.get_parameter_value(1, 0, 1)
			tpb = master.get_parameter_value(1, 0, 2)
			#rectime = utils.ticks_to_time(master.get_ticks_written(), bpm, tpb)
			if os.path.isfile(self.filename):
				recsize = os.stat(self.filename)[stat.ST_SIZE]
			else:
				recsize = 0
			#self.textposition.set_markup("<b>Time</b> %s     <b>Size</b> %.2fM" % (utils.format_time(rectime), float(recsize)/(1<<20)))
			self.textposition.set_markup("<b>Size</b> %.2fM" % (float(recsize)/(1<<20)))
		return True
		
	def on_saveas(self, widget):
		"""
		Handler for the "Save As..." button.
		"""
		dlg = Gtk.FileChooserDialog(title="Save", parent=self, action=Gtk.FILE_CHOOSER_ACTION_SAVE,
			buttons=(Gtk.STOCK_CANCEL, Gtk.RESPONSE_CANCEL, Gtk.STOCK_SAVE, Gtk.RESPONSE_OK)
		)
		player = com.get('neil.core.player')
		dlg.set_do_overwrite_confirmation(True)
		ffwav = Gtk.FileFilter()
		ffwav.set_name("PCM Waves (*.wav)")
		ffwav.add_pattern("*.wav")
		dlg.set_filename(self.filename)
		dlg.add_filter(ffwav)
		result = dlg.run()
		if result == Gtk.RESPONSE_OK:
			self.filename = dlg.get_filename()
			if (dlg.get_filter() == ffwav) and not (self.filename.endswith('.wav')):
				self.filename += '.wav'
			#self.btnsaveas.set_label(self.filename)
			recorder = player.get_stream_recorder()
			recorder.configure('wavefilepath', self.filename)
		dlg.destroy()

	def on_toggle_record(self, widget):
		"""
		Handler for the "Record" button.
		"""
		player = com.get('neil.core.player')
		recorder = player.get_stream_recorder()
		recorder.set_parameter_value_direct(zzub.zzub_parameter_group_global, 0, 1, widget.get_active(), False)

__all__ = [
'HDRecorderDialog',
]

__neil__ = dict(
	classes = [
		HDRecorderDialog,
	],
)

if __name__ == '__main__':
	import testplayer, utils
	player = testplayer.get_player()
	player.load_ccm(utils.filepath('demosongs/paniq-knark.ccm'))
	window = testplayer.TestWindow()
	window.show_all()
	dlg = HDRecorderDialog(window)
	dlg.connect('destroy', lambda widget: Gtk.main_quit())
	dlg.show_all()
	Gtk.main()
