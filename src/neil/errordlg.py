from traceback import format_exception, print_exc as traceback_print_exc
import sys
from gi.repository import Gtk

Parent = None


def error(parent, msg, msg2=None, details=None, offer_quit=False):
    """
    Shows an error message dialog.
    """
    dialog = Gtk.MessageDialog(parent=parent and parent.get_toplevel(),
#        Gtk.Dialog.MODAL | Gtk.DIALOG_DESTROY_WITH_PARENT,
        
#        Gtk.MESSAGE_ERROR, Gtk.BUTTONS_NONE
                               )
    dialog.set_markup(msg)
    dialog.set_resizable(True)
    if msg2:
        dialog.format_secondary_text(msg2)
    if details:
        expander = Gtk.Expander(label="Details")
        dialog.vbox.pack_start(expander, False, True, 0)
        label = Gtk.TextView()
        label.set_editable(False)
        label.get_buffer().set_property('text', details)
        label.set_wrap_mode(Gtk.WrapMode.NONE)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(-1, 200)

        sw.add(label)
        expander.add(sw)
        dialog.show_all()
    dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
    if offer_quit:
        dialog.add_button(Gtk.STOCK_QUIT, Gtk.ResponseType.REJECT)

        def delayed_quit():
            try:
                Gtk.main_quit()
            except RuntimeError:
                raise SystemExit

        def quit_on_cancel(dlg, response_id):
            if response_id == Gtk.Response.REJECT:
                gobject.timeout_add(1, delayed_quit)
        dialog.connect('response', quit_on_cancel)
    response = dialog.run()
    dialog.destroy()
    return response

last_exc = None


def show_exc_dialog(exc_type, value, traceback):
    global last_exc
    exc = ''.join(format_exception(exc_type, value, traceback))
    if exc == last_exc:
        return
    last_exc = exc
    error(Parent, "<b>An exception (<i>%s</i>) occurred.</b>" % exc_type.__name__, str(value), exc, offer_quit=True)


def print_exc():
    traceback_print_exc()
    show_exc_dialog(*sys.exc_info())


def local_excepthook(exc_type, value, traceback):
    sys.__excepthook__(exc_type, value, traceback)
    show_exc_dialog(exc_type, value, traceback)


def install(parent=None):
    global Parent
    Parent = parent
    sys.excepthook = local_excepthook

if __name__ == '__main__':
    install()
