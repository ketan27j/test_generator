from setuptools import setup, find_packages

setup(
    name="web-page-analyzer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "selenium>=4.15.0",
        "beautifulsoup4>=4.12.0",
        "requests>=2.31.0",
        "webdriver-manager>=4.0.0",
        "lxml>=4.9.0",
        "pillow>=10.0.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A comprehensive web page analyzer for automation testing",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/web-page-analyzer",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)