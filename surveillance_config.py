import datetime
from collections import namedtuple
import os

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
Camera = namedtuple("Camera", ['name', 'record_url', 'monitor_url'])
# TODO parse from csv: https://docs.python.org/2/library/collections.html#collections.namedtuple
cameras = [ 
    Camera(
        "back1",
        "rtsp://view:3units3814@192.168.0.31:554/Streaming/Channels/2/",
        "rtsp://view:3units3814@192.168.0.31:554/Streaming/Channels/2/"),
    Camera(
        "front1",
        "rtsp://view:3units3814@192.168.0.32:554/Streaming/Channels/2/",
        "rtsp://view:3units3814@192.168.0.32:554/Streaming/Channels/2/"),
    Camera(
        "front2",
        "rtsp://view:3units3814@192.168.0.33:554/Streaming/Channels/2/",
        "rtsp://view:3units3814@192.168.0.33:554/Streaming/Channels/2/"),
    Camera(
        "entry1",
        "rtsp://view:3units3814@192.168.0.34:554/Streaming/Channels/2/",
        "rtsp://view:3units3814@192.168.0.33:554/Streaming/Channels/2/") ]

#------------------------------------------------------------------------------
# End User Defined Variables ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#------------------------------------------------------------------------------

video_motion_dir="motion"
video_all_dir="all"
video_unprocessed_dir="unprocessed"

segment_length = datetime.timedelta(seconds=300)
periodic_process_rate = datetime.timedelta(seconds=30)
space_check_rate = datetime.timedelta(days=1)
event_gap = datetime.timedelta(seconds=15)  # time before or after motion
date_time_format = "%Y%m%d-%H%M%S%Z"
directory_date_format = "%Y.%m.%d"
duration_to_keep_all_segments = datetime.timedelta(days=14) # TODO revise this
disk_usage_limit_bytes = (3 * 1024 * 1024 * 1024 * 1024)

def init():
    global working_area
    global motion_config_path
    global video_unprocessed_path
    working_area=os.path.join(ramdisk, "surveillance")
    motion_config_path=os.path.join(working_area, "motion_config")
    video_unprocessed_path=os.path.join(video_store_path, video_unprocessed_dir)