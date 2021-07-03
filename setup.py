import setuptools

"""
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
"""

setuptools.setup(
    name="uddd",
    version="0.1.0",
    author="cu1455",
    author_email="ddhzl1455@outlook.com",
    url="",
    description="A simple tool to download hls stream with regular configure.",
    long_description="null",
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    entry_points ={
            'console_scripts': [
                'uddd = src.cli:main'
            ]
        },
)