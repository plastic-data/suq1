# -*- coding: utf-8 -*-


# ElectData -- Popularity-based data & datasets
# By: Emmanuel Raviart <emmanuel@raviart.com>
#
# Copyright (C) 2014 Emmanuel Raviart
# https://gitorious.org/electdata
#
# This file is part of ElectData.
#
# ElectData is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# ElectData is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""WSGI Middlewares"""


import webob
from weberror.errormiddleware import ErrorMiddleware


conf = None  # from ??? import conf
contexts = None  # from ??? import contexts
model = None  # from ??? import model


def environment_setter(app):
    """WSGI middleware that sets request-dependant environment."""
    def set_environment(environ, start_response):
        req = webob.Request(environ)
        ctx = contexts.Ctx(req)
        model.configure(ctx)
        try:
            return app(req.environ, start_response)
        except webob.exc.WSGIHTTPException as wsgi_exception:
            return wsgi_exception(environ, start_response)

    return set_environment


def init_module(components):
    global conf
    conf = components['conf']
    global contexts
    contexts = components['contexts']
    global model
    model = components['model']


def wrap_app(app):
    """Encapsulate main WSGI application within WSGI middlewares."""
    # Set request-dependant environment.
    app = environment_setter(app)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    # Handle Python exceptions.
    if not conf['debug']:
        app = ErrorMiddleware(app, conf['global_conf'], **conf['errorware'])

    return app

