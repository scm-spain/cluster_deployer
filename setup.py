from setuptools import setup

setup(
    name='deployer',
    version='0.0.1',
    description='Python module to deploy microservices.',
    author='Schibsted Spain',
    author_email='ferran.grau@scmspain.com',
    packages=['deployer'],
    install_requires=['boto', 'requests'],
)
