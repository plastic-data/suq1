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


import collections
import json


def make_api1_upsert_access(contexts, conv, model, wsgihelpers):
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
                    model.Access.make_token_to_instance(),
                    conv.method('require_client_access'),
                    conv.not_none,
                    ),
                account = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    model.Account.make_str_to_instance(),
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

        client = data['access_token'].client
        access = model.Access.find_one(
            dict(
                account_id = data['account']._id,
                blocked = {'$exists': False},
                client_id = client._id,
                expiration = {'$exists': False},
                ),
            as_class = collections.OrderedDict)
        if access is None:
            access = model.Access(
                account_id = data['account']._id,
                client_id = client._id,
                token = unicode(uuid.uuid4()),
                )
            changed = access.save(ctx, safe = True)
        else:
            changed = False

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

    return api1_upsert_access
