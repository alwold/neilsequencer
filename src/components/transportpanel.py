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
    os.system('../../bin/neil-combrowser neil.core.panel.transport')
    raise SystemExit

import gtk
from neil.common import MARGIN, MARGIN2, MARGIN3, MARGIN0
import gobject
from neil.utils import new_stock_image_toggle_button, new_stock_image_button
from neil.utils import format_time, ticks_to_time, new_theme_image_toggle_button
from neil.utils import new_image_button, new_image_toggle_button, imagepath
import neil.audiogui as audiogui
import time
import config
import neil.com as com
import zzub
import neil.common as common
from neil.utils import ObjectHandlerGroup

class TransportPanel(gtk.HBox):
    """
    A panel containing the BPM/TPB spin controls.
    """

    __neil__ = dict(
            id = 'neil.core.panel.transport',
            singleton = True,
            categories = [
                    'view',
            ],
    )

    __view__ = dict(
                    label = "Transport",
                    order = 0,
                    toggle = True,
    )

    def __init__(self):
        """
        Initializer.
        """
        gtk.HBox.__init__(self)
        eventbus = com.get('neil.core.eventbus')
        eventbus.zzub_parameter_changed += self.on_zzub_parameter_changed
        eventbus.zzub_player_state_changed += self.on_zzub_player_state_changed
        eventbus.document_loaded += self.update_all
        self.cpulabel = gtk.Label("CPU:")
        #self.cpu = gtk.ProgressBar()
        #self.cpu.set_size_request(80,-1)
        self.cpuvalue = gtk.Label("100%")
        self.cpuvalue.set_size_request(32,-1)
        self.bpmlabel = gtk.Label("BPM")
        self.bpm = gtk.SpinButton()
        self.bpm.set_range(16,500)
        self.bpm.set_value(126)
        self.bpm.set_increments(1, 10)
        #self.bpm.connect('button-press-event', self.spinbox_clicked)
        self.tpblabel = gtk.Label("TPB")
        self.tpb = gtk.SpinButton()
        self.tpb.set_range(1,32)
        self.tpb.set_value(4)
        self.tpb.set_increments(1, 2)
        #self.tpb.connect('button-press-event', self.spinbox_clicked)

        self.btnplay = new_image_toggle_button(imagepath("playback_play.svg"),
                                               "Play (F5/F6)")
        self.btnrecord = new_image_toggle_button(imagepath("playback_record.svg"), 
                                                 "Record (F7)")
        self.btnrecord.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.color_parse("red"))
        self.btnstop = new_image_button(imagepath("playback_stop.svg"), 
                                        "Stop (F8)")
        self.btnloop = new_image_toggle_button(imagepath("playback_repeat.svg"),
                                               "Repeat")
        self.btnloop.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.color_parse("green"))
        self.btnpanic = new_image_toggle_button(imagepath("playback_panic.svg"),
                                                "Panic (F12)")
        vbox = gtk.VBox(False, 0)
        sg1 = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        sg2 = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        def add_row(name):
            import pango
            c1 = gtk.Label()
            c1.modify_font(pango.FontDescription("Monospace 6"))
            c1.set_markup("<b>%s</b>" % name)
            c1.set_alignment(1, 0.5)
            c2 = gtk.Label()
            c2.modify_font(pango.FontDescription("Monospace 6"))
            c2.set_alignment(1, 0.5)
            hbox = gtk.HBox(False, MARGIN)
            hbox.pack_start(c1, expand=False)
            hbox.pack_start(c2, expand=False)
            sg1.add_widget(c1)
            sg2.add_widget(c2)
            vbox.add(hbox)
            return c2
        self.elapsed = add_row("Elapsed")
        self.current = add_row("Current")
        self.loop = add_row("Loop")
        self.starttime = time.time()
        self.update_label()


        combosizer = gtk.HBox(False, MARGIN)
        combosizer.pack_start(vbox, expand=False)
        combosizer.pack_start(gtk.VSeparator(), expand=False)

        hbox = gtk.HBox(False, MARGIN0)
        hbox.pack_start(self.btnplay,expand=False)
        hbox.pack_start(self.btnrecord,expand=False)
        hbox.pack_start(self.btnstop,expand=False)
        hbox.pack_start(self.btnloop,expand=False)
        self.transport_buttons = hbox.get_children() + [self.btnpanic]
        def on_realize(self):
            for e in self.transport_buttons:
                rc = e.get_allocation()
                w = max(rc.width, rc.height)
                e.set_size_request(w,w)
        self.connect('realize', on_realize)

        combosizer.pack_start(hbox, expand=False)
        combosizer.pack_start(gtk.VSeparator(), expand=False)

        combosizer.pack_start(self.bpmlabel,expand=False)
        combosizer.pack_start(self.bpm,expand=False)
        combosizer.pack_start(self.tpblabel,expand=False)
        combosizer.pack_start(self.tpb,expand=False)

        combosizer.pack_start(gtk.VSeparator(), expand=False)
        cpubox = gtk.HBox(False, MARGIN)
        cpubox.pack_start(self.cpulabel, expand=False)
        #cpubox.pack_start(self.cpu, expand=False)
        cpubox.pack_start(self.cpuvalue, expand=False)
        cpuvbox = gtk.VBox(False, MARGIN0)
        cpuvbox.pack_start(gtk.VBox())
        cpuvbox.pack_start(cpubox, expand=False)
        cpuvbox.pack_end(gtk.VBox())
        combosizer.pack_start(cpuvbox, expand=False)
        combosizer.pack_start(gtk.VSeparator(), expand=False)
        combosizer.pack_start(self.btnpanic, expand=False)

        self.pack_start(gtk.HBox())
        self.pack_start(combosizer, expand=False)
        self.pack_end(gtk.HBox())
        self.set_border_width(MARGIN)
        player = com.get('neil.core.player')
        player.get_plugin(0).set_parameter_value(1, 0, 1, config.get_config().get_default_int('BPM', 126), 1)
        player.get_plugin(0).set_parameter_value(1, 0, 2, config.get_config().get_default_int('TPB', 4), 1)
        player.history_flush_last()
        self.hgroup = ObjectHandlerGroup()
        self.hgroup.connect(self.bpm, 'value-changed', self.on_bpm)
        self.hgroup.connect(self.tpb, 'value-changed', self.on_tpb)
        gobject.timeout_add(100, self.update_label)
        gobject.timeout_add(500, self.update_cpu)

        self.hgroup.connect(self.btnplay, 'clicked', self.play)
        self.hgroup.connect(self.btnrecord, 'clicked', self.on_toggle_automation)
        self.hgroup.connect(self.btnstop, 'clicked', self.stop)
        self.hgroup.connect(self.btnloop, 'clicked', self.on_toggle_loop)
        self.hgroup.connect(self.btnpanic, 'clicked', self.on_toggle_panic)

        accel = com.get('neil.core.accelerators')
        #accel.add_accelerator('F5', self.btnplay, 'clicked')
        accel.add_accelerator('F7', self.btnrecord, 'clicked')
        #accel.add_accelerator('F8', self.btnstop, 'clicked')
        accel.add_accelerator('F12', self.btnpanic, 'clicked')

        self.update_all()

    #def spinbox_clicked(self, widget, event):
    #    player = com.get('neil.core.player')
    #    player.spinbox_edit = True

    def play(self, widget):
        player = com.get('neil.core.player')
        player.play()

    def on_toggle_automation(self, widget):
        player = com.get('neil.core.player')
        if widget.get_active():
            player.set_automation(1)
        else:
            player.set_automation(0)

    def stop(self, widget):
        player = com.get('neil.core.player')
        player.stop()

    def on_toggle_loop(self, widget):
        """
        Handler triggered by the loop toolbar button. Decides whether
        the song loops or not.

        @param event command event.
        @type event: CommandEvent
        """
        player = com.get('neil.core.player')
        if widget.get_active():
            player.set_loop_enabled(1)
        else:
            player.set_loop_enabled(0)

    def on_toggle_panic(self, widget):
        """
        Handler triggered by the mute toolbar button. Deinits/reinits
        sound device.

        @param event command event.
        @type event: CommandEvent
        """
        driver = com.get('neil.core.driver.audio')
        if widget.get_active():
            driver.enable(0)
        else:
            driver.enable(1)

    def update_cpu(self):
        cpu = com.get('neil.core.driver.audio').get_cpu_load()
        #self.cpu.set_fraction(cpu)
        self.cpuvalue.set_label("%i%%" % int((cpu*100) + 0.5))
        return True

    def update_label(self):
        """
        Event handler triggered by a 10fps timer event.
        """
        player = com.get('neil.core.player')
        p = player.get_position()
        m = player.get_plugin(0)
        bpm = m.get_parameter_value(1, 0, 1)
        tpb = m.get_parameter_value(1, 0, 2)
        time.time() - self.starttime
        if player.get_state() == 0: # playing
            e = format_time(time.time() - player.playstarttime)
        else:
            e = format_time(0.0)
        c = format_time(ticks_to_time(p,bpm,tpb))
        lb,le = player.get_loop()
        l = format_time(ticks_to_time(le-lb,bpm,tpb))
        for text,control in [(e,self.elapsed),(c,self.current),(l,self.loop)]:
            #~ if text != control.get_text():
            control.set_markup("%s" % text)
        return True

    def update_btnplay(self):
        state = com.get('neil.core.player').get_state()
        token = self.hgroup.autoblock()
        if state == zzub.zzub_player_state_playing:
            self.btnplay.set_active(True)
        elif state == zzub.zzub_player_state_stopped:
            self.btnplay.set_active(False)

    def on_zzub_player_state_changed(self,state):
        """
        called when the player state changes. updates the play button.
        """
        self.update_btnplay()

    def on_zzub_parameter_changed(self,plugin,group,track,param,value):
        """
        called when a parameter changes in zzub. checks whether this parameter
        is related to master bpm or tpb and updates the view.
        """
        player = com.get('neil.core.player')
        master = player.get_plugin(0)
        bpm = master.get_parameter_value(1, 0, 1)
        if (group,track) == (1,0):
            if param == 1:
                self.update_bpm()
                try:
                    com.get('neil.core.wavetablepanel').waveedit.view.view_changed()
                except AttributeError:
                    pass

            elif param == 2:
                self.update_tpb()

    def on_bpm(self, widget):
        """
        Event handler triggered when the bpm spin control value is being changed.

        @param event: event.
        @type event: wx.Event
        """
        player = com.get('neil.core.player')
        player.get_plugin(0).set_parameter_value(1, 0, 1, int(self.bpm.get_value()), 1)
        player.history_commit("change BPM")
        config.get_config().set_default_int('BPM', int(self.bpm.get_value()))

    def on_tpb(self, widget):
        """
        Event handler triggered when the tpb spin control value is being changed.

        @param event: event.
        @type event: wx.Event
        """
        player = com.get('neil.core.player')
        player.get_plugin(0).set_parameter_value(1, 0, 2, int(self.tpb.get_value()), 1)
        player.history_commit("change TPB")
        config.get_config().set_default_int('TPB', int(self.tpb.get_value()))

    def update_bpm(self):
        block = self.hgroup.autoblock()
        player = com.get('neil.core.player')
        master = player.get_plugin(0)
        bpm = master.get_parameter_value(1, 0, 1)
        self.bpm.set_value(bpm)

    def update_tpb(self):
        block = self.hgroup.autoblock()
        player = com.get('neil.core.player')
        master = player.get_plugin(0)
        tpb = master.get_parameter_value(1, 0, 2)
        self.tpb.set_value(tpb)

    def update_all(self):
        """
        Updates all controls.
        """
        self.update_bpm()
        self.update_tpb()
        player = com.get('neil.core.player')
        self.btnloop.set_active(player.get_loop_enabled())
        self.btnrecord.set_active(player.get_automation())


__neil__ = dict(
        classes = [
                TransportPanel,
        ],
)

