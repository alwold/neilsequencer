# Code update
This branch has modifications to neil to make it work in Python 3 with Gtk 3. It is a work in progress.

Here's what I had to do to get it to run. My test system is running Ubuntu 24.10.

- Install package dependencies. The ubuntu packages are:
  - `scons`
  - `libmad0-dev`?
  - `libgtk2.0-dev`
  - `libgl-dev`
  - `libglu-dev`
  - `libglade2-dev`?
  - `libsndfile-dev`
  - `libsamplerate-dev`
  - `libfftw3-dev`
  - `libboost-dev`
  - `libportaudio2-dev`
  - `libportaudio19-dev`
  - `xmlto`
  - `libcairo2-dev`?
  - `libmad0-dev`
  
- Install `gtkgl` from source.
  - `git clone https://github.com/peccatoris/gtkgl`
  - `./autogen.sh`
  - `make`
  - `sudo make install`
  
- Install python dependencies (I'm using a pyenv)
  - `pip -m venv venv`
  - `source venv/bin/activate`
  - `pip install -r requirements.txt`
  
- Build the code
  - `scons`

- Run
  - `LD_LIBRARY_PATH=libneil/lib PYTHONPATH=src:src/neil:libneil/src/pyzzub:libneil/lib bin/neil`

## Remaining work
### Tasks
- [ ] Creating master track in sequencer, click it, crash on `zzub_player_get_sequence`
- [x] Fix the way we load the component path in `com.py`
- [ ] Verify clipboard code in utils.py works
- [x] Fix sorting in searchplugins.py
- [x] Fix sorting in mainwindow.py (two places)
- [ ] Check if we need to decode() in prepstr() in utils.py
- [ ] Convert drawing code (where there are commented out expose event connect calls) to cairo:
  - [ ] masterpanel.py
  - [ ] patterns.py (partly implemented)
  - [ ] router.py
  - [x] sequencer.py
  - [ ] envelope.py
  - [ ] waveedit.py
- [ ] Restore background color save/restore on clipbtn in masterpanel.py
- [ ] Verify pickle works in rack.py
- [ ] Find out if we need the frozen detection in gtkcodebuffer.py (and elsewhere?)
- [ ] Convert C plugins that use GTK to GTK 3
- [ ] Verify the code in Sequencer.draw_tracks where it uses translate instead of the old way of creating a new drawable
