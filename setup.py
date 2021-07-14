"""Module doscstring to make pylint STFU."""

import setuptools
from formsite_util.internal.interfaces import __version__

with open('README.md', 'r', encoding='utf-8') as reader:
    long_description = reader.read()

packages = setuptools.find_packages()

setuptools.setup(
    name='formsite-util',
    version=__version__,
    author='Jakub Strnad',
    author_email='jakub.strnad@protonmail.com',
    description='A simple Formsite API python script to get results and download files from your forms.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=['asyncio', 'aiohttp','requests','colorama', 'dataclasses', 'typing',
                      'pandas', 'python_dateutil', 'pytz', 'regex', 'tqdm', 'prompt_toolkit'],
    keywords=['python', 'formsite', 'fs', 'api', 'automation', 'download', 'form', 'python3',
              'utility', 'util', 'system', 'rest', 'integration', 'links', 'url', 'urls',
              'cli', 'gui', 'py'],
    url='https://github.com/strny0/formsite-utility/',
    project_urls={
        'Bug Tracker': 'https://github.com/strny0/formsite-utility/issues',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Development Status :: 5 - Production/Stable',
        'Topic :: Utilities',
        'Typing :: Typed',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)'
    ],
    packages=packages,
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'getform=formsite_util.terminal_cli:main',
        ]
    }
)
