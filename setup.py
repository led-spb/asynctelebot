#!/usr/bin/python

import setuptools
                  

setuptools.setup(
    name="asynctelebot",
    version="0.0.1",
    author="Alexey Ponimash",
    author_email="alexey.ponimash@gmail.com",
    description="Async telegram bot framework",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/led-spb/asynctelebot",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
       'tornado',
    ]
)
