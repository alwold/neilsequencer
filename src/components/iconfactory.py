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

if __name__ == '__main__':
	import os
	os.environ['NEIL_BASE_PATH'] = '/home/paniq/devel/neil'
import neil.com as com
from gi.repository import Gtk
from gi.repository import GdkPixbuf

import glob, os
from neil.utils import filepath, get_root_folder_path, iconpath, imagepath

ICON_SEARCHPATH = [
	iconpath('16x16'),
	iconpath('22x22'),
	iconpath('24x24'),
	iconpath('32x32'),
	iconpath('48x48'),
	iconpath('scalable'),
	imagepath(''),
]

ICON_EXTENSIONS = [
	'.svg',
	'.png',
]

class IconLibrary:
	"""
	registers icons to gtk and the rest of the application in a simple,
	unified way.
	"""
	
	__neil__ = dict(
		id = 'neil.core.icons',
		singleton = True,
	)	
	
	def __init__(self):
		sizenames = [
			Gtk.IconSize.MENU,
			Gtk.IconSize.SMALL_TOOLBAR,
			Gtk.IconSize.LARGE_TOOLBAR,
			Gtk.IconSize.BUTTON,
			Gtk.IconSize.DND,
			Gtk.IconSize.DIALOG,
		]
		icons = {}
		for searchpath in ICON_SEARCHPATH:
			for ext in ICON_EXTENSIONS:
				mask = searchpath + '/*' + ext
				for filename in glob.glob(mask):
					key = os.path.splitext(os.path.basename(filename))[0]
					pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
					w,h = pixbuf.get_width(),pixbuf.get_height()
					iconsizes = icons.get(key, {})
					iconsizes[(w,h)] = pixbuf
					icons[key] = iconsizes
		for key,iconsizes in icons.items():
			for size in sizenames:
				valid,w,h = Gtk.icon_size_lookup(size)
				if (w,h) in iconsizes:
					pixbuf = iconsizes[(w,h)]
				else:
					bestw = 999999
					pixbuf = None
					c = w*w + h*h
					for (iw,ih),icon in iconsizes.items():
						l = iw*iw + ih*ih
						d = abs(l - c)
						if d < bestw:
							bestw = d
							pixbuf = icon
				#print "new icon: %s (%r = %i,%i ~ %i,%i)" % (key,size,w,h,pixbuf.get_width(),pixbuf.get_height())
				Gtk.IconTheme.add_builtin_icon(key, size, pixbuf)
					
	def register_single(self, stockid, label, key=''):
		if key:
			key = Gdk.keyval_from_name(key)
		else:
			key = 0
		Gtk.stock_add((
			(stockid, label, 0, key, 'neil'),
		))

__neil__ = dict(
	classes = [
		IconLibrary,
	],
)

if __name__ == '__main__':
	com.init()
	icons = com.get('neil.core.icons')
	
