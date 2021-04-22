import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="formsite_utility-strny",
    version="1.2.6",
    author="Jakub Strnad",
    author_email="jakub.strnad@protonmail.com",
    license="GPL3+",
    description="A simple Formsite API python script, used to get results or to download files from your formsite forms.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/strny0/formsite-utility/",
    project_urls={
        "Bug Tracker": "https://github.com/strny0/formsite-utility/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GPL3+",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=["asyncio","aiofiles","aiohttp","openpyxl","pandas","python_dateutil","pytz","regex","tqdm"],
    entry_points={
        "console_scripts": [
            "getform=formsite_utility.__main__:main",
            "formsite-util=formsite-util.__main__:main"
        ]
    }
)