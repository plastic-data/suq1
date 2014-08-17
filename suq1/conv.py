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


"""Conversion functions"""


from biryani1.base64conv import *
from biryani1.baseconv import *
from biryani1.bsonconv import *
from biryani1.datetimeconv import *
from biryani1.jsonconv import *
from biryani1.objectconv import *
from biryani1.states import default_state, State
from biryani1.uuidconv import *


input_to_words = pipe(
    input_to_slug,
    function(lambda slug: sorted(set(slug.split(u'-')))),
    empty_to_none,
    )


def method(method_name, *args, **kwargs):
    def method_converter(value, state = None):
        if value is None:
            return value, None
        return getattr(value, method_name)(state or default_state, *args, **kwargs)
    return method_converter
