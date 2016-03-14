from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from setuptools import setup

setup(
    name='deployer',
    version='0.0.2',
    description='Python module to deploy microservices.',
    author='Schibsted Spain',
    author_email='ferran.grau@scmspain.com',
    packages=['deployer'],
    install_requires=['boto', 'requests'],
)
