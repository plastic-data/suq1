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


"""Models for access, account & client classes"""


import calendar
import collections
import datetime

import pymongo

from . import objects


__all__ = [
    'Access',
    'Account',
    'AuthenticationSession',
    'Client',
    'init_module',
    ]

conv = None  # from ??? import conv
model = None  # from ??? import model


class Access(objects.Initable, objects.JsonMonoClassMapper, objects.Mapper, objects.ActivityStreamWrapper):
    _account = UnboundLocalError
    _client = UnboundLocalError
    account_id = None
    blocked = False
    client_id = None
    collection_name = 'access'
    expiration = None
    token = None

    @property
    def account(self):
        if self._account is UnboundLocalError:
            self._account = model.Account.find_one(self.account_id, as_class = collections.OrderedDict) \
                if self.account_id is not None \
                else None
        return self._account

    @property
    def client(self):
        if self._client is UnboundLocalError:
            self._client = model.Client.find_one(self.client_id, as_class = collections.OrderedDict) \
                if self.client_id is not None \
                else None
        return self._client

    @classmethod
    def ensure_indexes(cls):
        cls.ensure_index('account_id')
        cls.ensure_index('client_id')
        cls.ensure_index('expiration')
        cls.ensure_index('token', unique = True)

    @classmethod
    def make_token_to_instance(cls):
        def token_to_instance(value, state = None):
            if value is None:
                return value, None
            if state is None:
                state = conv.default_state

            # First, delete expired instances.
            cls.remove_expired(state)

            self = cls.find_one(
                dict(
                    token = value,
                    ),
                as_class = collections.OrderedDict,
                )
            if self is None:
                return value, state._(u"No access with given token")
            if self.blocked:
                return self, state._(u"Access is blocked")
            return self, None

        return token_to_instance

    @classmethod
    def remove_expired(cls, ctx):
        for self in cls.find(
                dict(expiration = {'$lt': datetime.datetime.utcnow()}),
                as_class = collections.OrderedDict,
                ):
            self.delete(ctx)

    def require_account_access(self, state):
        if self.account_id is None:
            return self, state._(u"Expected an access token. Got a client token")
        return self, None

    def require_client_access(self, state):
        if self.account_id is not None:
            return self, state._(u"Expected a client token. Got an access token")
        return self, None

    def to_bson(self):
        self_bson = self.__dict__.copy()
        self_bson.pop('_account', None)
        self_bson.pop('_client', None)
        return self_bson

    def turn_to_json_attributes(self, state):
        value, error = conv.object_to_clean_dict(self, state = state)
        if error is not None:
            return value, error
        if value.get('account_id') is not None:
            value['account_id'] = unicode(value['account_id'])
        if value.get('client_id') is not None:
            value['client_id'] = unicode(value['client_id'])
        if value.get('draft_id') is not None:
            value['draft_id'] = unicode(value['draft_id'])
        if value.get('expiration') is not None:
            value['expiration'] = int(calendar.timegm(value['expiration'].timetuple()) * 1000)
        id = value.pop('_id', None)
        if id is not None:
            value['id'] = unicode(id)
        if value.get('published') is not None:
            value['published'] = int(calendar.timegm(value['published'].timetuple()) * 1000)
        if value.get('updated') is not None:
            value['updated'] = int(calendar.timegm(value['updated'].timetuple()) * 1000)
        return value, None


class Account(objects.Initable, objects.JsonMonoClassMapper, objects.Mapper, objects.ActivityStreamWrapper):
    blocked = False
    collection_name = 'accounts'
    email = None
    email_verified = None  # Datetime of last email verification
    full_name = None
    url_name = None

    def before_delete(self, ctx, old_bson):
        for access in model.Access.find(dict(account_id = self._id), as_class = collections.OrderedDict):
            access.delete(ctx)

    def compute_attributes(self):
        url_name = conv.check(conv.input_to_url_name)(self.full_name)
        if url_name is None:
            if self.url_name is not None:
                del self.url_name
        else:
            self.url_name = url_name

        self.words = sorted(set(strings.slugify(u'-'.join(
            fragment
            for fragment in (
                unicode(self._id),
                self.email,
                self.full_name,
                )
            if fragment is not None
            )).split(u'-'))) or None

        return self

    @classmethod
    def ensure_indexes(cls):
        cls.ensure_index('email', unique = True)
#        cls.ensure_index('updated')
        cls.ensure_index('url_name', sparse = True)
        cls.ensure_index('words')

#    @classmethod
#    def make_access_token_to_instance(cls):
#        def access_token_to_instance(value, state = None):
#            if value is None:
#                return value, None
#            if state is None:
#                state = conv.default_state
#            access = Access.make_token_to_instance(value, state = state)
#            if access is None:
#                return value, state._(u"No access with given token")
#            self = cls.find_one(access.account_id, as_class = collections.OrderedDict)
#            if self is None:
#                return value, state._(u"No account with given access token")
#            return self, None

#        return access_token_to_instance

    @classmethod
    def make_str_to_instance(cls):
        def str_to_instance(value, state = None):
            if value is None:
                return value, None
            if state is None:
                state = conv.default_state
            id, error = conv.str_to_object_id(value, state = state)
            if id is not None and error is None:
                self = cls.find_one(id, as_class = collections.OrderedDict)
                if self is None:
                    return id, state._(u"No account with given ID")
            else:
                email, error = conv.str_to_email(value, state = state)
                if email is None or error is not None:
                    return email, error
                self = cls.find_one(dict(email = email), as_class = collections.OrderedDict)
                if self is None:
                    return email, state._(u"No account with given email")
            return self, None

        return str_to_instance

    def turn_to_json_attributes(self, state):
        value, error = conv.object_to_clean_dict(self, state = state)
        if error is not None:
            return value, error
        if value.get('draft_id') is not None:
            value['draft_id'] = unicode(value['draft_id'])
        if value.get('email_verified') is not None:
            value['email_verified'] = int(calendar.timegm(value['email_verified'].timetuple()) * 1000)
        id = value.pop('_id', None)
        if id is not None:
            value['id'] = unicode(id)
        if value.get('published') is not None:
            value['published'] = int(calendar.timegm(value['published'].timetuple()) * 1000)
        if value.get('updated') is not None:
            value['updated'] = int(calendar.timegm(value['updated'].timetuple()) * 1000)
        value.pop('words', None)
        return value, None


class AuthenticationSession(objects.Initable, objects.JsonMonoClassMapper, objects.Mapper, objects.SmartWrapper):
    _client = UnboundLocalError
    client_id = None
    collection_name = 'authentication_sessions'
    expiration = None
    synchronizer_token = None  # the UI session anti CSRF token
    token = None  # the cookie token

    @property
    def client(self):
        if self._client is UnboundLocalError:
            self._client = model.Client.find_one(self.client_id, as_class = collections.OrderedDict) \
                if self.client_id is not None \
                else None
        return self._client

    @classmethod
    def ensure_indexes(cls):
        cls.ensure_index('expiration')
        cls.ensure_index('token', unique = True)

    @classmethod
    def remove_expired(cls, ctx):
        for self in cls.find(
                dict(expiration = {'$lt': datetime.datetime.utcnow()}),
                as_class = collections.OrderedDict,
                ):
            self.delete(ctx)

    def to_bson(self):
        self_bson = self.__dict__.copy()
        self_bson.pop('_client', None)
        return self_bson

    @classmethod
    def token_to_instance(cls, value, state = None):
        if value is None:
            return value, None
        if state is None:
            state = conv.default_state

        # First, delete expired instances.
        cls.remove_expired(state)

        self = cls.find_one(dict(token = value), as_class = collections.OrderedDict)
        if self is None:
            return value, state._(u"No session with UUID {0}").format(value)
        return self, None


class Client(objects.Initable, objects.JsonMonoClassMapper, objects.Mapper, objects.ActivityStreamWrapper):
    blocked = False
    collection_name = 'clients'
    name = None
    owner_id = None
    symbol = None
    token = None
    url_name = None

    def before_delete(self, ctx, old_bson):
        for access in Access.find(dict(client_id = self._id), as_class = collections.OrderedDict):
            access.delete(ctx)

    def compute_attributes(self):
        url_name = conv.check(conv.input_to_url_name)(self.name)
        if url_name is None:
            if self.url_name is not None:
                del self.url_name
        else:
            self.url_name = url_name

        self.words = sorted(set(strings.slugify(u'-'.join(
            fragment
            for fragment in (
                unicode(self._id),
                self.name,
                )
            if fragment is not None
            )).split(u'-'))) or None

        return self

    @classmethod
    def ensure_indexes(cls):
        cls.ensure_index('symbol', sparse = True, unique = True)
        cls.ensure_index('token', unique = True)
        cls.ensure_index([('owner_id', pymongo.ASCENDING), ('url_name', pymongo.ASCENDING)], unique = True)
        cls.ensure_index('words')

    @classmethod
    def make_str_to_instance(cls):
        def str_to_instance(value, state = None):
            if value is None:
                return value, None
            if state is None:
                state = conv.default_state
            id, error = conv.str_to_object_id(value, state = state)
            if id is None or error is not None:
                return id, error
            self = cls.find_one(id, as_class = collections.OrderedDict)
            if self is None:
                return id, state._(u"No client with given ID")
            return self, None

        return str_to_instance

#    @classmethod
#    def make_token_to_instance(cls):
#        def token_to_instance(value, state = None):
#            if value is None:
#                return value, None
#            if state is None:
#                state = conv.default_state
#            self = cls.find_one(
#                dict(
#                    token = value,
#                    ),
#                as_class = collections.OrderedDict,
#                )
#            if self is None:
#                return value, state._(u"No client with given token")
#            if self.blocked:
#                return self, state._(u"Client is blocked")
#            return self, None

#        return token_to_instance

    def turn_to_json_attributes(self, state):
        value, error = conv.object_to_clean_dict(self, state = state)
        if error is not None:
            return value, error
        if value.get('draft_id') is not None:
            value['draft_id'] = unicode(value['draft_id'])
        id = value.pop('_id', None)
        if id is not None:
            value['id'] = unicode(id)
        value['owner_id'] = unicode(value['owner_id'])
        if value.get('published') is not None:
            value['published'] = int(calendar.timegm(value['published'].timetuple()) * 1000)
        if value.get('updated') is not None:
            value['updated'] = int(calendar.timegm(value['updated'].timetuple()) * 1000)
        value.pop('words', None)
        return value, None


def init_module(components):
    global conv
    conv = components['conv']
    global model
    model = components['model']

