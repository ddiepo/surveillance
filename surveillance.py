import os
import re
import subprocess
import shutil
import datetime
import time
import traceback

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
video_unprocessed_dir=video_store_path + "/unprocessed"
video_motion_dir="/motion"
video_all_dir="/all"
segment_length = 300 # seconds
event_gap = 15  # time before or after motion
motion_pid = None
date_time_format = "%Y%m%d-%H%M%S%Z"

class CameraItems:
    """ Data structure for storing information about a single camera """
    def __init__(self, camera_index):
        print "running init"
        self.camera_name = cameras[camera_index][0]
        self.capture_url = cameras[camera_index][1]
        self.capture_path = video_unprocessed_dir + '/' + self.camera_name
        self.capture_process = None
        self.save_prefix = "save-"
        self.motion_index = camera_index + 1
        self.monitor_url = cameras[camera_index][2]
        self.pipe = working_area + "motion_pipe_cam" + str(self.motion_index)
        self.motion_start_time = None
        
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
        
        self.process_segments()
        shutil.rmtree(self.capture_path, True)
    
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
                "-rtsp_transport", "tcp",
                "-stimeout", "500000",  # TCP Timeout for the stream
                "-i", self.capture_url,
                "-c", "copy",
                "-f", "segment",
                "-segment_time", str(segment_length),
                "-segment_format", "mp4",
                "-reset_timestamps", "1",
                "-strftime", "1",
                self.capture_path + "/" + self.camera_name + "." + date_time_format + ".mp4"]
        self.capture_process = subprocess.Popen(_cmd, stdout=FNULL, stderr=subprocess.STDOUT)
        print "ffmpeg capturing ", self.capture_url, " pid: ", self.capture_process.pid
        
    
    def mark_capture_start(self):
        self.motion_start_time = datetime.datetime.now()
        
    def process_segments(self):
        now = datetime.datetime.now()
        print "Processing segments for: " + self.camera_name
        file_list = os.listdir(self.capture_path)
        newest_file = None
        newest_start_time = None
        for _file in file_list:
            pieces = _file.split('.')
            if len(pieces) < 2 or pieces[len(pieces)-1] != "mp4":
                print "Unexpected pieces count: " + str(pieces)
                continue
            try:
                segment_start_time = datetime.datetime.strptime(pieces[len(pieces)-2], date_time_format)
                if newest_start_time == None or segment_start_time > newest_start_time:
                    newest_start_time = segment_start_time
                    newest_file = _file
                date_stamp = segment_start_time.strftime('%Y.%m.%d')
                motion_file_destination = video_store_path + "/" + date_stamp + "/" + video_motion_dir + "/" + _file
                if self.motion_start_time != None \
                   and (segment_start_time - datetime.timedelta(seconds=event_gap)) > self.motion_start_time \
                   and (segment_start_time + datetime.timedelta(seconds=segment_length)) < now \
                   and not os.path.exists(motion_file_destination):
                    
                    os_help.ignore_exist(os.makedirs, os.path.dirname(motion_file_destination))
                    os_help.ignore_exist(os.link(self.capture_path + "/" + _file, motion_file_destination))
            except:
                traceback.print_exc()
            
        if newest_file == None:
            print "No newest file?  Odd, but okay... bailing out"
            return
        
        for _file in file_list:
            try:
                pieces = _file.split('.')
                segment_start_time = datetime.datetime.strptime(pieces[len(pieces)-2], date_time_format)
                date_stamp = segment_start_time.strftime('%Y.%m.%d')
                destination = video_store_path + "/" + date_stamp + "/" + video_all_dir + "/" + _file
                os_help.ignore_exist(os.makedirs, os.path.dirname(destination))
                os_help.ignore_exist(os.link(self.capture_path + "/" + _file, destination))
                
                if (_file != newest_file):
                    os.unlink(self.capture_path + "/" + _file)
                else:
                    print "Keeping the file currently being written to: " + _file
            except:
                traceback.print_exc()
                print "Exception happened"
            
    def restart_process_if_died(self):
        print "TODO verify capture_pid is still running" # TODO
        
    def mark_capture_stop(self):
        process_segments()
        this.motion_start_time = None

def write_base_motion_config_file():
    os_help.ignore_exist(os.makedirs, motion_config_path)
    motion_conf_file = open(motion_config_path + 'motion.cfg', 'w')
    motion_conf_file.write("rtsp_uses_tcp on\n")
    # Don't capture anything with motion
    motion_conf_file.write("output_pictures off\n")
    motion_conf_file.write("on_event_start /home/pi/flagStart.bash %t\n")
    motion_conf_file.write("on_event_end /home/pi/flagEnd.bash %t\n")
    motion_conf_file.write("event_gap " + str(event_gap) + "\n")
    motion_conf_file.write("log_level 4\n")
    motion_conf_file.write("\n")

def on_change(message, pipe):
    is_on = (message == "on")
    for camera in camera_item:
        if camera.pipe == pipe and (camera.motion_start_time != None) != is_on:
            print "pipe called for camera: " + camera.camera_name + " msg: " + message
            if is_on:
                camera.mark_capture_start()
            else:
                camera.mark_capture_stop()

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

def start_motion_detection():
    FNULL = open(os.devnull, 'w')
    _cmd = ["motion", 
            "-c", motion_config_path + "/motion.cfg"]
#    motion_pid = subprocess.Popen(_cmd, stdout=FNULL, stderr=subprocess.STDOUT)

try:
    shutil.rmtree(working_area, True);
    os_help.ignore_exist(os.makedirs, working_area)
    initialize_cameras()
    my_input = pipe_watcher.PipesWatcher(get_pipes())
    start_motion_detection()

    start_time = datetime.datetime.now()
    while True:
        my_input.check(on_change)
        now = datetime.datetime.now()
        if (now - start_time) > datetime.timedelta(seconds=segment_length):
            start_time = now
            
            for camera in camera_item:
                camera.process_segments()
                camera.restart_process_if_died()
            
        else:
            time.sleep(1)

finally:
    print "Shutting down..."
    for camera in camera_item:
        camera.cleanup()
    
    shutil.rmtree(video_unprocessed_dir, True);
    
