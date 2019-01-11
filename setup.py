#!/usr/bin/python
import setuptools
import pkg_resources
import pytelegram_async as module

setuptools.setup(
    name=module.name,
    version=pkg_resources.parse_version(module.version).public,
    author="Alexey Ponimash",
    author_email="alexey.ponimash@gmail.com",
    description="Async telegram bot framework",
    packages=setuptools.find_packages(exclude=["tests"]),
    install_requires=[
       'tornado',
    ]
)
