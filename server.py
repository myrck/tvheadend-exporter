import argparse
from tvh.htsp import HTSPClient
from tvh.api import HTSPApi
import logging
import os.path
import prometheus_client.core
import sys
import time
import wsgiref.simple_server

log = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'


class Gauge(prometheus_client.core.GaugeMetricFamily):

    NAMESPACE = 'tvheadend'

    def __init__(self, name, documentation):
        super(Gauge, self).__init__('%s_%s' % (self.NAMESPACE, name), documentation, labels=['ip_address', 'title'])
        self._name = name

    def clone(self):
        return type(self)(self._name, self.documentation)


class tvheadendCollector(object):
    METRICS = {
        'active_subscription_start_time': Gauge('active_subscription_start_time', 'Start time for an active connection/stream to the TVHeadend Server'),
        'channel_count': Gauge('channel_count', 'Number of channels on the server'),
        'subscription_count': Gauge('subscription_count', 'Number of active subscriptions'),
        'scrape_duration_seconds': Gauge(
            'scrape_duration_seconds', 'Duration of tvheadend scrape'),
    }

    def configure(self, server_hostname, server_user, server_pass):
        htsp = HTSPClient((server_hostname, 9982))
        msg = htsp.hello()
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

            labels = [
                '',
            ]
            channel_count = self.htspapi.get_channels_count()
            streams = self.htspapi.get_streams()
            metrics['channel_count'].add_metric([], int(channel_count))
            metrics['subscription_count'].add_metric([], int(len(streams)))
            for stream in streams:
                try:
                    hostname = stream['hostname']
                    channel = stream['channel']
                    metrics['active_subscription_start_time'].add_metric([hostname, channel], stream['start'])
                except:
                    metrics['active_subscription_start_time'].add_metric([], stream['start'])

                print(stream)
            metrics['scrape_duration_seconds'].add_metric([], time.time() - start)
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
    parser.add_argument('--username', default=os.getenv("TVH_USER"), help='username for authentication')
    parser.add_argument('--password', default=os.getenv("TVH_PASS"), help='password for authentication')
    parser.add_argument('--server', default=os.getenv("TVH_SERVER"), help='server url for tvheadend')
    options = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT)
    COLLECTOR.configure(options.server, options.username, options.password)
    # Disable accesslog
    wsgiref.simple_server.ServerHandler.close = (
        wsgiref.simple_server.SimpleHandler.close)
    wsgiref.simple_server.make_server(
        options.host, options.port, APP).serve_forever()
