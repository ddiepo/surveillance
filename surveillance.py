import os
import re
import subprocess
import shutil
import time

import os_help
import pipe_watcher

ramdisk="/dev/shm/"

# List of camera tuples, of (record stream, motion stream)
cameras = [ ("rtsp://192.168.0.31:554/Streaming/Channels/1/", "rtsp://192.168.0.31:554/Streaming/Channels/2/") ]
motion_fps = 1

# Global variable to store all our camera stuff
camera_item = []
video_path=ramdisk + "/video/"
motion_is_active = False

class CameraItems:
    """ Data structure for storing information about a single camera """
    def __init__(self, camera_index):
        print "running init"
        self.capture_prefix = "cam" + str(camera_index)
        self.capture_url = cameras[camera_index][0]
        self.capture_path = video_path + str(camera_index)
        self.capture_process = None
        self.save_prefix = "save-"
        self.monitor_url = cameras[camera_index][1]
        self.monitor_jpg = ramdisk + "cam" + str(camera_index) + ".jpg"
        self.pipe = ramdisk + "cam_motion_" + str(camera_index)
        self.motion_process = None
        self.motion_is_active = False
        self.motion_start_num = None
        
        os_help.ignore_exist(os.mkdir, self.capture_path)
        self.start_monitor()
        self.start_capture()
        
    def cleanup(self):
        # Stop ffmpeg monitor
        try:
            self.motion_process.terminate()
        except:
            pass
        
        try:
            self.capture_process.terminate()
        except:
            pass
        
        # Clean up the jpg's from ffmpeg
        os_help.ignore_exist(os.unlink, self.monitor_jpg)
        
        # Clean up captures, ignore errors
        shutil.rmtree(self.capture_path, True);
    
    def start_monitor(self):
        FNULL = open(os.devnull, 'w')
        _cmd = ["ffmpeg", 
                "-y", 
                "-i", self.monitor_url,
                "-r", str(motion_fps),
                "-updatefirst", "1",
                self.monitor_jpg]
        self.motion_process = subprocess.Popen(_cmd, stdout=FNULL, stderr=subprocess.STDOUT)
        print "ffmpeg monitoring ", self.monitor_url, " pid: ", self.motion_process.pid
        
    def start_capture(self):
        FNULL = open(os.devnull, 'w')
        _cmd = ["ffmpeg", 
                "-i", self.capture_url,
                "-c", "copy",
                "-f", "segment",
                "-segment_time", "300",
                "-segment_format", "mp4",
                self.capture_path + "/" + self.capture_prefix + "-%05d.mp4"]
        self.capture_process = subprocess.Popen(_cmd, stdout=FNULL, stderr=subprocess.STDOUT)
        print "ffmpeg capturing ", self.capture_url, " pid: ", self.capture_process.pid
        
    def get_latest_capture_number(self):
        _files = os.listdir(self.capture_path)
        _largest = NONE
        for _file in _files:
            if (os.path.isfile(_file)):
                _s = re.split('\.|_', _file)
                if (_s[0] == self.capture_prefix):
                    try:
                        _val = int(_s[1])
                        if (_val > _largest):
                            _largest = val
                    except:
                        pass
        return _largest
    
    def mark_capture_start(self):
        latest = self.get_latest_capture_number()
        if (latest == NONE):
            return
        open(self.save_prefix + str(latest), 'a').close()
        if (latest > 1):
            open(self.save_prefix + str(latest - 1), 'a').close()
            
    def get_capture_start_number(self):
        _smallest = NONE
        for _file in os.listdir(self.capture_path):
            _s = _file.split("-")
            if (_s[0] == self.save_prefix):
                try:
                    _val = int(_s[1])
                    if _val < _smallest:
                        _smallest = _val
                except:
                    pass
        return _smallest
        
    def mark_capture_stop(self):
        latest = self.get_latest_capture_number()
        start = get_capture_start_number()
        if (latest == NONE or start == NONE):
            return
        for x in range(start + 1, latest + 1):
            open(self.save_prefix + str(x), 'a').close()

def on_change(message, pipe):
    is_on = (message == "on")
    state_change = True;
    for camera in camera_item:
        if camera.pipe == pipe:
            camera.motion_is_active = is_on;
        elif camera.motion_is_active:
            state_change = False;
            break;
    
    if state_change:
        for camera in camera_item:
            if is_on:
                camera.mark_capture_start()
            else:
                camera.mark_capture_stop()
        
def save_marked_files():
    print "Saving marked files"

def initialize_cameras():
    os_help.ignore_exist(os.mkdir, video_path)
    for index, camera in enumerate(cameras):
        _cam = CameraItems(index)
        camera_item.append(_cam)

def get_pipes():
    _pipes = []
    for camera in camera_item:
        _pipes.append(camera.pipe)
    return _pipes

try:
    initialize_cameras()
    my_input = pipe_watcher.PipesWatcher(get_pipes())

    start_time = time.time()
    while True:
        my_input.check(on_change)
        now = time.time()
        if (now - start_time > 120):
            start_time = now
            save_marked_files()
        else:
            time.sleep(1)

finally:
    for camera in camera_item:
        camera.cleanup()
        
    shutil.rmtree(video_path, True);
    
