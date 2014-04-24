# -*- coding: utf-8 -
import sys
from setuptools import setup

requirements = [
    'python-daemon==1.6',
    'lockfile==0.9.1'
]

if sys.version_info < (2, 7):
    requirements.extend([
        'argparse==1.2.1'
    ])


setup(name='daemon-runner',
      version='0.0.15',
      description='Simple command line runner on top of python-daemon',
      author='HubSpot Developers',
      author_email='dev@hubspot.com',
      url='http://www.hubspot.com',
      zip_safe=False,
      include_package_data=True,
      install_requires=requirements,
      py_modules=['daemon_runner'],
      platforms=['any'],
      entry_points={
          'console_scripts': ['daemon-runner=daemon_runner:main'],
      })
