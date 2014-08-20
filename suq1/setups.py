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


"""Helpers to handle setups and upgrades"""


import collections
import imp
import os

from . import accesses, contexts, middlewares, objects, urls, wsgihelpers
from .controllers import accesses as controllers_accesses


__all__ = [
    'configure',
    'init',
    'init_module',
    'setup',
    'Status',
    ]

model = None  # from ??? import model


class Status(objects.Mapper, objects.Wrapper):
    collection_name = 'status'
    last_upgrade_name = None


def configure(ctx):
    urls.application_url = ctx.req.application_url


def init(components):
    init_module(components)

    accesses.init_module(components)
    contexts.init_module(components)
    controllers_accesses.init_module(components)
    middlewares.init_module(components)
    objects.init_module(components)
    urls.init_module(components)
    wsgihelpers.init_module(components)


def init_module(components):
    global model
    model = components['model']


def setup(drop_indexes = False, upgrades_dir = None):
    """Setup MongoDb database."""

    if upgrades_dir is not None:
        upgrades_name = sorted(
            os.path.splitext(upgrade_filename)[0]
            for upgrade_filename in os.listdir(upgrades_dir)
            if upgrade_filename.endswith('.py') and upgrade_filename != '__init__.py'
            )
        status = Status.find_one(as_class = collections.OrderedDict)
        if status is None:
            status = Status()
            if upgrades_name:
                status.last_upgrade_name = upgrades_name[-1]
            status.save()
        else:
            for upgrade_name in upgrades_name:
                if status.last_upgrade_name is None or status.last_upgrade_name < upgrade_name:
                    print 'Upgrading "{0}"'.format(upgrade_name)
                    upgrade_file, upgrade_file_path, description = imp.find_module(upgrade_name, [upgrades_dir])
                    try:
                        upgrade_module = imp.load_module(upgrade_name, upgrade_file, upgrade_file_path, description)
                    finally:
                        if upgrade_file:
                            upgrade_file.close()
                    upgrade_module.upgrade(status)

    if drop_indexes:
        db = objects.Wrapper.db
        for collection_name in db.collection_names():
            if not collection_name.startswith('system.'):
                db[collection_name].drop_indexes()

