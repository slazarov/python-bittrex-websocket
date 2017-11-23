#!/usr/bin/python

from setuptools import setup, find_packages

install_requires = \
    [
        'cfscrape==1.9.0'  # ,
        # 'requests[security]==2.18.4'#,
        # 'signalr-client==0.0.7'
    ]

setup(
    name='bittrex_websocket',
    version='0.0.1',
    author='Stanislav Lazarov',
    author_email='s.a.lazarov@gmail.com',
    license='MIT',
    url='https://github.com/slazarov/python-bittrex-websocket',
    packages=find_packages(exclude=['tests*']),
    install_requires=install_requires,
    description='The unofficial Python websocket client for the Bittrex Cryptocurrency Exchange',
    download_url='https://github.com/slazarov/python-bittrex-websocket.git',
    keywords=['bittrex', 'bittrex-websocket', 'orderbook', 'trade', 'bitcoin', 'ethereum', 'BTC', 'ETH', 'client',
              'websocket', 'exchange', 'crypto', 'currency', 'trading'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
