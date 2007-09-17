/*
Copyright (C) 2003-2007 Anders Ervik <calvin@countzero.no>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*/

#include "common.h"
#include <functional>
#include <algorithm>
#include <time.h>
#include <float.h>
#include "bmxreader.h"
#include "bmxwriter.h"
#include "timer.h"
#include "dummy.h"
#include "archive.h"
#include "tools.h"

#if defined(POSIX)
#include <dirent.h>
#include <sys/stat.h>
#endif

#if defined(__SSE__)
// denormalisation issues can be avoided by turning on
// flush zero mode, which is an SSE instruction.
// at the moment, this is only being enabled for 
// gcc and i686 machines. modify sconstruct to 
// support other targets.
// also see http://www.intel.com/cd/ids/developer/asmo-na/eng/dc/pentium4/knowledgebase/90575.htm
	#include <xmmintrin.h>

	#if defined(__GNUC__)
		#define SETGRADUN setgradun_
		#define SETABRPUN setabrpun_
	#endif
	
	void SETGRADUN()
	{
	 _MM_SET_FLUSH_ZERO_MODE (_MM_FLUSH_ZERO_OFF);
	}

	void SETABRPUN()
	{
	 _MM_SET_FLUSH_ZERO_MODE (_MM_FLUSH_ZERO_ON);
	}
#else
#define SETGRADUN()
#define SETABRPUN()
#endif

// HKEY_CURRENT_USER\Software\Jeskola\Buzz\Settings
// her er en key som heter BuzzPath, som forteller roten av default buzz-installasjon

using namespace std;

namespace zzub {

short player::oscTables[8][OSCTABSIZE];

/***

	player

***/

/**
 *	\struct player
 *	\brief This struct provides libzzub's core services.
 */
player::player()
	:song_sequencer(this) 
{
	for (int c = 0; c < 2; ++c) {
		mixBuffer[c] = new float[MAXBUFFERSAMPLES*4];
		memset(mixBuffer[c], 0, sizeof(float) * MAXBUFFERSAMPLES*4);
	}
	soloMachine=0;
	workPos=0;
	workFracs=0.0f;
	playerState=player_state_muted;
	currentlyPlayingSequencer=&song_sequencer;
	master=0;
	masterLoader = 0;
	recordParameters=false;
	for (int i = 0; i < audiodriver::MAX_CHANNELS; i++) {
		inputBuffer[i] = 0;
	}
	cpuLoad = 0;
	editCommand = 0;
	stopFlag = false;
}

player::~player(void) {
	// free machineloaders
	clearMachineLoaders();
	machineInstances.clear();	// finally remove master

	if (master)
		delete master;
	if (masterLoader)
		delete masterLoader;
	for (int c = 0; c < 2; ++c) {
		delete[] mixBuffer[c];
	}
}


/*! \brief Generates diverse tables used by some (old, Buzz only) machines */

void player::generateOscillatorTables() {
	int tabSize=2048;
	srand(static_cast<unsigned int>(time(0)));
	for (int tabLevel=0; tabLevel<11; tabLevel++) {
		int tabOfs=zzub::get_oscillator_table_offset(tabLevel);
		for (int i=0; i<tabSize; i++) {
			double dx=(double)i/tabSize;
			oscTables[zzub::oscillator_type_sine][tabOfs+i]=(short)(sin(dx*2.0f*PI)*32000);
			oscTables[zzub::oscillator_type_sawtooth][tabOfs+i]=(short)(sawtooth(dx*2.0f*PI)*32000);
			oscTables[zzub::oscillator_type_pulse][tabOfs+i]=(short)(square(dx*2.0f*PI)*32000);
			oscTables[zzub::oscillator_type_triangle][tabOfs+i]=(short)(triangle(dx*2.0f*PI)*32000);
			oscTables[zzub::oscillator_type_noise][tabOfs+i]=(short) (((float)rand()/(float)RAND_MAX)*64000.f - 32000);
			oscTables[zzub::oscillator_type_sawtooth_303][tabOfs+i]=(short)(sawtooth(dx*2.0f*PI)*32000);
			oscTables[6][tabOfs+i]=(short)(sin(dx*2.0f*PI)*32000);
		}
		tabSize/=2;
	}
}

/*! \brief Create a plugin library from a DLL */

void player::loadPluginLibrary(const std::string &fullpath) {
	int dpos=(int)fullpath.find_last_of('.');
	string fileExtension = fullpath.substr(dpos);
#if defined(_WIN32)
	transform(fileExtension.begin(), fileExtension.end(), fileExtension.begin(), toLower);
	if (fileExtension == ".dll") {	
#elif defined(POSIX)
	if (fileExtension == ".so") {
#endif
		pluginlib* lib=new pluginlib(fullpath,*this);
		// machine loaders will be registered by lib through registerMachineLoader,
		// now and during loading of songs
		pluginLibraries.push_back(lib);
	}
}

/*! \brief Register a plugin type with the players list of known plugins 

	Machine loaders will be registered by pluginlib instances
	upon initialization and during loading of songs.
*/

void player::registerMachineLoader(pluginloader *pl) {
	string pluginUri=pl->getUri();
	transform(pluginUri.begin(), pluginUri.end(), pluginUri.begin(), toLower);
	if (!isBlackListed(pluginUri)) {
		machines[pluginUri]=pl;
	}
}

/*! \brief Enumerate all files in the given folder and initialie all plugins. 

	\param folder Name of folder to scan, must end with a slash (or backslash for Win32).
*/
void player::initializeFolder(std::string folder) {
	using namespace std;

#if defined(_WIN32)

	string searchPath=folder + "*.dll";

	WIN32_FIND_DATA fd;
	HANDLE hFind=FindFirstFile(searchPath.c_str(), &fd);

	while (hFind!=INVALID_HANDLE_VALUE) {
		
		if ( (fd.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)==0) {
			string fullFilePath=folder + fd.cFileName;
			printf("enumerating %s\n", fullFilePath.c_str());
			char fullPath[1024];
			char* filePart;
			GetFullPathName(fullFilePath.c_str(), 1024, fullPath, &filePart);

			loadPluginLibrary(fullPath);
		}

		if (!FindNextFile(hFind, &fd)) break;
	}
	FindClose(hFind);

#elif defined(POSIX)
	struct dirent **namelist;
	struct stat statinfo;
	int n;
	
	string searchPath=folder;
	
    n = scandir(searchPath.c_str(), &namelist, 0, alphasort);
    if (n < 0)
        perror("scandir");
    else {
        while(n--) {
			string fullFilePath=folder + namelist[n]->d_name;
			printf("enumerating %s\n", fullFilePath.c_str());
			if (!stat(fullFilePath.c_str(), &statinfo))
			{
				if (!S_ISDIR(statinfo.st_mode))
				{
					loadPluginLibrary(fullFilePath);
				}
			}
            free(namelist[n]);
        }
        free(namelist);
    }

#endif

}

/*! \brief Add a folder name to scan for plugins upon initialization.

	\param folder Name of folder to scan, must end with a slash (or backslash for Win32).
*/
void player::addMachineFolder(std::string folder) {
	pluginFolders.push_back(folder);
}

/*! \brief Clear registered plugin libraries and free plugin DLLs. */
void player::clearMachineLoaders() {
    for (size_t i=0; i<pluginLibraries.size(); i++) {
        pluginlib* lib = pluginLibraries[i];
        delete lib;
    }
    machines.clear();
    pluginLibraries.clear();
}

/*! \brief Returns a plugin library by URI. */
pluginlib* player::getPluginlibByUri(const std::string &uri) {
    for (size_t i=0; i<pluginLibraries.size(); i++) {
		pluginlib *lib = pluginLibraries[i];
		if (lib->collection && lib->collection->get_uri() && (uri == lib->collection->get_uri())) {
			return lib;
		}
    }
	return 0;
}

/*! \brief Enumerates all plugin folders for plugin libraries. */
void player::loadMachineLoaders() {
	// add input collection
	pluginLibraries.push_back(new pluginlib("input",*this, &inputPluginCollection));
	// add output collection
	pluginLibraries.push_back(new pluginlib("output",*this, &outputPluginCollection));
	// add recorder collection
	recorderPluginCollection.setPlayer(this);
	pluginLibraries.push_back(new pluginlib("recorder",*this, &recorderPluginCollection));

	// initialize rest like usual
	for (size_t i=0; i<pluginFolders.size(); i++) {
		initializeFolder(pluginFolders[i]);
	}
}

/*! \brief Returns the current state of the player 
*/
player_state player::getPlayState() { 
	return playerState; 
}

/*! \brief Initializes internal player data.
	\param samplesPerSec Initial mixing rate, passed on to audio driver
	\return Returns false if player could not be initialized.

    initialize does the following:
		- initializes mixer
		- loads and indexes all dll's
		- generate built-in oscillator tables
		- initializes master and adds it to the stage
		- initializes a performance timer for CPU measurement
		- sets the player to stopped state
		- check if internal memory structures are aligned correctly

*/
bool player::initialize() {

	masterInfo.samples_per_second = workRate;

    masterLoader=new master_pluginloader();

    master=createMachine(0, 0, "Master", masterLoader);
	if (!master) return false;

    master->initialize(0, 0, 0, 0, 0);
    master->tickAsync();

	wavePlayer.initialize(this);

	loadMachineLoaders();

	player::generateOscillatorTables();

	timer.start();
	workPos=0;

    resetMachines();
	playerState=player_state_stopped;
	
//	driver.initialize(this);
//    midiDriver.initialize(this);
	
	return true;
}

/*! \brief Returns the number of known machines.
*/
int player::getMachineLoaders() {
	return machines.size();
}

/*! \brief Returns a machine loader by index.
*/
pluginloader* player::getMachineLoader(int index) {
	int j=0;
	for (map<string, pluginloader*>::iterator i=machines.begin(); i!=machines.end(); ++i) {
		if (index==j) return i->second;
		j++;
	}
	return 0;
}

/*! \brief Returns a machine loader by name. 
*/
pluginloader* player::getMachineLoader(std::string uri) {

    // master is hardcoded
    if (uri=="Master" || uri=="@zzub.org/master") return masterLoader;

	string keyName=uri;
	transform(keyName.begin(), keyName.end(), keyName.begin(), toLower);
	map<string, pluginloader*>::iterator i=machines.find(keyName);
	pluginloader* l=i==machines.end()?0:i->second;

	return l;
}

/*! \brief Lock the player. Restrict access on player resources to calling thread.

	This causes the player to halt all processing until unlock() is called.
	This method is used when you need to invoke non-thread safe methods on player 
	member objects, and return values from zzub::metaplugin and player methods.
*/
void player::lock() {
	playerLock.Lock();
}

/*! \brief Unlock the player.
*/
void player::unlock() {
	playerLock.Unlock();
}

/*! \brief Lock sequencer and pattern data. */
void player::lockTick() {
	playerTickLock.Lock();
}

/*!	\brief Unlock sequencer and pattern data. */
void player::unlockTick() {
	playerTickLock.Unlock();
}

/*! \brief Returns a machine loader by index. */
void player::resetMachines() {
	for (size_t i=0; i<getMachines(); i++) {
		zzub::metaplugin* machine=getMachine(i);
		if (!machine) continue;
		machine->resetMixer();
	}
}

/*!	\brief Tells the player to use another sequencer for playing.
	\param newseq If this is NULL, the player resumes playing from the built-in sequencer
	\return Returns the previous sequencer instance.
*/
sequencer* player::setCurrentlyPlayingSequencer(sequencer* newseq) {
	sequencer* prev=currentlyPlayingSequencer;
	lock();
	if (!newseq)
		newseq=&song_sequencer;

	currentlyPlayingSequencer=newseq;
	//resetMachines();	// maybe not necessary, since we playerLock anyway?
	unlock();
	return prev;
}

/*	\brief Set player state, used to start and stop playing. */

void player::setPlayerState(player_state state) {
	if (playerState==state) return;

	lock();
	resetMachines();
	playerState=state;
	unlock();

	switch (playerState) {
		case player_state_stopped:
			for (size_t i=0; i<getMachines(); i++) {
				zzub::metaplugin* stopMachine=getMachine(i);
				stopMachine->stop();	// (some?) effects seem to never start again (maybe because of softmuting which maybe should not be set?)
			}
			stopFlag = false;
			break;
	}
	
	// send event
	zzub_event_data eventData={event_type_player_state_changed};
	eventData.player_state_changed.player_state=(int)state;
	master->invokeEvent(eventData, false); // can also be fired if loop ends
}

/*	\brief Clears all data associated with current song from the player.
*/
void player::clear() {
	using namespace std;
	lock();
    setPlayerState(player_state_muted);
    recordParameters=false;
	unlock();

	song_sequencer.clear();

	waveTable.clear();

    midiInputMappings.clear();

	// delete all machines except master and nonsongplugins
	std::vector<zzub::metaplugin*> machinesCopy = machineInstances;
	for (int i = 0; i<machinesCopy.size(); i++) {
		zzub::metaplugin* plugin = machinesCopy[i];
		if (plugin->machineInfo->type == zzub::plugin_type_master) continue;
		if (plugin->nonSongPlugin) continue;
		deleteMachine(plugin);
	}

	master->clear();
	master->tick();

    setPlayerState(player_state_stopped);
	
	infoText = "";

}


/*	\brief Generates a new, unique name for a machine.
	\param The machine instance name you wish to generate a name for.
*/
std::string player::getNewMachineName(std::string machineUri) {
	using namespace std;
	
	pluginloader* loader=getMachineLoader(machineUri);
	string baseName;
	if (!loader) 
		baseName=machineUri; else
		baseName=loader->getInfo()->short_name;
	char pc[16];
	for (int i=0; i<9999; i++) {
		if (i==0) {
			strcpy(pc, baseName.substr(0,12).c_str());
		}  else
			sprintf(pc, "%s%i", baseName.substr(0,12).c_str(), i+1);
		zzub::metaplugin* m=getMachine(pc);
		if (!m) return pc;
	}
	return "_(error)"+baseName;
}

/*	\brief Sets or clears the solo machine.
	\param machine When machine is set to NULL, no machine is playing solo.
*/
void player::setSoloMachine(zzub::metaplugin* machine) {
	soloMachine=machine;
}

/*	\brief Returns current solo machine.
*/
zzub::metaplugin* player::getSoloMachine() {
	return soloMachine;
}

/*	\brief Returns the index of a machine.
*/
int player::getMachineIndex(zzub::metaplugin* machine) {
	for (int i=0; i<(int)machineInstances.size(); i++) {
		if (machine==getMachine(i)) {
			//machineLock.Unlock();
			return i;
		}
	}
	return -1;
}

/*	\brief Deletes a machine.

	Releases all connections, sequencer tracks, patterns and events associated with the machine.
*/
void player::deleteMachine(zzub::metaplugin* machine) {
	assert(machine!=master);

	lock();
	machineInstances.erase(machineInstances.begin()+getMachineIndex(machine));
    machine->initialized=false;
	unlock();

	for (size_t i=song_sequencer.getTracks(); i>0; i--) {
		if (song_sequencer.getTrack(i-1)->getMachine()==machine)
			song_sequencer.removeTrack(i-1);
	}

	
	machine->clear();

    // buzz has a gDeleteEvent declared in its machineinterface.h, but it is apparently never called
    // we tell out master
    zzub_event_data eventData={event_type_delete_plugin};
    eventData.delete_plugin.plugin=(zzub_plugin_t*)machine;
	master->invokeEvent(eventData, true);

    // flush pending events for this machine
    eventLock.Lock();
    for (deque<event_message>::iterator i = messageQueue.begin(); i!=messageQueue.end(); i++) {
        if (i->plugin == machine) {
            i = messageQueue.erase(i);
            --i;
        }
    }
    eventLock.Unlock();

	delete machine;
}

/*!	\brief Tests if the machine exists in the current song.

    Used internally to test for rogue pointers sent to CMICallbacks.
*/
bool player::machineExists(zzub::metaplugin* machine) {
	bool test=false;
	for (size_t i=0; i<machineInstances.size(); i++) {
		if (getMachine(i)==machine) {
			return true;
		}
	}

	return test;
}

/*!	\brief Returns number of machines in current song.
*/
size_t player::getMachines() { 
	size_t size=machineInstances.size(); 
	return size;
}

/*!	\brief Returns a machine by name.
*/
zzub::metaplugin* player::getMachine(std::string instanceName) {
	for (size_t i=0; i<machineInstances.size(); i++) {
		if (machineInstances[i]->getName()==instanceName) {
			zzub::metaplugin* m=(zzub::metaplugin*)machineInstances[i];
			return m;
		}
	}
	return 0;
}


/*!	\brief Returns a machine by index.
*/
zzub::metaplugin* player::getMachine(size_t index) {
	zzub::metaplugin* m=0;
	if (index>=0 && index<machineInstances.size()) 
		m=(zzub::metaplugin*)machineInstances[index];
	return m;
}


/*! \brief Returns information about the master.
*/
zzub::master_info* player::getMasterInfo() {
	return &masterInfo;
}

/*! \brief Returns currently playing position in the sequencer.
*/
int player::getSequencerPosition() {
	return song_sequencer.getPosition();
}

/*! \brief Sets the currently playing position in the sequencer.

If the player is playing, this changes the song position.
*/
void player::setSequencerPosition(int v) {
	song_sequencer.setPosition(v);
}

/*! \brief Sets the loop start point of a song.
*/
void player::setSongBeginLoop(int v) {
	song_sequencer.beginOfLoop=v;
}

/*! \brief Sets the loop end point of a song.
*/
void player::setSongEndLoop(int v) {
	song_sequencer.endOfLoop=v;
}

/*! \brief Sets the song start point of a song.
*/
void player::setSongBegin(int v) {
	song_sequencer.startOfSong=v;
}

/*! \brief Retreives the loop start point of a song.
*/
int player::getSongBeginLoop() {
	return song_sequencer.beginOfLoop;
}

/*! \brief Retreives the loop end point of a song.
*/
int player::getSongEndLoop() {
	return song_sequencer.endOfLoop;
}

/*! \brief Retreives the song start point of a song.
*/
int player::getSongBegin() {
	return song_sequencer.startOfSong;
}

/*! \brief Set song looping mode.

	If enabled, the player will stop when the song position reaches the end.
*/
void player::setLoopEnabled(bool enable) {
	song_sequencer.loop = enable;
}

/*! \brief Retreives song looping mode. */

bool player::getLoopEnabled() {
	return song_sequencer.loop;
}

/*! \brief Sets the song end point of a song. */

void player::setSongEnd(int v) {
	song_sequencer.endOfSong=v;
}

/*! \brief Retreives the song end point of a song. */

int player::getSongEnd() {
	return song_sequencer.endOfSong;
}

/*! \brief Returns the number of waves in the wavetable. Is usually 0xc8.
*/
size_t player::getWaves() {
	return waveTable.waves.size();
}

/*! \brief Returns the wave in the specified wavetable location.
*/
wave_info_ex* player::getWave(size_t index) {
	return &waveTable.waves[index];
}

/*! \brief Returns the index of a wave.
*/

int player::getWaveIndex(wave_info_ex* entry) {
	for (size_t i=0; i<getWaves(); i++) {
		if (getWave(i)==entry) return i;
	}
	return -1;
}


/*! \brief Returns the built-in wave player instance.
*/
wave_player* player::getWavePlayer() {
	return &wavePlayer;
}

/*! \brief Returns audio driver mixing rate.
*/
int player::samplesPerTick() {
	return masterInfo.samples_per_tick;
}

/*! \brief Returns a string of warnings that occured during last load.

	If there were no warnings, this string is blank.
*/
std::string player::getLoadWarnings() {
	return loadWarning;
}

/*! \brief Returns a string of errrors that occured during last load.

	If there were no errors, this string is blank.
*/
std::string player::getLoadErrors() {
	return loadError;
}

/*! \brief Returns a sequence by index */

sequence* player::getSequenceTrack(size_t i) {
	return song_sequencer.getTrack(i);
}

/*! \brief Returns the number of sequences */

size_t player::getSequenceTracks() {
	return song_sequencer.getTracks();
}

/*! \brief Create a dummy plugin.
*/
pluginloader* player::createDummyLoader(int type, std::string fullName, int attributeCount, int numGlobalParams, int numTrackParams, zzub::parameter* params) {
    return new dummy_loader(type, fullName, attributeCount, numGlobalParams, numTrackParams, params);
}

/*! \brief Create a plugin instance.
*/
metaplugin* player::createMachine(char* inputData, int inputSize, std::string machineName, pluginloader *loader) {
	metaplugin* machine=new metaplugin(this, loader);
	
	machine->setName(machineName);

	machineInstances.push_back(machine);

	if (!machine->create(inputData, inputSize)) {
        // couldnt create, so remove from internal collection and clean up
        machineInstances.erase(machineInstances.begin() + machineInstances.size()-1);
        delete machine;
        return 0;
    }

    // automatically add NO_OUTPUT-machines to the master
	if (machine->isNoOutput()) {
		getMaster()->addAudioInput((metaplugin*)machine, 0x4000, 0x4000);
	}

    return machine;
}

/*! \brief Test if a plugin name is blacklisted.
*/
bool player::isBlackListed(std::string name) {
	transform(name.begin(), name.end(), name.begin(), toLower);
	for (size_t i=0; i<blacklist.size(); i++) {
		string keyName=blacklist[i];
		transform(keyName.begin(), keyName.end(), keyName.begin(), toLower);
		if (keyName==name) return true;
	}
	return false;
}

/*! \brief Audio processing helper.
*/
void player::updateTick(int workSamples) {
	player_state state=getPlayState();

	if (masterInfo.tick_position==0 && (state!=player_state_released && state!=player_state_muted)) {
		if (stopFlag)
			setPlayerState(player_state_stopped);

		lockTick();
		lastTickPos=getWorkPosition();

		// the player machines process their own sequences

		for (size_t i=0; i<getMachines(); i++) {
			if (getMachine(i)->isNoOutput())
				getMachine(i)->tick();
		}
		for (size_t i=0; i<getMachines(); i++) {
			if (!getMachine(i)->isNoOutput())
				getMachine(i)->tick();
		}

		// this is for advancing the entire seqiuencer, each machine advances each track itself in tickmachine()
		if (state==player_state_playing && !currentlyPlayingSequencer->advanceTick())
			// signal we want to mix until the end of this tick before stopping
			stopFlag = true;

		unlockTick();

        workFracs+=masterInfo.samples_per_tick_frac;
	}

	mixSamples=masterInfo.samples_per_tick+floor(workFracs)-masterInfo.tick_position;	// mix only up to closest tick

	nextPosInTick=0;

    if (mixSamples>buffer_size) {
		mixSamples=buffer_size;
		if (mixSamples>(unsigned int)workSamples)
			mixSamples=workSamples;
		nextPosInTick=masterInfo.tick_position+mixSamples;	// remember where we are
	} else
	if (mixSamples>(unsigned int)workSamples) {
		mixSamples=workSamples;
		nextPosInTick=masterInfo.tick_position+mixSamples;	// remember where we are
    } else {
        double n;
        workFracs=modf(workFracs, &n);
	    nextPosInTick=0;
    }
}

/*! \brief Audio processing helper.
*/
void player::finishWork() {
	player_state state=getPlayState();

	metaplugin* masterInternal=(metaplugin*)master;
	if (state!=player_state_released)
		wavePlayer.work(masterInternal->machineBuffer, mixSamples, true);

	masterInfo.tick_position=nextPosInTick;
	workPos+=mixSamples;
}

/*! \brief Audio processing helper.
*/
bool player::workMachine(metaplugin* machine, int numSamples) {
	assert(machine->lastWorkPos!=workPos);

	size_t inputConnections=machine->inConnections.size();
	bool inputState=inputConnections?false:true;

	memset(machine->machineBuffer[0], 0, numSamples*sizeof(float));
	memset(machine->machineBuffer[1], 0, numSamples*sizeof(float));

	int maxInputAmp=0;
	for (size_t i=0; i<inputConnections; i++) {
		connection *cx = machine->inConnections[i];
		if (cx->connectionType == connection_type_audio) {
			audio_connection *cax = (audio_connection*)cx;
			maxInputAmp = std::max(maxInputAmp, (int)cax->values.amp);
		}

		// check for no_output: these have been processed anyway, 
		// and master->no_output would enter an infinite loop unless we continue
		if (cx->plugin_in->isNoOutput()) continue;

		if (cx->work(this, numSamples)) {
			inputState=true;
		}
	}

	// bestem flagg: 
	//	- hvis minst en av inn-maskinene var suksess s� blir det WM_READWRITE p� fx
	// TODO: m� sette WM_NOIO n�r maskinen ikke er koblet p� noen, men alle pathene til dette stedet kommer via connections, s� det er noe som mangler
	int flags;
	if (inputState) {
		// testing for doesInputMixing || !isBufferZero() fixes F:\audio\bmx\div\nool+ladproject - the longest travel.bmx
		// testing for maxInputAmp fixes F:\audio\bmx\orange.bmx
		if (inputConnections>0 && maxInputAmp>0 && (machine->doesInputMixing() || !isBufferZero(machine->machineBuffer, numSamples)))
//		if (inputConnections>0 && maxInputAmp>0)
			flags=zzub::process_mode_read_write; else
			flags=zzub::process_mode_write;
	} else {
		flags=zzub::process_mode_write;
	}

    // this if-test worked fine before the -1 - 1 transition, but now it cant be here anymore (clears the work buffer, but inside there is mode_write and ret=false all the way)
    // -> machineBuffer is all zeros, so this clears the mixBuffer, which is a good idea
    //if (((flags&zzub::process_mode_read)!=0) && !machine->doesInputMixing())
	memcpy(mixBuffer[0], machine->machineBuffer[0], numSamples*sizeof(float));
	memcpy(mixBuffer[1], machine->machineBuffer[1], numSamples*sizeof(float));

	bool ret=machine->work(mixBuffer, numSamples, flags);

	return ret;
}

/*! \brief This methods generates audio and fills he specified buffer with output.
*/
void player::workStereo(int numSamples) {
	using namespace std;
	lock();

	// update master samplerate
	if (workRate != masterInfo.samples_per_second) {
		masterInfo.samples_per_second = workRate;
		master->tickAsync();
	}

	SETABRPUN();
	double tempTime=timer.frame();
	int samplecount = numSamples;

    long bufpos = 0;
    while (numSamples > 0) {
		// init buffer pointers for all input and output channels
		for (int i = 0; i < workDevice->out_channels; i++) {
			outputBuffer[i] = &workOutputBuffer[i][bufpos];
			//memset(outputBuffer[i], 0, numSamples * sizeof(float));
		}
		for (int i = 0; i < workDevice->in_channels; i++) {
	        if (workInputDevice)
				inputBuffer[i] = &workInputBuffer[i][bufpos]; else
	            inputBuffer[i] = 0;
		}

	    updateTick(numSamples);

	    player_state state = getPlayState();

	    memset(master->machineBuffer[0], 0, MAXBUFFERSAMPLES*sizeof(float));
	    memset(master->machineBuffer[1], 0, MAXBUFFERSAMPLES*sizeof(float));

		if (state != player_state_muted && state != player_state_released) {
			for (unsigned i = 0; i < machineInstances.size(); i++) {
				if (machineInstances[i]->isNoOutput())
					workMachine(machineInstances[i], mixSamples);
			}
		    workMachine(master, mixSamples);
		}

	    finishWork();
		// support more than 2 output channels
		// this can be called from many context, eg a recorder in the ui thread
		// so - outputChannel may need to be adjusted depending on the situation
		assert(workChannel < workDevice->out_channels/2);
        memcpy(&workOutputBuffer[workChannel*2+0][bufpos], master->machineBuffer[0], mixSamples*sizeof(float));
        memcpy(&workOutputBuffer[workChannel*2+1][bufpos], master->machineBuffer[1], mixSamples*sizeof(float));
	    numSamples -= mixSamples;
        bufpos += mixSamples;
    }
	
	workTime=timer.frame()-tempTime;
	// how long we needed / how much we could have needed
	double load=(100.0 * workTime * double(masterInfo.samples_per_second)) / double(samplecount);
	// slowly approach to new value
	cpuLoad += 0.1 * (load - cpuLoad);
	//SETGRADUN(); // don't turn it off

	if (midiDriver)
		midiDriver->poll();

	unlock();

	if (editCommand) {
		zzub_edit* edit = (zzub_edit*)editCommand;
		edit->apply();
		editCommand = 0;
		edit->done.signal();
	}

}

/*! \brief Look up URI based on an alias */
std::string player::getBuzzUri(std::string name) {
    transform(name.begin(), name.end(), name.begin(), toLower);
    for (map<string, string>::iterator i=aliases.begin(); i!=aliases.end(); ++i) {
        string alias=i->first;
        transform(alias.begin(), alias.end(), alias.begin(), toLower);
        if (alias==name) return i->second;
    }
    return "";
}

/*! \brief Look up alias based on a URI */
std::string player::getBuzzName(std::string uri) {
    transform(uri.begin(), uri.end(), uri.begin(), toLower);
    for (map<string, string>::iterator i=aliases.begin(); i!=aliases.end(); ++i) {
        string id=i->second;
        transform(id.begin(), id.end(), id.begin(), toLower);
        if (id==uri) return i->first;
    }
    return "";
}

/*! \brief MIDI callback */

void player::midiEvent(unsigned short status, unsigned char data1, unsigned char data2) {
    // look up mapping(s) and send value to plugin
    int channel=status&0xF;
    for (size_t i=0; i<midiInputMappings.size(); i++) {
        midimapping& mm=midiInputMappings[i];
        if (mm.channel==channel && mm.controller==data1) {
            metaplugin* plugin=mm.machine;
            const parameter* param=plugin->getMachineParameter(mm.group, mm.track, mm.column);
            int minValue=param->value_min;
		    int maxValue=param->value_max;
            float delta=(float)((maxValue-minValue)) / 127.0f;

            plugin->setParameter(mm.group, mm.track, mm.column, minValue + (float)data2 * delta, true);
		    //plugin->machine->process_events();
        }
    }
	
	// also send note events to plugins directly
	int command = (status & 0xf0) >> 4;
	if ((command == 8) || (command == 9)) {
		int velocity = (int)data2;
		if (command == 8)
			velocity = 0;
		for (size_t i=0; i<machineInstances.size(); i++) {
			zzub::metaplugin* m=(zzub::metaplugin*)machineInstances[i];
			if (m->machine)
				m->machine->midi_note(channel, (int)data1, velocity);
		}
	}
	else if (command == 0xb) {
		for (size_t i=0; i<machineInstances.size(); i++) {
			zzub::metaplugin* m=(zzub::metaplugin*)machineInstances[i];
			if (m->machine)
				m->machine->midi_control_change((int)data1, channel, (int)data2);
		}
	}

    // plus all midi messages should be sent as master-events, so ui's can pick these up
    zzub_event_data eventData={event_type_midi_control};
    eventData.midi_message.status=status;
    eventData.midi_message.data1=data1;
    eventData.midi_message.data2=data2;

    master->invokeEvent(eventData);
}

/*! \brief Define a MIDI mapping */

midimapping* player::addMidiMapping(metaplugin* plugin, size_t group, size_t track, size_t param, size_t channel, size_t controller) {
    midimapping mm={plugin, group, track, param, channel, controller };
    midiInputMappings.push_back(mm);
    return &midiInputMappings.back();
}

/*! \brief Remove a MIDI mapping */

bool player::removeMidiMapping(metaplugin* plugin, size_t group, size_t track, size_t param) {
    for (size_t i=0; i<midiInputMappings.size(); i++) {
        midimapping& mm=midiInputMappings[i];
        if (mm.machine==plugin && mm.group==group && mm.track==track && mm.column==param) {
            midiInputMappings.erase(midiInputMappings.begin()+i);
            i--;
        }
    }
    return false;
}

/*! \brief Retreive a MIDI mapping in current song */

midimapping* player::getMidiMapping(size_t index) {
    return &midiInputMappings[index];
}

/*! \brief Retreive number of MIDI mappings in current song */

size_t player::getMidiMappings() {
    return midiInputMappings.size();
}

/*! \brief Process GUI messages. 

Whenever the player invokes an event that may reach the GUI, it is
queued until the host invokes handleMessages() on its thread.

*/
void player::handleMessages() {
	while (true) {
		eventLock.Lock();
		size_t messages = messageQueue.size();
		eventLock.Unlock();

 		if (messages == 0) break;

		eventLock.Lock();
        event_message& message=messageQueue.front();
		eventLock.Unlock();

		message.event->invoke(message.data);

		eventLock.Lock();
        messageQueue.pop_front();
        eventLock.Unlock();
    }
}

/*! \brief Retreive master information.
*/
float player::getBeatsPerMinute() {
	return float(master->getParameter(1, 0, 1));
}

/*! \brief Retreive master information.
*/
int player::getTicksPerBeat() {
	return master->getParameter(1, 0, 2);
}

/*! \brief Set master information.
*/
void player::setBeatsPerMinute(float bpm) {
	master->setParameter(1, 0, 1, (int)(bpm+0.5), false);
}

/*! \brief Set master information.
*/
void player::setTicksPerBeat(int tpb) {
	master->setParameter(1, 0, 2, tpb, false);
}

void player::executeThreadCommand(zzub_edit* edit) {
	if (workStarted) {
		// there is a workDevice, the player thread runs and we must wait
		editCommand = edit;
		edit->done.wait();
	} else {
		// no worker, execute in current thread
		edit->apply();
	}
}

plugin* player::createStream(std::string streamPluginUri, std::string streamDataUrl) {
	pluginloader* loader = getMachineLoader(streamPluginUri);
	if (!loader) return 0;
	plugin* plugin = loader->createMachine();
	archive* a = new mem_archive();
	outstream* outs = a->get_outstream("");
	outs->write(streamDataUrl.c_str());
	// without a host, the plugin wont give any sample data =)
	plugin->_host = master->machine->_host;
	plugin->_master_info = &masterInfo;
	plugin->init(a);
	int* streamvals = (int*)plugin->global_values;
	streamvals[0] = 0xFFFFFFFF;
	streamvals[1] = 0xFFFFFFFF;

	return plugin;
}

/***

	zzub_edit_connection

***/

void zzub_edit_connection::apply() {
	conn->plugin_out->inConnections.swap(input_connections);
	conn->plugin_in->outConnections.swap(output_connections);

	for (size_t i = 0; i < pattern_connection_tracks.size(); i++) {
		conn->plugin_out->patterns[i]->_connections.swap(pattern_connection_tracks[i]);
		for (unsigned j = 0; j < conn->plugin_out->patterns[i]->_connections.size(); j++) {
			conn->plugin_out->patterns[i]->_connections[j]->setTrack(j);
		}
	}

	conn->plugin_out->connectionStates.swap(parameter_states);

	for (unsigned i = 0; i < conn->plugin_out->connectionStates.size(); i++) {
		conn->plugin_out->connectionStates[i]->getStateTrack()->setTrack(i);
		conn->plugin_out->connectionStates[i]->getStateTrackControl()->setTrack(i);
		conn->plugin_out->connectionStates[i]->getStateTrackCopy()->setTrack(i);
	}

	if (type == zzub_edit_add_input) {
		conn->plugin_out->machine->add_input(conn->plugin_in->getName().c_str());
	} else
	if (type == zzub_edit_delete_input) {
		conn->plugin_out->machine->delete_input(conn->plugin_in->getName().c_str());
	}
}


/***

	zzub_edit_pattern

***/

void zzub_edit_pattern::apply() {
	plugin->patterns.swap(patterns);

	if (sequence_events.size() == 0) return ;

	zzub::player* player = plugin->getPlayer();
	unsigned track_index = 0;
	for (size_t i = 0; i<player->getSequenceTracks(); i++) {
		sequence* track = player->getSequenceTrack(i);
		if (track->getMachine() == plugin) {
			track->events.swap(sequence_events[track_index]);
			track_index++;

			if (type == zzub_edit_delete_pattern && pattern == track->pattern) {
				// if this track is currently playing the pattern we delete, clear it
				track->pattern = 0;
			}
		}
	}

}

/***

	zzub_edit_tracks

***/

void zzub_edit_tracks::apply() {
	if (plugin->machine) plugin->machine->set_track_count(num_tracks);
	plugin->tracks = num_tracks;
	plugin->trackStates.swap(parameter_states);
    
	for (size_t i=0; i<plugin->patterns.size(); i++) {
		plugin->patterns[i]->_tracks.swap(pattern_tracks[i]);
	}

}


/***

	zzub_edit_sequence

***/


void zzub_edit_sequence::apply() {
	sequencer->tracks.swap(sequences);
}


} // namespace zzub



