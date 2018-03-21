import os
import datetime
import shutil
import syslog
import traceback

import os_help
import surveillance_config as config


def get_dir_size(path):
    """ Gets size of all files in the directory, does not recurse. """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


class UsageInfo:
    def __init__(self, directory):
        self.directory = directory
        self.date = datetime.datetime.strptime(
            directory, config.directory_date_format)

        all_path = os.path.join(config.video_store_path, directory,
                                config.video_all_dir)
        self.bytes_used_all = None
        if (os.path.exists(all_path)):
            self.bytes_used_all = get_dir_size(all_path)

        motion_path = os.path.join(config.video_store_path, directory,
                                   config.video_motion_dir)
        self.bytes_used_motion = get_dir_size(motion_path)


class UsageInfos:
    """ Stores usage info for each directory ordered by date."""

    def __init__(self):

        self.usage_info_list = []
        for item in os.listdir(config.video_store_path):
            if (item == config.video_unprocessed_dir
                or not os.path.isdir(
                    os.path.join(config.video_store_path, item))):
                continue
            try:
                self.usage_info_list.append(UsageInfo(item))
            except Exception:
                syslog.syslog(1, traceback.format_exc())
                traceback.print_exc()
        self.usage_info_list.sort(key=lambda item: item.date, reverse=True)

    def get_max_all_usage(self):
        largest = 0
        for usage_info in self.usage_info_list:
            if usage_info.bytes_used_all is not None:
                largest = max(largest, usage_info.bytes_used_all)

        return largest

    def compute_space_usaged_ignoring_today(self):
        # Ignore the first entry which should be for today
        bytes = 0
        for i in self.usage_info_list[1:]:
            if i.bytes_used_all is not None:
                bytes += i.bytes_used_all
            else:
                bytes += i.bytes_used_motion
        return bytes

    def get_oldest_day(self):
        return self.usage_info_list[-1]

    def remove_oldest_day(self):
        self.usage_info_list.pop(-1)


def clear_non_motion_segments_for_days_too_old(usage_infos):
    now = datetime.datetime.now()
    for info in reversed(usage_infos.usage_info_list):
        if (info.bytes_used_all is not None and
                (now - info.date) > config.duration_to_keep_all_segments):
            syslog.syslog(2, "Clearing non-motion to free disk space: "
                          + info.directory)
            shutil.rmtree(
                os.path.join(config.video_store_path, info.directory,
                             config.video_all_dir), True)
            info.bytes_used_all = None
        else:
            break


def remove_oldest_day(usage_infos):
    syslog.syslog(2, "Clearing day to free disk space: "
                  + usage_infos.get_oldest_day().directory)
    shutil.rmtree(os.path.join(
        config.video_store_path, usage_infos.get_oldest_day().directory), True)
    usage_infos.remove_oldest_day()


def cleanup():
    """ Removes video segments as needed.

    Configuration allows to specify the number of days we keep all
    segments. For all days older than that we only keep the segments
    with motion.

    Configuration also allows setting a max total disk space to use.
    We estimate the size for the current day by using the maximum size
    for any of days, and remove the oldest days until we are under the
    cap.

    Note: This code assumes the motion & all directories use hard links
          to share the segments.
    """
    infos = UsageInfos()

    on_disk = infos.compute_space_usaged_ignoring_today()
    max_day_size = infos.get_max_all_usage()
    syslog.syslog(3, "Disk Usage initial (except today): " + str(on_disk)
                  + " Max Day Size: " + str(max_day_size))

    clear_non_motion_segments_for_days_too_old(infos)
    on_disk = infos.compute_space_usaged_ignoring_today()
    while (on_disk + max_day_size > config.disk_usage_limit_bytes):
        remove_oldest_day(infos)
        on_disk = infos.compute_space_usaged_ignoring_today()

    syslog.syslog(3, "Disk Usage final (except today): " + str(on_disk))

    return
