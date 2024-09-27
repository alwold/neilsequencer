# Code update
This branch has modifications to neil to make it work in Python 3 with Gtk 3. It is a work in progress.

Here's what I had to do to get it to run.

- Install package dependencies. The ubuntu packages are:
  - `libgtk2.0-dev`
  - `libgl-dev`
  - `libglu-dev`
  
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
