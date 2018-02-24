import os
import re
import subprocess
import shutil
import time

import os_help
import pipe_watcher

#------------------------------------------------------------------------------
# User Defined Variables:
#------------------------------------------------------------------------------

# Temporary area for us to create config files on-the-fly, etc.
ramdisk="/dev/shm/"

# Where we will store the captured videos
video_store_path = "/tmp/video_storage"

# Location where mask files are for the various cameras.
# Mask file should use the format: " <camera name>.pgm"
# see https://motion-project.github.io/motion_config.html#mask_file
motion_mask_path = "~/motion_masks"

# List of camera tuples, of (record stream, motion stream)
cameras = [ ("back",
             "rtsp://view:3units3814@192.168.0.31:554/Streaming/Channels/1/", 
             "rtsp://view:3units3814@192.168.0.31:554/Streaming/Channels/2/"),
             ("front1",
              "rtsp://view:3units3814@192.168.0.32:554/Streaming/Channels/1/",
              "rtsp://view:3units3814@192.168.0.32:554/Streaming/Channels/2/") ]

#------------------------------------------------------------------------------
# End User Defined Variables ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#------------------------------------------------------------------------------

# Global variable to store all our camera stuff
camera_item = []
working_area=ramdisk + "surveillance/"
motion_config_path=working_area + "motion_config/"
unprocessed_videos=video_store_path + "/unprocessed"

class CameraItems:
    """ Data structure for storing information about a single camera """
    def __init__(self, camera_index):
        print "running init"
        self.camera_name = cameras[camera_index][0]
        self.capture_prefix = "cam" + str(camera_index)
        self.capture_url = cameras[camera_index][1]
        self.capture_path = unprocessed_videos + '/' + self.camera_name
        self.capture_process = None
        self.save_prefix = "save-"
        self.monitor_url = cameras[camera_index][2]
        self.pipe = working_area + "motion_pipe_cam" + str(camera_index + 1)
        self.motion_is_active = False
        self.motion_start_num = None
        
        os_help.ignore_exist(os.makedirs, self.capture_path)
        self.write_motion_config()
        self.start_capture()
        
    def cleanup(self):       
        try:
            self.capture_process.terminate()
        except:
            pass
        
        # Clean up the camera config (probably don't need this because the whole working area will be blown away
        os_help.ignore_exist(os.unlink, motion_config_path + self.camera_name + '.cfg')
        
        # TODO link the videos for motion or not first!
        shutil.rmtree(self.capture_path, True);
    
    def write_motion_config(self):
        thread_conf_file = open(motion_config_path + self.camera_name + '.cfg', 'w')
        thread_conf_file.write("netcam_url " + self.monitor_url + '\n')
        maskFile = motion_mask_path + '/' + self.camera_name + '.pgm'
        if os.path.isfile(maskFile):
            thread_conf_file.write("mask_file " + maskFile + '\n')
        
        motion_conf_file = open(motion_config_path + 'motion.cfg', 'a')
        motion_conf_file.write("thread " + thread_conf_file.name + '\n')
        print "created motion config file: " + thread_conf_file.name
        
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
        # TODO this function needs to be revisited!
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
        # TODO this function needs to be revisited!
        latest = self.get_latest_capture_number()
        if (latest == NONE):
            return
        open(self.save_prefix + str(latest), 'a').close()
        if (latest > 1):
            open(self.save_prefix + str(latest - 1), 'a').close()
            
    def get_capture_start_number(self):
        # TODO this function needs to be revisited!
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
        # TODO this function needs to be revisited!
        latest = self.get_latest_capture_number()
        start = get_capture_start_number()
        if (latest == NONE or start == NONE):
            return
        for x in range(start + 1, latest + 1):
            open(self.save_prefix + str(x), 'a').close()

def write_base_motion_config_file():
    os_help.ignore_exist(os.makedirs, motion_config_path)
    motion_conf_file = open(motion_config_path + 'motion.cfg', 'w')
    motion_conf_file.write("rtsp_uses_tcp on\n")
    # Don't capture anything with motion
    motion_conf_file.write("output_pictures off\n")
    motion_conf_file.write("on_event_start /home/pi/flagStart.bash %t\n")
    motion_conf_file.write("on_event_end /home/pi/flagEnd.bash %t\n")
    motion_conf_file.write("event_gap 15\n")
    motion_conf_file.write("log_level 4\n")
    motion_conf_file.write("\n")

def on_change(message, pipe):
    is_on = (message == "on")
    state_change = True;
    for camera in camera_item:
        if camera.pipe == pipe:
            camera.motion_is_active = is_on
            print "pipe called for camera: " + camera.camera_name + " msg: " + message
        elif camera.motion_is_active:
            state_change = False
            break
    
#    if state_change:
#        for camera in camera_item:
#            if is_on:
#                camera.mark_capture_start()
#            else:
#                camera.mark_capture_stop()
        
def save_marked_files():
    print "Saving marked files"

def initialize_cameras():
    write_base_motion_config_file()
    for index, camera in enumerate(cameras):
        _cam = CameraItems(index)
        camera_item.append(_cam)

def get_pipes():
    _pipes = []
    for camera in camera_item:
        _pipes.append(camera.pipe)
    return _pipes

try:
    shutil.rmtree(working_area, True);
    os_help.ignore_exist(os.makedirs, working_area)
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
    
    shutil.rmtree(unprocessed_videos, True);
    
