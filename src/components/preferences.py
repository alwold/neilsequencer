# encoding: latin-1

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
Contains panels and dialogs related to application preferences.
"""

import os
from gi.repository import Gtk
import webbrowser

from neil.utils import prepstr, buffersize_to_latency, filepath, error, add_scrollbars, new_listview, sharedpath
import config
from neil.common import MARGIN, MARGIN2, MARGIN3

from neil.controller import learn_controller
import neil.com as com

import zzub

samplerates = [96000, 48000, 44100, 22050]
buffersizes = [32768, 16384, 8192, 4096, 2048, 1024, 512, 256, 128, 64, 32, 16]


class CancelException(Exception):
    """
    Is being thrown when the user hits cancel in a sequence of
    modal UI dialogs.
    """
    __neil__ = dict(
        id='neil.exception.cancel',
        exception=True,
        categories=[
        ]
    )


class GeneralPanel(Gtk.VBox):
    """
    Panel which allows changing of general settings.
    """

    __neil__ = dict(
        id='neil.core.pref.general',
        categories=[
            'neil.prefpanel',
        ]
    )

    __prefpanel__ = dict(
        label="General",
    )

    def __init__(self):
        """
        Initializing.
        """
        Gtk.VBox.__init__(self)
        self.set_border_width(MARGIN)
        frame1 = Gtk.Frame.new("General Settings")
        fssizer = Gtk.VBox(False, MARGIN)
        fssizer.set_border_width(MARGIN)
        frame1.add(fssizer)
        incsave = config.get_config().get_incremental_saving()
        # rackpanel = config.get_config().get_experimental('RackPanel')
        leddraw = config.get_config().get_led_draw()
        curvearrows = config.get_config().get_curve_arrows()
        patnoteoff = config.get_config().get_pattern_noteoff()
        self.patternfont = Gtk.FontButton(
            config.get_config().get_pattern_font())
        self.patternfont.set_use_font(True)
        self.patternfont.set_use_size(True)
        self.patternfont.set_show_style(True)
        self.patternfont.set_show_size(True)
        self.incsave = Gtk.CheckButton()
        self.leddraw = Gtk.CheckButton()
        self.curvearrows = Gtk.CheckButton()
        self.patnoteoff = Gtk.CheckButton()
        self.rackpanel = Gtk.CheckButton()
        self.incsave.set_active(int(incsave))
        self.leddraw.set_active(int(leddraw))
        self.curvearrows.set_active(int(curvearrows))
        self.patnoteoff.set_active(int(patnoteoff))
        # self.rackpanel.set_active(rackpanel)

        self.theme = Gtk.ComboBoxText.new()
        themes = os.listdir(sharedpath('themes'))
        self.theme.append_text('Default')
        for i, theme in enumerate(themes):
            name = os.path.splitext(theme)[0]
            self.theme.append_text(name)
            if name == config.get_config().active_theme:
                self.theme.set_active(i)

        sg1 = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        sg2 = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        def add_row(c1, c2):
            row = Gtk.HBox(False, MARGIN)
            c1.set_alignment(1, 0.5)
            sg1.add_widget(c1)
            sg2.add_widget(c2)
            row.pack_start(c1, expand=False)
            row.pack_end(c2)
            fssizer.pack_start(row, expand=False)
        add_row(Gtk.Label("Incremental Saves"), self.incsave)
        add_row(Gtk.Label("Draw Amp LEDs in Router"), self.leddraw)
        add_row(Gtk.Label("Auto Note-Off in Pattern Editor"), self.patnoteoff)
        add_row(Gtk.Label("Pattern Font"), self.patternfont)
        # add_row(gtk.Label("Rack Panel View (After Restart)"), self.rackpanel)
        add_row(Gtk.Label("Theme"), self.theme)
        add_row(Gtk.Label("Draw Curves in Router"), self.curvearrows)
        self.add(frame1)

    def apply(self):
        """
        Writes general config settings to file.
        """
        config.get_config().set_pattern_font(self.patternfont.get_font_name())
        config.get_config().set_incremental_saving(self.incsave.get_active())
        config.get_config().set_led_draw(self.leddraw.get_active())
        config.get_config().set_pattern_noteoff(self.patnoteoff.get_active())
        config.get_config().set_curve_arrows(self.curvearrows.get_active())
        # config.get_config().set_experimental('RackPanel', self.rackpanel.get_active())
        theme_name = self.theme.get_active_text()
        if config.get_config().active_theme != theme_name:
            if theme_name == 'Default':
                config.get_config().select_theme(None)
            else:
                config.get_config().select_theme(self.theme.get_active_text())
        import neil.com
        neil.com.get('neil.core.patternpanel').update_all()
        neil.com.get('neil.core.router.view').update_all()
        neil.com.get('neil.core.sequencerpanel').update_all()


class DriverPanel(Gtk.VBox):
    """
    Panel which allows to see and change audio driver settings.
    """

    __neil__ = dict(
        id='neil.core.pref.driver',
        categories=[
            'neil.prefpanel',
        ]
    )

    __prefpanel__ = dict(
        label="Audio",
    )

    def __init__(self):
        """
        Initializing.
        """
        Gtk.VBox.__init__(self)
        self.set_border_width(MARGIN)
        self.cboutput = Gtk.ComboBoxText.new()
        self.cbsamplerate = Gtk.ComboBoxText.new()
        self.cblatency = Gtk.ComboBoxText.new()
        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        def add_row(c1, c2):
            row = Gtk.HBox(False, MARGIN)
            size_group.add_widget(c1)
            c1.set_alignment(1, 0.5)
            row.pack_start(c1, expand=False)
            row.pack_start(c2)
            return row

        sizer1 = Gtk.Frame.new("Audio Output")
        vbox = Gtk.VBox(False, MARGIN)
        vbox.pack_start(add_row(Gtk.Label("Driver"),
                        self.cboutput), expand=False)
        vbox.pack_start(add_row(Gtk.Label("Samplerate"),
                        self.cbsamplerate), expand=False)
        vbox.pack_start(add_row(Gtk.Label("Latency"),
                        self.cblatency), expand=False)
        vbox.set_border_width(MARGIN)
        sizer1.add(vbox)
        inputname, outputname, samplerate, buffersize = config.get_config().get_audiodriver_config()
        audiodriver = com.get('neil.core.driver.audio')
        if not outputname:
            outputname = audiodriver.get_name(-1)
        for i in range(audiodriver.get_count()):
            name = prepstr(audiodriver.get_name(i))
            self.cboutput.append_text(name)
            if audiodriver.get_name(i) == outputname:
                self.cboutput.set_active(i)
        for sr in samplerates:
            self.cbsamplerate.append_text("%iHz" % sr)
        self.cbsamplerate.set_active(samplerates.index(samplerate))
        for bs in buffersizes:
            self.cblatency.append_text(
                "%.1fms" % buffersize_to_latency(bs, 44100))
        self.cblatency.set_active(buffersizes.index(buffersize))
        self.add(sizer1)

    def apply(self):
        """
        Validates user input and reinitializes the driver with current
        settings. If the reinitialization fails, the user is being
        informed and asked to change the settings.
        """
        sr = self.cbsamplerate.get_active()
        if sr == -1:
            error(self, "You did not pick a valid sample rate.")
            raise com.exception('neil.exception.cancel')
        sr = samplerates[sr]
        bs = self.cblatency.get_active()
        if bs == -1:
            error(self, "You did not pick a valid latency.")
            raise com.exception('neil.exception.cancel')
        bs = buffersizes[bs]
        o = self.cboutput.get_active()
        if o == -1:
            error(self, "You did not select a valid output device.")
            raise com.exception('neil.exception.cancel')
        iname = ""
        audiodriver = com.get('neil.core.driver.audio')
        oname = audiodriver.get_name(o)
        inputname, outputname, samplerate, buffersize = config.get_config().get_audiodriver_config()
        if (oname != outputname) or (samplerate != sr) or (bs != buffersize):
            config.get_config().set_audiodriver_config(iname, oname, sr, bs)  # write back
            try:
                audiodriver.init()
            except audiodriver.AudioInitException:
                import traceback
                traceback.print_exc()
                error(self, "<b><big>There was an error initializing the audio driver.</big></b>\n\nThis can happen when the specified sampling rate or latency is not supported by a particular audio device. Change settings and try again.")
                raise com.exception('neil.exception.cancel')


class ControllerPanel(Gtk.VBox):
    """
    Panel which allows to set up midi controller mappings.
    """

    __neil__ = dict(
        id='neil.core.pref.controller',
        categories=[
            'neil.prefpanel',
        ]
    )

    __prefpanel__ = dict(
        label="Controllers",
    )

    def __init__(self):
        self.sort_column = 0
        Gtk.VBox.__init__(self)
        self.set_border_width(MARGIN)
        frame1 = Gtk.Frame.new("Controllers")
        sizer1 = Gtk.VBox(False, MARGIN)
        sizer1.set_border_width(MARGIN)
        frame1.add(sizer1)
        self.controllers, self.store, columns = new_listview([
            ('Name', str),
            ('Channel', str),
            ('Controller', str),
        ])
        self.controllers.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        sizer1.add(add_scrollbars(self.controllers))
        self.btnadd = Gtk.Button(stock=Gtk.STOCK_ADD)
        self.btnremove = Gtk.Button(stock=Gtk.STOCK_REMOVE)
        hsizer = Gtk.HButtonBox()
        hsizer.set_spacing(MARGIN)
        hsizer.set_layout(Gtk.ButtonBoxStyle.START)
        hsizer.pack_start(self.btnadd, expand=False)
        hsizer.pack_start(self.btnremove, expand=False)
        sizer1.pack_start(hsizer, expand=False)
        self.add(frame1)
        self.btnadd.connect('clicked', self.on_add_controller)
        self.btnremove.connect('clicked', self.on_remove_controller)
        self.update_controllers()

    def update_controllers(self):
        """
        Updates the controller list.
        """
        self.store.clear()
        for name, channel, ctrlid in config.get_config().get_midi_controllers():
            self.store.append([name, str(channel), str(ctrlid)])

    def on_add_controller(self, widget):
        """
        Handles 'Add' button click. Opens a popup that records controller events.
        """
        res = learn_controller(self)
        if res:
            name, channel, ctrlid = res
            self.store.append([name, str(channel), str(ctrlid)])

    def on_remove_controller(self, widget):
        """
        Handles 'Remove' button click. Removes the selected controller from list.
        """
        store, sel = self.controllers.get_selection().get_selected_rows()
        refs = [Gtk.TreeRowReference(store, row) for row in sel]
        for ref in refs:
            store.remove(store.get_iter(ref.get_path()))

    def apply(self):
        """
        Validates user input and reinitializes the driver with current
        settings. If the reinitialization fails, the user is being
        informed and asked to change the settings.
        """
        ctrllist = []
        for row in self.store:
            name = row[0]
            channel = int(row[1])
            ctrlid = int(row[2])
            ctrllist.append((name, channel, ctrlid))
        config.get_config().set_midi_controllers(ctrllist)


class MidiPanel(Gtk.VBox):
    """
    Panel which allows to see and change a list of used MIDI output devices.
    """

    __neil__ = dict(
        id='neil.core.pref.midi',
        categories=[
            'neil.prefpanel',
        ]
    )

    __prefpanel__ = dict(
        label="MIDI",
    )

    def __init__(self):
        Gtk.VBox.__init__(self, False, MARGIN)
        self.set_border_width(MARGIN)
        frame1 = Gtk.Frame.new("MIDI Input Devices")
        sizer1 = Gtk.VBox()
        sizer1.set_border_width(MARGIN)
        frame1.add(sizer1)
        self.idevicelist, self.istore, columns = new_listview([
            ("Use", bool),
            ("Device", str),
        ])
        self.idevicelist.set_property('headers-visible', False)
        inputlist = config.get_config().get_mididriver_inputs()
        player = com.get('neil.core.player')
        for i in range(zzub.Mididriver.get_count(player)):
            if zzub.Mididriver.is_input(player, i):
                name = prepstr(zzub.Mididriver.get_name(player, i))
                use = name.strip() in inputlist
                self.istore.append([use, name])
        sizer1.add(add_scrollbars(self.idevicelist))
        frame2 = Gtk.Frame.new("MIDI Output Devices")
        sizer2 = Gtk.VBox()
        sizer2.set_border_width(MARGIN)
        frame2.add(sizer2)
        self.odevicelist, self.ostore, columns = new_listview([
            ("Use", bool),
            ("Device", str),
        ])
        self.odevicelist.set_property('headers-visible', False)
        outputlist = config.get_config().get_mididriver_outputs()
        for i in range(zzub.Mididriver.get_count(player)):
            if zzub.Mididriver.is_output(player, i):
                name = prepstr(zzub.Mididriver.get_name(player, i))
                use = name in outputlist
                self.ostore.append([use, name])
        sizer2.add(add_scrollbars(self.odevicelist))
        self.add(frame1)
        self.add(frame2)
        label = Gtk.Label(
            "Checked MIDI devices will be used the next time you start Neil.")
        label.set_alignment(0, 0)
        self.pack_start(label, expand=False, fill=True, padding=0)

    def apply(self):
        """
        Adds the currently selected drivers to the list.
        """
        inputlist = []
        for row in self.istore:
            if row[0]:
                inputlist.append(row[1])
        config.get_config().set_mididriver_inputs(inputlist)
        outputlist = []
        for row in self.ostore:
            if row[0]:
                outputlist.append(row[1])
        config.get_config().set_mididriver_outputs(outputlist)


class KeyboardPanel(Gtk.VBox):
    """
    Panel which allows to see and change the current keyboard configuration.
    """

    __neil__ = dict(
        id='neil.core.pref.keyboard',
        categories=[
            'neil.prefpanel',
        ]
    )

    __prefpanel__ = dict(
        label="Keyboard",
    )

    KEYMAPS = [
        ('en', 'English (QWERTY)'),
        ('de', 'Deutsch (QWERTZ)'),
        ('dv', 'Dvorak (\',.PYF)'),
        ('fr', 'French (AZERTY)'),
        ('neo', 'Neo (XVLCWK)')
    ]

    def __init__(self):
        Gtk.VBox.__init__(self, False, MARGIN)
        self.set_border_width(MARGIN)
        hsizer = Gtk.HBox(False, MARGIN)
        hsizer.pack_start(Gtk.Label("Keyboard Map"), expand=False, fill=True, padding=0)
        self.cblanguage = Gtk.ComboBoxText.new()
        sel = 0
        lang = config.get_config().get_keymap_language()
        index = 0
        for kmid, name in self.KEYMAPS:
            self.cblanguage.append_text(name)
            if lang == kmid:
                sel = index
            index += 1
        hsizer.add(self.cblanguage)
        self.pack_start(hsizer, expand=False, fill=True, padding=0)
        self.cblanguage.set_active(sel)

    def apply(self):
        """
        applies the keymap.
        """
        config.get_config().set_keymap_language(
            self.KEYMAPS[self.cblanguage.get_active()][0])


def cmp_prefpanel(a, b):
    a_order = (hasattr(a, '__prefpanel__')
               and a.__prefpanel__.get('label', '')) or ''
    b_order = (hasattr(b, '__prefpanel__')
               and b.__prefpanel__.get('label', '')) or ''
    return cmp(a_order, b_order)


class PreferencesDialog(Gtk.Dialog):
    """
    This Dialog aggregates the different panels and allows
    the user to switch between them using a tab control.
    """

    __neil__ = dict(
        id='neil.core.prefdialog',
        categories=[
        ]
    )

    def __init__(self, parent=None, visible_panel=None):
        Gtk.Dialog.__init__(self,
                            "Preferences",
                            parent,
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
        self.nb = Gtk.Notebook()
        self.nb.set_show_tabs(False)
        self.nb.set_border_width(MARGIN)
        self.nb.set_show_border(False)
        self.panels = sorted(com.get_from_category(
            'neil.prefpanel'), cmp_prefpanel)
        starting_tab_index = 0
        for i, panel in enumerate(self.panels):
            if not hasattr(panel, '__prefpanel__'):
                continue
            cfg = panel.__prefpanel__
            label = cfg.get('label', None)
            if not label:
                continue
            if visible_panel == panel.__neil__['id']:
                starting_tab_index = i
            self.nb.append_page(panel, Gtk.Label(label))
        self.tab_list, self.tab_list_store, columns = new_listview([
                                                                   ('Name', str),])
        self.tab_list.set_headers_visible(False)
        self.tab_list.set_size_request(120, 100)
        # iterate through all tabs and add to tab list
        for i in range(self.nb.get_n_pages()):
            tab_label = self.nb.get_tab_label(
                self.nb.get_nth_page(i)).get_label()
            self.tab_list_store.append([tab_label])
        self.tab_list.connect('cursor-changed', self.on_tab_list_change)
        self.splitter = Gtk.HPaned()
        self.splitter.pack1(add_scrollbars(self.tab_list))
        self.splitter.pack2(self.nb)
        self.vbox.add(self.splitter)

        btnok = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY)
        btnok.grab_default()

        self.connect('response', self.on_response)
        self.show_all()
        print(starting_tab_index)
        # select starting tab and adjust the list index
        self.nb.set_current_page(starting_tab_index)

    def on_response(self, widget, response):
        if response == Gtk.ResponseType.OK:
            self.on_ok()
        elif response == Gtk.ResponseType.APPLY:
            self.on_apply()
        else:
            self.destroy()

    def on_tab_list_change(self, treeview):
        self.nb.set_current_page(treeview.get_cursor()[0][0])

    def apply(self):
        """
        Apply changes in settings without closing the dialog.
        """
        for panel in self.panels:
            panel.apply()

    def on_apply(self):
        """
        Event handler for apply button.
        """
        try:
            self.apply()
        except com.exception('neil.exception.cancel'):
            pass

    def on_ok(self):
        """
        Event handler for OK button. Calls apply
        and then closes the dialog.
        """
        try:
            self.apply()
            self.destroy()
        except com.exception('neil.exception.cancel'):
            pass


def show_preferences(parent, *args):
    """
    Shows the {PreferencesDialog}.

    @param rootwindow: The root window which receives zzub callbacks.
    @type rootwindow: wx.Frame
    @param parent: Parent window.
    @type parent: wx.Window
    """
    PreferencesDialog(parent, *args)


__neil__ = dict(
    classes=[
        CancelException,
        GeneralPanel,
        DriverPanel,
        ControllerPanel,
        MidiPanel,
        KeyboardPanel,
        PreferencesDialog,
    ],
)

__all__ = [
    'CancelException',
    'DriverPanel',
    'MidiInPanel',
    'MidiOutPanel',
    'KeyboardPanel',
    'ExtensionsPanel',
    'PreferencesDialog',
    'show_preferences',
]

if __name__ == '__main__':
    import testplayer
    player = testplayer.get_player()
    window = testplayer.TestWindow()
    window.show_all()
    show_preferences(window)
    Gtk.main()
