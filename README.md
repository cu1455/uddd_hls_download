# uddd

A command line tool to download hls stream. For self-use.
Currently supports common hls stream configure. More features and supported platforms to be added.

## Installation
[Python 3.6](https://www.python.org/) or upper is required.
To install,
```sh
pip install -i https://test.pypi.org/simple/ uddd
```

## Version
0.1.0

## Usage
To download a stream, simply do
```sh
uddd [URL]
```

A list of options:
```sh
  --output , -o      Output file name.
  --threads          Number of threads used for downloading.
  --header           Header used for downloading.
  --cookies          Cookies used for downloading.
  --proxy            Proxy used for downloading.
  --split-all        Download all fragments without merging.
  --split-when-fail  Merge consecutive fragments only.
  --out-digit        Number of digits used for labeling output files. 0 for no digit.
  --retry-attempts   Number of attemps to retry before giving up a failed fragment.
  --retry-interval   Number of seconds before another attempt.
  --timeout          Wait time before finishing download when no new segment is available.
  --help, -h         Show help info.
  --version, -v      Show version info.
```

## License
MIT
