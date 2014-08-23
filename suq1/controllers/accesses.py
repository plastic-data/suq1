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


"""Controllers for accesses, accounts & clients"""


import calendar
import collections
import datetime
import json
import uuid

import pymongo
import webob
import webob.exc
import ws4py.server.wsgiutils
import ws4py.websocket
import zmq.green as zmq

from .. import urls, wsgihelpers


contexts = None  # from ??? import contexts
conf = None  # from ??? import conf
conv = None  # from ??? import conv
model = None  # from ??? import model


@wsgihelpers.wsgify
def api1_new_authentication_session(req):
    ctx = contexts.Ctx(req)
    headers = wsgihelpers.handle_cross_origin_resource_sharing(ctx)

    assert req.method == 'POST', req.method

    content_type = req.content_type
    if content_type is not None:
        content_type = content_type.split(';', 1)[0].strip()
    if content_type != 'application/json':
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    message = ctx._(u'Bad content-type: {}').format(content_type),
                    ).iteritems())),
                method = req.script_name,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    inputs, error = conv.pipe(
        conv.make_input_to_json(object_pairs_hook = collections.OrderedDict),
        conv.test_isinstance(dict),
        conv.not_none,
        )(req.body, state = ctx)
    if error is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [error],
                    message = ctx._(u'Invalid JSON in request POST body'),
                    ).iteritems())),
                method = req.script_name,
                params = req.body,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    data, errors = conv.struct(
        dict(
            access_token = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_uuid_str,
                model.Access.make_token_to_instance(accept_client = True),
                conv.not_none,
                ),
            ),
        default = conv.noop,
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                context = inputs.get('context'),
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [errors],
                    message = ctx._(u'Bad authentication parameters in request'),
                    ).iteritems())),
                method = req.script_name,
                params = inputs,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    data, errors = conv.struct(
        dict(
            access_token = conv.noop,
            context = conv.test_isinstance(basestring),  # For asynchronous calls
            synchronizer_token = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_uuid_str,
                conv.not_none,
                ),
            ),
        )(data, state = ctx)
    if errors is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                context = inputs.get('context'),
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [errors],
                    message = ctx._(u'Bad parameters in request'),
                    ).iteritems())),
                method = req.script_name,
                params = inputs,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    # First, delete expired authentication sessions.
    model.AuthenticationSession.remove_expired(ctx)

    authentication_session = model.AuthenticationSession(
        client_id = data['access_token'].client_id,
        expiration = datetime.datetime.utcnow() + datetime.timedelta(hours = 4),
        synchronizer_token = data['synchronizer_token'],
        token = unicode(uuid.uuid4()),
        )
    changed = authentication_session.save(ctx, safe = True)

    authentication_session_json = collections.OrderedDict(sorted(dict(
#        client_id = unicode(authentication_session.client_id),
        expiration = int(calendar.timegm(authentication_session.expiration.timetuple()) * 1000
            + authentication_session.expiration.microsecond / 1000.0),
        token = authentication_session.token,
        url = u'{}?client_id={}&state={}'.format(conf['weotu.authentication_url'], conf['weotu.id'],
            authentication_session.token),
        websocket_url = urls.get_full_url(ctx, u'ws/1/authentication', token = authentication_session.token).replace(
            u'http', u'ws', 1),
        ).iteritems()))
    if changed:
        model.zmq_sender.send_multipart([
            'v1/new_authentication_session/',
            unicode(json.dumps(
                authentication_session_json,
                encoding = 'utf-8',
                ensure_ascii = False,
                indent = 2,
                )).encode('utf-8'),
            ])
    return wsgihelpers.respond_json(ctx,
        collections.OrderedDict(sorted(dict(
            apiVersion = '1.0',
            authentication_session = authentication_session_json,
            context = data['context'],
            method = req.script_name,
            params = inputs,
            url = req.url.decode('utf-8'),
            ).iteritems())),
        headers = headers,
        )


@wsgihelpers.wsgify
def api1_upsert_access(req):
    ctx = contexts.Ctx(req)
    headers = wsgihelpers.handle_cross_origin_resource_sharing(ctx)

    assert req.method == 'POST', req.method

    content_type = req.content_type
    if content_type is not None:
        content_type = content_type.split(';', 1)[0].strip()
    if content_type != 'application/json':
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    message = ctx._(u'Bad content-type: {}').format(content_type),
                    ).iteritems())),
                method = req.script_name,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    inputs, error = conv.pipe(
        conv.make_input_to_json(object_pairs_hook = collections.OrderedDict),
        conv.test_isinstance(dict),
        conv.not_none,
        )(req.body, state = ctx)
    if error is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [error],
                    message = ctx._(u'Invalid JSON in request POST body'),
                    ).iteritems())),
                method = req.script_name,
                params = req.body,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    data, errors = conv.struct(
        dict(
            access_token = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_uuid_str,
                model.Access.make_token_to_instance(accept_client = True),
                conv.not_none,
                ),
            account = conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_line,
                model.Account.str_to_instance,
                conv.not_none,
                ),
            context = conv.test_isinstance(basestring),  # For asynchronous calls
            ),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                context = inputs.get('context'),
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [errors],
                    message = ctx._(u'Bad parameters in request'),
                    ).iteritems())),
                method = req.script_name,
                params = inputs,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    account = data['account']
    client = data['access_token'].client
    access = model.Access.find_one(
        dict(
            account_id = account._id,
            blocked = {'$exists': False},
            client_id = client._id,
            expiration = {'$exists': False},
            ),
        as_class = collections.OrderedDict)
    if access is None:
        access = model.Access(
            account_id = account._id,
            client_id = client._id,
            token = unicode(uuid.uuid4()),
            )
        changed = access.save(ctx, safe = True)
    else:
        changed = False
    access._account = account
    access._client = client

    access_json = access.to_json()
    if changed:
        model.zmq_sender.send_multipart([
            'v1/new_access/',
            unicode(json.dumps(access_json, encoding = 'utf-8', ensure_ascii = False, indent = 2)).encode('utf-8'),
            ])
    return wsgihelpers.respond_json(ctx,
        collections.OrderedDict(sorted(dict(
            access = access_json,
            apiVersion = '1.0',
            context = data['context'],
            method = req.script_name,
            params = inputs,
            url = req.url.decode('utf-8'),
            ).iteritems())),
        headers = headers,
        )


@wsgihelpers.wsgify
def api1_upsert_client(req):
    ctx = contexts.Ctx(req)
    headers = wsgihelpers.handle_cross_origin_resource_sharing(ctx)

    assert req.method == 'POST', req.method

    content_type = req.content_type
    if content_type is not None:
        content_type = content_type.split(';', 1)[0].strip()
    if content_type != 'application/json':
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    message = ctx._(u'Bad content-type: {}').format(content_type),
                    ).iteritems())),
                method = req.script_name,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    inputs, error = conv.pipe(
        conv.make_input_to_json(object_pairs_hook = collections.OrderedDict),
        conv.test_isinstance(dict),
        conv.not_none,
        )(req.body, state = ctx)
    if error is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [error],
                    message = ctx._(u'Invalid JSON in request POST body'),
                    ).iteritems())),
                method = req.script_name,
                params = req.body,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )
    data, errors = conv.struct(
        dict(
            access_token = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_uuid_str,
                model.Access.make_token_to_instance(accept_account = True, accept_client = True),
                conv.not_none,
                ),
            blocked = conv.pipe(
                conv.test_isinstance((bool, int)),
                conv.anything_to_bool,
                conv.default(False),
                ),
            context = conv.test_isinstance(basestring),  # For asynchronous calls
            name = conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_line,
                conv.not_none,
                ),
            ),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                context = inputs.get('context'),
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [errors],
                    message = ctx._(u'Bad parameters in request'),
                    ).iteritems())),
                method = req.script_name,
                params = inputs,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )

    individual = data['access_token'].individual
    client = model.Client.find_one(
        dict(
            owner_id = individual._id,
            url_name = conv.check(conv.input_to_url_name)(data['name'], state = ctx),
            ),
        as_class = collections.OrderedDict,
        )
    if client is None:
        address = 'v1/new_client/'
        client = model.Client()
    else:
        address = 'v1/update_client/'
    client.set_attributes(
        blocked = data['blocked'],
        name = data['name'],
        owner_id = individual._id,
        )
    client.compute_attributes()
    client_changed = client.save(ctx, safe = True)
    client_json = client.to_json()
    if client_changed:
        model.zmq_sender.send_multipart([
            address,
            unicode(json.dumps(client_json, encoding = 'utf-8', ensure_ascii = False, indent = 2)).encode('utf-8'),
            ])

    access = model.Access.find_one(
        dict(
            account_id = {'$exists': False},
            blocked = {'$exists': False},
            client_id = client._id,
            expiration = {'$exists': False},
            ),
        as_class = collections.OrderedDict,
        )
    if access is None:
        access = model.Access(
            client_id = client._id,
            token = unicode(uuid.uuid4()),
            )
        access_changed = access.save(ctx, safe = True)
    else:
        access_changed = False
    access._account = None
    access._client = client
    access_json = access.to_json()
    if access_changed:
        model.zmq_sender.send_multipart([
            'v1/new_access/',
            unicode(json.dumps(access_json, encoding = 'utf-8', ensure_ascii = False, indent = 2)).encode('utf-8'),
            ])

    return wsgihelpers.respond_json(ctx,
        collections.OrderedDict(sorted(dict(
            apiVersion = '1.0',
            client = client_json,
            context = data['context'],
            method = req.script_name,
            params = inputs,
            token = access.token,
            url = req.url.decode('utf-8'),
            ).iteritems())),
        headers = headers,
        )


def ws1_authentication(environ, start_response):
    req = webob.Request(environ)
    ctx = contexts.Ctx(req)
    try:
        headers = wsgihelpers.handle_cross_origin_resource_sharing(ctx)
    except webob.exc.HTTPException as response:
        return response(environ, start_response)

    assert req.method == 'GET', req.method
    params = req.GET
    inputs = dict(
        token = params.get('token'),
        )

    data, errors = conv.pipe(
        conv.struct(
            dict(
                token = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.input_to_uuid_str,
                    model.AuthenticationSession.token_to_instance,
                    conv.not_none,
                    ),
                ),
            ),
        conv.rename_item('token', 'authentication_session'),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                context = inputs.get('context'),
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [errors],
                    message = ctx._(u'Bad parameters in request'),
                    ).iteritems())),
                method = req.script_name,
                params = inputs,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )(environ, start_response)
    authentication_session = data['authentication_session']

    # Delete authentication session to avoid its reuse (but keep it in RAM).
    authentication_session.delete(ctx, safe = True)

    ws1_authentication_emitter_app = ws4py.server.wsgiutils.WebSocketWSGIApplication(
        handler_cls = type(
            'WS1AuthenticationEmitter{}'.format(authentication_session.token),
            (WS1AuthenticationEmitter,),
            dict(
                authentication_session = authentication_session,
                ctx = ctx,
                ),
            ),
        )
    try:
        return ws1_authentication_emitter_app(environ, start_response)
    except ws4py.server.wsgiutils.HandshakeError as error:
        return wsgihelpers.bad_request(ctx, explanation = ctx._(u'WebSocket Handshake Error: {0}').format(error))(
            environ, start_response)


class WS1AuthenticationEmitter(ws4py.websocket.WebSocket):
    authentication_session = None
    ctx = None

    def opened(self):
        zmq_subscriber = model.zmq_context.socket(zmq.SUB)
        zmq_subscriber.connect(conf['zmq_sub_socket'])
        zmq_subscriber.setsockopt(zmq.SUBSCRIBE, 'v1/authenticated/')

        while not self.terminated:
            address, content = zmq_subscriber.recv_multipart()
            authentication_json = json.loads(content)
            if authentication_json['state'] == self.authentication_session.token:
                # Remove access_token, because browser doesn't have to know it.
                del authentication_json['access_token']
                self.send(unicode(json.dumps(authentication_json, encoding = 'utf-8', ensure_ascii = False,
                    indent = 2)).encode('utf-8'))
                self.close()


def ws1_authentications(environ, start_response):
    req = webob.Request(environ)
    ctx = contexts.Ctx(req)
    try:
        headers = wsgihelpers.handle_cross_origin_resource_sharing(ctx)
    except webob.exc.HTTPException as response:
        return response(environ, start_response)

    content_type = req.content_type
    if content_type is not None:
        content_type = content_type.split(';', 1)[0].strip()
    if content_type == 'application/json':
        inputs, error = conv.pipe(
            conv.make_input_to_json(),
            conv.test_isinstance(dict),
            )(req.body, state = ctx)
        if error is not None:
            return wsgihelpers.respond_json(ctx,
                collections.OrderedDict(sorted(dict(
                    apiVersion = '1.0',
                    error = collections.OrderedDict(sorted(dict(
                        code = 400,  # Bad Request
                        errors = [error],
                        message = ctx._(u'Invalid JSON in request POST body'),
                        ).iteritems())),
                    method = req.script_name,
                    params = req.body,
                    url = req.url.decode('utf-8'),
                    ).iteritems())),
                headers = headers,
                )(environ, start_response)
    else:
        # URL-encoded GET or POST.
        inputs = dict(req.params)

    data, errors = conv.struct(
        dict(
            access_token = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_uuid_str,
                model.Access.make_token_to_instance(accept_client = True),
                conv.not_none,
                ),
            ),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.respond_json(ctx,
            collections.OrderedDict(sorted(dict(
                apiVersion = '1.0',
                context = inputs.get('context'),
                error = collections.OrderedDict(sorted(dict(
                    code = 400,  # Bad Request
                    errors = [errors],
                    message = ctx._(u'Bad parameters in request'),
                    ).iteritems())),
                method = req.script_name,
                params = inputs,
                url = req.url.decode('utf-8'),
                ).iteritems())),
            headers = headers,
            )(environ, start_response)

    # TODO: Check that client can receive accounts.
    client = data['access_token'].client

    ws1_authentications_emitter_app = ws4py.server.wsgiutils.WebSocketWSGIApplication(
        handler_cls = type(
            'WS1AuthenticationsEmitter{}'.format(client._id),
            (WS1AuthenticationsEmitter,),
            dict(
                client_id = client._id,
                ctx = ctx,
                ),
            ),
        )
    try:
        return ws1_authentications_emitter_app(environ, start_response)
    except ws4py.server.wsgiutils.HandshakeError as error:
        return wsgihelpers.bad_request(ctx, explanation = ctx._(u'WebSocket Handshake Error: {0}').format(error))(
            environ, start_response)


class WS1AuthenticationsEmitter(ws4py.websocket.WebSocket):
    client_id = None
    ctx = None

    def opened(self):
        zmq_subscriber = model.zmq_context.socket(zmq.SUB)
        zmq_subscriber.connect(conf['zmq_sub_socket'])
        zmq_subscriber.setsockopt(zmq.SUBSCRIBE, 'v1/authenticated/')

        while not self.terminated:
            address, content = zmq_subscriber.recv_multipart()
            authentication_json = json.loads(content)
            if authentication_json['client_id'] == unicode(self.client_id):
                main_access = model.Access.find_one(
                    dict(
                        client_id = None,
                        token = authentication_json['access_token'],
                        ),
                    as_class = collections.OrderedDict,
                    sort = [('updated', pymongo.DESCENDING)],
                    )
                assert main_access is not None, u'Missing access for authentication: {}'.format(
                    authentication_json).encode('utf-8')
                access = model.Access.find_one(
                    dict(
                        account_id = main_access.account_id,
                        client_id = self.client_id,
                        ),
                    as_class = collections.OrderedDict,
                    sort = [('updated', pymongo.DESCENDING)],
                    )
                if access is None:
                    access = model.Access(
                        account_id = main_access.account_id,
                        client_id = self.client_id,
                        token = unicode(uuid.uuid4()),
                        )
                    access.save(self.ctx, safe = True)
                authentication_json['access_token'] = access.token
                self.send(unicode(json.dumps(authentication_json, encoding = 'utf-8', ensure_ascii = False,
                    indent = 2)).encode('utf-8'))


def init_module(components):
    global contexts
    contexts = components['contexts']
    global conf
    conf = components['conf']
    global conv
    conv = components['conv']
    global model
    model = components['model']

