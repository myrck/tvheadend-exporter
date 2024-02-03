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
        'serverinfo': Gauge('serverinfo', 'Information of the TVHeadend Server',
                            labels=['server_name', 'sw_version']
        ),
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
        'dvr_finish_time': Gauge('dvr_start_time',
                                 'Finish time for DVR Event',
                                 labels=["channel_name",
                                         "programme_title",
                                         "status", "state"]),
        'dvr_duration': Gauge('dvr_start_time',
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

            serverinfo = self.tvhapi.get_serverinfo()
            server_name = serverinfo['name']
            sw_version = serverinfo['sw_version']
            # Counts
            channel_count = self.tvhapi.get_channels_count()
            epg_count = self.tvhapi.get_epg_count()
            dvr_upcoming_count = self.tvhapi.get_dvr_count({}, 'upcoming')
            dvr_finished_count = self.tvhapi.get_dvr_count({}, 'finished')
            dvr_failed_count = self.tvhapi.get_dvr_count({}, 'failed')
            metrics['serverinfo'].add_metric([server_name, sw_version], 0)
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
