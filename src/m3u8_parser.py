# -*- coding: utf-8 -*-
import sys
import requests
from urllib.parse import urlparse


DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'


class M3U8():
    # Constructor
    def __init__(self, inputURL, header, cookies, proxies, parsedHeader=None, parsedCookies=None, parsedProxies=None):
        # Common attributes
        self.fullURL = inputURL     # Eg. https://example.com/path1/path2/playlist.m3u8?Key-Pair-Id=ABCDE12345
        self.generalURL = ''        # Eg. https://example.com/path1/path2/
        self.tokens = []            # Tokens of downloaded file
        self.type = ''              # master or media
        # For master m3u8 file
        self.masterINFO = []        # List of dicts with subUri, resolution and bandwidth
        # For media m3u8 file
        self.playlistType = ''      # Can be directly read or manually determined (if not specified), VOD or EVENT
        self.targetDuration = ''    # Maximum length for each ts segment
        self.mediaSequence = ''     # Current media sequence
        self.ts = []                # List of dicts with each segments' uri and length
        # Optinoal attribute for sub m3u8
        self.keys = []              # List of dicts with encryptMethod, keyURI, key, iv
        # User option for getting file
        self.headers = {}
        self.cookies = {}
        self.proxies = {}

        # Parsing user option
        if proxies:
            self.proxies = {'https':proxies}
        if header:
            try:
                headersTokens =  header.split('; ')
                for headersToken in headersTokens:
                    self.headers[headersToken.split('=')[0]] = headersToken.split('=')[1]
            except:
                print('[ERROR] Headers in invalid format')
                sys.exit()
        if cookies:
            try:
                cookiesTokens =  cookies.split('; ')
                for cookieToken in cookiesTokens:
                    self.cookies[cookieToken.split('=')[0]] = cookieToken.split('=')[1]
            except:
                print('[ERROR] Cookies in invalid format')
                sys.exit()
        if parsedHeader:
            self.headers = parsedHeader
        if parsedCookies:
            self.cookies = parsedCookies
        if parsedProxies:
            self.proxies = parsedProxies
        if 'user-agent' not in self.headers:
            self.headers = {'user-agent': DEFAULT_USER_AGENT}

        
    # Download file and parse into tokens
    def get_tokens(self):            
        rawTask = requests.get(self.fullURL, headers=self.headers, cookies=self.cookies, proxies=self.proxies,timeout=10.00)
        task = rawTask.content.decode('utf-8')
        result = task.split('\n')   # Seperate by line
        if rawTask.status_code == 403:
            raise Exception('Forbidden')
        elif rawTask.status_code == 404:
            raise Exception('Not Found')
        return result


    # Determine type of m3u8 file
    def get_type(self):
        for token in self.tokens:    
            if token.startswith('#EXTINF:'):
                return 'media'
        return 'master'
        

    # General funtion for getting from given url
    def parse_m3u8(self, operation=None): 
        # If just listening for changes while downloading, the program should not exit
        # Return false when url is not available while downloading, true otherwise
        try:
            self.tokens = self.get_tokens()
        except:
            if operation == 'update':
                return False
            else:
                print('[ERROR] Provided URL is invalid or expired.')
                sys.exit()
        if (self.tokens[0] != '#EXTM3U'):
            print('[ERROR] The file is not a valid m3u8 file.')
            sys.exit()
        firstM3U8 = self.fullURL.find('.m3u8')
        lastSlash = self.fullURL.rfind('/',0,firstM3U8)
        self.generalURL = self.fullURL[0:lastSlash+1]
        self.type = self.get_type()
        if self.type == 'master':
            self.parse_master()
        else:
            self.parse_media()
        return True


    # Parse master m3u8 file
    def parse_master(self):
        tokenLength = len(self.tokens)
        i = 1
        result = []
        while i < tokenLength:
            token = self.tokens[i]
            splitedToken = token.split(':')
            if splitedToken[0] != '#EXT-X-STREAM-INF':
                i += 1
                continue
            # URI
            subURI = self.tokens[i+1]
            streamInfs = splitedToken[1].split(',')
            bandWidth = '-'
            resolution = '-'
            for streamInf in streamInfs:
                if '=' not in streamInf:
                    continue
                infToken = streamInf.split('=')
                attribute = infToken[0]
                attributeValue = infToken[1]
                if attribute == 'BANDWIDTH':
                    bandWidth = attributeValue
                elif attribute == 'RESOLUTION':
                    resolution = attributeValue
            result.append({'subURI':subURI,'resolution':resolution,'bandWidth':bandWidth})
            i += 2
        self.masterINFO = result


    # Parse media m3u8 file
    def parse_media(self):
        tokenLength = len(self.tokens)
        i = 1
        self.playlistType = 'EVENT'
        while i < tokenLength:
            token = self.tokens[i]
            splitedToken = token.split(':')
            attribute = splitedToken[0]
            if attribute == '#EXT-X-ENDLIST':
                self.playlistType = 'VOD'
            elif attribute != '':
                try:
                    attributeValue = splitedToken[1]
                except IndexError:
                    pass
            if attribute == '#EXT-X-PLAYLIST-TYPE':
                self.playlistType = attributeValue
            elif attribute == '#EXT-X-TARGETDURATION':
                self.targetDuration = attributeValue
            elif attribute == '#EXT-X-MEDIA-SEQUENCE':
                self.mediaSequence = attributeValue
            elif attribute == '#EXT-X-PLAYLIST-TYPE':
                self.type = attributeValue
            elif attribute == '#EXT-X-KEY':
                keyTokens = token.split(',')
                for keytoken in keyTokens:
                    keyAttribute = keytoken.split('=')
                    keyAttribute1 = keyAttribute[0]
                    keyAttribute2 = keyAttribute[1]
                    if 'METHOD' in keyAttribute1:
                        encryptMethod = keyAttribute2
                    elif 'URI' in keyAttribute1:
                        keyURI = keyAttribute2[1:-1]
                    elif 'IV' in keyAttribute1:
                        if len(keyAttribute2) < 34:
                            iv = '{:0>32d}'.format(keyAttribute2[2:]) 
                        else:
                            iv = keyAttribute2[-32:]
                if encryptMethod == 'AES-128':
                    try:
                        if urlparse(keyURI).netloc == '':
                            keyFullURL = self.generalURL + keyURI
                        else:
                            keyFullURL = keyURI
                        keyFile = requests.get(keyFullURL, headers=self.headers, cookies=self.cookies, proxies=self.proxies, timeout=10.00)
                        key = keyFile.content
                    except:
                        print ('[ERROR] Unable to download the key file.')
                        sys.exit()
                    if iv == None:
                        iv = '{:0>32d}'.format(self.mediaSequence)      
                self.keys.append({'encryptMethod':encryptMethod,'keyURI':keyURI,'key':key,'iv':iv})
            elif attribute == '#EXTINF':
                segmentLength = attributeValue[:-1]
                segmentURI = self.tokens[i+1]
                self.ts.append({'segmentURI':segmentURI,'segmentLength':segmentLength})
                i += 2
                continue
            i += 1
        
        
    # Print parsed info    
    def print_info(self):
        print('fullURL: ')
        print(self.fullURL)
        print('generalURL: ')
        print(self.generalURL)
        print('type: ')
        print(self.type)
        if self.type == 'master':
            print('masterINFO: ')
            print(self.masterINFO)
        else:
            print('playlistType: ')
            print(self.playlistType)
            print('targetDuration: ')
            print(self.targetDuration)
            print('mediaSequence: ')
            print(self.mediaSequence)
            print('keys: ')
            print(self.keys)
            print('headers: ')
            print(self.headers)
            print('cookies: ')
            print(self.cookies)
            print('proxies: ')
            print(self.proxies)
            """
            print('ts: ')
            print(self.ts)
            """