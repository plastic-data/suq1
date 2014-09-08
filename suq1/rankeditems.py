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


"""Helpers to handle ranked items (ie a list of items sorted by rank; items of the same rank being in the same sublist)
"""


def iter_ranked_items(items):
    if items is not None:
        for rank, same_rank_items in enumerate(items):
            for item in iter_same_rank_items(same_rank_items):
                yield rank, item


def iter_same_rank_items(same_rank_items):
    if same_rank_items is not None:
        if isinstance(same_rank_items, list):
            for item in same_rank_items:
                yield item
        else:
            yield same_rank_items

