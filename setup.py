import re
from setuptools import setup


with open('lfixer/__init__.py') as fl:
    makefile_contents = fl.read()
    version_match = re.search(r'__version__ \= \'(.+?)\'\n', makefile_contents)
    version = version_match.group(1)


setup(name='lfixer',
      version=version,
      description='Log Fixer Utility',
      author='mksh',
      author_email='to.catch.a.flying.saucer@gmail.com',
      include_package_data=True,
      url='https://github.com/mksh/lfixer',
      scripts=['bin/log-fixer-healthcheck.sh', 'bin/log-fixer.py'],
      test_suite='lfixer.test',
      packages=['lfixer',])
