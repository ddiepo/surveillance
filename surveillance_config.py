import datetime
from collections import namedtuple
import os
import ConfigParser


# List of camera tuples, of (record stream, motion stream)
Camera = namedtuple("Camera", ['name', 'record_url', 'monitor_url'])
cameras = []

# Subdirectory to store video segments flagged with motion for a given day
video_motion_dir = "motion"

# Subdirectory to store all the video segments for a given day
video_all_dir = "all"

# Subdirectory to store segments not yet processed
video_unprocessed_dir = "unprocessed"

# How long each video file will be
segment_length = datetime.timedelta(seconds=300)

# How often to move files from the unprocessed dir
periodic_process_rate = datetime.timedelta(seconds=30)

# How frequently to cleanup disk space
# Note: That logic assumes it will be called at least every 1 day
space_check_rate = datetime.timedelta(days=1)

# How long before or after a motion event to trigger a segment to be flagged.
event_gap = datetime.timedelta(seconds=15)  # time before or after motion

# Format used for writing/parsing file segment's date & time.
date_time_format = "%Y%m%d-%H%M%S%Z"

# Format used for writing/parsing directories for storing segments.
directory_date_format = "%Y.%m.%d"


def parse_overall(configuration, section):
    global ramdisk
    global video_store_path
    global motion_mask_path
    global duration_to_keep_all_segments
    global disk_usage_limit_bytes

    ramdisk = configuration.get(section, "ramdisk")
    video_store_path = configuration.get(section, "video_store_path")
    motion_mask_path = configuration.get(section, "motion_mask_path")

    days = configuration.getint(section, "days_to_keep_motionless_segments")
    duration_to_keep_all_segments = datetime.timedelta(days=days)

    disk_usage_limit_bytes = configuration.getint(
        section, "disk_usage_limit_bytes")


def parse_cameras(configuration, sectionToIgnore):
    global cameras

    for section in configuration.sections():
        if section == sectionToIgnore:
            continue

        cameras.append(
            Camera(section,
                   configuration.get(section, "record_url"),
                   configuration.get(section, "monitor_url")))


def parse(config_file):
    print "Parsing: " + config_file
    configuration = ConfigParser.RawConfigParser()
    configuration.read(config_file)

    section = "surveillance"
    parse_overall(configuration, section)
    parse_cameras(configuration, section)


def init(config_file):
    global working_area
    global motion_config_path
    global video_unprocessed_path

    parse(config_file)
    working_area = os.path.join(ramdisk, "surveillance")
    motion_config_path = os.path.join(working_area, "motion_config")
    video_unprocessed_path = os.path.join(video_store_path,
                                          video_unprocessed_dir)
