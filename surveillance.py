import os, pipe_watcher, time, subprocess

ramdisk="/dev/shm/"

# List of camera tuples, of (record stream, motion stream)
cameras = [ ("rtsp://192.168.0.31:554/Streaming/Channels/1/", "rtsp://192.168.0.31:554/Streaming/Channels/2/") ]
motion_fps = 1

# Global variable to store all our camera stuff
camera_item = []

class CameraItems:
    """ Data structure for storing information about a single camera """
    def __init__(self, camera_index, pipe):
        self.capture_url = cameras[camera_index][0]
        self.monitor_url = cameras[camera_index][1]
        self.monitor_jpg = ramdisk + "cam" + str(camera_index) + ".jpg"
        self.pipe = pipe
        self.is_active = False
        self.motion_process = None

def on_change(message, pipe):
    if (message == "on"):
        print ("It's On: " + pipe)
    else:
        print ("It's Off: " + pipe)
        
def start_ffmpeg_monitor():
    FNULL = open(os.devnull, 'w')
    for camera in camera_item:
        _cmd = ["ffmpeg", 
                "-y", 
                "-i", camera.monitor_url,
                "-r", str(motion_fps),
                "-updatefirst", "1",
                camera.monitor_jpg]
        proc = subprocess.Popen(_cmd, stdout=FNULL, stderr=subprocess.STDOUT)
        camera.motion_process = proc
        print "ffmpeg monitoring ", camera.monitor_url, " pid: ", proc.pid

def get_pipes():
    _pipes = []
    for index, camera in enumerate(cameras):
        _pipe = ramdisk + "cam_motion_" + str(index)
        _pipes.append(_pipe)
        _cam = CameraItems(index, _pipe)
        camera_item.append(_cam)
    return _pipes

try:
    pipes = get_pipes()
    my_input = pipe_watcher.PipesWatcher(pipes)

    print pipes
    start_ffmpeg_monitor()


    while True:
        my_input.check(on_change)
        time.sleep(1)

finally:
    for camera in camera_item:
        # Stop ffmpeg monitor
        try:
            print "Cleaning up camera: ", camera.monitor_url, " pid: ", camera.motion_process.pid
            camera.motion_process.terminate()
        except NameError:
            print "No process for: ", camera_item.monitor_url
        
        try:
            # Clean up the jpg's from ffmpeg
            os.unlink(camera.monitor_jpg)
        except OSError:
            pass