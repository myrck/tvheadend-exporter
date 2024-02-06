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
        'active_subscription_start_time': Gauge(
            'active_subscription_start_time',
            'Start time for an active connection to the TVHeadend Server',
            labels=['hostname', 'channel_name', 'username', 'client']),
        'channel_count': Gauge('channel_count',
                               'Number of channels on the server', labels=[]),
        'epg_count': Gauge('epg_count', 'Number of programmes in the EPG',
                           labels=[]),
        'subscription_count': Gauge('subscription_count',
                                    'Number of active subscriptions',
                                    labels=[]),
        'input_signal_noise_ratio': Gauge('input_signal_noise_ratio',
                                          'Signal Noise Ratio for DVB Inputs',
                                          labels=['name', 'stream']),
        'input_signal_noise_ratio_scale': Gauge(
            'input_signal_noise_ratio_scale',
            'A value of 1 indicates that the '
            'corresponding signal or SNR reading'
            'is relative',
            labels=['name', 'stream']),
        'input_signal_scale': Gauge('input_signal_scale',
                                    'A value of 1 indicates that the '
                                    'corresponding signal or SNR reading '
                                    'is relative',
                                    labels=['name', 'stream']),
        'input_signal': Gauge('input_signal', 'Signal Strength for DVB Inputs',
                              labels=['name', 'stream']),
        'input_continuity_errors': Gauge('input_continuity_errors',
                                         'Continuity Errors for Inputs',
                                         labels=['name', 'stream']),
        'dvr_count': Gauge('dvr_count',
                           'Number of events in the DVR',
                           labels=["status"]),

        'dvr_start_time': Gauge('dvr_start_time',
                                'Start time for DVR Event',
                                labels=["channel_name",
                                        "programme_title",
                                        "status", "state"]),
        'dvr_finish_time': Gauge('dvr_finish_time',
                                 'Finish time for DVR Event',
                                 labels=["channel_name",
                                         "programme_title",
                                         "status", "state"]),
        'dvr_duration': Gauge('dvr_duration',
                              'Duration for DVR Event',
                              labels=["channel_name",
                                      "programme_title",
                                      "status", "state"]),
        'scrape_duration_seconds': Gauge(
            'scrape_duration_seconds', 'Duration of TVHeadend scrape',
            labels=[]),
    }

    def basic_auth(self, username, password):
        token = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
        return f'Basic {token}'

    def configure(self, server_hostname, server_port, server_user, server_pass):
        connection = HTTPConnection(server_hostname, server_port)
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

            # Counts
            channel_count = self.tvhapi.get_channels_count()
            epg_count = self.tvhapi.get_epg_count()
            dvr_upcoming_count = self.tvhapi.get_dvr_count({}, 'upcoming')
            dvr_finished_count = self.tvhapi.get_dvr_count({}, 'finished')
            dvr_failed_count = self.tvhapi.get_dvr_count({}, 'failed')
            metrics['channel_count'].add_metric([], int(channel_count))
            metrics['epg_count'].add_metric([], int(epg_count))
            metrics['dvr_count'].add_metric(['upcoming'],
                                            int(dvr_upcoming_count))
            metrics['dvr_count'].add_metric(['finished'],
                                            int(dvr_finished_count))
            metrics['dvr_count'].add_metric(['failed'], int(dvr_failed_count))

            # Arrays
            streams = self.tvhapi.get_streams()
            inputs = self.tvhapi.get_input_stats()
            dvr = self.tvhapi.get_dvr()

            metrics['subscription_count'].add_metric([], int(len(streams)))
            # Iterate through arrays
            for stream in streams:
                try:
                    hostname = stream['hostname']
                    channel = stream['channel']
                    username = stream['username']
                    client = stream['client']
                    metrics['active_subscription_start_time'].add_metric(
                        [hostname, channel, username, client], stream['start'])
                except KeyError:
                    metrics['active_subscription_start_time'].add_metric(
                        [], stream['start'])

            for dvb_input in inputs:
                try:
                    name = dvb_input['input']
                    stream = dvb_input['stream']
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
                except KeyError:
                    pass

                for recording in dvr:
                    try:
                        channel_name = recording['channelname']
                        programme_title = recording['disp_title']
                        start_timestamp = recording['start']
                        finish_timestamp = recording['stop']
                        duration = recording['duration']
                        status = recording['status']
                        recording_state = recording['sched_status']

                        metrics['dvr_start_time'].add_metric(
                            [channel_name, programme_title, status,
                             recording_state], start_timestamp)
                        metrics['dvr_finish_time'].add_metric(
                            [channel_name, programme_title, status,
                             recording_state], finish_timestamp)
                        metrics['dvr_duration'].add_metric(
                            [channel_name, programme_title, status,
                             recording_state],
                            duration)

                    except KeyError:
                        pass

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
