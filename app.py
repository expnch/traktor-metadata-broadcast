from flask import Flask, request
import logging
import threading
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk, Gtk


def writePlayerState(now_playing, decks):
    with open('player_state.txt', 'w+') as f:
        f.write(now_playing + '\n')
        for key, value in decks.items():
            f.write(key + ':' + value + '\n')


def loadPlayerState():
    now_playing = 'A'
    decks = {'A': '', 'B': ''}
    try:
        with open('player_state.txt', 'r') as f:
            now_playing = f.readline().strip()
            print('Loaded now playing:', now_playing)
            for line in f:
                if line:
                    name, value = line.strip().split(':')
                    decks[name] = value
                    print('Loaded deck', name, 'with value', value)
    except Exception as e:
        print('No save file found')

    return now_playing, decks


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super(AppWindow, self).__init__(application=app)

        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_path('style.css')
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.init_ui()

    def init_ui(self):
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.box)
        self.box.set_css_classes(['box'])

        self.label_now_playing = Gtk.Label(label="NOW_PLAYING:")
        self.box.append(self.label_now_playing)
        self.label_now_playing.set_css_classes(['title'])
        self.label_now_playing.set_halign(Gtk.Align.START)

        self.label_up_next = Gtk.Label(label="UP_NEXT:")
        self.box.append(self.label_up_next)
        self.label_up_next.set_css_classes(['title'])
        self.label_up_next.set_halign(Gtk.Align.START)

        self.set_show_menubar(False)

    def now_playing(self, s):
        self.label_now_playing.set_text("NOW_PLAYING: " + s)

    def up_next(self, s):
        self.label_up_next.set_text("UP_NEXT: " + s)


class GtkApp(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

        self.decks = {}
        self.deck_playing = 'A'

    def on_activate(self, app):
        self.win = AppWindow(app)
        self.win.present()

        np, d = loadPlayerState()
        self.decks = d
        self.deck_playing = np
        self.now_playing(np)
        if np == 'A':
            self.deck_loaded('B', d['B'])
        else:
            self.deck_loaded('A', d['A'])

    def now_playing(self, deck):
        self.deck_playing = deck
        s = self.decks[deck]
        self.win.now_playing(s)

        writePlayerState(self.deck_playing, self.decks)

    def deck_loaded(self, deck, s):
        self.decks[deck] = s
        if self.deck_playing == deck:
            self.win.now_playing(s)
        else:
            self.win.up_next(s)

        writePlayerState(self.deck_playing, self.decks)

def genDeckLoadedFunction(gtk_app):
    def deckLoaded(deck):
        data = request.get_json()

        title = data.get('title', '')
        artist = data.get('artist' '')
        submitter = data.get('comment', '')

        msg = f'{title} by {artist}, submitted by {submitter}'
        gtk_app.deck_loaded(deck, msg)

        return 'ok'

    return deckLoaded


def genDeckUpdatedFunction(gtk_app):
    def deckUpdated(deck):
        data = request.get_json()

        if data.get('isPlaying', False):
            gtk_app.now_playing(deck)

        return 'ok'

    return deckUpdated


app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@app.route('/')
def doNothing():
    return 'ok'


if __name__ == '__main__':
    gtk_app = GtkApp(application_id="com.github.expnch.traktor-meta-broadcast")

    app.add_url_rule(
        '/deckLoaded/<deck>',
        'deckLoaded',
        genDeckLoadedFunction(gtk_app),
        methods=['POST']
    )
    app.add_url_rule(
        '/updateDeck/<deck>',
        'deckUpdated',
        genDeckUpdatedFunction(gtk_app),
        methods=['POST']
    )

    server = threading.Thread(target=app.run, kwargs={
            'host': '0.0.0.0',
            'port': 8080
        },
        daemon=True)

    server.start()
    gtk_app.run()
