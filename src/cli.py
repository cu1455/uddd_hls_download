# -*- coding: utf-8 -*-
import argparse
import src.downloader
import src.m3u8_parser

parser = argparse.ArgumentParser(prog='uddd',usage='%(prog)s [URL] [options]',description='A simple tool to download hls stream with regular configure.',allow_abbrev=True,conflict_handler='resolve')

parser.add_argument('URL', help='URL of the m3u8 file.')
parser.add_argument('--output', '-o', metavar = '', help='Output file name.', default='./output.ts')
parser.add_argument('--threads', metavar = '', help='Number of threads used for downloading.', choices=[i for i in range(1,11)], type=int, default=5)
parser.add_argument('--header', metavar = '', help='Header used for downloading.', default=None)
parser.add_argument('--cookies', metavar = '', help='Cookies used for downloading.', default=None)
parser.add_argument('--proxy', metavar = '', help='Proxy used for downloading.', default=None)

group = parser.add_mutually_exclusive_group()
group.add_argument('--split-all', help='Download all fragments without merging.', action='store_true')
group.add_argument('--split-when-fail', help='Merge consecutive fragments only.', action='store_true')
parser.add_argument('--out-digit', metavar = '', help='Number of digits used for labeling output files. 0 for no digit.', choices=[i for i in range(0,32)], type=int, default=4)
parser.add_argument('--retry-attempts', metavar = '', help='Number of attemps to retry before giving up a failed fragment.', choices=[i for i in range(0,11)], type=int, default=5)
parser.add_argument('--retry-interval', metavar = '', help='Number of seconds before another attempt.', choices=[i for i in range(0,16)], type=int, default=1)
parser.add_argument('--timeout', metavar = '', help='Wait time before finishing download when no new segment is available.', type=int, default=60)

parser.add_argument('--help', '-h', help='Show help info.', action='help')
parser.add_argument('--version', '-v', help='Show version info.', action='version', version='uddd 0.1.0')

# Currently not available
# parser.add_argument('--verbose', help='More detailed output.', action='store_true')

args = parser.parse_args()

def main():    
    mainM3U8 = src.m3u8_parser.M3U8(args.URL, args.header, args.cookies, args.proxy)
    src.m3u8_parser.M3U8.parse_m3u8(mainM3U8)
    mainDownloader = src.downloader.Downloader(mainM3U8,args)
    src.downloader.Downloader.start_downloader(mainDownloader)