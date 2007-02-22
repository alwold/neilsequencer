#encoding: latin-1

# Aldrin
# Modular Sequencer
# Copyright (C) 2006 The Aldrin Development Team
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
Provides utility functions needed all over the place,
which have no specific module or class they belong to.
"""

import time, sys, math, os, zzub, imp
from string import ascii_letters, digits
import struct
from gtkimport import gtk

def is_debug():
	if os.environ.get('ALDRIN_DEBUG'):
		return True
	return False
 
def is_frozen():
	"""
	Determines whether the application is being executed by
	a Python installation or it is running standalone (as a
	py2exe executable.)
	
	@return: True if frozen, otherwise False
	@rtype: bool
	"""
	return (hasattr(sys, "frozen") or # new py2exe
			hasattr(sys, "importers") # old py2exe
			or imp.is_frozen("__main__")) # tools/freeze

def get_root_folder_path():
	"""
	Returns the base folder from which this script is being
	executed. This is mainly used for windows, where loading
	of resources relative to the execution folder must be
	possible, regardless of current working directory.
	
	@return: Path to execution folder.
	@rtype: str
	"""
	if is_frozen():
		return os.path.dirname(sys.executable)
	return os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__))))

basedir = get_root_folder_path()

def filepath(path):
	"""
	Translates a path relative to a base dir into an absolute
	path.
	
	@param path: Relative path to file.
	@type path: str
	@return: Absolute path to file.
	@rtype: str
	"""
	return os.path.abspath(os.path.normpath(os.path.join(basedir,path)))

def db2linear(val, limit = -48.0):
	"""
	Translates a dB volume to a linear amplitude.
	
	@param val: Volume in dB.
	@type val: float
	@param limit: If val is lower than limit, 0.0 will be returned.
	@type limit: float
	@return: Linear amplitude.
	@rtype: float
	"""
	if val == 0.0:
		return 1.0
	if val <= limit:
		return 0.0
	return 10 ** (val / 20.0)
	
def linear2db(val, limit = -48.0):
	"""
	Translates a linear amplitude to a dB volume.
	
	@param val: Linear amplitude between 0.0 and 1.0.
	@type val: float
	@param limit: If amplitude is zero or lower, limit will be returned.
	@type limit: float
	@return: Volume in dB.
	@rtype: float
	"""
	if val <= 0.0:
		return limit
	return math.log(val) * 20.0 / math.log(10)

def format_time(t):
	"""
	Translates a time value into a string of the format
	"h:mm:ss:ms".
	
	@param t: Relative time value.
	@type t: float
	@return: String of the format "h:mm:ss:ms".
	@rtype: str
	"""
	h = int(t / 3600)
	m = int((t % 3600) / 60)
	s = t % 60
	ms = int((t - int(t))*10.0)
	return "%i:%02i:%02i:%i" % (h,m,s,ms)

def ticks_to_time(ticks,bpm,tpb):
	"""
	Translates positions in ticks as returned by zzub
	to time values.
	
	@param ticks: Tick value as returned by zzub.
	@type ticks: int
	@param bpm: Beats per minutes.
	@type bpm: int
	@param tpb: Ticks per beats.
	@type tpb: int
	@return: Relative time value.
	@rtype: float
	"""
	return (float(ticks)*60) / (bpm * tpb)

def prepstr(s):
	"""
	prepstr ensures that a string is always 
	ready to be displayed in a GUI control by wxWidgets.
	
	@param s: Text to be prepared.
	@type s: str
	@return: Correctly encoded text.
	@rtype: str
	"""
	s = s.decode('latin-1')
	return s

def fixbn(v):
	"""
	Occasionally, invalid note inputs are being made, 
	either by user error or	invalid paste or loading operations.
	This function fixes a Buzz note value so it has
	always a correct value.
	
	@param v: Buzz note value.
	@type v: int
	@return: Corrected Buzz note value.
	@rtype: int
	"""
	if v == zzub.zzub_note_value_off:
		return v
	o,n = ((v & 0xf0) >> 4), (v & 0xf)
	o = min(max(o,0),9)
	n = min(max(n,1),12)
	return (o << 4) | n

def bn2mn(v):
	"""
	Converts a Buzz note value into a MIDI note value.
	
	@param v: Buzz note value.
	@type v: int
	@return: MIDI note value.
	@rtype: int
	"""
	if v == zzub.zzub_note_value_off:
		return 255
	return ((v & 0xf0) >> 4)*12 + (v & 0xf)-1

def mn2bn(v):	
	"""
	Converts a MIDI note value into a Buzz note value.
	
	@param v: MIDI note value.
	@type v: int
	@return: Buzz note value.
	@rtype: int
	"""
	if v == 255:
		return zzub.zzub_note_value_off
	return ((int(v)/12) << 4) | ((v%12)+1)

NOTES = ('?-','C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-')

def note2str(p,v):
	"""
	Translates a Buzz note value into a string of the format
	"NNO", where NN is note, and O is octave.
	
	@param p: A parameter object. You can supply None here
	if the value is not associated with a plugin parameter.
	@type p: zzub.Parameter
	@return: A string of the format "NNO", where NN is note,
	and O is octave, or "..." for no value.
	@rtype: str
	"""
	if p and (v == p.get_value_none()):
		return '...'
	if v == zzub.zzub_note_value_off:
		return 'off'
	o,n = (v & 0xf0) >> 4, v & 0xf
	return "%s%i" % (NOTES[n],o)

def switch2str(p,v):
	"""
	Translates a Buzz switch value into a hexstring ready to
	be printed in a pattern view.
	
	@param p: A plugin parameter object.
	@type p: zzub.Parameter
	@param v: A Buzz switch value.
	@type v: int
	@return: A 1-digit hexstring or "." for no value.
	@rtype: str
	"""
	if v == p.get_value_none():
		return '.'
	return "%1X" % v

def byte2str(p,v):
	"""
	Translates a Buzz byte value into a hexstring ready to
	be printed in a pattern view.
	
	@param p: A plugin parameter object.
	@type p: zzub.Parameter
	@param v: A Buzz byte value.
	@type v: int
	@return: A 2-digit hexstring or ".." for no value.
	@rtype: str
	"""
	if v == p.get_value_none():
		return '..'
	return "%02X" % v

def word2str(p,v):
	"""
	Translates a Buzz word value into a hexstring ready to
	be printed in a pattern view.
	
	@param p: A plugin parameter object.
	@type p: zzub.Parameter
	@param v: A Buzz word value.
	@type v: int
	@return: A 4-digit hexstring or "...." for no value.
	@rtype: str
	"""
	if v == p.get_value_none():
		return '....'
	return "%04X" % v

def roundint(v):
	"""
	Rounds a float value to the next integer if its
	fractional part is larger than 0.5.
	
	@type v: float
	@rtype: int
	"""
	return int(v+0.5)

def buffersize_to_latency(bs, sr):
	"""
	Translates buffer size to latency.
	
	@param bs: Size of buffer in samples.
	@type bs: int
	@param sr: Samples per second in Hz.
	@type sr: int
	@return: Latency in ms.
	@rtype: float
	"""
	return (float(bs) / float(sr)) * 1000.0

def filenameify(text):
	"""
	Replaces characters in a text in such a way
	that it's feasible to use it as a filename. The
	result will be lowercase and all special chars
	replaced by underscores.
	
	@param text: The original text.
	@type text: str
	@return: The filename.
	@rtype: str
	"""
	return ''.join([(c in (ascii_letters+digits) and c) or '_' for c in text.lower()])

def read_int(f):
	"""
	Reads an 32bit integer from a binary file.
	"""
	return struct.unpack('<I', f.read(4))[0]

def read_string(f):
	"""
	Reads a pascal string (32bit len, data) from a binary file.
	"""
	size = read_int(f)
	return f.read(size)

def write_int(f,v):
	"""
	Writes a 32bit integer to a binary file.
	"""
	f.write(struct.pack('<I', v))

def write_string(f,s):
	"""
	Writes a pascal string (32bit len, data) to a binary file.
	"""
	s = str(s)
	write_int(f, len(s))
	f.write(s)

def from_hsb(h=0.0,s=1.0,b=1.0):
	"""
	Converts hue/saturation/brightness into red/green/blue components.
	"""
	if not s:
		return b,b,b
	scaledhue = (h%1.0)*6.0
	index = int(scaledhue)
	fraction = scaledhue - index
	p = b * (1.0 - s)
	q = b * (1.0 - s*fraction)
	t = b * (1.0 - s*(1.0 - fraction))
	if index == 0:
		return b,t,p
	elif index == 1:
		return q,b,p	
	elif index == 2:
		return p,b,t
	elif index == 3:
		return p,q,b
	elif index == 4:
		return t,p,b
	elif index == 5:
		return b,p,q
	return b,p,q
	
def to_hsb(r,g,b):
	"""
	Converts red/green/blue into hue/saturation/brightness components.
	"""
	if (r == g) and (g == b):
		h = 0.0
		s = 0.0
		b = r
	else:
		v = float(max(r,g,b))
		temp = float(min(r,g,b))
		diff = v - temp
		if v == r:
			h = (g - b)/diff
		elif v == g:
			h = (b - r)/diff + 2
		else:
			h = (r - g)/diff + 4
		if h < 0:
			h += 6
		h = h / 6.0
		s = diff / v
		b = v
	return h,s,b
	
def question(parent, msg, allowcancel = True):
	"""
	Shows a question dialog.
	"""
	dialog = gtk.MessageDialog(parent.get_toplevel(),
		gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
		gtk.MESSAGE_QUESTION , gtk.BUTTONS_NONE)
	dialog.set_markup(msg)
	dialog.add_buttons(
		gtk.STOCK_YES, gtk.RESPONSE_YES,
		gtk.STOCK_NO, gtk.RESPONSE_NO)
	if allowcancel:
		dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
	response = dialog.run()
	dialog.destroy()
	return response

def error(parent, msg):
	"""
	Shows an error message dialog.
	"""
	dialog = gtk.MessageDialog(parent.get_toplevel(),
		gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
		gtk.MESSAGE_ERROR , gtk.BUTTONS_NONE)
	dialog.set_markup(msg)
	dialog.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
	response = dialog.run()
	dialog.destroy()
	return response

def message(parent, msg):
	"""
	Shows an info message dialog.
	"""
	dialog = gtk.MessageDialog(parent.get_toplevel(),
		gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
		gtk.MESSAGE_INFO , gtk.BUTTONS_NONE)
	dialog.set_markup(msg)
	dialog.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
	response = dialog.run()
	dialog.destroy()
	return response

def warning(parent, msg):
	"""
	Shows an warning message dialog.
	"""
	dialog = gtk.MessageDialog(parent.get_toplevel(),
		gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
		gtk.MESSAGE_WARNING, gtk.BUTTONS_NONE)
	dialog.set_markup(msg)
	dialog.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
	response = dialog.run()
	dialog.destroy()
	return response

def new_listview(columns):
	"""
	Creates a gtk.TreeView for a list store with multiple columns.
	"""
	class ToggledHandler:
		def fixed_toggled(self, cell, path, model):
			iter = model.get_iter((int(path),))
			checked = model.get_value(iter, self.column)
			checked = not checked
			model.set(iter, self.column, checked)
	
	liststore = gtk.ListStore(*[col[1] for col in columns])
	treeview = gtk.TreeView(liststore)
	treeview.set_rules_hint(True)
	columncontrols = []
	for i,args in enumerate(columns):
		assert len(args) >= 2
		options = {}
		if len(args) == 2:
			name,coltype = args
		else:
			name,coltype,options = args
		column = gtk.TreeViewColumn(name)
		if coltype == str:
			column.set_resizable(True)
			cellrenderer = gtk.CellRendererText()
			column.pack_start(cellrenderer)
			if options.get('markup',False):
				column.add_attribute(cellrenderer, 'markup', i)
			else:
				column.add_attribute(cellrenderer, 'text', i)
			if options.get('wrap',False):
				cellrenderer.set_property('wrap-width', 250)
		elif coltype == bool:
			th = ToggledHandler()
			th.column = i
			cellrenderer = gtk.CellRendererToggle()
			cellrenderer.connect('toggled', th.fixed_toggled, liststore)
			column.pack_start(cellrenderer)
			column.add_attribute(cellrenderer, 'active', i)
		treeview.append_column(column)
		column.set_sort_column_id(i)
		columncontrols.append(column)
	treeview.set_search_column(0)
	return treeview, liststore, columncontrols
	
def new_image_button(path, tooltip):
	"""
	Creates a button with a single image.
	"""
	image = gtk.Image()
	image.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file(path))
	button = gtk.Button()
	button.set_image(image)
	return button

def new_image_toggle_button(path, tooltip):
	"""
	Creates a toggle button with a single image.
	"""
	image = gtk.Image()
	image.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file(path))
	button = gtk.ToggleButton()
	button.set_image(image)
	return button

def get_item_count(model):
	"""
	Returns the number of items contained in a tree model.
	"""
	class Count:
		value = 0
	def inc_count(model, path, iter, data):
		data.value += 1
	count = Count()
	model.foreach(inc_count,count)
	return count.value
	
def add_scrollbars(view):
	"""
	adds scrollbars around a view
	"""
	scrollwin = gtk.ScrolledWindow()
	scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
	if isinstance(view, gtk.TreeView):
		scrollwin.set_shadow_type(gtk.SHADOW_IN)
		scrollwin.add(view)
	else:
		scrollwin.add_with_viewport(view)
	return scrollwin

def file_filter(name,*patterns):
	ff = gtk.FileFilter()
	ff.set_name(name)
	for pattern in patterns:
		ff.add_pattern(pattern)
	return ff

	
def format_filesize(size):
	if (size / (1<<40)):
		return "%.2f TB" % (float(size) / (1<<40))
	elif (size / (1<<30)):
		return "%.2f GB" % (float(size) / (1<<30))
	elif (size / (1<<20)):
		return "%.2f MB" % (float(size) / (1<<20))
	elif (size / (1<<10)):
		return "%.2f KB" % (float(size) / (1<<10))
	else:
		return "%i bytes" % size
		
def set_clipboard_text(data):
	clipboard = gtk.clipboard_get()
	clipboard.set_text(data, len(data))
	clipboard.store()
	
def get_clipboard_text():
	clipboard = gtk.clipboard_get()
	return clipboard.wait_for_text()

__all__ = [
'is_frozen',
'get_root_folder_path',
'filepath',
'db2linear',
'linear2db',
'format_time',
'ticks_to_time',
'prepstr',
'fixbn',
'bn2mn',
'mn2bn',
'note2str',
'switch2str',
'byte2str',
'word2str',
'roundint',
'buffersize_to_latency',
'filenameify',
'read_int',
'read_string',
'write_int',
'write_string',
'from_hsb',
'to_hsb',
'question',
'error',
'message',
'warning',
'new_listview',
'new_image_button',
'get_item_count',
'add_scrollbars',
'file_filter',
'format_filesize',
'set_clipboard_text',
'get_clipboard_text',
]
