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


"""Context loaded and saved in WSGI requests"""


import gettext
import os

import pkg_resources
import webob

from . import conv  # Overridden with real conv during init_module().


__all__ = [
    'Ctx',
    'init_module',
    ]


class Ctx(conv.State):
    _parent = None
    default_values = dict(
        _lang = None,
        _translator = None,
        conf = None,
        req = None,
        )
    env_keys = ('_lang', '_translator')
    translators_infos = [
        ('biryani1', os.path.join(pkg_resources.get_distribution('biryani1').location, 'biryani1', 'i18n')),
        ('suq1', os.path.join(pkg_resources.get_distribution('suq1').location, 'suq1', 'i18n')),
        ]

    def __init__(self, req = None):
        if req is not None:
            self.req = req
            ctx_env = req.environ.get(self.conf['package_name'], {})
            for key in object.__getattribute__(self, 'env_keys'):
                value = ctx_env.get(key)
                if value is not None:
                    setattr(self, key, value)

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            parent = object.__getattribute__(self, '_parent')
            if parent is None:
                default_values = object.__getattribute__(self, 'default_values')
                if name in default_values:
                    return default_values[name]
                raise
            return getattr(parent, name)

    @property
    def _(self):
        return self.translator.ugettext

    def blank_req(self, path, environ = None, base_url = None, headers = None, POST = None, **kw):
        env = environ.copy() if environ else {}
        ctx_env = env.setdefault(self.conf['package_name'], {})
        for key in self.env_keys:
            value = getattr(self, key)
            if value is not None:
                ctx_env[key] = value
        return webob.Request.blank(path, environ = env, base_url = base_url, headers = headers, POST = POST, **kw)

    def get_containing(self, name, depth = 0):
        """Return the n-th (n = ``depth``) context containing attribute named ``name``."""
        ctx_dict = object.__getattribute__(self, '__dict__')
        if name in ctx_dict:
            if depth <= 0:
                return self
            depth -= 1
        parent = ctx_dict.get('_parent')
        if parent is None:
            return None
        return parent.get_containing(name, depth = depth)

    def get_inherited(self, name, default = UnboundLocalError, depth = 1):
        ctx = self.get_containing(name, depth = depth)
        if ctx is None:
            if default is UnboundLocalError:
                raise AttributeError('Attribute %s not found in %s' % (name, self))
            return default
        return object.__getattribute__(ctx, name)

    def iter(self):
        yield self
        parent = object.__getattribute__(self, '_parent')
        if parent is not None:
            for ancestor in parent.iter():
                yield ancestor

    def iter_containing(self, name):
        ctx_dict = object.__getattribute__(self, '__dict__')
        if name in ctx_dict:
            yield self
        parent = ctx_dict.get('_parent')
        if parent is not None:
            for ancestor in parent.iter_containing(name):
                yield ancestor

    def iter_inherited(self, name):
        for ctx in self.iter_containing(name):
            yield object.__getattribute__(ctx, name)

    def lang_del(self):
        del self._lang
        package_name = self.conf['package_name']
        if self.req is not None and self.req.environ.get(package_name) is not None \
                and '_lang' in self.req.environ[package_name]:
            del self.req.environ[package_name]['_lang']

    def lang_get(self):
        if self._lang is None:
            self._lang = ['en-US', 'en']
            if self.req is not None:
                self.req.environ.setdefault(self.conf['package_name'], {})['_lang'] = self._lang
        return self._lang

    def lang_set(self, lang):
        self._lang = lang
        package_name = self.conf['package_name']
        if self.req is not None:
            self.req.environ.setdefault(package_name, {})['_lang'] = self._lang
        # Reinitialize translator for new languages.
        if self._translator is not None:
            # Don't del self._translator, because attribute _translator can be defined in a parent.
            self._translator = None
            if self.req is not None and self.req.environ.get(package_name) is not None \
                    and '_translator' in self.req.environ[package_name]:
                del self.req.environ[package_name]['_translator']

    lang = property(lang_get, lang_set, lang_del)

    def new(self, **kwargs):
        ctx = Ctx()
        ctx._parent = self
        for name, value in kwargs.iteritems():
            setattr(ctx, name, value)
        return ctx

    @property
    def parent(self):
        return object.__getattribute__(self, '_parent')

    @property
    def translator(self):
        """Get a valid translator object from one or several languages names."""
        if self._translator is None:
            languages = self.lang
            if not languages:
                return gettext.NullTranslations()
            if not isinstance(languages, list):
                languages = [languages]
            translator = gettext.NullTranslations()
            for name, i18n_dir in object.__getattribute__(self, 'translators_infos'):
                if i18n_dir is not None:
                    translator = new_translator(name, i18n_dir, languages, fallback = translator)
            translator = new_translator(self.conf['package_name'], self.conf['i18n_dir'], languages,
                fallback = translator)
            self._translator = translator
        return self._translator

    @property
    def ungettext(self):
        return self.translator.ungettext


def init_module(components):
    global conv
    conv = components['conv']
    if Ctx.__bases__ != (conv.State,):
        Ctx.__bases__ = (conv.State,)


def new_translator(domain, localedir, languages, fallback = None):
    new = gettext.translation(domain, localedir, fallback = True, languages = languages)
    if fallback is not None:
        new.add_fallback(fallback)
    return new
