import argparse
import logging
import os.path
import sys
import time
import wsgiref.simple_server

import prometheus_client.core
from tvh.api import HTSPApi
from tvh.htsp import HTSPClient

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
        'active_subscription_start_time': Gauge(
            'active_subscription_start_time',
            'Start time for an active connection to the TVHeadend Server',
            labels=['ip_address', 'title', 'stream']),
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
        'input_signal': Gauge('input_signal', 'Signal Strength for DVB Inputs',
                              labels=['name', 'stream']),
        'scrape_duration_seconds': Gauge(
            'scrape_duration_seconds', 'Duration of tvheadend scrape',
            labels=[]),
    }

    def configure(self, server_hostname, server_user, server_pass):
        htsp = HTSPClient((server_hostname, 9982))
        htsp.hello()
        htsp.authenticate(server_user, server_pass)
        self.htspapi = HTSPApi(htsp=htsp)

    def describe(self):
        return self.METRICS.values()

    def collect(self):
        try:
            start = time.time()

            # Use a separate instance for each scrape request, to prevent
            # race conditions with simultaneous scrapes.
            metrics = {
                key: value.clone() for key, value in self.METRICS.items()}
            channel_count = self.htspapi.get_channels_count()
            streams = self.htspapi.get_streams()
            inputs = self.htspapi.get_input_stats()
            epg_count = self.htspapi.get_epg_count()

            metrics['channel_count'].add_metric([], int(channel_count))
            metrics['epg_count'].add_metric([], int(epg_count))
            metrics['subscription_count'].add_metric([], int(len(streams)))
            for stream in streams:
                try:
                    hostname = stream['hostname']
                    channel = stream['channel']
                    metrics['active_subscription_start_time'].add_metric(
                        [hostname, channel], stream['start'])
                except KeyError:
                    metrics['active_subscription_start_time'].add_metric(
                        [], stream['start'])

            for dvb_input in inputs:
                try:
                    name = dvb_input['input']
                    stream = dvb_input['stream']
                    metrics['input_signal_noise_ratio'].add_metric(
                        [name, stream], dvb_input['snr'])
                    metrics['input_signal'].add_metric(
                        [name, stream], dvb_input['signal'])
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
    options = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT)
    COLLECTOR.configure(options.server, options.username, options.password)
    # Disable accesslog
    wsgiref.simple_server.ServerHandler.close = (
        wsgiref.simple_server.SimpleHandler.close)
    wsgiref.simple_server.make_server(
        options.host, options.port, APP).serve_forever()
