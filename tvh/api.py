import re
import json

class HTMLApi(object):

    GRID_LIMIT = '4294967295'

    def __init__(self, httpCon, headers):
        self.httpCon = httpCon
        self.headers = headers

    def get(self, path, args={}):
        self.httpCon.request("GET", path, headers=self.headers)
        res = self.httpCon.getresponse()

        contentType = res.headers["Content-Type"]
        match = re.search("charset=(.+)", contentType)
        data = res.read()
        #print("Response: %s" % data)
        
        if match is not None:
            encoding = match.groups()[0]

            return json.loads(data.decode(encoding))
        return json.loads(data)

    def get_serverinfo(self, kwargs={}):
        response = self.get('/api/serverinfo', kwargs)
        return response

    def get_network_grid(self, kwargs={}):
        response = self.get('/api/mpegts/network/grid?limit='+self.GRID_LIMIT, kwargs)
        return response['entries']

    def get_mux_grid(self, kwargs={}):
        response = self.get('/api/mpegts/mux/grid?limit='+self.GRID_LIMIT, kwargs)
        return response['entries']

    def get_service_grid(self, kwargs={}):
        response = self.get('/api/mpegts/service/grid?limit='+self.GRID_LIMIT, kwargs)
        return response['entries']

    def get_channels_grid(self, kwargs={}):
        response = self.get('/api/channel/grid', kwargs)
        return response['entries']
    
    def get_channels_count(self, kwargs={}):
        response = self.get('/api/channel/grid', kwargs)
        return response['total']
    
    def get_epg_count(self, kwargs={}):
        response = self.get('/api/epg/events/grid', kwargs)
        return response['totalCount']

    def get_input_stats(self, kwargs={}):
        response = self.get('/api/status/inputs', kwargs)
        return response['entries']
    
    def get_dvr_count(self, kwargs={}, state=''):
        if state == '':
            path = '/api/dvr/entry/grid'
        else:
            path = '/api/dvr/entry/grid_'+state

        response = self.get(path, kwargs)
        return response['total']

    def get_streams(self, kwargs={}):
        response = self.get('/api/status/subscriptions', kwargs)
        return response['entries']

    def get_dvr(self, kwargs={}, state=''):
        if state == '':
            path = '/api/dvr/entry/grid'
        else:
            path = '/api/dvr/entry/grid_'+state

        response = self.get(path, kwargs)
        return response['entries']
