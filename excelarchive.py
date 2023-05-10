from datetime import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta
import numpy as np 
import os
import sys
import time

# * Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
from slack_sdk import WebClient

# * not standard imports crearted in the project
from config import get_channel_settings
from utils import get_logger


class ExcelArchiver():
    """
    This class is a base for Archival Process with channels.csv
    Path : auto-archive/data/excelarchive/
    Filename : channels.csv
    """
    def __init__(self) -> None:
        try:
            # * get settings 
            self.settings = get_channel_settings()
            self.logger = get_logger('excel_archiver', datetime.now().strftime("%d_%m_%Y")+'audit.log')
            
            # * Create a WebClient to be used for Slack API connection
            # * self.client_bot --> This will be a slack bot Connection
            # * self.client_admin --> This will be a slack person Connection
            self.client_bot = WebClient(token=self.settings.get('slack_token'))
            self.client_admin = WebClient(token=self.settings.get('slack_token_admin'))


            # * Initialize the Variable needed
            # * df_csv --> dataframe for reading the source excel.(channels.csv)
            # * df_filtered_data --> dataframe after filtering source df_csv
            # * allowlistkeywords --> store all the allowlist
            self.df_csv = pd.DataFrame()
            self.df_filtered_data = pd.DataFrame()
            self.allowlistkeywords = self.get_allow_list()

            # * Get bot userid to add to all Private Channels to be archived
            self.bot_user_id = self.client_bot.auth_test()["user_id"] # ** Volume is not a issue as this is only claled once

        except Exception as e:
            self.exit_on_critical_exception(e)

    ## * log the error and then exit the program as any excpetion at read is critical exceptions.
    ## * Further execution of program is not needed for Critical Errors.
    def exit_on_critical_exception(self, e):  
        self.logger.critical((e))
        sys.exit(1)

    ## * Read all the source data needed
    def readdata(self):
        try:
            # * read the csv sourcefile in dataframe
            csvfile = self.settings.get('channelscsvfile')
            self.df_csv = pd.read_excel(csvfile)
            # * convert the last activity Column to datetime
            """
            Commented for Future Automations ... PLEASE DO NOT DELETE.
            ###self.df_csv['Last activity'] = pd.to_datetime(self.df_csv['Last activity'],errors='coerce', utc=True ,format='%a, %d %b %Y %H:%M:%S %z')
            #self.df_csv['Last activity'] = pd.to_datetime(self.df_csv['Last activity'],format='%d/%m/%y')
            ###self.df_csv['Last activity']= self.df_csv['Last activity'].dt.tz_localize(None)
            # * filter the data where last activity is before 365 days and Archived is not true
            #filtered_values = np.where(((self.df_csv['Members'] <1) | (self.df_csv['Last activity']< datetime.now()- relativedelta(days=self.settings.get('days_inactive')))) & (self.df_csv['Archived']!= 1.0 ))
            ###filtered_values = np.where(((self.df_csv['Last activity']< datetime.now()- relativedelta(days=self.settings.get('days_inactive')))) & (self.df_csv['Archived']!= 1.0 ))
            ###self.df_filtered_data = (self.df_csv.loc[filtered_values])
            """
            self.df_filtered_data = (self.df_csv)
            # * add new columns to capture the log and errors when processing the channels.
            self.df_filtered_data["MembersList"] = ""           # * captures all the members in the channel 
            self.df_filtered_data["Allowlisted"] = False        # * will be True if channel is allowlisted
            self.df_filtered_data["IsBotMember"] = False        # * will be True if bot is already in the channel
            self.df_filtered_data["IsError"] = False            # * will be True if error occurs while processing the channel
            self.df_filtered_data["ErrorMessage"] = ""          # * captures the error message
            self.df_filtered_data["IsCriticalError"] = False    # * will be True if Critical occurs while processing the channel
            self.df_filtered_data["CriticalErrorMessage"] = ""  # * captures the Critical error message
            self.df_filtered_data["InviteFailed"] = False       # * will be True if Invite Event executes without error is allowlisted
            self.df_filtered_data["GetMembersFailed"] = False   # * will be True Members are fetched without error
            self.df_filtered_data["ArchiveFailed"] = False      # * will be True if archived without error
        except Exception as e:
            self.exit_on_critical_exception(e)

    
    ## * Read the allowlistfile and return the list of keywords
    def get_allow_list(self):
        try:        
            keywords = []
            if os.path.isfile(self.settings.get('allowlistfile')):
                with open(self.settings.get('allowlistfile')) as filecontent:
                    keywords = filecontent.readlines()
            else:
                raise Exception("File Not Found : " + self.settings.get('allowlistfile'))
            
            keywords = map(lambda x: x.strip(), keywords)
            return list(keywords)
        except Exception as e:
            self.exit_on_critical_exception(e)

    ## * Process all the data
    def processdata(self):
        try:
            self.logger.info("Name,ID,Members")
            ## * Get Channel Members and append it to dataframe 
            for index, row in self.df_filtered_data.iterrows():           
                self.get_channel_members(row,index)

            ## * Archive channels and apend the output to dataframe
            for index, row in self.df_filtered_data.iterrows():
                self.archive_channel(row,index)
        except Exception as e:
            self.logger.error(e)
    
    ## * Wite the final data froma to excel and send it to slack admin channel
    def writedata(self):
        try:
            self.df_filtered_data.to_excel(self.settings.get('archive_filename'))
            self.send_file_to_channel(self.settings.get('admin_channel'),self.settings.get('archive_filename'))
        except Exception as e:
            self.logger.error(e)

    ## * Invite the bot to Private Channel so that bot has access to archive the channel
    def invite_to_channel(self,row,index):
        try:
            time.sleep(3)
            result = self.client_admin.admin_conversations_invite(channel_id= row["ID"], user_ids = [self.bot_user_id]) # ** Tier 2 20+ per minute
        except Exception as e:
            self.df_filtered_data.at[index, 'ErrorMessage'] = format(e) + row['ErrorMessage']
            self.df_filtered_data.at[index, 'IsError'] = True
            self.df_filtered_data.at[index, 'InviteFailed'] = True
            self.logger.error(e)

    ## * Get memebers of each channel and add to Memberlist column for rollbacks
    def get_channel_members(self,row,index):
        try:
            channel_id = row["ID"]
            # * check if channel is allowlisted if yes archiving is not needed comment as whitelisted in the MemberList
            if row["Name"] not in self.allowlistkeywords:
                # * Add bot to Private Channels in scope
                if ((not self.settings.get('dry_run'))):
                    self.invite_to_channel(row,index)

                # * Get members for each channel and add it to dataframe to send as attachment to Slack Admin Channel
                membersArray= self.client_bot.conversations_members(channel=channel_id , limit = 8000)["members"]  # ** Tier 4 100+ per minute
                membersStr = ','.join(membersArray)
                self.df_filtered_data.at[index, 'MembersList'] = membersStr

                # * if bot is already a member it will raise an exception on invite to channel which can be ignored
                # * ignore the error by setting IsBotMember = True and IsError = False
                if self.bot_user_id in membersStr:
                    self.df_filtered_data.at[index, "IsBotMember"] = True
                    self.df_filtered_data.at[index, "IsError"] = False
                    
                # * Capyuring this as fall back in case someting goes bad
                self.logger.info('%s,%s,"%s"' % (row["Name"],row["ID"],membersStr))
            else:
                self.df_filtered_data.at[index, 'Allowlisted'] = True
        except Exception as e:
            self.df_filtered_data.at[index, 'ErrorMessage'] = format(e) + row['ErrorMessage']
            self.df_filtered_data.at[index, 'IsError'] = True
            self.df_filtered_data.at[index, 'GetMembersFailed'] = True
            self.logger.error(e)

    def archive_channel(self,row,index):
        try:
            if not (row["Allowlisted"] == True or (row["IsError"] == True)):
                if not self.settings.get('dry_run'):
                    time.sleep(3)
                    self.client_bot.conversations_archive(channel = row["ID"]) # ** Tier 2 20+ per minute
            else:
                self.df_filtered_data.at[index, 'ArchiveFailed'] = True
                    
        except Exception as e:
            self.df_filtered_data.at[index, 'ErrorMessage'] = format(e) + row['ErrorMessage']
            self.df_filtered_data.at[index, 'IsError'] = True
            self.df_filtered_data.at[index, 'ArchiveFailed'] = True
            self.logger.error(e)

    def send_file_to_channel(self, channel_id, file_name):
        """ Send a message to a channel or user. """
        try:
            if self.settings.get('dry_run'):
                comment = "THIS IS A DRY RUN. NO CHANNELS ARE ACTUALLY ARCHIVED."
            else:
                comment = "Please find the list of channels Archived in the attachment."
            # Call the chat.postMessage method using the WebClient # ** Tier not a problem as this will be 1 time call
            result = self.client_bot.files_upload(
                channel=channel_id,
                initial_comment= comment,
                file=file_name,
            )

        except Exception as e:
            self.logger.error(e)


    def send_channel_message(self, channel_id, message):
        """ Send a message to a channel or user. """
        try:
            # Call the chat.postMessage method using the WebClient
            result = self.client.chat_postMessage(
                channel=channel_id, 
                text=message
            )
        except Exception as e:
            self.logger.error(e)
    
    def main(self):
        """
        This is the main method that checks all inactive channels in excel and archives them.
        """
        try:
            if self.settings.get('dry_run'):
                self.logger.info(
                    'THIS IS A DRY RUN. NO CHANNELS ARE ACTUALLY ARCHIVED.')
                
            self.readdata()
            self.processdata()
            self.writedata()

        except Exception as e:
            self.logger.error(e)

if __name__ == '__main__':
    EXCEL_ARCHIVER = ExcelArchiver()
    EXCEL_ARCHIVER.main()
