import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'setuptools',
    'pyramid',
    'transaction',
    'repoze.tm2>=1.0b1', # default_commit_veto
    'WebError',
    'WebTest',
    'pyramid_formalchemy',
    'pyramid_beaker',
    'pyramid_rpc',
    'pyramid_skins',
    'pyramid_debugtoolbar',
    'pyramid_zcml',
    'pyramid_exclog',
    'repoze.workflow',
    'python-cjson',
    'repoze.who.plugins.sa',
    'repoze.who-friendlyform',
    'repoze.who<1.9',
    'python-openid>=2.0',
    'zope.interface',
    'por.models',
    'por.gdata',
    'por.trac',
    'jsonrpc',
    'js.jquery_timepicker_addon',
    'js.jqgrid ',
    'fa.bootstrap',
    'xlwt',
    'deform',
    'feedparser',
    'Babel',
    'lingua',
    'profilehooks',
    'velruse',
    'pyramid_mailer',
    'pyramid_fanstatic',
    'js.lesscss',
    'deform_bootstrap',
    'Beaker',
    'js.jquery_datatables==1.8.2',
    'unittest2',
    ]

if sys.version_info[:3] < (2,5,0):
    requires.append('pysqlite')

setup(name='por.dashboard',
      version='1.5.3',
      description='Penelope main package',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        ],
      author='Penelope Team',
      author_email='penelopedev@redturtle.it',
      url='https://getpenelope.github.com',
      keywords='web wsgi bfg pylons pyramid',
      namespace_packages=['por'],
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='por.dashboard',
      install_requires = requires,
      entry_points = """\
      [paste.app_factory]
      main = por.dashboard:main
      [fanstatic.libraries]
      por = por.dashboard.fanstatic_resources:por_library
      deform_library = por.dashboard.fanstatic_resources:deform_library
      deform_bootstrap_library = por.dashboard.fanstatic_resources:deform_bootstrap_library
      """,
      )

