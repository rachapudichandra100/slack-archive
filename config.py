"""
All settings you can change for running slack channel reaper will live in this file.
"""

import os
from datetime import datetime, timedelta


def get_channel_settings():
    """ This returns a dictionary of all settings. """
    days_inactive = int(os.environ.get('DAYS_INACTIVE', 365))
    excelarchive_data_path = os.path.dirname(os.path.abspath(__file__)) + "/data/excelarchive/"
    return {
        'admin_channel': os.environ.get('ADMIN_CHANNEL', '<Slack Admin Channel>'),
        'days_inactive': days_inactive,
        'dry_run': (os.environ.get('DRY_RUN', 'false') == 'true'),
        'slack_token_admin': os.environ.get('SLACK_ADMIN_TOKEN', '<Slack Admin Token>'),
        'slack_token': os.environ.get('SLACK_TOKEN', '<Slack Bot Token>'),
        'too_old_datetime': (datetime.now() - timedelta(days=days_inactive)),
        'root_dir' : os.path.dirname(os.path.abspath(__file__)) ,
        'allowlistfile' : excelarchive_data_path + "allowlist.txt",
        'channelscsvfile' : excelarchive_data_path + "channels.xlsx" ,
        'archive_filename' : excelarchive_data_path + os.environ.get('WORKSPACE_NAME', '')+"archived_output.xlsx",
        'unarchive_filename' : excelarchive_data_path + "unarchive.xlsx",
        'unarchive_output' : excelarchive_data_path + "unarchive_output.xlsx"
    }
