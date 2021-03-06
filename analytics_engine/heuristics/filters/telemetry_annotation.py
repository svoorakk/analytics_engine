# Copyright (c) 2017, Intel Research and Development Ireland Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'Giuliana Carullo, Vincenzo Riccobene'
__copyright__ = "Copyright (c) 2017, Intel Research and Development Ireland Ltd."
__license__ = "Apache 2.0"
__maintainer__ = "Giuliana Carullo"
__email__ = "giuliana.carullo@intel.com"
__status__ = "Development"

import pandas
from analytics_engine import common
from analytics_engine.heuristics.beans.infograph import \
    InfoGraphNode, InfoGraphUtilities, InfoGraphNodeType, InfoGraphNodeLayer
from analytics_engine.heuristics.infrastructure.telemetry.snap_telemetry.snap_graph_telemetry import SnapAnnotation
from analytics_engine.heuristics.infrastructure.telemetry.prometheus.prometheus_annotation import PrometheusAnnotation
from analytics_engine.heuristics.infrastructure.telemetry.snap_telemetry.snap_utils import SnapUtils
from analytics_engine.utilities import misc

LOG = common.LOG

class TelemetryAnnotation(object):

    SUPPORTED_TELEMETRY_SYSTEMS = ['snap', 'prometheus', 'local']

    def __init__(self,
                 server_ip="",
                 server_port="",
                 telemetry_system='snap'):

        if telemetry_system not in self.SUPPORTED_TELEMETRY_SYSTEMS:
            raise ValueError("Telemetry system {} is not supported".
                             format(telemetry_system))

        if telemetry_system == "snap":
            self.telemetry = SnapAnnotation()
        elif telemetry_system == "prometheus":
            self.telemetry = PrometheusAnnotation()
        else:
            self.telemetry = None

    def get_annotated_graph(self,
                            graph,
                            ts_from,
                            ts_to,
                            utilization=False,
                            saturation = False):
        """
        Collect data from cimmaron tsdb in relation to the specified graph and
         time windows and store an annotated subgraph in specified directory

        :param graph: (NetworkX Graph) Graph to be annotated with data
        :param ts_from: (str) Epoch time representation of start time
        :param ts_to: (str) Epoch time representation of stop time
        :param utilization: (bool) if True the method calculates also
                                    utilization for each node, if available
        :return: NetworkX Graph annotated with telemetry data
        """
        TelemetryAnnotation._get_annotated_graph_input_validation(
            graph, ts_from, ts_to)
        internal_graph = graph.copy()
        self.internal_graph = internal_graph
        for node in internal_graph.nodes(data=True):
            if isinstance(self.telemetry, SnapAnnotation):
                queries = list()
                try:
                    queries = self.telemetry.get_queries(internal_graph, node, ts_from, ts_to)
                    # queries = self.telemetry.get_queries(graph, node, ts_from, ts_to)
                except Exception as e:
                    LOG.error("Exception: {}".format(e))
                    LOG.error(e)
                    import traceback
                    traceback.print_exc()
                if len(queries) != 0:
                    InfoGraphNode.set_queries(node, queries)

                    telemetry_data = self.telemetry.get_data(node)
                    InfoGraphNode.set_telemetry_data(node, telemetry_data)
                    if utilization and not telemetry_data.empty:
                        SnapUtils.utilization(internal_graph, node, self.telemetry)
                        # if only procfs is available, results needs to be
                        # propagated at machine level
                        if InfoGraphNode.get_type(node) == InfoGraphNodeType.PHYSICAL_PU:
                            SnapUtils.annotate_machine_pu_util(internal_graph, node)
                        if InfoGraphNode.node_is_disk(node):
                            SnapUtils.annotate_machine_disk_util(internal_graph, node)
                        if InfoGraphNode.node_is_nic(node):
                            SnapUtils.annotate_machine_network_util(internal_graph, node)
                    if saturation:
                        SnapUtils.saturation(internal_graph, node, self.telemetry)
            elif isinstance(self.telemetry, PrometheusAnnotation):
                queries = list()
                try:
                    queries = self.telemetry.get_queries(internal_graph, node, ts_from, ts_to)
                    # queries = self.telemetry.get_queries(graph, node, ts_from, ts_to)
                except Exception as e:
                    LOG.error("Exception: {}".format(e))
                    LOG.error(e)
                    import traceback
                    traceback.print_exc()
                if len(queries) != 0:
                    InfoGraphNode.set_queries(node, queries)

                    telemetry_data = self.telemetry.get_data(node)
                    InfoGraphNode.set_telemetry_data(node, telemetry_data)
                    # if utilization and not telemetry_data.empty:
                        #PrometheusUtils.utilization(internal_graph, node, self.telemetry)
                        # if only procfs is available, results needs to be
                            # propagated at machine level
                        #if InfoGraphNode.get_type(node) == InfoGraphNodeType.PHYSICAL_PU:
                        #    PrometheusUtils.annotate_machine_pu_util(internal_graph, node)
                        #if InfoGraphNode.node_is_disk(node):
                        #    PrometheusUtils.annotate_machine_disk_util(internal_graph, node)
                        #if InfoGraphNode.node_is_nic(node):
                        #    PrometheusUtils.annotate_machine_network_util(internal_graph, node)
                    #if saturation:
                        #PrometheusUtils.saturation(internal_graph, node, self.telemetry)
            else:
                telemetry_data = self.telemetry.get_data(node)
                InfoGraphNode.set_telemetry_data(node, telemetry_data)
                if utilization and not telemetry_data.empty:
                    SnapUtils.utilization(internal_graph, node, self.telemetry)
                    # if only procfs is available, results needs to be
                    # propagated at machine level
                    if InfoGraphNode.get_type(node) == InfoGraphNodeType.PHYSICAL_PU:
                        source = InfoGraphNode.get_machine_name_of_pu(node)
                        machine = InfoGraphNode.get_node(internal_graph, source)
                        machine_util = InfoGraphNode.get_compute_utilization(machine)
                        if '/intel/use/compute/utilization' not in machine_util.columns:
                            sum_util = None
                            pu_util = InfoGraphNode.get_compute_utilization(node)[
                                    'intel/procfs/cpu/utilization_percentage']
                            pu_util = pu_util.fillna(0)
                            if 'intel/procfs/cpu/utilization_percentage' in machine_util.columns:

                                machine_util = machine_util['intel/procfs/cpu/utilization_percentage']
                                machine_util = machine_util.fillna(0)
                                sum_util = machine_util.add(pu_util, fill_value=0)
                            else:
                                sum_util = pu_util
                            if isinstance(sum_util, pandas.Series):
                                # sum_util.index.name = None
                                sum_util = pandas.DataFrame(sum_util, columns=['intel/procfs/cpu/utilization_percentage'])
                            InfoGraphNode.set_compute_utilization(machine, sum_util)
                        else:
                            LOG.debug('Found use for node {}'.format(InfoGraphNode.get_name(node)))
                if saturation:
                    self._saturation(internal_graph, node, self.telemetry)
        return internal_graph

    @staticmethod
    def get_pandas_df_from_graph(graph, metrics='all'):
        return TelemetryAnnotation._create_pandas_data_frame_from_graph(
            graph, metrics)

    @staticmethod
    def export_graph_metrics(graph,
                             destination_file_name='./graph_metrics.csv',
                             mode='csv',
                             metrics='all'):
        supported_modes = ['csv']
        supported_metrics = ['all', 'utilization', 'saturation']

        if mode not in supported_modes:
            raise ValueError("Mode {} not supported. "
                             "Supported modes are: {}".
                             format(mode, supported_modes))

        if metrics not in supported_metrics:
            raise ValueError("Metrics {} not supported. "
                             "Supported modes are: {}".
                             format(metrics, supported_metrics))

        if mode == 'csv':
            TelemetryAnnotation._export_graph_metrics_as_csv(
                graph, destination_file_name, metrics)

    @staticmethod
    def _create_pandas_data_frame_from_graph(graph, metrics='all'):
        """
        Save on csv files the data in the graph.
        Stores one csv per node of the graph

        :param graph: (NetworkX Graph) Graph to be annotated with data
        :param directory: (str) directory where to store csv files
        :return: NetworkX Graph annotated with telemetry data
        """
        result = pandas.DataFrame()
        for node in graph.nodes(data=True):
            node_name = InfoGraphNode.get_name(node)
            node_layer = InfoGraphNode.get_layer(node)
            node_type = InfoGraphNode.get_type(node)

            if node_type == 'vm':
                node_attrs = InfoGraphNode.get_attributes(node)
                node_name = node_attrs['vm_name'] if node_attrs.get('vm_name') else node_name

            # This method supports export of either normal metrics coming
            #  from telemetry agent or utilization type of metrics.
            if metrics == 'all':
                node_telemetry_data = InfoGraphNode.get_telemetry_data(node)
            else:
                node_telemetry_data = InfoGraphNode.get_utilization(node)
            # df = node_telemetry_data.copy()

            # LOG.info("Node Name: {} -- Telemetry: {}".format(
            #     InfoGraphNode.get_name(node),
            #     InfoGraphNode.get_telemetry_data(node).columns.values
            # ))
            if isinstance(node_telemetry_data, pandas.DataFrame):
                if node_telemetry_data.empty:
                    continue
                node_telemetry_data = node_telemetry_data.reset_index()
            else:
                continue
            node_telemetry_data['timestamp'] = node_telemetry_data['timestamp'].astype(
                float)
            node_telemetry_data['timestamp'] = node_telemetry_data['timestamp'].round()
            node_telemetry_data['timestamp'] = node_telemetry_data['timestamp'].astype(
                int)
            renames = {}
            for metric_name in node_telemetry_data.columns.values:
                if metric_name == 'timestamp':
                    continue
                col_name = "{}@{}@{}@{}".\
                    format(node_name, node_layer, node_type, metric_name)
                col_name = col_name.replace(".", "_")
                renames[metric_name] = col_name
            node_telemetry_data = node_telemetry_data.rename(
                columns=renames)

                # LOG.info("TELEMETRIA: {}".format(node_telemetry_data.columns.values))

            if node_telemetry_data.empty or len(node_telemetry_data.columns) <= 1:
                continue
            if result.empty:
                result = node_telemetry_data.copy()
            else:
                node_telemetry_data = \
                    node_telemetry_data.drop_duplicates(subset='timestamp')
                result = pandas.merge(result, node_telemetry_data, how='outer',
                                      on='timestamp')
            # TODO: Try with this removed
            # result.set_index(['timestamp'])
        return result

    @staticmethod
    def get_metrics(graph, metrics='all'):
        """
        Returns all the metrics associated with the input graph
        :param graph: (NetworkX Graph) Graph to be annotated with data
        :param metrics: metric type to be considered. default = all
        :return: the list of metrics associated with the graph
        """
        metric_list = []
        for node in graph.nodes(data=True):
            node_name = InfoGraphNode.get_name(node)
            node_layer = InfoGraphNode.get_layer(node)
            node_type = InfoGraphNode.get_type(node)
            # This method supports export of either normal metrics coming
            #  from telemetry agent or utilization type of metrics.
            if metrics == 'all':
                node_telemetry_data = InfoGraphNode.get_telemetry_data(node)
            else:
                node_telemetry_data = InfoGraphNode.get_utilization(node)

            metric_list.extend(["{}@{}@{}@{}".format(node_name, node_layer, node_type, metric_name).replace(".", "_")
                                for metric_name in node_telemetry_data.columns.values
                                if metric_name != 'timestamp'])
        return metric_list

    @staticmethod
    def _export_graph_metrics_as_csv(graph, file_name, metrics):
        """
        Save on csv files the data in the graph.
        Stores one csv per node of the graph

        :param graph: (NetworkX Graph) Graph to be annotated with data
        :param directory: (str) directory where to store csv files
        :return: NetworkX Graph annotated with telemetry data
        """
        result = TelemetryAnnotation._create_pandas_data_frame_from_graph(
            graph, metrics)
        result.to_csv(file_name, index=False)

    @staticmethod
    def filter_graph(graph):
        """
        Returns the graph filtered removing all the nodes with no telemetry
        """
        template_mapping = dict()

        res = graph.copy()
        for node in res.nodes(data=True):
            # for p in node[1]['attributes']:
            #     p = str(p)
            template = node[1]['attributes']['template'] \
                if 'template' in node[1]['attributes'] else None

            # If node is a service node, need to remove the template
            if template:
                template_mapping[InfoGraphNode.get_name(node)] = template
                node[1]['attributes'].pop('template')

            # Fix format for conversion to JSON (happening in analytics)
            node[1]['attributes'] = \
                str(misc.convert_unicode_dict_to_string(node[1]['attributes'])).\
                    replace("'", '"')

        for node in res.nodes(data=True):
            node_name = InfoGraphNode.get_name(node)
            telemetry = InfoGraphNode.get_telemetry_data(node)
            layer = InfoGraphNode.get_layer(node)
            # if len(telemetry.columns.values) <= 1:

            if len(telemetry.columns) <= 1 and \
                    not layer == InfoGraphNodeLayer.SERVICE:
                InfoGraphNode.set_telemetry_data(node, dict())
                res.filter_nodes('node_name', node_name)

        # Convert attributes back to dict()
        for node in res.nodes(data=True):
            string = InfoGraphNode.get_attributes(node)
            attrs = InfoGraphUtilities.str_to_dict(string)
            if InfoGraphNode.get_type(node) == \
                    InfoGraphNodeType.SERVICE_COMPUTE:
                attrs['template'] = \
                    template_mapping[InfoGraphNode.get_name(node)]
            InfoGraphNode.set_attributes(node, attrs)
        return res

    @staticmethod
    def _get_annotated_graph_input_validation(graph, ts_from, ts_to):
        # TODO - Validate Graph is in the correct format
        return True


