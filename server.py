import argparse
import base64
import logging
import os.path
import sys
import time
import wsgiref.simple_server

import prometheus_client.core
from http.client import HTTPConnection
from tvh.api import HTMLApi

log = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'


class Gauge(prometheus_client.core.GaugeMetricFamily):
    NAMESPACE = 'tvheadend'

    def __init__(self, name, documentation, labels):
        super(Gauge, self).__init__('%s_%s' %
                                    (self.NAMESPACE, name), documentation,
                                    labels=labels)
        self._name = name

    def clone(self):
        return type(self)(self._name, self.documentation, self._labelnames)

class Counter(prometheus_client.core.CounterMetricFamily):
    NAMESPACE = 'tvheadend'

    def __init__(self, name, documentation, labels):
        super(Counter, self).__init__('%s_%s' %
                                      (self.NAMESPACE, name), documentation,
                                      labels=labels)
        self._name = name

    def clone(self):
        return type(self)(self._name, self.documentation, self._labelnames)


class tvheadendCollector(object):
    METRICS = {
        'serverinfo': Gauge('serverinfo',
                            'Information of the TVHeadend server',
                            labels=['server_name', 'sw_version']
        ),
        'network_count': Gauge('network_count',
                               'Total number of networks on this server',
                               labels=[]),
        'network_enabled': Gauge('network_enabled',
                                 'Whether the network is enabled or disabled',
                                 labels=['network_name']),
        'network_muxes': Gauge('network_muxes',
                               'Total number of muxes found on this network',
                               labels=['network_name']),
        'network_services': Gauge('network_services',
                                  'Total number of services found on this network',
                                  labels=['network_name']),
        'network_channels': Gauge('network_channels',
                                  'Total number of mapped channels found on this network',
                                  labels=['network_name']),
        'network_scans': Gauge('network_scans',
                               'The number of muxes left to scan on this network',
                               labels=['network_name']),
        'mux_count': Gauge('mux_count',
                           'Total number of muxes on this server',
                            labels=[]),
        'mux_enabled': Gauge('mux_enabled',
                             'Whether the mux is enabled, disabled or ignored',
                             labels=['network_name', 'mux_name']),
        'mux_scan_state': Gauge('mux_scan_state',
                                'The scan state',
                                labels=['network_name', 'mux_name']),
        'mux_scan_result': Gauge('mux_scan_result',
                                 'The outcome of the last scan performed',
                                 labels=['network_name', 'mux_name']),
        'mux_services': Gauge('mux_services',
                              'Total number of services found',
                              labels=['network_name', 'mux_name']),
        'mux_channels': Gauge('mux_channels',
                              'The number of services currently mapped to channels',
                              labels=['network_name', 'mux_name']),
        'service_count': Gauge('service_count',
                               'Total number of services on this server',
                               labels=[]),
        'service_enabled': Gauge('service_enabled',
                                 'Whether the service is enabled or disabled',
                                  labels=['network_name', 'mux_name', 'service_name']),
        'service_channel_count': Gauge('service_channel_count',
                                       'Total number of channels mapped to this service',
                                       labels=['network_name', 'mux_name', 'service_name']),
        'channel_count': Gauge('channel_count',
                               'Number of channels on the server',
                               labels=[]),
        'channel_enabled': Gauge('channel_enabled',
                                 'Whether the channel is enabled or disabled',
                                  labels=['channel_name']),
        'channel_service_count': Gauge('channel_service_count',
                                       'Total number of services associated to this channel',
                                        labels=['channel_name']),
        'channel_epg_count': Gauge('channel_epg_count',
                                   'Total number of EPG event to this channel',
                                   labels=['channel_name']),
        'epg_count': Gauge('epg_count',
                           'Number of programmes in the EPG',
                           labels=[]),
        'dvr_start_time': Gauge('dvr_start_time',
                                'Start time for DVR Event',
                                labels=["uuid", "channel_name", "programme_title", "status", "username"]),
        'dvr_finish_time': Gauge('dvr_finish_time',
                                 'Finish time for DVR Event',
                                 labels=["uuid", "channel_name", "programme_title", "status", "username"]),
        'dvr_duration': Gauge('dvr_duration',
                              'Duration for DVR Event',
                              labels=["uuid", "channel_name", "programme_title", "status", "username"]),
        'connection_streaming': Gauge('connection_streaming',
                                      'The number of active streams',
                                      labels=["hostname", "type", "username"]),
        'subscription_count': Gauge('subscription_count',
                                    'Number of active subscriptions',
                                    labels=[]),
        'subscription_errors': Gauge('subscription_errors',
                                     'Number of errors occurred sending the stream',
                                     labels=['title', 'state', 'hostname', 'username', 
                                             'client', 'channel_name', 'service', 'profile']),
        'subscription_in': Gauge('subscription_in',
                                 'The input data rate in kb/s',
                                 labels=['title', 'state', 'hostname', 'username', 
                                         'client', 'channel_name', 'service', 'profile']),
        'subscription_out': Gauge('subscription_out',
                                  'The output data rate in kb/s',
                                  labels=['title', 'state', 'hostname', 'username', 
                                          'client', 'channel_name', 'service', 'profile']),
        'subscription_total_in': Counter('subscription_in',
                                         'The total data in kb',
                                          labels=['title', 'state', 'hostname', 'username', 
                                               'client', 'channel_name', 'service', 'profile']),
        'subscription_total_out': Counter('subscription_out',
                                          'The total data in kb',
                                           labels=['title', 'state', 'hostname', 'username', 
                                                   'client', 'channel_name', 'service', 'profile']),
        'input_subscriptions': Gauge('input_subscriptions',
                                     'Number of subscriptions using the stream',
                                     labels=['name', 'stream']),
        'input_signal_noise_ratio': Gauge('input_signal_noise_ratio',
                                          'Signal Noise Ratio for DVB Inputs',
                                          labels=['name', 'stream']),
        'input_signal_noise_ratio_scale': Gauge('input_signal_noise_ratio_scale',
                                                'A value of 1 indicates that the '
                                                'corresponding signal or SNR reading'
                                                'is relative',
                                                labels=['name', 'stream']),
        'input_signal_scale': Gauge('input_signal_scale',
                                    'A value of 1 indicates that the '
                                    'corresponding signal or SNR reading '
                                    'is relative',
                                    labels=['name', 'stream']),
        'input_signal': Gauge('input_signal', 
                              'Signal Strength for DVB Inputs',
                              labels=['name', 'stream']),
        'input_continuity_errors': Gauge('input_continuity_errors',
                                         'Continuity Errors for Inputs',
                                         labels=['name', 'stream']),

        'scrape_duration_seconds': Gauge(
            'scrape_duration_seconds', 'Duration of TVHeadend scrape',
            labels=[]),
    }

    def basic_auth(self, username, password):
        token = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
        return f'Basic {token}'

    def configure(self, server_hostname, server_port, server_user, server_pass):
        connection = HTTPConnection(server_hostname, server_port)
        headers = {}
        if server_user and server_pass:
            headers = { "Authorization" : self.basic_auth(server_user, server_pass) }

        self.tvhapi = HTMLApi(connection, headers)

    def describe(self):
        return self.METRICS.values()

    def collect(self):
        try:
            start = time.time()

            # Use a separate instance for each scrape request, to prevent
            # race conditions with simultaneous scrapes.
            metrics = {
                key: value.clone() for key, value in self.METRICS.items()}

            # Serverinfo
            serverinfo = self.tvhapi.get_serverinfo()
            server_name = serverinfo['name']
            sw_version = serverinfo['sw_version']
            metrics['serverinfo'].add_metric([server_name, sw_version], 0)

            # Networks
            networks = self.tvhapi.get_network_grid()
            metrics['network_count'].add_metric([], len(networks))
            for network in networks:
                network_name = network['networkname']

                metrics['network_enabled'].add_metric(
                    [network_name], int(network['enabled']))
                metrics['network_muxes'].add_metric(
                    [network_name], network['num_mux'])
                metrics['network_services'].add_metric(
                    [network_name], network['num_svc'])
                metrics['network_channels'].add_metric(
                    [network_name], network['num_chn'])
                metrics['network_scans'].add_metric(
                    [network_name], network['scanq_length'])

            # Muxes
            muxes = self.tvhapi.get_mux_grid()
            metrics['mux_count'].add_metric([], len(muxes))
            for mux in muxes:
                network_name = mux['network']
                mux_name = mux['name']

                metrics['mux_enabled'].add_metric(
                    [network_name, mux_name], mux['enabled'])
                metrics['mux_scan_state'].add_metric(
                    [network_name, mux_name], mux['scan_state'])
                metrics['mux_scan_result'].add_metric(
                    [network_name, mux_name], mux['scan_result'])
                metrics['mux_services'].add_metric(
                    [network_name, mux_name], mux['num_svc'])
                metrics['mux_channels'].add_metric(
                    [network_name, mux_name], mux['num_chn'])

            # Service
            services = self.tvhapi.get_service_grid()
            metrics['service_count'].add_metric([], len(services))
            for service in services:
                network_name = service['network']
                mux_name = service['multiplex']
                service_name = service['svcname']

                metrics['service_enabled'].add_metric(
                    [network_name, mux_name, service_name], int(service['enabled']))
                metrics['service_channel_count'].add_metric(
                    [network_name, mux_name, service_name], len(service['channel']))

            # Channels
            channels = self.tvhapi.get_channel_grid()
            metrics['channel_count'].add_metric([], len(channels))
            for channel in channels:
                channel_name = channel['name']

                metrics['channel_enabled'].add_metric(
                    [channel_name], int(channel['enabled']))
                metrics['channel_service_count'].add_metric(
                    [channel_name], len(channel['services']))
                count = self.tvhapi.get_epg_count(channel_name)
                metrics['channel_epg_count'].add_metric(
                    [channel_name], count)

            # EPG
            epg_count = self.tvhapi.get_epg_count()
            metrics['epg_count'].add_metric([], int(epg_count))

            # DVR
            dvr = self.tvhapi.get_dvr()
            for recording in dvr:
                uuid = recording['uuid']
                channel_name = recording['channelname']
                programme_title = recording['disp_title']
                status = recording['status']
                creator = recording['creator']

                metrics['dvr_start_time'].add_metric(
                    [uuid, channel_name, programme_title, status, creator], recording['start'])
                metrics['dvr_finish_time'].add_metric(
                    [uuid, channel_name, programme_title, status, creator], recording['stop'])
                metrics['dvr_duration'].add_metric(
                    [uuid, channel_name, programme_title, status, creator], recording['duration'])

            # Connections
            connections = self.tvhapi.get_connection_stats()
            for connection in connections:
                hostname = connection['peer']
                typename = connection['type']
                if 'name' in connection.keys():
                    username = connection['user']
                else:
                    username = ''
                streaming = connection['streaming']

                metrics['connection_streaming'].add_metric(
                    [hostname, typename, username], streaming)

            # Subscriptions
            subscriptions = self.tvhapi.get_subscriptions()
            metrics['subscription_count'].add_metric([], int(len(subscriptions)))
            for subscription in subscriptions:
                title = subscription['title']
                state = subscription['state']
                hostname = subscription.get('hostname', '')
                if 'username' in subscription.keys():
                    username = subscription.get('username', '')
                else:
                    username = ''
                client = subscription.get('client', '')
                channel = subscription.get('channel', '')
                service = subscription.get('service', '')
                profile = subscription.get('profile', '')

                metrics['subscription_errors'].add_metric(
                    [title, state, hostname, username, 
                    client, channel, service, profile], 
                    subscription['errors'])
                metrics['subscription_in'].add_metric(
                    [title, state, hostname, username, 
                    client, channel, service, profile], 
                    subscription['in'])
                metrics['subscription_out'].add_metric(
                    [title, state, hostname, username, 
                    client, channel, service, profile], 
                    subscription['out'])
                metrics['subscription_total_in'].add_metric(
                    [title, state, hostname, username, 
                    client, channel, service, profile], 
                    subscription['total_in'])
                metrics['subscription_total_out'].add_metric(
                    [title, state, hostname, username, 
                    client, channel, service, profile], 
                    subscription['total_out'])

            # Inputs
            inputs = self.tvhapi.get_input_stats()
            for dvb_input in inputs:
                name = dvb_input.get('input', '')
                stream = dvb_input.get('stream', '')
                
                metrics['input_subscriptions'].add_metric(
                    [name, stream], dvb_input['subs'])
                metrics['input_signal_noise_ratio'].add_metric(
                    [name, stream], dvb_input['snr'])
                metrics['input_signal_noise_ratio_scale'].add_metric(
                    [name, stream], dvb_input['snr_scale'])
                metrics['input_signal'].add_metric(
                    [name, stream], dvb_input['signal'])
                metrics['input_signal_scale'].add_metric(
                    [name, stream], dvb_input['signal_scale'])
                metrics['input_continuity_errors'].add_metric(
                    [name, stream], dvb_input['cc'])

            metrics['scrape_duration_seconds'].add_metric(
                [], time.time() - start)
            return metrics.values()
        except Exception:
            log.error('Error during collect', exc_info=True)
            raise


COLLECTOR = tvheadendCollector()
# We don't want the `process_` and `python_` metrics, we're a collector,
# not an exporter.
REGISTRY = prometheus_client.core.CollectorRegistry()
REGISTRY.register(COLLECTOR)
APP = prometheus_client.make_wsgi_app(REGISTRY)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='bind host')
    parser.add_argument('--port', default='9429', help='bind port', type=int)
    parser.add_argument('--username', default=os.getenv("TVH_USER"),
                        help='username for authentication')
    parser.add_argument('--password', default=os.getenv("TVH_PASS"),
                        help='password for authentication')
    parser.add_argument(
        '--server', default=os.getenv("TVH_SERVER"),
        help='server url for tvheadend')
    parser.add_argument(
        '--serverport', default=os.getenv("TVH_PORT"),
        help='port for tvheadend')
    options = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT)
    COLLECTOR.configure(options.server, options.serverport, options.username, options.password)
    # Disable accesslog
    wsgiref.simple_server.ServerHandler.close = (
        wsgiref.simple_server.SimpleHandler.close)
    wsgiref.simple_server.make_server(
        options.host, options.port, APP).serve_forever()
