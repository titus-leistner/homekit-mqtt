#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md') as history_file:
    history = history_file.read()

requirements = ['Click', 'HAP-python', 'base36', 'pyqrcode', 'paho-mqtt']

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="Titus Leistner",
    author_email='mail@titus-leistner.de',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="This is a lightweight bridge between HomeKit and MQTT.",
    entry_points={
        'console_scripts': [
            'homekit-mqtt=homekit_mqtt.cli:main',
        ],
    },
    python_requires='>=3.5',
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='homekit_mqtt',
    name='homekit_mqtt',
    packages=find_packages(include=['homekit_mqtt']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/titus-leistner/homekit_mqtt',
    version='0.1.9',
    zip_safe=False,
    package_dir={'homekit_mqtt': 'homekit_mqtt'},
    package_data={'homekit_mqtt': ['data/*']},
)
