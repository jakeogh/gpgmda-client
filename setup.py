# -*- coding: utf-8 -*-
"""
client tools for https://github.com/jakeogh/gpgmda
"""

from setuptools import find_packages
from setuptools import setup

dependencies = []

version = 0.01


setup(
    name="gpgmda-client",
    version=version,
    url="https://github.com/jakeogh/gpgmda-client",
    license="MIT",
    author="jakeogh",
    author_email="github.com@v6y.net",
    description="client for gpgmda",
    long_description=__doc__,
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=dependencies,
    entry_points={
        "console_scripts": [
            "gpgmda-client = gpgmda_client.gpgmda_client:client",
        ],
    },
    #   long_description = long_descr,
    classifiers=[
        # As from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        # 'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        # 'Development Status :: 3 - Alpha',
        "Development Status :: 4 - Beta",
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
        "Operating System :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
