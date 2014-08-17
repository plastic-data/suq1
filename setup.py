#! /usr/bin/env python
# -*- coding: utf-8 -*-


# Suq1 -- An ad hoc Python toolbox for a web service
# By: Emmanuel Raviart <emmanuel@raviart.com>
#
# Copyright (C) 2009, 2010, 2011, 2012 Easter-eggs & Emmanuel Raviart
# Copyright (C) 2013, 2014 Easter-eggs, Etalab & Emmanuel Raviart
# https://github.com/eraviart/suq1
#
# This file is part of Suq1.
#
# Suq1 is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Suq1 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""An ad hoc Python toolbox for a web service

Suq1 is build for my own specific needs. If you want to improve it for other projects, fork it and rename it.
"""


from setuptools import setup, find_packages


classifiers = """\
Development Status :: 2 - Pre-Alpha
Intended Audience :: Developers
Environment :: Web Environment
License :: OSI Approved :: GNU Affero General Public License v3
Operating System :: POSIX
Programming Language :: Python
Topic :: Internet :: WWW/HTTP :: WSGI :: Server
"""

doc_lines = __doc__.split('\n')


setup(
    name = 'Suq1',
    version = '0.1dev',

    author = 'Emmanuel Raviart',
    author_email = 'emmanuel@raviart.com',
    classifiers = [classifier for classifier in classifiers.split('\n') if classifier],
    description = doc_lines[0],
    keywords = 'service toolbox web',
    license = 'http://www.fsf.org/licensing/licenses/agpl-3.0.html',
    long_description = '\n'.join(doc_lines[2:]),
    url = 'https://github.com/eraviart/suq1',

    data_files = [
        ('share/locale/fr/LC_MESSAGES', ['suq1/i18n/fr/LC_MESSAGES/suq1.mo']),
        ],
    install_requires = [
        'Babel >= 0.9.4',
        'Biryani1 >= 0.9dev',
#        'pymongo >= 2.2',
        'WebError >= 0.10',
        'WebOb >= 1.1',
        ],
    message_extractors = {
        'suq1': [
            ('**.py', 'python', None),
            ],
        },
    packages = find_packages(),
    zip_safe = False,
    )
