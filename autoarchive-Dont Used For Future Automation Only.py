#!/usr/bin/env python
"""
This program lets you do archive slack channels which are no longer active.
"""

# standard imports
from datetime import datetime
import os
import sys
import time
import json
import logging
# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# not standard imports
from config import get_channel_reaper_settings
from utils import get_logger


class ChannelReaper():
    """
    This class can be used to archive slack channels.
    """

    def __init__(self):
        self.settings = get_channel_reaper_settings()
        #self.logger = get_logger('channel_reaper', './'+datetime.now().strftime("%d_%m_%Y %H_%M_%S")+'audit.log')
        self.logger = get_logger('channel_reaper', './'+datetime.now().strftime("%d_%m_%Y")+'audit.log')
        self.client = WebClient(token=self.settings.get('slack_token'))
        self.logger = logging.getLogger(__name__)
        self.logger.info(self.settings)

    def get_whitelist_keywords(self):
        """
        Get all whitelist keywords. If this word is used in the channel
        purpose or topic, this will make the channel exempt from archiving.
        """
        keywords = []
        if os.path.isfile('whitelist.txt'):
            with open('whitelist.txt') as filecontent:
                keywords = filecontent.readlines()

        # remove whitespace characters like `\n` at the end of each line
        keywords = map(lambda x: x.strip(), keywords)
        #whitelist_keywords = self.settings.get('whitelist_keywords')
        #if whitelist_keywords:
        #    keywords = keywords + whitelist_keywords.split(',')
        return list(keywords)

    def get_channel_alerts(self):
        """Get the alert message which is used to notify users in a channel of archival. """
        archive_msg = """
This channel has had no activity for %d days. It is being auto-archived.
If you feel this is a mistake you can <https://get.slack.help/hc/en-us/articles/201563847-Archive-a-channel#unarchive-a-channel|unarchive this channel>.
This will bring it back at any point. In the future, you can add '%%noarchive' to your channel topic or purpose to avoid being archived.
""" % self.settings.get('days_inactive')
        alerts = {'channel_template': archive_msg}
        if os.path.isfile('templates.json'):
            with open('templates.json') as filecontent:
                alerts = json.load(filecontent)
        return alerts

    def get_all_channels(self):
        """ Get a list of all non-archived channels from slack channels.list. """

        try:
            result = self.client.conversations_list(exclude_archived = 1)

            channels = result["channels"]
            all_channels = []
            for channel in channels:
                all_channels.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'created': channel['created'],
                    'num_members': channel['num_members']
                })
            return all_channels
        except SlackApiError as e:
            self.logger.error("Error fetching conversations: {}".format(e))


    def get_last_message_timestamp(self, channel_history, too_old_datetime):
        """ Get the last message from a slack channel, and return the time. """
        last_message_datetime = too_old_datetime
        last_bot_message_datetime = too_old_datetime

        if 'messages' not in channel_history:
            return (last_message_datetime, False)  # no messages

        for message in channel_history['messages']:
            if 'subtype' in message and message[
                    'subtype'] in self.settings.get('skip_subtypes'):
                continue
            last_message_datetime = datetime.fromtimestamp(float(
                message['ts']))
            break
        # for folks with the free plan, sometimes there is no last message,
        # then just set last_message_datetime to epoch
        if not last_message_datetime:
            last_bot_message_datetime = datetime.utcfromtimestamp(0)
        # return bot message time if there was no user message
        if too_old_datetime >= last_bot_message_datetime > too_old_datetime:
            return (last_bot_message_datetime, False)
        return (last_message_datetime, True)

    def is_channel_disused(self, channel, too_old_datetime):
        """ Return True or False depending on if a channel is "active" or not.  """
        try:
            num_members = channel['num_members']

            channel_id = channel['id']
            messages_after_date = time.mktime(self.settings.get('too_old_datetime').timetuple())
            self.logger.info(channel_id);
            channel_history = self.client.conversations_history(channel=channel_id , count = 100 , oldest = messages_after_date)
            self.logger.info(channel_history)
            (last_message_datetime, is_user) = self.get_last_message_timestamp(
                channel_history, datetime.fromtimestamp(float(channel['created'])))
            # mark inactive if last message is too old, but don't
            # if there have been bot messages and the channel has
            # at least the minimum number of members
            min_members = self.settings.get('min_members')
            has_min_users = (min_members == 0 or min_members > num_members)
            return last_message_datetime <= too_old_datetime and (not is_user
                                                              or has_min_users)
        except SlackApiError as e:
            self.logger.error("Error creating conversation: {}".format(e))

    # If you add channels to the WHITELIST_KEYWORDS constant they will be exempt from archiving.
    def is_channel_whitelisted(self, channel, white_listed_channels):
        """ Return True or False depending on if a channel is exempt from being archived. """
        # self.settings.get('skip_channel_str')
        # if the channel purpose contains the string self.settings.get('skip_channel_str'), we'll skip it.
        '''
        info_payload = {'channel': channel['id']}
        channel_info = self.slack_api_http(api_endpoint='channels.info',
                                           payload=info_payload,
                                           method='GET')
        channel_purpose = channel_info['channel']['purpose']['value']
        channel_topic = channel_info['channel']['topic']['value']
        if self.settings.get(
                'skip_channel_str') in channel_purpose or self.settings.get(
                    'skip_channel_str') in channel_topic:
            return True
        '''
        # check the white listed channels (file / env)
        for white_listed_channel in white_listed_channels:
            wl_channel_name = white_listed_channel.strip('#')
            if wl_channel_name in channel['name']:
                return True
        return False

    def send_channel_message(self, channel_id, message):
        """ Send a message to a channel or user. """
        try:
            # Call the chat.postMessage method using the WebClient
            result = self.client.chat_postMessage(
                channel=channel_id, 
                text=message
            )
            self.logger.info("Message Added" % result)

        except SlackApiError as e:
            self.logger.error(f"Error posting message: {e}")

    def archive_channel(self, channel, alert):
        """ Archive a channel, and send alert to slack admins. """
        api_endpoint = 'channels.archive'
        stdout_message = 'Archiving channel... %s' % channel['name']
        self.logger.info(stdout_message)

        if not self.settings.get('dry_run'):
            channel_message = alert.format(self.settings.get('days_inactive'))
            self.send_channel_message(channel['id'], channel_message)
            #payload = {'channel': channel['id']}
            self.client.conversations_archive(channel = channel['id'])
            #self.slack_api_http(api_endpoint=api_endpoint, payload=payload)
            self.logger.info(stdout_message)

    def send_admin_report(self, channels):
        """ Optionally this will message admins with which channels were archived. """
        if self.settings.get('admin_channel'):
            channel_names = ', '.join('#' + channel['name']
                                      for channel in channels)
            admin_msg = 'Archiving %d channels: %s' % (len(channels),
                                                       channel_names)
            if self.settings.get('dry_run'):
                admin_msg = '[DRY RUN] %s' % admin_msg
            self.send_channel_message(self.settings.get('admin_channel'),
                                      admin_msg)

    def main(self):
        """
        This is the main method that checks all inactive channels and archives them.
        """
        if self.settings.get('dry_run'):
            self.logger.info(
                'THIS IS A DRY RUN. NO CHANNELS ARE ACTUALLY ARCHIVED.')

        whitelist_keywords = self.get_whitelist_keywords()
        self.logger.info(whitelist_keywords)
        alert_templates = self.get_channel_alerts()
        self.logger.info(alert_templates)
        archived_channels = []

        self.logger.info(self.get_all_channels())
        for channel in self.get_all_channels():
            sys.stdout.write('.')
            sys.stdout.flush()

            channel_whitelisted = self.is_channel_whitelisted(
                channel, whitelist_keywords)
            self.logger.info(channel_whitelisted)

            channel_disused = self.is_channel_disused(
                channel, self.settings.get('too_old_datetime'))
            self.logger.info(channel_disused)
            if (not channel_whitelisted and channel_disused):
                archived_channels.append(channel)
                self.archive_channel(channel,alert_templates['channel_template'])

        self.send_admin_report(archived_channels)

if __name__ == '__main__':
    CHANNEL_REAPER = ChannelReaper()
    CHANNEL_REAPER.main()
