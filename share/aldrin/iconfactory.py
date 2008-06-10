#encoding: latin-1

# Aldrin
# Modular Sequencer
# Copyright (C) 2006,2007,2008 The Aldrin Development Team
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

from aldrincom import com
from gtkimport import gtk

import glob, os
from utils import filepath, get_root_folder_path

ICON_SEARCHPATH = [
	'icons/16x16',
	'icons/22x22',
	'icons/24x24',
	'icons/32x32',
	'icons/48x48',
	'icons/scalable',
	'icons',
	'res',
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
	
	__aldrin__ = dict(
		id = 'aldrin.core.icons',
		singleton = True,
	)	
	
	def __init__(self):
		sizenames = [
			gtk.ICON_SIZE_MENU,
			gtk.ICON_SIZE_SMALL_TOOLBAR,
			gtk.ICON_SIZE_LARGE_TOOLBAR,
			gtk.ICON_SIZE_BUTTON,
			gtk.ICON_SIZE_DND,
			gtk.ICON_SIZE_DIALOG,
		]
		icons = {}
		for searchpath in ICON_SEARCHPATH:
			for ext in ICON_EXTENSIONS:
				mask = filepath(searchpath) + '/*' + ext
				for filename in glob.glob(mask):
					key = os.path.splitext(os.path.basename(filename))[0]
					pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
					w,h = pixbuf.get_width(),pixbuf.get_height()
					iconsizes = icons.get(key, {})
					iconsizes[(w,h)] = pixbuf
					icons[key] = iconsizes
		for key,iconsizes in icons.iteritems():
			for size in sizenames:
				w,h = gtk.icon_size_lookup(size)
				if (w,h) in iconsizes:
					pixbuf = iconsizes[(w,h)]
				else:
					bestw = 999999
					pixbuf = None
					c = w*w + h*h
					for (iw,ih),icon in iconsizes.iteritems():
						l = iw*iw + ih*ih
						d = abs(l - c)
						if d < bestw:
							bestw = d
							pixbuf = icon
					#pixbuf = pixbuf.scale_simple(w,h,gtk.gdk.INTERP_HYPER)
				print "new icon: %s (%r = %i,%i ~ %i,%i)" % (key,size,w,h,pixbuf.get_width(),pixbuf.get_height())
				gtk.icon_theme_add_builtin_icon(key, size, pixbuf)
					
	def register_single(self, stockid, label, key=''):
		if key:
			key = gtk.gdk.keyval_from_name(key)
		else:
			key = 0
		gtk.stock_add((
			(stockid, label, 0, key, 'aldrin'),
		))

__aldrin__ = dict(
	classes = [
		IconLibrary,
	],
)

if __name__ == '__main__':
	pass
