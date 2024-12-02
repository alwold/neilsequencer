# Installing Neil

## Installing _Neil_ for the first time

To install _Neil_ you should enter the commands shown below to the terminal. These steps should be executed in order specified in this page. They are also meant for the latest version of the Debian GNU/Linux distribution. If you are on some other system you are on your own. They should work with other Debian derived distributions as well. If something during the installation goes wrong you can try bothering me at unaudio@gmail.com. For those of you who are computer challenged I will explain the meaning of commands that are shown here.

1. Install dependencies (this may take a while).
    ```bash
    sudo apt-get install g++ mercurial scons python-numpy zlib1g-dev libsndfile1-dev libsamplerate0-dev libfftw3-dev libboost-graph-dev libasound2-dev libjack-jackd2-dev ladspa-sdk liblo-dev libflac-dev libmad0-dev xmlto libgtk2.0-dev libgl1-mesa-dev glutg3-dev libgtkgl2.0-dev libgtkglext1-dev
    ```
2. Clone the _Neil_ repository:
    ```bash
    git clone https://github.com/alwold/neilsequencer
    ```
    This creates a copy of the _Neil_ source tree on your hard drive. This is done by calling Git with the "clone" option. To read more about how Git works go here: https://git-scm.com/. A new repository is created for the code in a directory called `neil`.
3. Compile and install Neil:
    ```bash
    cd neil; scons configure; scons; sudo scons install
    ```
    This launches the build scripts with different options. This will configure the build system, compile the C++ code and install it in the `/usr/local/` prefix by default (it is possible to change this).
4. Now you ought to be able to run _Neil_:
    ```bash
    neil
    ```
