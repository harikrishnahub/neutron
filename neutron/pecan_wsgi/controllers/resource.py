# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging
import pecan
from pecan import request

from neutron._i18n import _LW
from neutron import manager
from neutron.pecan_wsgi.controllers import utils


LOG = logging.getLogger(__name__)


class ItemController(utils.NeutronPecanController):

    def __init__(self, resource, item, plugin=None, resource_info=None):
        super(ItemController, self).__init__(None, resource, plugin=plugin,
                                             resource_info=resource_info)
        self.item = item

    @utils.expose(generic=True)
    def index(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get(self, *args, **kwargs):
        neutron_context = request.context['neutron_context']
        fields = request.context['query_params'].get('fields')
        return {self.resource: self.plugin_shower(neutron_context, self.item,
                                                  fields=fields)}

    @utils.when(index, method='HEAD')
    @utils.when(index, method='POST')
    @utils.when(index, method='PATCH')
    def not_supported(self):
        pecan.abort(405)

    @utils.when(index, method='PUT')
    def put(self, *args, **kwargs):
        neutron_context = request.context['neutron_context']
        resources = request.context['resources']
        # TODO(kevinbenton): bulk?
        # Bulk update is not supported, 'resources' always contains a single
        # elemenet
        data = {self.resource: resources[0]}
        return {self.resource: self.plugin_updater(neutron_context,
                                                   self.item, data)}

    @utils.when(index, method='DELETE')
    def delete(self):
        # TODO(kevinbenton): setting code could be in a decorator
        pecan.response.status = 204
        neutron_context = request.context['neutron_context']
        return self.plugin_deleter(neutron_context, self.item)

    @utils.expose()
    def _lookup(self, collection, *remainder):
        request.context['collection'] = collection
        controller = manager.NeutronManager.get_controller_for_resource(
            collection)
        if not controller:
            LOG.warning(_LW("No controller found for: %s - returning response "
                         "code 404"), collection)
            pecan.abort(404)
        return controller, remainder


class CollectionsController(utils.NeutronPecanController):

    item_controller_class = ItemController

    @utils.expose()
    def _lookup(self, item, *remainder):
        # Store resource identifier in request context
        request.context['resource_id'] = item
        uri_identifier = '%s_id' % self.resource
        request.context['uri_identifiers'][uri_identifier] = item
        return (self.item_controller_class(
            self.resource, item, resource_info=self.resource_info),
                remainder)

    @utils.expose(generic=True)
    def index(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get(self, *args, **kwargs):
        # NOTE(blogan): query_params is set in the QueryParametersHook
        query_params = request.context['query_params']
        neutron_context = request.context['neutron_context']
        return {self.collection: self.plugin_lister(neutron_context,
                **query_params)}

    @utils.when(index, method='HEAD')
    @utils.when(index, method='PATCH')
    @utils.when(index, method='PUT')
    @utils.when(index, method='DELETE')
    def not_supported(self):
        pecan.abort(405)

    @utils.when(index, method='POST')
    def post(self, *args, **kwargs):
        # TODO(kevinbenton): emulated bulk!
        resources = request.context['resources']
        pecan.response.status = 201
        return self.create(resources)

    def create(self, resources):
        if len(resources) > 1:
            # Bulk!
            creator = self.plugin_bulk_creator
            key = self.collection
            data = {key: [{self.resource: res} for res in resources]}
        else:
            creator = self.plugin_creator
            key = self.resource
            data = {key: resources[0]}
        neutron_context = request.context['neutron_context']
        return {key: creator(neutron_context, data)}
