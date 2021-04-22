import setuptools

with open("README.md", "r", encoding="utf-8") as reader:
    long_description = reader.read()

setuptools.setup(
    name="formsite-util",
    version="1.2.6",
    author="Jakub Strnad",
    author_email="jakub.strnad@protonmail.com",
    license="GPL3+",
    description="A simple Formsite API python script, used to get results or to download files from your formsite forms.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=["asyncio", "aiofiles", "aiohttp", "openpyxl",
                      "pandas", "python_dateutil", "pytz", "regex", "tqdm"],
    keywords=['python', 'formsite', 'fs' 'api',
              'utility', 'system', 'rest', 'integration'],
    url="https://github.com/strny0/formsite-utility/",
    project_urls={
        "Bug Tracker": "https://github.com/strny0/formsite-utility/issues",
    },
    classifiers=[
        "Development Status :: Production",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL3+",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "getform=formsite-util",
            "formsite-util=formsite-util"
        ]
    }
)