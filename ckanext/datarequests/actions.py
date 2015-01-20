# -*- coding: utf-8 -*-

# Copyright (c) 2015 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Data Requests Extension.

# CKAN Data Requests Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Data Requests Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Data Requests Extension. If not, see <http://www.gnu.org/licenses/>.


import ckan.plugins as plugins
import constants
import datetime
import db
import validator

c = plugins.toolkit.c
tk = plugins.toolkit


def _dictize_datarequest(datarequest):
    # Transform time
    open_time = str(datarequest.open_time)
    # Close time can be None and the transformation is only needed when the
    # fields contains a valid date
    close_time = datarequest.close_time
    close_time = str(close_time) if close_time else close_time

    # Convert the data request into a dict
    datarequest = {
        'id': datarequest.id,
        'user_id': datarequest.user_id,
        'title': datarequest.title,
        'description': datarequest.description,
        'organization_id': datarequest.organization_id,
        'open_time': open_time,
        'accepted_dataset': datarequest.accepted_dataset,
        'close_time': close_time,
        'closed': datarequest.closed
    }

    return datarequest


def _undictize_datarequest_basic(data_request, data_dict):
    data_request.title = data_dict['title']
    data_request.description = data_dict['description']
    organization = data_dict['organization_id']
    data_request.organization_id = organization if organization else None


def datarequest_create(context, data_dict):

    model = context['model']
    session = context['session']

    # Init the data base
    db.init_db(model)

    # Check access
    tk.check_access(constants.DATAREQUEST_CREATE, context, data_dict)

    # Validate data
    validator.validate_datarequest(context, data_dict)

    # Store the data
    data_req = db.DataRequest()
    _undictize_datarequest_basic(data_req, data_dict)
    data_req.user_id = context['auth_user_obj'].id
    data_req.open_time = datetime.datetime.now()

    session.add(data_req)
    session.commit()

    return _dictize_datarequest(data_req)


def datarequest_show(context, data_dict):

    model = context['model']
    datarequest_id = data_dict['id']

    # Init the data base
    db.init_db(model)

    # Check access
    tk.check_access(constants.DATAREQUEST_SHOW, context, data_dict)

    # Get the data request
    result = db.DataRequest.get(id=datarequest_id)
    if not result:
        raise tk.ObjectNotFound('Data Request %s not found in the data base' % datarequest_id)

    data_req = result[0]
    return _dictize_datarequest(data_req)


def datarequest_update(context, data_dict):

    model = context['model']
    session = context['session']
    datarequest_id = data_dict['id']

    # Init the data base
    db.init_db(model)

    # Check access
    tk.check_access(constants.DATAREQUEST_UPDATE, context, data_dict)

    # Get the initial data
    result = db.DataRequest.get(id=datarequest_id)
    if not result:
        raise tk.ObjectNotFound('Data Request %s not found in the data base' % datarequest_id)

    data_req = result[0]

    # Avoid the validator to return an error when the user does not change the title
    context['avoid_existing_title_check'] = data_req.title == data_dict['title']

    # Validate data
    validator.validate_datarequest(context, data_dict)

    # Set the data provided by the user in the data_red
    _undictize_datarequest_basic(data_req, data_dict)

    session.add(data_req)
    session.commit()

    return _dictize_datarequest(data_req)


def datarequest_index(context, data_dict):

    model = context['model']
    organization_show = tk.get_action('organization_show')

    # Init the data base
    db.init_db(model)

    # Check access
    tk.check_access(constants.DATAREQUEST_INDEX, context, data_dict)

    # Get the organization
    organization_id = data_dict.get('organization_id', None)
    params = {}
    if organization_id:
        # Get organization ID
        organization_id = organization_show({'ignore_auth': True}, {'id': organization_id}).get('id')

        # Include the organization into the parameters to filter the database query
        params['organization_id'] = organization_id

    # Call the function
    db_datarequests = db.DataRequest.get_ordered_by_date(**params)

    # Dictize the results
    offset = data_dict.get('offset', 0)
    limit = data_dict.get('limit', constants.DATAREQUESTS_PER_PAGE)
    datarequests = []
    for data_req in db_datarequests[offset:offset + limit]:
        datarequests.append(_dictize_datarequest(data_req))

    # Facets
    no_processed_organization_facet = {}
    for data_req in db_datarequests:
        if data_req.organization_id:
            # Facets
            if data_req.organization_id in no_processed_organization_facet:
                no_processed_organization_facet[data_req.organization_id] += 1
            else:
                no_processed_organization_facet[data_req.organization_id] = 1

    # Format facets
    organization_facet = []
    for organization_id in no_processed_organization_facet:
        organization = organization_show({'ignore_auth': True}, {'id': organization_id})
        organization_facet.append({
            'name': organization.get('name'),
            'display_name': organization.get('display_name'),
            'count': no_processed_organization_facet[organization_id]
        })

    return {
        'count': len(db_datarequests),
        'facets': {
            'organization': {
                'items': organization_facet
            }
        },
        'result': datarequests
    }
