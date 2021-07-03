# -*- coding: utf-8 -*-
import os
import sys
import requests
import binascii
import argparse
import hashlib
import time
import threading
from Crypto.Cipher import AES
from src.m3u8_parser import M3U8


DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'


class Downloader():
    # Constructor
    def __init__(self, m3u8:M3U8, args:argparse.Namespace):
        # m3u8 object
        self.m3u8 = m3u8
        # pointers recording download progress
        self.downloadedNumber = 0
        self.mergePointer = 0
        self.failPointer = 1
        # Threads used for downloading
        self.semaphore = threading.BoundedSemaphore(args.threads)
        # How many tasks can be assigned currently
        self.tasksSlot = 0
        # User KeyboardInterrupt such as ctrl+c
        self.forceStop = False
        # Path for downloaded video
        self.fullPath = args.output
        # Check if file already exists
        if os.path.exists(self.fullPath):
            print('[ERROR] File "{0}" already exists.'.format(os.path.split(self.fullPath)[-1]))
            sys.exit()
        # md5 value for the url of the object being downloaded
        self.md5Digit = args.out_digit
        self.fullUrlMD5 = ''
        # User options for how to split fragments
        self.splitAll = args.split_all
        self.splitWhenFail = args.split_when_fail
        #  User options for retrying a failed segment
        self.retryAttempts = args.retry_attempts
        self.retryInterval = args.retry_interval
        # Headers, cookies and proxies used for downloading
        self.headers = {}
        self.cookies = {}
        self.proxies = {}
        # Live end timeout
        self.timeout = args.timeout
        self.timeoutCount = 0

        # Parsing user option
        if args.proxy != None:
            self.proxies = {'https':args.proxy}
        if args.header != None:
            try:
                headersTokens =  args.header.split(',')
                for headersToken in headersTokens:
                    self.headers[headersToken.split('=')[0]] = headersToken.split('=')[1]
            except:
                print('[ERROR] Headers in invalid format')
                sys.exit()
        if 'user-agent' not in self.headers:
            self.headers = {'user-agent': DEFAULT_USER_AGENT}
        if args.cookies != None:
            try:
                cookiesTokens =  args.cookies.split(',')
                for cookieToken in cookiesTokens:
                    self.cookies[cookieToken.split('=')[0]] = cookieToken.split('=')[1]
            except:
                print('[ERROR] Cookies in invalid format')
                sys.exit()


    # Start downloading
    def start_downloader(self):
        if self.m3u8.type == 'master':
            self.choose_resolution()
        else:
            self.init_download()


    # Choose resolution for a master file
    def choose_resolution(self):
        print('   Resolution    Bandwidth')
        for i,choices in enumerate(self.m3u8.masterINFO):
            print(str(i+1) + '. ' + '{: <14s}'.format(choices['resolution']) + format(choices['bandWidth']))
        choicesNum = [str(i+1) for i in range(len(self.m3u8.masterINFO))]
        choice = input('[m3u8] Enter the index of resolution to download: ')
        while (choice not in choicesNum):
            choice = input('[m3u8] Invalid resolution. Enter the index of resolution to download: ')
        subURL = self.m3u8.generalURL + self.m3u8.masterINFO[int(choice)-1]['subURI']
        subM3U8 = M3U8(subURL, None, None, None, parsedHeader=self.headers, parsedCookies=self.cookies, parsedProxies=self.proxies)
        M3U8.parse_m3u8(subM3U8)
        self.m3u8 = subM3U8
        self.init_download()


    # Choose corresponding method for downloading
    def init_download(self):
        self.fullUrlMD5 = hashlib.md5(self.m3u8.fullURL.encode(encoding='UTF-8')).hexdigest()[:self.md5Digit]
        if self.m3u8.playlistType == 'VOD':
            self.download_vod()
        else:
            self.download_event()
    

    # For EVENT
    def download_event(self):
        tasks = self.m3u8.ts
        newM3U8 = M3U8(self.m3u8.fullURL, None, None, None, parsedHeader=self.headers, parsedCookies=self.cookies, parsedProxies=self.proxies)
        downloadPointer = 0
        try:
            while M3U8.parse_m3u8(newM3U8,'update'):
                if self.forceStop:
                    break
                updateInterval = newM3U8.targetDuration
                haveUpdate = False
                for token in newM3U8.ts:
                    if haveUpdate:
                        tasks.append(token)
                    if token not in tasks:
                        tasks.append(token)
                        haveUpdate = True
                keyNum = len(self.m3u8.keys)
                for i,task in enumerate(tasks[downloadPointer:]):
                    if keyNum > 0:
                        try:
                            if keyNum > i:
                                decryptor = AES.new(self.m3u8.keys[i]['key'], AES.MODE_CBC, binascii.unhexlify(self.m3u8.keys[i]['iv']))
                            else:
                                decryptor = AES.new(self.m3u8.keys[0]['key'], AES.MODE_CBC, binascii.unhexlify(self.m3u8.keys[0]['iv']))
                        except:
                            print ('[ERROR] Unable to create the decryptor.')
                            sys.exit()
                        getTSThread = threading.Thread(target = self.get_ts, args = (self.m3u8.generalURL, task['segmentURI'], downloadPointer, 0, decryptor))
                        self.semaphore.acquire()
                    else:
                        getTSThread = threading.Thread(target = self.get_ts, args = (self.m3u8.generalURL, task['segmentURI'], downloadPointer, 0))
                        self.semaphore.acquire()
                    getTSThread.start()
                    downloadPointer += 1
                if not haveUpdate:
                    self.timeoutCount += updateInterval
                else:
                    self.timeoutCount = 0
                if self.timeoutCount == self.timeout:
                    break
                time.sleep(int(updateInterval))
                newM3U8 = M3U8(self.m3u8.fullURL, None, None, None, parsedHeader=self.headers, parsedCookies=self.cookies, parsedProxies=self.proxies)
            if not self.forceStop:
                print('[download] Live is end.')
                haveUpdate = False
                for token in newM3U8.ts:
                    if haveUpdate:
                        tasks.append(token)
                    if token not in tasks:
                        tasks.append(token)
                        haveUpdate = True
                for task in tasks[downloadPointer:]:
                    getTSThread = threading.Thread(target = self.get_ts, args =(self.m3u8.generalURL, task['segmentURI'], downloadPointer))
                    self.semaphore.acquire()
                    getTSThread.start()
                    getTSThread.join()
                    downloadPointer += 1
        except KeyboardInterrupt:
            self.forceStop = True
            while self.tasksSlot != 0:
                continue
        print ('[download] Downloading finished. {0} segments downloaded.'.format(self.downloadedNumber))


    # For VOD
    def download_vod(self):
        tasks = self.m3u8.ts
        totalNum = len(tasks)
        keyNum = len(self.m3u8.keys)
        try:
            for i,task in enumerate(tasks):
                if self.forceStop:
                    break
                if keyNum > 0:
                    try:
                        if keyNum > i:
                            decryptor = AES.new(self.m3u8.keys[i]['key'], AES.MODE_CBC, binascii.unhexlify(self.m3u8.keys[i]['iv']))
                        else:
                            decryptor = AES.new(self.m3u8.keys[0]['key'], AES.MODE_CBC, binascii.unhexlify(self.m3u8.keys[0]['iv']))
                    except:
                        print ('[ERROR] Unable to create the decryptor.')
                        sys.exit()
                    getTSThread = threading.Thread(target = self.get_ts, args = (self.m3u8.generalURL, task['segmentURI'], i, totalNum, decryptor))
                    self.semaphore.acquire()
                else:
                    getTSThread = threading.Thread(target = self.get_ts, args = (self.m3u8.generalURL, task['segmentURI'], i, totalNum))
                    self.semaphore.acquire()
                getTSThread.start()
                if i == totalNum-1:
                    getTSThread.join()
        except KeyboardInterrupt:
            self.forceStop = True
            while self.tasksSlot != 0:
                continue
        print ('[download] Downloading finished. {0}/{1} segments downloaded'.format(self.downloadedNumber, totalNum))


    # Download ts segment and write
    def get_ts(self, generalURL, uri, downloadPointer, totalNum, decryptor = None):
        self.tasksSlot += 1
        fullURL = generalURL + uri
        try:
            # Download
            task = requests.get(fullURL, headers=self.headers, cookies=self.cookies, proxies=self.proxies, timeout=10.00)
            if decryptor:
                tsContent = decryptor.decrypt(task.content)
            else:
                tsContent = task.content
            self.downloadedNumber += 1
            self.semaphore.release()
            if totalNum:
                print ('[download] Successfully downloaded {0}. {1}/{2} segments downloaded'.format(uri[:-3], self.downloadedNumber, totalNum))
            else:
                print ('[download] Successfully downloaded {0}. {1}th segment downloaded.'.format(uri[:-3], self.downloadedNumber))
            # Write
            with open(self.get_path(False, downloadPointer), 'ab') as f:
                while True:
                    if self.mergePointer == downloadPointer or self.splitAll:
                        f.write(tsContent)
                        self.mergePointer += 1
                        self.tasksSlot -= 1
                        f.close()
                        break
        except:
            print ('[download] Fail to download {0}.'.format(uri[:-3]))
            self.semaphore.release()
            self.tasksSlot -= 1
            self.get_failed_ts(generalURL, uri, downloadPointer, totalNum, decryptor)
        
        
    # Redownload a failed ts segment
    def get_failed_ts(self, generalURL, uri, downloadPointer, totalNum = 0, decryptor = None):
        self.tasksSlot += 1
        fullURL = generalURL + uri
        self.failPointer += 1
        currentPath = self.get_path(True, downloadPointer)
        self.failPointer += 1
        if self.splitWhenFail:
            self.mergePointer += 1
        attempts = self.retryAttempts
        while attempts >= 0:
            try:
                task = requests.get(fullURL, headers=self.headers, cookies=self.cookies, proxies=self.proxies, timeout=10.00)
                if decryptor:
                    tsContent = decryptor.decrypt(task.content)
                else:
                    tsContent = task.content
                if self.splitWhenFail:
                    # Since the failed segement does not merge to other segments, no need to wait for merge pointer
                    with open(currentPath, 'ab') as f:
                        f.write(tsContent)
                        self.downloadedNumber += 1
                        if totalNum:
                            print ('[download] Successfully downloaded {0}. {1}/{2} segments downloaded'.format(uri[:-3], self.downloadedNumber, totalNum))
                        else:
                            print ('[download] Successfully downloaded {0}. {1}th segment downloaded.'.format(uri[:-3], self.downloadedNumber))
                        f.close()      
                else:
                    # Need to wait for merge pointer if the user choose to merge every segment
                    with open(currentPath, 'ab') as f:
                        while True:
                            if mergePointer == downloadPointer or self.splitAll:
                                f.write(tsContent)
                                self.downloadedNumber += 1
                                if totalNum:
                                    print ('[download] Successfully downloaded {0}. {1}/{2} segments downloaded'.format(uri[:-3], self.downloadedNumber, totalNum))
                                else:
                                    print ('[download] Successfully downloaded {0}. {1}th segment downloaded.'.format(uri[:-3], self.downloadedNumber))
                                mergePointer += 1
                                f.close()
                break
            except:
                print ('[download] Fail to download {0}.'.format(uri[:-3]))
                time.sleep(self.retryInterval)
                if attempts == 1 and not self.splitWhenFail:
                    # This means completely failed to download a segment. The program gives this up and stops blocking other segments from merging
                    mergePointer += 1
                attempts -= 1
        self.semaphore.release()
        self.tasksSlot -= 1
    
    
    # Generate the path for downloaded segment
    def get_path(self, isFail, downloadPointer):
        splitedPath = os.path.splitext(self.fullPath)
        seperatePath = self.fullUrlMD5
        if self.fullUrlMD5 != 0:
            seperatePath = seperatePath + '_'
        # Merge the downloaded segments
        if not self.splitAll:
            if isFail:
                if self.splitWhenFail:    # Try to download a failed segment
                    # Split and get a new file name where download is failed
                    result = splitedPath[0] + '_' + seperatePath + str(self.failPointer) + splitedPath[1]
                else:    # Do not split anyway
                    result = splitedPath[0] + splitedPath[1]    
            else:    # Try to download a segment normally
                if self.failPointer > 2:
                    result = splitedPath[0] + '_' + seperatePath + str(self.failPointer) + splitedPath[1]
                else:
                    result = splitedPath[0] + splitedPath[1]
        else:   # Split all segments
            result = splitedPath[0] + '_' + seperatePath + str(downloadPointer) + splitedPath[1]
        return result