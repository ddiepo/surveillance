import os
import datetime
import syslog

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
        self.date = datetime.date.strptime(directory, 
                                           config.directory_date_format)
        
        all_path = os.path.join(config.video_store_path, directory, 
                                config.video_all_dir)
        self.bytes_used_all = None
        if (os.path.exists(all_path)):
            self.bytes_used_all = get_dir_size(all_path)
        
        motion_path = os.path.join(config.video_store_path, directory,
                                  config.video_all_dir)
        self.bytes_used_motion = get_dir_size(video_all_dir)
        
class UsageInfos:
    """ Stores usage info for each directory, newest directories first, oldest last."""
    def __init__(self):
        self.usage_info_list = []
        for item in os.listdir(config.video_store_path):
            if not os.path.isdir(item): continue
            try:
                usage_info_list.append(UsageInfo(item));
            except:
                syslog.syslog(1, traceback.format_exc())
                traceback.print_exc()
        self.usage_info_list.sort(key = lambda item: item.date, reverse=True)
    
    def get_max_all_usage(self):
        largest = 0;
        for usage_info in self.usage_info_list:
            if usage_info.bytes_used_all != None:
                largest = max(largest, usage_info.bytes_used_all)
        
        return largest;

    def compute_space_usaged_ignoring_today(self):
        # Ignore the first entry which should be for today
        bytes = 0
        for i in self.usage_info_list[1:]:
            if i.bytes_used_all != None:
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
    for info in usage_infos.usage_info_list:
        if (now - info.date) > config.duration_to_keep_all_segments:
            syslog.syslog(2, "Clearing non-motion to free disk space: " 
                  + info.directory)
            shutil.rmtree(os.path.join(config.video_store_path, 
                                       info.directory, 
                                       config.video_all_dir), True)
            info.bytes_used_all = None
        else:
            break

def remove_oldest_day(usage_infos):
    syslog.syslog(2, "Clearing day to free disk space: " 
                  + usage_infos.get_oldest_day().directory)
    shutil.rmtree(os.path.join(
        config.video_store_path, usage_infos.get_oldest_day().directory), True);
    usage_infos.remove_oldest_day()


def cleanup():
    """ Keeps all segments as specified, and cleans up others to keep total usage in check. """
    usage_infos = UsageInfos()
    clear_non_motion_segments_for_days_too_old(usage_infos)
    
    max_day_size = usage_infos.get_max_all_usage()
    while (usage_infos.compute_space_usaged_ignoring_today() + max_day_size >
           config.disk_usage_limit_bytes):
        remove_oldest_day(usage_infos)
    
    return
