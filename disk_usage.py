import os_help
import datetime
import syslog
import surveillance_config as config

def keep_only_motion_for_days_older_than(
        time_to_keep_all, from_dir, subdir_to_remove):
    for item in os.listdir(from_dir):
        if not os.path.isdir(item): continue
        try:
            date = datetime.date.strptime(config.directory_date_format)
            if (datetime.datetime.now() - date) > time_to_keep_all:
                shutil.rmtree(
                    from_dir + "/" + item + "/" + subdir_to_remove, True);
        except:
            syslog.syslog(1, traceback.format_exc())
            traceback.print_exc()
    return


def cleanup(time_to_keep_all, 
            max_space_to_use):
    """ Keeps all segments as specified, and cleans up others to keep total usage in check. """
    
    keep_only_motion_for_days_older_than(
        time_to_keep_all, config.video_store_path, video_all_dir)
    
    
    return
