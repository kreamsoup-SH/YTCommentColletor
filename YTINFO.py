'''
Install Google API Client library to use YouTube Data API.
"pip install --upgrade google-api-python-client"

you need pandas and openpyxl when export .xlsx file
'''
import os

import requests
from bs4 import BeautifulSoup
# class : web_controller

import re
# class : youtube_controller_base > def get_channelId()

import googleapiclient.discovery
# class : youtube_API_controller

from pytube import Playlist
# 

import pandas as pd
# when you crawl comments by videoId

import json
with open('config.json') as f: CONFIG = json.load(f)
# import config file
'''
{
    "PATTERN_DICT" :{
        "youtube" : <string>
    },
    "URL" : <string>,
    "API_CONFIGS" : {
        "api_version" : <string>,
        "api_service_name" : <string>,
        "DEVELOPER_KEY" : <string>
    },
    "export":{
        "header": <list>
    }
}
'''

class web_controller:
    def __init__(self):
        super().__init__()
    
    def get_parsed_html(self,url:str):
        if re.compile('https?://').match(url) is None:
            print("https://로 시작하지 않아요!!!")
            url='https://'+url
        response = requests.get(url)
        
        if response.status_code != 200:
            print("Unknown error occured! <response.status_code is not 200>")
            return False
        # response error control

        html = response.text
        parsed_html = BeautifulSoup(html, 'html.parser')
        return parsed_html  # : <class 'bs4.BeautifulSoup'>
    
    def check_url_pattern_valid(self, url:str, pattern:str):
        compile_obj = re.compile(r''+CONFIG['PATTERN_DICT'][pattern])
        isMatched = compile_obj.match(url)
        if isMatched:
            #print('Match found: ', isMatched.group())
            return isMatched.group()
        else:
            #print('No match')
            return False
        
    def export_xlsx(self,_list:list, targetname:str, header:list, index=None):
        pd.DataFrame(_list).to_excel(targetname+'.xlsx', header=None, index=None)

class youtube_controller_base(web_controller):
    def __init__(self):
        super().__init__()

    def get_channelId(self, url):
        parsed_url = self.check_url_pattern_valid(url=url, pattern='youtube') # :str or False
        if parsed_url is False:
            print("invalid url")
            return False
        else:
            print("valid url이에요~")
            print('parsed_url=',parsed_url)
            parsed_html = self.get_parsed_html(parsed_url)
            orig_url = parsed_html.find("link",{"rel":"canonical"})['href'] # 캐노니컬 태그로 채널id 찾기
            channelId = orig_url.split(r'/')[-1]
            return channelId
        

        
class youtube_API_controller(youtube_controller_base):    
    def __init__(self, api_configs):
        super().__init__()
        self.api_version = api_configs['api_version']
        self.api_service_name = api_configs['api_service_name']
        self.developerKey = api_configs['DEVELOPER_KEY']

        self.youtube = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, developerKey = self.developerKey)

    def get_videoIds_by_channelId(self,channelId:str, maxResults=100):
        request = self.youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=channelId,
            maxResults=25
        )
        response = request.execute()
        playlistId = response["items"][0]['contentDetails']['relatedPlaylists']['uploads']

        youtube_playlist_baseurl="https://www.youtube.com/playlist?list="
        url_playlist = youtube_playlist_baseurl + playlistId
        playlists = [url_playlist]
        videoIds= []
        for playlist in playlists:
            playlist_urls = Playlist(playlist)
            for url in playlist_urls:
                videoIds.append(url.split("watch?v=")[-1])
        return videoIds #type: list


    def get_comments_by_videoId(self, video_id):
        request = self.youtube.commentThreads().list(
            part="snippet, replies",
            videoId= video_id,
            maxResults=100,
        )
        response = request.execute()
        # with open('output.json','w') as f: json.dump(response, f, indent=4, ensure_ascii=False)
        
        comments = [CONFIG['export']['header']]
        while response:
            for item in response['items']:
                toplvCommentData = item['snippet']['topLevelComment']['snippet']
                comments.append([ toplvCommentData['authorDisplayName'], toplvCommentData['textDisplay'], toplvCommentData['textOriginal'], toplvCommentData['likeCount'] ])

                if item['snippet']['totalReplyCount'] > 0:
                    for reply in item['replies']['comments']:
                        replyData = reply['snippet']
                        comments.append([ replyData['authorDisplayName'], replyData['textDisplay'], replyData['textOriginal'], replyData['likeCount'] ])

            if 'nextPageToken' in response:
                response = self.youtube.commentThreads().list(part='snippet,replies', videoId=video_id, pageToken=response['nextPageToken'], maxResults=100).execute()
            else:
                break
        return comments # <list>
    
    

def main():
    obj_youtube_api = youtube_API_controller(api_configs=CONFIG['API_CONFIGS'])

    rawURLs=CONFIG['URL'] #임시로 그냥 적어둔거임
    for rawURL in rawURLs:
        channelId = obj_youtube_api.get_channelId(rawURL)
        print("채널ID : ", channelId)

        try :
            os.mkdir('./data')
        except:
            print('already exist folder<case 0>. pass')
        try :
            os.mkdir('./data/'+channelId)
        except:
            print('already exist folder<case 1>. pass')
        videoIds = obj_youtube_api.get_videoIds_by_channelId(channelId)
        print("print videoIds :",videoIds)
        for videoId in videoIds:
            comments = obj_youtube_api.get_comments_by_videoId(videoId)
            print("print comments :",comments)
            obj_youtube_api.export_xlsx(comments,'./data/'+channelId+'/'+videoId,CONFIG['export']['header'],index=None)

if __name__ == "__main__":
	main()



# URLpattern_youtube = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/((watch\?v=|embed/|v/|.+\?v=)?(?P<id>[A-Za-z0-9\-=_]{11})|@[A-Za-z0-9\-=_]*)')