import setuptools

with open("README.md", "r", encoding="utf-8") as reader:
    long_description = reader.read()

setuptools.setup(
    name="formsite-util",
    version="1.2.7.1",
    author="Jakub Strnad",
    author_email="jakub.strnad@protonmail.com",
    description="A simple Formsite API python script, used to get results or to download files from your formsite forms.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=["asyncio", "aiofiles", "aiohttp", "openpyxl",
                      "pandas", "python_dateutil", "pytz", "regex", "tqdm"],
    keywords=['python', 'formsite', 'fs', 'api',
              'utility', 'util', 'system', 'rest', 'integration'],
    url="https://github.com/strny0/formsite-utility/",
    project_urls={
        "Bug Tracker": "https://github.com/strny0/formsite-utility/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)"
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "getform=formsite_util.cli:main"
        ]
    }
)
