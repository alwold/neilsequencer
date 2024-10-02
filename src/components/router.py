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
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.

"""
Provides dialogs and controls to render the plugin view/router and its
associated components.
"""

if __name__ == '__main__':
    import os
    os.system('../../bin/neil-combrowser neil.core.routerpanel')
    raise SystemExit

import neil.com as com
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import PangoCairo
import cairo

from neil.utils import PLUGIN_FLAGS_MASK, ROOT_PLUGIN_FLAGS,\
     GENERATOR_PLUGIN_FLAGS, EFFECT_PLUGIN_FLAGS,\
     CONTROLLER_PLUGIN_FLAGS
from neil.utils import is_effect, is_generator, is_controller, is_root
from neil.utils import prepstr, db2linear, linear2db, error, new_listview, add_scrollbars
from neil.utils import blend
import config
import zzub
# import sys
# import os
# import fnmatch
# import ctypes
# import time
# import random
# from neil.preset import PresetCollection, Preset
import neil.common as common
from neil.common import MARGIN
from rack import ParameterView
from neil.presetbrowser import PresetView
from patterns import key_to_note

PLUGINWIDTH = 100
PLUGINHEIGHT = 25
LEDWIDTH, LEDHEIGHT = 6, PLUGINHEIGHT - 8         # size of LED
LEDOFSX, LEDOFSY = 4, 4                           # offset of LED
CPUWIDTH, CPUHEIGHT = 6, PLUGINHEIGHT - 8         # size of LED
CPUOFSX, CPUOFSY = PLUGINWIDTH - CPUWIDTH - 4, 4  # offset of LED

ARROWRADIUS = 8

QUANTIZEX = PLUGINWIDTH + ARROWRADIUS * 2
QUANTIZEY = PLUGINHEIGHT + ARROWRADIUS * 2

VOLBARWIDTH = 32
VOLBARHEIGHT = 128
VOLKNOBHEIGHT = 16

AREA_ANY = 0
AREA_PANNING = 1
AREA_LED = 2


class AttributesDialog(Gtk.Dialog):
    """
    Displays plugin atttributes and allows to edit them.
    """
    __neil__ = dict(
            id = 'neil.core.attributesdialog',
            singleton = False,
            categories = [
            ]
    )

    def __init__(self, plugin, parent):
        """
        Initializer.

        @param plugin: Plugin object.
        @type plugin: wx.Plugin
        """
        Gtk.Dialog.__init__(self,
                "Attributes",
                parent.get_toplevel(),
                Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                None
        )
        vbox = Gtk.VBox(False, MARGIN)
        vbox.set_border_width(MARGIN)
        self.plugin = plugin
        self.pluginloader = plugin.get_pluginloader()
        self.resize(300, 200)
        self.attriblist, self.attribstore, columns = new_listview([
                ('Attribute', str),
                ('Value', str),
                ('Min', str),
                ('Max', str),
                ('Default', str),
        ])
        vbox.add(add_scrollbars(self.attriblist))
        hsizer = Gtk.HButtonBox()
        hsizer.set_spacing(MARGIN)
        hsizer.set_layout(Gtk.ButtonBoxStyle.START)
        self.edvalue = Gtk.Entry()
        self.edvalue.set_size_request(50, -1)
        self.btnset = Gtk.Button("_Set")
        self.btnok = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.btncancel = self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        hsizer.pack_start(self.edvalue, expand=False, fill=True, padding=0)
        hsizer.pack_start(self.btnset, expand=False, fill=True, padding=0)
        vbox.pack_start(hsizer, expand=False, fill=True, padding=0)
        self.attribs = []
        for i in range(self.pluginloader.get_attribute_count()):
            attrib = self.pluginloader.get_attribute(i)
            self.attribs.append(self.plugin.get_attribute_value(i))
            self.attribstore.append([
                    prepstr(attrib.get_name()),
                    "%i" % self.plugin.get_attribute_value(i),
                    "%i" % attrib.get_value_min(),
                    "%i" % attrib.get_value_max(),
                    "%i" % attrib.get_value_default(),
            ])
        self.btnset.connect('clicked', self.on_set)
        self.connect('response', self.on_ok)
        self.attriblist.get_selection().connect('changed',
                                                self.on_attrib_item_focused)
        if self.attribs:
            self.attriblist.grab_focus()
            self.attriblist.get_selection().select_path((0,))
        self.vbox.add(vbox)
        self.show_all()

    def get_focused_item(self):
        """
        Returns the currently focused attribute index.

        @return: Index of the attribute currently selected.
        @rtype: int
        """
        store, rows = self.attriblist.get_selection().get_selected_rows()
        return rows[0][0]

    def on_attrib_item_focused(self, selection):
        """
        Called when an attribute item is being focused.

        @param event: Event.
        @type event: wx.Event
        """
        v = self.attribs[self.get_focused_item()]
        self.edvalue.set_text("%i" % v)

    def on_set(self, widget):
        """
        Called when the "set" button is being pressed.
        """
        i = self.get_focused_item()
        attrib = self.pluginloader.get_attribute(i)
        try:
            v = int(self.edvalue.get_text())
            assert v >= attrib.get_value_min()
            assert v <= attrib.get_value_max()
        except:
            error(self, "<b><big>The number you entered is invalid.</big></b>\n\nThe number must be in the proper range.")
            return
        self.attribs[i] = v
        iter = self.attribstore.get_iter((i,))
        self.attribstore.set_value(iter, 1, "%i" % v)

    def on_ok(self, widget, response):
        """
        Called when the "ok" or "cancel" button is being pressed.
        """
        if response == Gtk.ResponseType.OK:
            for i in range(len(self.attribs)):
                self.plugin.set_attribute_value(i, self.attribs[i])


class ParameterDialog(Gtk.Dialog):
    """
    Displays parameter sliders for a plugin in a new Dialog.
    """
    __neil__ = dict(
            id = 'neil.core.parameterdialog',
            singleton = False,
            categories = [
            ]
    )

    def __init__(self, manager, plugin, parent):
        Gtk.Dialog.__init__(self, parent=parent.get_toplevel())
        self.plugin = plugin
        self.manager = manager
        self.manager.plugin_dialogs[plugin] = self
        self.paramview = ParameterView(plugin)
        self.set_title(self.paramview.get_title())
        self.vbox.add(self.paramview)
        self.connect('destroy', self.on_destroy)
        self.connect('realize', self.on_realize)
        eventbus = com.get('neil.core.eventbus')
        eventbus.zzub_delete_plugin += self.on_zzub_delete_plugin

    def on_realize(self, widget):
        self.set_default_size(*self.paramview.get_best_size())

    def on_zzub_delete_plugin(self, plugin):
        if plugin == self.plugin:
            self.destroy()

    def on_destroy(self, event):
        """
        Handles destroy events.
        """
        del self.manager.plugin_dialogs[self.plugin]


class ParameterDialogManager:
    """
    Manages the different parameter dialogs.
    """
    __neil__ = dict(
            id = 'neil.core.parameterdialog.manager',
            singleton = True,
            categories = [
            ]
    )

    def __init__(self):
        self.plugin_dialogs = {}

    def show(self, plugin, parent):
        """
        Shows a parameter dialog for a plugin.

        @param plugin: Plugin instance.
        @type plugin: Plugin
        """
        dlg = self.plugin_dialogs.get(plugin, None)
        if not dlg:
            dlg = ParameterDialog(self, plugin, parent)
        dlg.show_all()


class PresetDialogManager:
    """
    Manages the different preset dialogs.
    """
    __neil__ = dict(
            id = 'neil.core.presetdialog.manager',
            singleton = True,
            categories = [
            ]
    )

    def __init__(self):
        self.preset_dialogs = {}

    def show(self, plugin, parent):
        """
        Shows a preset dialog for a plugin.

        @param plugin: Plugin instance.
        @type plugin: Plugin
        """
        dlg = self.preset_dialogs.get(plugin, None)
        if not dlg:
            dlg = PresetDialog(self, plugin, parent)
        dlg.show_all()


class PresetDialog(Gtk.Dialog):
    """
    Displays parameter sliders for a plugin in a new Dialog.
    """
    def __init__(self, manager, plugin, parent):
        #gtk.Dialog.__init__(self, parent=parent.get_toplevel())
        Gtk.Dialog.__init__(self, parent=com.get('neil.core.window.root'))
        self.plugin = plugin
        self.manager = manager
        self.manager.preset_dialogs[plugin] = self
        self.view = parent
        self.plugin = plugin
        self.presetview = PresetView(self, plugin, self)
        self.set_title(self.presetview.get_title())
        self.vbox.add(self.presetview)
        self.connect('realize', self.on_realize)
        eventbus = com.get('neil.core.eventbus')
        eventbus.zzub_delete_plugin += self.on_zzub_delete_plugin

    def on_zzub_delete_plugin(self, plugin):
        if plugin == self.plugin:
            self.destroy()

    def on_destroy(self, event):
        """
        Handles destroy events.
        """
        del self.manager.preset_dialogs[self.plugin]

    def on_realize(self, widget):
        # This is the size specified in presetbrowser.py.
        # Seems to have no effect though -- PresetView is full-screen?
        self.set_default_size(200, 400)


DRAG_FORMAT_PLUGIN_URI = 0

DRAG_FORMATS = [
        Gtk.TargetEntry('application/x-neil-plugin-uri', 0, DRAG_FORMAT_PLUGIN_URI)
]


class RoutePanel(Gtk.VBox):
    """
    Contains the view panel and manages parameter dialogs.
    """
    __neil__ = dict(
            id = 'neil.core.routerpanel',
            singleton = True,
            categories = [
                    'neil.viewpanel',
                    'view',
            ]
    )

    __view__ = dict(
                    label = "Router",
                    stockid = "neil_router",
                    shortcut = 'F3',
                    default = True,
                    order = 3,
    )

    def __init__(self):
        """
        Initializer.
        """
        Gtk.VBox.__init__(self)
        self.view = com.get('neil.core.router.view', self)
        self.add(self.view)

    def handle_focus(self):
        self.view.grab_focus()

    def reset(self):
        """
        Resets the router view. Used when
        a new song is being loaded.
        """
        self.view.reset()

    def update_all(self):
        self.view.update_colors()
        self.view.redraw()


class VolumeSlider(Gtk.Window):
    """
    A temporary popup volume control for the router. Can
    only be summoned parametrically and will vanish when the
    left mouse button is being released.
    """
    def __init__(self, parent):
        """
        Initializer.
        """
        self.parent_window = parent
        self.plugin = None
        self.index = -1
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)
        self.drawingarea = Gtk.DrawingArea()
        self.add(self.drawingarea)
        self.drawingarea.add_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.drawingarea.set_property('can-focus', True)
        self.resize(VOLBARWIDTH, VOLBARHEIGHT)
        self.hide()
        self.drawingarea.connect('motion-notify-event', self.on_motion)
        self.drawingarea.connect('draw', self.expose)
        self.drawingarea.connect('button-release-event', self.on_left_up)

    def expose(self, widget, ctx):
        self.draw(ctx)
        return False

    def redraw(self):
        if self.get_parent_window():
            rect = self.drawingarea.get_allocation()
            window = self.drawingarea.window
            window.invalidate_rect((0, 0, rect.width, rect.height), False)

    def on_motion(self, widget, event):
        """
        Event handler for mouse movements.
        """
        x, y, state = self.drawingarea.window.get_pointer()
        newpos = int(y)
        delta = newpos - self.y
        if delta == 0:
            return
        self.y = newpos
        self.amp = max(min(self.amp + (float(delta) / VOLBARHEIGHT), 1.0), 0.0)
        amp = min(max(int(db2linear(self.amp * -48.0, -48.0) * 16384.0), 0), 16384)
        self.plugin.set_parameter_value_direct(0, self.index, 0, amp, False)
        self.redraw()
        return True

    def draw(self, ctx):
        """
        Event handler for paint requests for the volume slider.
        """
        rect = self.drawingarea.get_allocation()
        w, h = rect.width, rect.height

        cfg = config.get_config()
        whitebrush = cfg.get_float_color('MV Amp BG')
        blackbrush = cfg.get_float_color('MV Amp Handle')
        outlinepen = cfg.get_float_color('MV Amp Border')

        ctx.set_source_rgb(*whitebrush)
        ctx.rectangle(0, 0, w, h)
        ctx.fill()

        ctx.set_source_rgb(*outlinepen)
        ctx.rectangle(0, 0, w - 1, h - 1)
        ctx.stroke()

        if self.plugin:
            ctx.set_source_rgb(*blackbrush)
            pos = int(self.amp * (VOLBARHEIGHT - VOLKNOBHEIGHT))
            ctx.rectangle(1, pos + 1,
                          VOLBARWIDTH - 2, VOLKNOBHEIGHT - 2)
            ctx.fill()

        black = (0, 0, 0)
        ctx.set_source_rgb(*black)
        layout = Pango.Layout(self.get_pango_context())
        font = Pango.FontDescription("sans 6")
        layout.set_font_description(font)
        layout.set_markup("<small>%.1f dB</small>" % (self.amp * -48.0))
        ctx.move_to(2, 2)
        PangoCairo.update_layout(ctx, layout)
        PangoCairo.show_layout(ctx, layout)

    def display(self, m, mp, index):
        """
        Called by the router view to show the control.

        @param mx: X coordinate of the control center in pixels.
        @type mx: int
        @param my: Y coordinate of the control center in pixels.
        @type my: int
        @param conn: Connection to control.
        @type conn: zzub.Connection
        """
        mx, my = m
        self.y = VOLBARHEIGHT / 2
        self.plugin = mp
        self.index = index
        self.amp = (linear2db((self.plugin.get_parameter_value(0, index, 0) /
                               16384.0), -48.0) / -48.0)
        #print self.amp
        self.move(int(mx - VOLBARWIDTH * 0.5), int(my - VOLBARHEIGHT * 0.5))
        self.show_all()
        self.drawingarea.grab_add()

    def on_left_up(self, widget, event):
        """
        Event handler for left mouse button releases. Will
        hide control.

        @param event: Mouse event.
        @type event: wx.MouseEvent
        """
        self.parent_window.redraw()
        self.hide()
        self.drawingarea.grab_remove()


class RouteView(Gtk.DrawingArea):
    """
    Allows to monitor and control plugins and their connections.
    """
    __neil__ = dict(
            id = 'neil.core.router.view',
            singleton = True,
            categories = [
            ]
    )

    current_plugin = None
    connecting = False
    dragging = False
    dragoffset = 0, 0
    contextmenupos = 0, 0

    # 0 = default
    # 1 = muted
    # 2 = led off
    # 3 = led on
    # 4 = led border
    # 5 = led warning
    COLOR_DEFAULT = 0
    COLOR_MUTED = 1
    COLOR_LED_OFF = 2
    COLOR_LED_ON = 3
    COLOR_LED_BORDER = 4
    COLOR_LED_WARNING = 7
    COLOR_CPU_OFF = 2
    COLOR_CPU_ON = 3
    COLOR_CPU_BORDER = 4
    COLOR_CPU_WARNING = 9
    COLOR_BORDER_IN = 10
    COLOR_BORDER_OUT = 12
    COLOR_BORDER_SELECT = 13
    COLOR_TEXT = 14

    def __init__(self, parent):
        """
        Initializer.

        @param rootwindow: Main window.
        @type rootwindow: NeilFrame
        """
        Gtk.DrawingArea.__init__(self)
        self.panel = parent
        self.routebitmap = None
        # self.peaks = {}
        eventbus = com.get('neil.core.eventbus')
        eventbus.zzub_connect += self.on_zzub_redraw_event
        eventbus.zzub_disconnect += self.on_zzub_redraw_event
        eventbus.zzub_plugin_changed += self.on_zzub_plugin_changed
        eventbus.document_loaded += self.redraw
        eventbus.active_plugins_changed += self.on_active_plugins_changed
        self.autoconnect_target = None
        self.chordnotes = []
        self.update_colors()
        self.volume_slider = VolumeSlider(self)
        self.add_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.set_property('can-focus', True)
        self.connect('button-press-event', self.on_left_down)
        self.connect('button-release-event', self.on_left_up)
        self.connect('motion-notify-event', self.on_motion)
        self.connect('draw', self.expose)
        self.connect('key-press-event', self.on_key_jazz, None)
        self.connect('key-release-event', self.on_key_jazz_release, None)
        self.connect('size-allocate', self.on_size_allocate)
        if config.get_config().get_led_draw() == True:
            GObject.timeout_add(100, self.on_draw_led_timer)
        self.drag_dest_set(0, DRAG_FORMATS, 0)
        self.connect('drag_motion', self.on_drag_motion)
        self.connect('drag_drop', self.on_drag_drop)
        self.connect('drag_data_received', self.on_drag_data_received)
        self.connect('drag_leave', self.on_drag_leave)

    def on_active_plugins_changed(self, *args):
       # player = com.get('neil.core.player')
        common.get_plugin_infos().reset_plugingfx()

    def get_plugin_info(self, plugin):
        return common.get_plugin_infos().get(plugin)

    def on_drag_leave(self, widget, context, time):
        #print "on_drag_leave",widget,context,time
        self.drag_unhighlight()

    def on_drag_motion(self, widget, context, x, y, time):
        #print "on_drag_motion",widget,context,x,y,time

        # TODO!: highlight arrow drop
        # conn = self.get_connection_at((x,y))
        # if conn:
        #     print conn
        #     bmpctx = self.routebitmap.cairo_create()
        #     bmpctx.translate(0.5,0.5)
        #     bmpctx.set_line_width(1)
        #     bmpctx.set_source_rgb(1,0,0)
        #     # draw_line_arrow(bmpctx, arrowcolors[mp.get_input_connection_type(index)], int(crx), int(cry), int(rx), int(ry))
        #     bmpctx.rectangle(x,y,20,20)
        #     bmpctx.stroke()

        source = context.get_source_widget()
        if not source:
            return
        self.drag_highlight()
        context.drag_status(context.suggested_action, time)
        return True

    def on_drag_drop(self, widget, context, x, y, time):
        #print "on_drag_drop",widget,context,x,y,time
        if context.targets:
            widget.drag_get_data(context, 'application/x-neil-plugin-uri', time)
            return True
        return False

    def on_drag_data_received(self, widget, context, x, y, data, info, time):
        if data.format == 8:
            context.finish(True, False, time)
            player = com.get('neil.core.player')
            player.plugin_origin = self.pixel_to_float((x, y))
            uri = data.data
            conn = None
            plugin = None
            pluginloader = player.get_pluginloader_by_name(uri)
            if is_effect(pluginloader):
                conn = self.get_connection_at((x, y))
            if not conn:
                res = self.get_plugin_at((x, y))
                if res:
                    mp, (px, py), area = res
                    if is_effect(mp) or is_root(mp):
                        plugin = mp
            player.create_plugin(pluginloader, connection=conn, plugin=plugin)
        else:
            context.finish(False, False, time)

    def on_size_allocate(self, widget, requisition):
        self.routebitmap = None

    def update_colors(self):
        """
        Updates the routers color scheme.
        """
        cfg = config.get_config()
        names = [
                'MV ${PLUGIN}',
                'MV ${PLUGIN} Mute',
                'MV ${PLUGIN} LED Off',
                'MV ${PLUGIN} LED On',
                'MV Indicator Background',
                'MV Indicator Foreground',
                'MV Indicator Border',
                'MV Indicator Warning',
                'MV Indicator Background',
                'MV Indicator Foreground',
                'MV Indicator Border',
                'MV Indicator Warning',
                'MV Border',
                'MV Border',
                'MV Border',
                'MV Text',
        ]
        flagids = [
                (ROOT_PLUGIN_FLAGS, 'Master'),
                (GENERATOR_PLUGIN_FLAGS, 'Generator'),
                (EFFECT_PLUGIN_FLAGS, 'Effect'),
                (CONTROLLER_PLUGIN_FLAGS, 'Controller'),
        ]
        self.flags2brushes = {}
        for flags, name in flagids:
            brushes = []
            for name in [x.replace('${PLUGIN}', name) for x in names]:
                brushes.append(cfg.get_float_color(name))
            self.flags2brushes[flags] = brushes
        common.get_plugin_infos().reset_plugingfx()

    def on_zzub_plugin_changed(self, plugin):
        common.get_plugin_infos().get(plugin).reset_plugingfx()
        self.redraw()

    def on_zzub_redraw_event(self, *args):
        self.redraw()

    def on_focus(self, event):
        self.redraw()

    def on_context_menu(self, widget, event):
        """
        Event handler for requests to show the context menu.

        @param event: event.
        @type event: wx.Event
        """
        mx, my = int(event.x), int(event.y)
        player = com.get('neil.core.player')
        player.plugin_origin = self.pixel_to_float((mx, my))
        res = self.get_plugin_at((mx, my))
        if res:
            mp, (x, y), area = res
            menu = com.get('neil.core.contextmenu', 'plugin', mp)
        else:
            res = self.get_connection_at((mx, my))
            if res:
                mp, index = res
                menu = com.get('neil.core.contextmenu',
                               'connection', (mp, index))
            else:
                point = self.pixel_to_float((mx, my))
                menu = com.get('neil.core.contextmenu', 'router', point)
        menu.popup(self, event)

    def float_to_pixel(self, xy):
        """
        Converts a router coordinate to an on-screen pixel coordinate.

        @param x: X coordinate.
        @type x: float
        @param y: Y coordinate.
        @type y: float
        @return: A tuple returning the pixel coordinate.
        @rtype: (int,int)
        """
        x, y = xy
        rect = self.get_allocation()
        w, h = rect.width, rect.height
        cx, cy = w * 0.5, h * 0.5
        return cx * (1 + x), cy * (1 + y)

    def pixel_to_float(self, xy):
        """
        Converts an on-screen pixel coordinate to a router coordinate.

        @param x: X coordinate.
        @type x: int
        @param y: Y coordinate.
        @type y: int
        @return: A tuple returning the router coordinate.
        @rtype: (float, float)
        """
        x, y = xy
        rect = self.get_allocation()
        w, h = rect.width, rect.height
        cx, cy = w * 0.5, h * 0.5
        return (x / cx) - 1, (y / cy) - 1

    def get_connection_at(self, m):
        """
        Finds the connection arrow at a specific position.

        @param mx: X coordinate in pixels.
        @type mx: int
        @param my: Y coordinate in pixels.
        @type my: int
        @return: A connection item or None.
        @rtype: zzub.Connection or None
        """
        mx, my = m
        player = com.get('neil.core.player')
        rect = self.get_allocation()
        w, h = rect.width, rect.height
        cx, cy = w * 0.5, h * 0.5

        def get_pixelpos(x, y):
            return cx * (1 + x), cy * (1 + y)
        for mp in player.get_plugin_list():
            rx, ry = get_pixelpos(*mp.get_position())
            for index in range(mp.get_input_connection_count()):
                crx, cry = get_pixelpos(*mp.get_input_connection_plugin(index).get_position())
                cpx, cpy = (crx + rx) * 0.5, (cry + ry) * 0.5
                dx, dy = cpx - mx, cpy - my
                length = (dx * dx + dy * dy) ** 0.5
                if length <= 14:  # why exactly 14?
                    return mp, index

    def get_plugin_at(self, xy):
        """
        Finds a plugin at a specific position.

        @param x: X coordinate in pixels.
        @type x: int
        @param y: Y coordinate in pixels.
        @type y: int
        @return: A connection item, exact pixel position and area (AREA_ANY, AREA_PANNING, AREA_LED) or None.
        @rtype: (zzub.Plugin,(int,int),int) or None
        """
        x, y = xy
        rect = self.get_allocation()
        w, h = rect.width, rect.height
        cx, cy = w * 0.5, h * 0.5
        mx, my = x, y
        PW, PH = PLUGINWIDTH / 2, PLUGINHEIGHT / 2
        area = AREA_ANY
        player = com.get('neil.core.player')
        for mp in reversed(list(player.get_plugin_list())):
            pi = common.get_plugin_infos().get(mp)
            if not pi.songplugin:
                continue
            x, y = mp.get_position()
            x, y = int(cx * (1 + x)), int(cy * (1 + y))
            if (mx >= (x - PW)) and (mx <= (x + PW)) and (my >= (y - PH)) and (my <= (y + PH)):
                if sum(tuple(Gdk.Rectangle(x - PW + LEDOFSX, y - PH + LEDOFSY, LEDWIDTH, LEDHEIGHT).intersect((mx, my, 1, 1)))):
                    area = AREA_LED
                return mp, (x, y), area

    def on_left_dclick(self, widget, event):
        """
        Event handler for left doubleclicks. If the doubleclick
        hits a plugin, the parameter window is being shown.
        """
        #player = com.get('neil.core.player')
        mx, my = int(event.x), int(event.y)
        res = self.get_plugin_at((mx, my))
        if not res:
            searchwindow = com.get('neil.core.searchplugins')
            searchwindow.show_all()
            searchwindow.set_transient_for(com.get('neil.core.window.root'))
            searchwindow.present()
            return
        mp, (x, y), area = res
        if area == AREA_ANY:
            data = zzub.zzub_event_data_t()
            data.type = zzub.zzub_event_type_double_click
            mp.invoke_event(data, 1)
            if not (mp.get_flags() & zzub.zzub_plugin_flag_has_custom_gui):
                com.get('neil.core.parameterdialog.manager').show(mp, self)

    def on_left_down(self, widget, event):
        """
        Event handler for left mouse button presses. Initiates
        plugin dragging or connection volume adjustments.

        @param event: Mouse event.
        @type event: wx.MouseEvent
        """
        self.grab_focus()
        player = com.get('neil.core.player')
        if (event.button == 3):
            return self.on_context_menu(widget, event)
        if not event.button in (1, 2):
            return
        if (event.button == 1) and (event.type == Gdk.EventType._2BUTTON_PRESS):
            self.get_parent_window().set_cursor(None)
            return self.on_left_dclick(widget, event)
        mx, my = int(event.x), int(event.y)
        res = self.get_plugin_at((mx, my))
        if res:
            mp, (x, y), area = res
            if area == AREA_LED:
                player.toggle_mute(mp)
                self.redraw()
            else:
                if not mp in player.active_plugins:
                    if (event.state & Gdk.ModifierType.SHIFT_MASK):
                        player.active_plugins = [mp] + player.active_plugins
                    else:
                        player.active_plugins = [mp]
                if not mp in player.active_patterns and is_generator(mp):
                    if (event.state & Gdk.ModifierType.SHIFT_MASK):
                        player.active_patterns = [(mp, 0)] + player.active_patterns
                    else:
                        player.active_patterns = [(mp, 0)]
                player.set_midi_plugin(mp)
                if (event.state & Gdk.ModifierType.CONTROL_MASK) or (event.button == 2):
                    if is_controller(mp):
                        pass
                    else:
                        self.connecting = True
                        self.connectpos = int(mx), int(my)
                        self.get_parent_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.CROSSHAIR))
                if not self.connecting:
                    for plugin in player.active_plugins:
                        pinfo = self.get_plugin_info(plugin)
                        pinfo.dragpos = plugin.get_position()
                        x, y = self.float_to_pixel(pinfo.dragpos)
                        pinfo.dragoffset = x - mx, y - my
                    self.dragging = True
                    self.get_parent_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.FLEUR))
                    self.grab_add()
        else:
            res = self.get_connection_at((mx, my))
            if res:
                mp, index = res
                ox, oy = self.get_parent_window().get_origin()
                connectiontype = mp.get_input_connection_type(index)
                if connectiontype == zzub.zzub_connection_type_audio:
                    self.volume_slider.display((ox + mx, oy + my), mp, index)
                elif connectiontype == zzub.zzub_connection_type_event:
                    # no idea what to do when clicking on an event connection yet
                    pass
            else:
                player.active_plugins = []

    def on_motion(self, widget, event):
        """
        Event handler for mouse movements.

        @param event: Mouse event.
        @type event: wx.MouseEvent
        """
        window, x, y, state = self.get_parent_window().get_pointer()
        if self.dragging:
            player = com.get('neil.core.player')
            ox, oy = self.dragoffset
            mx, my = int(x), int(y)
            size = self.get_allocation()
            x, y = max(0, min(mx - ox, size.width)), max(0, min(my - oy, size.height))
            if (event.state & Gdk.ModifierType.CONTROL_MASK):
                # quantize position
                x = int(float(x) / QUANTIZEX + 0.5) * QUANTIZEX
                y = int(float(y) / QUANTIZEY + 0.5) * QUANTIZEY
            for plugin in player.active_plugins:
                pinfo = self.get_plugin_info(plugin)
                dx, dy = pinfo.dragoffset
                pinfo.dragpos = self.pixel_to_float((x + dx, y + dy))
            self.redraw()
        elif self.connecting:
            self.connectpos = int(x), int(y)
            self.redraw()
        else:
            res = self.get_plugin_at((x, y))
            if res:
                mp, (mx, my), area = res
                self.get_parent_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1) if area == AREA_LED else None)
        return True

    def on_left_up(self, widget, event):
        """
        Event handler for left mouse button releases.

        @param event: Mouse event.
        @type event: wx.MouseEvent
        """
        mx, my = int(event.x), int(event.y)
        player = com.get('neil.core.player')
        if self.dragging:
            self.dragging = False
            self.get_parent_window().set_cursor(None)
            self.grab_remove()
            ox, oy = self.dragoffset
            size = self.get_allocation()
            x, y = max(0, min(mx - ox, size.width)), max(0, min(my - oy, size.height))
            if (event.state & Gdk.ModifierType.CONTROL_MASK):
                # quantize position
                x = int(float(x) / QUANTIZEX + 0.5) * QUANTIZEX
                y = int(float(y) / QUANTIZEY + 0.5) * QUANTIZEY
            for plugin in player.active_plugins:
                pinfo = self.get_plugin_info(plugin)
                dx, dy = pinfo.dragoffset
                plugin.set_position(*self.pixel_to_float((dx + x, dy + y)))
            player.history_commit("move plugin")
        if self.connecting:
            res = self.get_plugin_at((mx, my))
            if res:
                mp, (x, y), area = res
                if player.active_plugins:
                    if not is_controller(player.active_plugins[0]):
                        mp.add_input(player.active_plugins[0], zzub.zzub_connection_type_audio)
                        player.history_commit("new nonnection")
        self.connecting = False
        self.redraw()
        res = self.get_plugin_at((mx, my))
        if res:
            mp, (x, y), area = res
            if area == AREA_LED:
                self.get_parent_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1))
        else:
            self.get_parent_window().set_cursor(None)

    def update_all(self):
        self.update_colors()
        self.redraw()

    def on_draw_led_timer(self):
        """
        Timer event that only updates the plugin leds.
        """
        # TODO: find some other way to find out whether we are really visible
        #if self.rootwindow.get_current_panel() != self.panel:
        #       return True
        if self.get_parent_window():
            player = com.get('neil.core.player')
            rect = self.get_allocation()
            w, h = rect.width, rect.height
            cx, cy = w * 0.5, h * 0.5

            def get_pixelpos(x, y):
                return cx * (1 + x), cy * (1 + y)
            PW, PH = PLUGINWIDTH / 2, PLUGINHEIGHT / 2
            for mp, (rx, ry) in ((mp, get_pixelpos(*mp.get_position())) for mp in player.get_plugin_list()):
                rx, ry = rx - PW, ry - PH
                self.get_parent_window().invalidate_rect(Gdk.Rectangle(int(rx), int(ry), PLUGINWIDTH, PLUGINHEIGHT), False)
        return True

    def expose(self, widget, context):
        self.context = context
        self.draw(self.context)
        return False

    def redraw(self):
        if self.get_parent_window():
            self.routebitmap = None
            rect = self.get_allocation()
            self.get_parent_window().invalidate_rect(Gdk.Rectangle(0, 0, rect.width, rect.height), False)

    def draw_leds(self, ctx):
        """
        Draws only the leds into the offscreen buffer.
        """
        player = com.get('neil.core.player')
        if player.is_loading():
            return
        #cfg = config.get_config()
        rect = self.get_allocation()
        layout = Pango.Layout(self.get_pango_context())
        #~ layout.set_font_description(self.fontdesc)
        layout.set_width(-1)
        w, h = rect.width, rect.height
        cx, cy = w * 0.5, h * 0.5

        def get_pixelpos(x, y):
            return cx * (1 + x), cy * (1 + y)
        PW, PH = PLUGINWIDTH / 2, PLUGINHEIGHT / 2
        driver = com.get('neil.core.driver.audio')
        cpu_scale = driver.get_cpu_load()
        max_cpu_scale = 1.0 / player.get_plugin_count()
        for mp, (rx, ry) in ((mp, get_pixelpos(*mp.get_position())) for mp in player.get_plugin_list()):
            pi = common.get_plugin_infos().get(mp)
            if not pi.songplugin:
                continue
            if self.dragging and mp in player.active_plugins:
                pinfo = self.get_plugin_info(mp)
                rx, ry = get_pixelpos(*pinfo.dragpos)
            rx, ry = rx - PW, ry - PH
            pi = common.get_plugin_infos().get(mp)
            if not pi:
                continue
            brushes = self.flags2brushes.get(mp.get_flags() & PLUGIN_FLAGS_MASK,
                                             self.flags2brushes[GENERATOR_PLUGIN_FLAGS])

            if not pi.plugingfx:
                pi.plugingfx = cairo.ImageSurface(cairo.Format.ARGB32, PLUGINWIDTH, PLUGINHEIGHT)
                pctx = cairo.Context(pi.plugingfx)
                # adjust colour for muted plugins
                color = brushes[self.COLOR_MUTED if pi.muted else self.COLOR_DEFAULT]
                pctx.set_source_rgb(*color)
#                if pi.muted:
#                    gc.set_foreground(cm.alloc_color(brushes[self.COLOR_MUTED]))
#                else:
#                    gc.set_foreground(cm.alloc_color(brushes[self.COLOR_DEFAULT]))
                pctx.rectangle(-1, -1,
                                            PLUGINWIDTH + 1, PLUGINHEIGHT + 1)
                pctx.fill()

                # outer border
                pctx.set_source_rgb(*brushes[self.COLOR_BORDER_OUT])
                pctx.rectangle(0, 0, PLUGINWIDTH - 1, PLUGINHEIGHT - 1)
                pctx.stroke()

                #  inner border
                r, g, b = color
                border = blend(Gdk.Color(red=r, green=g, blue=b), Gdk.Color(red=1, green=1, blue=1), 0.65)
                pctx.set_source_rgb(border.red_float, border.green_float, border.blue_float)
                pctx.rectangle(1, 1, PLUGINWIDTH - 3, PLUGINHEIGHT - 3)
                pctx.stroke()

                if (player.solo_plugin and player.solo_plugin != mp
                    and is_generator(mp)):
                    title = prepstr('[' + mp.get_name() + ']')
                elif pi.muted or pi.bypassed:
                    title = prepstr('(' + mp.get_name() + ')')
                else:
                    title = prepstr(mp.get_name())
                layout.set_markup("<small>%s</small>" % title)
                lw, lh = layout.get_pixel_size()
                if mp in player.active_plugins:
                    pctx.set_source_rgb(*brushes[self.COLOR_BORDER_SELECT])
                    pctx.rectangle(PLUGINWIDTH / 2 - lw / 2 - 3, PLUGINHEIGHT / 2 - lh / 2, lw + 6, lh)
                    pctx.stroke()
                r, g, b = brushes[self.COLOR_MUTED if pi.muted else self.COLOR_DEFAULT]
                c2 = Gdk.Color(red=1, green=1, blue=1)
                blended = blend(Gdk.Color(red=r, green=g, blue=b), c2, 0.7)
                pctx.set_source_rgb(blended.red_float, blended.green_float, blended.blue_float)
                pctx.move_to(PLUGINWIDTH / 2 - lw / 2 + 1, PLUGINHEIGHT / 2 - lh / 2 + 1)
                PangoCairo.update_layout(pctx, layout)
                PangoCairo.show_layout(pctx, layout)
                pctx.set_source_rgb(*brushes[self.COLOR_TEXT])
                pctx.move_to(PLUGINWIDTH / 2 - lw / 2, PLUGINHEIGHT / 2 - lh / 2)
                PangoCairo.update_layout(pctx, layout)
                PangoCairo.show_layout(pctx, layout)
            else:
                pctx = cairo.Context(pi.plugingfx)
            if config.get_config().get_led_draw() == True:
                # led border
                r, g, b = brushes[self.COLOR_MUTED if pi.muted else self.COLOR_DEFAULT]
                border = blend(Gdk.Color(red=r, green=g, blue=b), Gdk.Color(red=0, green=0, blue=0), 0.5)
                pctx.set_source_rgb(border.red_float, border.green_float, border.blue_float)
                pctx.rectangle(LEDOFSX, LEDOFSY, LEDWIDTH - 1, LEDHEIGHT - 1)
                pctx.stroke()

                maxl, maxr = mp.get_last_peak()
                amp = min(max(maxl, maxr), 1.0)
                if amp != pi.amp:
                    if amp >= 1:
                        # from collections import deque
                        # if not mp.get_name() in self.peaks:
                            # self.peaks[mp.get_name()] = deque(maxlen=25)
                        # dq = self.peaks[mp.get_name()]
                        # dq.append(LEDHEIGHT - 4)

                        pctx.set_source_rgb(*brushes[self.COLOR_LED_WARNING])
                        pctx.rectangle(LEDOFSX + 1, LEDOFSY + 1, LEDWIDTH - 2, LEDHEIGHT - 2)
                        pctx.fill()

                    else:
                        pctx.set_source_rgb(*brushes[self.COLOR_LED_OFF])
                        pctx.rectangle(LEDOFSX, LEDOFSY, LEDWIDTH, LEDHEIGHT)
                        pctx.fill()
                        amp = 1.0 - (linear2db(amp, -76.0) / -76.0)
                        height = int((LEDHEIGHT - 4) * amp + 0.5)
                        if (height > 0):
                            # led fill
                            pctx.set_source_rgb(*brushes[self.COLOR_LED_ON])
                            pctx.rectangle(LEDOFSX + 1, (LEDOFSY + LEDHEIGHT - height - 1), LEDWIDTH - 2, height)
                            pctx.fill()
                            # # peak falloff
                            # from collections import deque
                            # if not mp.get_name() in self.peaks:
                            #     self.peaks[mp.get_name()] = deque(maxlen=25)
                            # dq = self.peaks[mp.get_name()]
                            # dq.append(height)

                            # peak_color = cm.alloc_color(blend(cm.alloc_color(brushes[self.COLOR_LED_ON]), gtk.gdk.Color("#fff"), 0.15))
                            # h = LEDOFSY + LEDHEIGHT - 1 - max(height, sum(dq)/len(dq))
                            # gc.set_foreground(peak_color)
                            # pi.plugingfx.draw_line(gc, LEDOFSX + 1, h, LEDOFSX + LEDWIDTH - 2, h)

                    pi.amp = amp
                relperc = (min(1.0, mp.get_last_cpu_load() / max_cpu_scale) * cpu_scale)
                if relperc != pi.cpu:
                    pi.cpu = relperc

                    # cpu fill
                    pctx.set_source_rgb(*brushes[self.COLOR_CPU_OFF])
                    pctx.rectangle(CPUOFSX, CPUOFSY, CPUWIDTH, CPUHEIGHT)
                    pctx.fill()

                    # cpu border
                    color = brushes[self.COLOR_MUTED if pi.muted else self.COLOR_DEFAULT]
                    r, g, b = color
                    border = blend(Gdk.Color(red=r, green=g, blue=b), Gdk.Color(red=0, green=0, blue=0), 0.5)
                    pctx.set_source_rgb(border.red_float, border.green_float, border.blue_float)
                    pctx.rectangle(CPUOFSX, CPUOFSY, CPUWIDTH - 1, CPUHEIGHT - 1)
                    pctx.stroke()

                    height = int((CPUHEIGHT - 4) * relperc + 0.5)
                    if (height > 0):
                        if relperc >= 0.9:
                            pctx.set_source_rgb(*brushes[self.COLOR_CPU_WARNING])
                        else:
                            pctx.set_source_rgb(*brushes[self.COLOR_CPU_ON])
                        pctx.rectangle(CPUOFSX + 1, (CPUOFSY + CPUHEIGHT - height - 1), CPUWIDTH - 2, height)
                        pctx.fill()
            # shadow
            ctx.rectangle(rx + 3, ry + 3, PLUGINWIDTH, PLUGINHEIGHT)
            ctx.set_source_rgba(0.0, 0.0, 0.0, 0.2)
            ctx.fill()

            if mp in player.active_plugins:
                pass

            # flip plugin pixmap to screen
            ctx.set_source_surface(pi.plugingfx, int(rx), int(ry))
            ctx.paint()

    def draw(self, ctx):
        """
        Draws plugins, connections and arrows.
        """
        player = com.get('neil.core.player')
        if player.is_loading():
            return
        cfg = config.get_config()
        rect = self.get_allocation()
        w, h = rect.width, rect.height
        arrowcolors = {
                zzub.zzub_connection_type_audio: [
                        cfg.get_float_color("MV Arrow"),
                        cfg.get_float_color("MV Arrow Border In"),
                        cfg.get_float_color("MV Arrow Border Out"),
                ],
                zzub.zzub_connection_type_event: [
                        cfg.get_float_color("MV Controller Arrow"),
                        cfg.get_float_color("MV Controller Arrow Border In"),
                        cfg.get_float_color("MV Controller Arrow Border Out"),
                ],
        }
        bgbrush = cfg.get_float_color("MV Background")
        linepen = cfg.get_float_color("MV Line")

        cx, cy = w * 0.5, h * 0.5

        def get_pixelpos(x, y):
            return cx * (1 + x), cy * (1 + y)

        def draw_line(bmpctx, crx, cry, rx, ry):
            vx, vy = (rx - crx), (ry - cry)
            length = (vx * vx + vy * vy) ** 0.5
            if not length:
                return
            vx, vy = vx / length, vy / length
            bmpctx.move_to(crx, cry)
            bmpctx.line_to(rx, ry)
            bmpctx.set_source_rgb(*linepen)
            bmpctx.stroke()

        def draw_line_arrow(bmpctx, clr, crx, cry, rx, ry):
            vx, vy = (rx - crx), (ry - cry)
            length = (vx * vx + vy * vy) ** 0.5
            if not length:
                return
            vx, vy = vx / length, vy / length

            cpx, cpy = crx + vx * (length * 0.5), cry + vy * (length * 0.5)

            def make_triangle(radius):
                ux, uy = vx, vy
                if cfg.get_curve_arrows():
                    # bezier curve tangent
                    def dp(t, a, b, c, d):
                        return -3 * (1 - t) ** 2 * a + 3 * (1 - t) ** 2 * b - 6 * t * (1 - t) * b - 3 * (t ** 2) * c + 6 * t * (1 - t) * c + 3 * (t ** 2) * d
                    tx = dp(.5, crx, crx + vx * (length * 0.6), rx - vx * (length * 0.6), rx)
                    ty = dp(.5, cry, cry, ry, ry)
                    tl = (tx ** 2 + ty ** 2) ** .5
                    ux, uy = tx / tl, ty / tl

                t1 = (int(cpx - ux * radius + uy * radius),
                      int(cpy - uy * radius - ux * radius))
                t2 = (int(cpx + ux * radius),
                      int(cpy + uy * radius))
                t3 = (int(cpx - ux * radius - uy * radius),
                      int(cpy - uy * radius + ux * radius))

                return t1, t2, t3

            def draw_triangle(t1, t2, t3):
                bmpctx.move_to(*t1)
                bmpctx.line_to(*t2)
                bmpctx.line_to(*t3)
                bmpctx.close_path()
            tri1 = make_triangle(ARROWRADIUS)

            bmpctx.save()
            bmpctx.translate(-0.5, -0.5)

            # curve
            if cfg.get_curve_arrows():
                # bezier curve tanget
                def dp(t, a, b, c, d):
                    return -3 * (1 - t) ** 2 * a + 3 * (1 - t) ** 2 * b - 6 * t * (1 - t) * b - 3 * (t ** 2) * c + 6 * t * (1 - t) * c + 3 * (t ** 2) * d
                tx = dp(.5, crx, crx + vx * (length * 0.6), rx - vx * (length * 0.6), rx)
                ty = dp(.5, cry, cry, ry, ry)
                tl = (tx ** 2 + ty ** 2) ** .5
                tx, ty = tx / tl, ty / tl

                # stroke the triangle
                draw_triangle(*tri1)
                bmpctx.set_source_rgb(*[x * 0.5 for x in bgbrush])
                bmpctx.set_line_width(1)
                bmpctx.stroke()

                bmpctx.move_to(crx, cry)
                bmpctx.curve_to(crx + vx * (length * 0.6), cry,
                                rx - vx * (length * 0.6), ry,
                                rx, ry)

                bmpctx.set_line_width(4)
                bmpctx.stroke_preserve()
                bmpctx.set_line_width(2.5)
                bmpctx.set_source_rgb(*clr[0])
                # bmpctx.set_source_rgb(*linepen)
                bmpctx.stroke()

                draw_triangle(*tri1)
                bmpctx.fill()
            # straight line
            else:
                bmpctx.set_line_width(1)
                bmpctx.set_source_rgb(*linepen)
                bmpctx.move_to(crx, cry)
                bmpctx.line_to(rx, ry)
                bmpctx.stroke()

                bmpctx.set_source_rgb(*clr[0])
                draw_triangle(*tri1)
                bmpctx.fill_preserve()
                bmpctx.set_source_rgb(*linepen)
                bmpctx.stroke()

            bmpctx.restore()

        if not self.routebitmap:
            self.routebitmap = cairo.ImageSurface(cairo.Format.ARGB32, w, h)
            bmpctx = cairo.Context(self.routebitmap)
            bmpctx.set_source_rgb(*cfg.get_float_color('MV Background'))
            bmpctx.rectangle(0, 0, w, h)
            bmpctx.fill()

            bmpctx.translate(0.5, 0.5)
            bmpctx.set_line_width(1)
            mplist = [(mp, get_pixelpos(*mp.get_position()))
                      for mp in player.get_plugin_list()]

            for mp, (rx, ry) in mplist:
                if self.dragging and mp in player.active_plugins:
                    pinfo = self.get_plugin_info(mp)
                    rx, ry = get_pixelpos(*pinfo.dragpos)
                for index in range(mp.get_input_connection_count()):
                    targetmp = mp.get_input_connection_plugin(index)
                    pi = common.get_plugin_infos().get(targetmp)
                    if not pi.songplugin:
                        continue
                    tmppos = targetmp.get_position()
                    if self.dragging and targetmp in player.active_plugins:
                        pinfo = self.get_plugin_info(targetmp)
                        tmppos = pinfo.dragpos
                    crx, cry = get_pixelpos(*tmppos)
                    if (mp.get_input_connection_type(index) !=
                        zzub.zzub_connection_type_event):
                        amp = mp.get_parameter_value(0, index, 0)
                        amp /= 16384.0
                        amp = amp ** 0.5
                        #color = [amp, amp, amp]
                        #arrowcolors[zzub.zzub_connection_type_audio][0] = color
                        r, g, b = cfg.get_float_color("MV Arrow")
                        c = blend(Gdk.Color(red=r, green=g, blue=b), Gdk.Color(red=0, green=0, blue=0), amp)
                        arrowcolors[zzub.zzub_connection_type_audio][0] = [c.red_float, c.green_float, c.blue_float]

                    draw_line_arrow(bmpctx, arrowcolors[mp.get_input_connection_type(index)], int(crx), int(cry), int(rx), int(ry))
        ctx.set_source_surface(self.routebitmap, 0, 0)
        ctx.paint()
        if self.connecting:
            ctx.set_line_width(1)
            crx, cry = get_pixelpos(*player.active_plugins[0].get_position())
            rx, ry = self.connectpos
            draw_line(ctx, int(crx), int(cry), int(rx), int(ry))
        self.draw_leds(ctx)

    # This method is not *just* for key-jazz, it handles all key-events in router. Rename?
    def on_key_jazz(self, widget, event, plugin):
        mask = event.state
        kv = event.keyval
        k = Gdk.keyval_name(kv)
        if (mask & Gdk.ModifierType.CONTROL_MASK):
            if k == 'Return':
                com.get('neil.core.pluginbrowser', self)
                return
        player = com.get('neil.core.player')
        if not plugin:
            if player.active_plugins:
                plugin = player.active_plugins[0]
            else:
                return
        note = None
        octave = player.octave
        if  k == 'KP_Multiply':
            octave = min(max(octave + 1, 0), 9)
        elif k == 'KP_Divide':
            octave = min(max(octave - 1, 0), 9)
        elif k == 'Delete':
            for plugin in player.active_plugins:
                if not is_root(plugin):
                    player.delete_plugin(plugin)
        elif kv < 256:
            note = key_to_note(kv)
        player.octave = octave
        if note:
            if note not in self.chordnotes:
                self.chordnotes.append(note)
                n = ((note[0] + octave) << 4 | note[1] + 1)
                plugin.play_midi_note(n, 0, 127)

    def on_key_jazz_release(self, widget, event, plugin):
        player = com.get('neil.core.player')
        if not plugin:
            if player.active_plugins:
                plugin = player.active_plugins[0]
            else:
                return
        kv = event.keyval
        if kv < 256:
            player = com.get('neil.core.player')
            octave = player.octave
            note = key_to_note(kv)
            if note in self.chordnotes:
                self.chordnotes.remove(note)
                n = ((note[0] + octave) << 4 | note[1] + 1)
                plugin.play_midi_note(zzub.zzub_note_value_off, n, 0)

__all__ = [
'ParameterDialog',
'ParameterDialogManager',
'PresetDialog',
'PresetDialogManager',
'AttributesDialog',
'RoutePanel',
'VolumeSlider',
'RouteView',
]

__neil__ = dict(
        classes = [
                ParameterDialog,
                ParameterDialogManager,
                PresetDialog,
                PresetDialogManager,
                AttributesDialog,
                RoutePanel,
                VolumeSlider,
                RouteView,
        ],
)

if __name__ == '__main__':
    import testplayer
    import utils
    player = testplayer.get_player()
    player.load_ccm(utils.filepath('demosongs/paniq-knark.ccm'))
    window = testplayer.TestWindow()
    window.add(RoutePanel(window))
    window.PAGE_ROUTE = 1
    window.index = 1
    window.show_all()
    Gtk.main()
