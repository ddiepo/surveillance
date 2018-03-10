import datetime
import os
import signal
import shutil
import subprocess
import sys
import syslog
import time
import traceback

import os_help
import pipe_watcher
import disk_usage
import surveillance_config as config

_debug=False

# Global variable to store all our camera stuff
camera_item = []
motion_pid = None

class CameraItems:
    """ Data structure for storing information about a single camera """
    def __init__(self, camera_index):
        self.camera_name = config.cameras[camera_index].name
        self.capture_url = config.cameras[camera_index].record_url
        self.capture_path = os.path.join(
            config.video_unprocessed_path, self.camera_name)
        self.capture_process = None
        self.save_prefix = "save-"
        self.motion_index = camera_index + 1
        self.monitor_url = config.cameras[camera_index].monitor_url
        self.pipe = os.path.join(
            config.working_area, "motion_pipe_cam" + str(self.motion_index))
        self.motion_start_time = None
        
        os_help.ignore_exist(os.makedirs, self.capture_path)
        self.write_motion_config()
        self.start_capture()
        
    def cleanup(self):       
        try:
            self.capture_process.terminate()
        except:
            pass
        
        self.process_segments()
    
    def write_motion_config(self):
        thread_conf_file = open(os.path.join(
            config.motion_config_path, self.camera_name + '.cfg'), 'w')
        thread_conf_file.write("log_level 4\n")
        thread_conf_file.write("netcam_url " + self.monitor_url + '\n')
        thread_conf_file.write("camera_id " + str(self.motion_index) + "\n")
        thread_conf_file.write("on_event_start echo on > " + self.pipe + "\n")
        thread_conf_file.write("on_event_end echo off %t " + self.camera_name 
                               + " > " + self.pipe + "\n")
        maskFile = config.motion_mask_path + '/' + self.camera_name + '.pgm'
        if os.path.isfile(maskFile):
            thread_conf_file.write("mask_file " + maskFile + '\n')
            
        motion_conf_file = open(os.path.join(
            config.motion_config_path, 'motion.cfg'), 'a')
        motion_conf_file.write("camera " + thread_conf_file.name + '\n')

    def start_capture(self):
        FNULL = open(os.devnull, 'w')
        _cmd = ["ffmpeg", 
                "-rtsp_transport", "tcp",
                "-stimeout", "2000000",  # TCP Timeout for the stream
                "-i", self.capture_url,
                "-c", "copy",
                "-f", "segment",
                "-segment_time", str(
                    config.segment_length.seconds),
                "-segment_format", "mp4",
                "-reset_timestamps", "1",
                "-strftime", "1",
                (self.capture_path + "/" + self.camera_name + "." 
                 + config.date_time_format + ".mp4")]
        self.capture_process = subprocess.Popen(_cmd, stdout=FNULL, 
                                                stderr=subprocess.STDOUT)
        syslog.syslog(2, "Capture started for: " + self.camera_name 
                      + " cmd: " + str(_cmd) 
                      + " pid: " + str(self.capture_process.pid))
            
    def mark_capture_start(self):
        self.motion_start_time = datetime.datetime.now()
        
    def process_segments(self):
        """ Mark video segments as having motion or not. 
            All segments are linked to the "all" subdir,
            segments with motion are also linked to the "motion" subdir.
            Segments are removed from the "unprocessed" dir except if that
            segment is still the currently-being-written-to segment. It would 
            be safe to unlink that segment, but we leave it to make it easy 
            to find that file.
        """
        now = datetime.datetime.now()
        file_list = os.listdir(self.capture_path)
        newest_file = None
        newest_start_time = None
        for _file in file_list:
            pieces = _file.split('.')
            if len(pieces) < 2 or pieces[len(pieces)-1] != "mp4":
                print "Unexpected pieces count: " + str(pieces)
                continue
            try:
                segment_start_time = datetime.datetime.strptime(
                    pieces[len(pieces)-2], 
                    config.date_time_format)
                if (newest_start_time == None 
                    or segment_start_time > newest_start_time):
                    newest_start_time = segment_start_time
                    newest_file = _file
                    
                date_stamp = segment_start_time.strftime(
                    config.directory_date_format)
                motion_file = os.path.join(
                    config.video_store_path, date_stamp, 
                    config.video_motion_dir, _file)
                
                if (self.motion_start_time != None and 
                    (self.motion_start_time - config.event_gap <
                     segment_start_time) and
                    segment_start_time < now and
                    not os.path.exists(motion_file)):
                    
                    os_help.ignore_exist(
                        os.makedirs, os.path.dirname(motion_file))
                    os_help.ignore_exist2(
                        os.link, 
                        os.path.join(self.capture_path, _file), 
                        motion_file)
                    
            except:
                syslog.syslog(1, traceback.format_exc())
                traceback.print_exc()
            
        if newest_file == None:
            print "No newest file for: " + self.camera_name
            return
        
        for _file in file_list:
            try:
                pieces = _file.split('.')
                segment_start_time = (
                    datetime.datetime.strptime(
                        pieces[len(pieces)-2], config.date_time_format))
                date_stamp = (
                    segment_start_time.strftime(config.directory_date_format))
                destination = (
                    config.video_store_path + "/" + date_stamp + "/" 
                    + config.video_all_dir + "/" + _file)
                os_help.ignore_exist(
                    os.makedirs, os.path.dirname(destination))
                os_help.ignore_exist2(
                    os.link, self.capture_path + "/" + _file, destination)
                
                if (_file != newest_file):
                    os.unlink(self.capture_path + "/" + _file)
        
            except:
                syslog.syslog(1, traceback.format_exc())
                traceback.print_exc()
            
    def restart_process_if_died(self):
        if self.capture_process.poll() != None:  
            syslog.syslog(1, "ffmpeg capture process died, restarting: " 
                          + self.camera_name)
            self.start_capture()
        
    def mark_capture_stop(self):
        self.process_segments()
        self.motion_start_time = None

def write_base_motion_config_file():
    motion_conf_file = open(os.path.join(
        config.motion_config_path, 'motion.cfg'), 'w')
    motion_conf_file.write("log_level 4\n")
    motion_conf_file.write("rtsp_uses_tcp on\n")
    # Don't capture anything with motion
    motion_conf_file.write("output_pictures off\n")
    motion_conf_file.write("event_gap " 
                           + str(config.event_gap.seconds) + "\n")
    motion_conf_file.write("\n")

def on_change(message, pipe):
    is_on = (message == "on")
    for camera in camera_item:
        if (camera.pipe == pipe and 
            (camera.motion_start_time != None) != is_on):
            if is_on:
                camera.mark_capture_start()
            else:
                camera.mark_capture_stop()

def initialize_cameras():
    write_base_motion_config_file()
    for index, camera in enumerate(config.cameras):
        _cam = CameraItems(index)
        camera_item.append(_cam)

def get_pipes():
    _pipes = []
    for camera in camera_item:
        _pipes.append(camera.pipe)
    return _pipes

def start_motion_detection():
    global motion_pid
    FNULL = open(os.devnull, 'w')
    _cmd = ["motion", 
            "-c", os.path.join(config.motion_config_path, "motion.cfg")]
    motion_pid = subprocess.Popen(_cmd, stdout=FNULL, stderr=subprocess.STDOUT)
    syslog.syslog(2, "Starting motion detection: " + str(_cmd) 
                  + " pid: " + str(motion_pid.pid))
    
def sighandler(signum, frame):
    sys.exit("caught signal: " + str(signum));

try:
    config.init()
    signal.signal(signal.SIGTERM, sighandler)
    shutil.rmtree(config.working_area, True)
    shutil.rmtree(config.motion_config_path, True)
    shutil.rmtree(config.video_unprocessed_path, True)
    os_help.ignore_exist(os.makedirs, config.motion_config_path)
    initialize_cameras()
    my_input = pipe_watcher.PipesWatcher(get_pipes())
    start_motion_detection()

    start_time = datetime.datetime.now()
    space_check_time = start_time - config.space_check_rate
    while True:
        my_input.check(on_change)
        now = datetime.datetime.now()
        if (now - space_check_time) > config.space_check_rate:
            space_check_time = now;
            disk_usage.cleanup()
        
        if (now - start_time) > config.periodic_process_rate:
            start_time = now
            
            for camera in camera_item:
                camera.process_segments()
                camera.restart_process_if_died()
            
            if motion_pid.poll() != None:
                syslog.syslog(1, "motion process died, restarting.")
                start_motion_detection()

        else:
            time.sleep(1)
            
except:
    traceback.print_exc()
    syslog.syslog(1, traceback.format_exc())

finally:
    print "Shutting down..."
    if motion_pid != None and motion_pid.poll() == None: 
        motion_pid.kill()
    
    for camera in camera_item:
        camera.cleanup()
    
    if not _debug:
        shutil.rmtree(config.motion_config_path, True);
        shutil.rmtree(config.video_unprocessed_path, True);
