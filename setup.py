# -*- coding: utf-8 -*-
#
# android_build setup script
#
# Copyright (C) 2018 Sathya Kuppuswamy
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# @Author  : Sathya Kupppuswamy(sathyaosid@gmail.com)
# @History :
#            @v0.0 - Initial update
# @TODO    :
#
#

from setuptools import setup
import os

this_directory = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_directory, 'README.rst')) as f:
    readme = f.read()

with open(os.path.join(this_directory, 'LICENSE')) as f:
    license = f.read()

setup(name='android_build',
      version='0.2',
      description='Python support classes fo automating android build/test',
      long_description=readme,
      classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2.7',
        'Topic :: Text Processing :: Linguistic',
      ],
      keywords='python git android autotesting test scripts shell linux',
      url='https://github.com/knsathya/android_build.git',
      author='Kuppuswamy Sathyanarayanan',
      author_email='sathyaosid@gmail.com',
      license='GPLv2',
      packages=['android_build'],
      install_requires=[
          'pyshell',
          'jsonparser',
          'pyyaml'
      ],
      dependency_links=[
          'git+https://github.com/knsathya/pyshell.git#egg=pyshell',
          'git+https://github.com/knsathya/jsonparser.git#egg=jsonparser'
      ],
      test_suite='tests',
      tests_require=[
          ''
      ],
      entry_points={
          'console_scripts': [''],
      },
      include_package_data=True,
      zip_safe=False)
