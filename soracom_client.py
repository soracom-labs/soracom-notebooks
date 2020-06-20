import os
import requests
import time

from datetime import datetime
from pandas import *


class SoracomClient:

    def __init__(self, **kwargs):
        self.api_token = None

        if 'api_endpoint' in kwargs.keys():
            self.api_endpoint = kwargs['api_endpoint']
        else:
            self.api_endpoint = 'https://api.soracom.io'

        self.api_base_url = self.api_endpoint + '/v1'

        if 'access_key_id' in kwargs.keys() and 'access_key' in kwargs:
            self.access_key_id = kwargs['access_key_id']
            self.access_key = kwargs['access_key']

        # TODO: Make this work when no environment variable set.
        elif 'ACCESS_KEY_ID' in os.environ and 'ACCESS_KEY' in os.environ:
            self.access_key_id = os.environ['ACCESS_KEY_ID']
            self.access_key = os.environ['ACCESS_KEY']

        else:
            raise Exception('No credential provided for SORACOM API.')

    def _auth(self):
        auth_result = requests.post(
            self.api_base_url + '/auth',
            json={'authKeyId': self.access_key_id, 'authKey': self.access_key}
        )
        self.api_token = auth_result.json()

    def _make_authorization_header(self):
        # TODO: Make this work in token expired case.
        if self.api_token is None:
            self._auth()

        headers = {
            "X-Soracom-API-Key": self.api_token["apiKey"],
            "X-Soracom-Token": self.api_token["token"]
        }
        return headers

    def _make_url(self, path):
        return self.api_base_url + path

    def _parse_response(self, res):
        return res.json()

    def _do_get(self, path, params={}):
        url = self._make_url(path)
        headers = self._make_authorization_header()
        f = requests.get(url, params=params, headers=headers)
        return self._parse_response(f)

    def _do_post(self, path, body, params={}):
        url = self._make_url(path)
        headers = self._make_authorization_header()
        f = requests.post(url, json=body, params=params, headers=headers)
        return self._parse_response(f)

    def getSubscribers(self):
        path = '/subscribers'
        api_result = self._do_get(path)

        for record in api_result:

            if not 'groupId' in record.keys() or record['groupId'] is None:
                record['groupId'] = 'NA'

            if record['sessionStatus'] is not None:
                record['online'] = record['sessionStatus']['online']
            else:
                record['oneline'] = False

            record['imsi'] = str(record['imsi'])

        subscribers = pandas.DataFrame(api_result)
        return subscribers

    def getAirStatsByDay(self, days):
        path = "/stats/air/operators/" + \
            self.api_token['operatorId'] + "/export"

        # TODO: Make this async.
        params = {
            "export_mode": "sync"
        }

        now = int(time.time())
        body = {
            "from": now - 86400*days,
            "to": now,
            "period": "day"
        }

        api_result = self._do_post(path, body, params)

        traffic = pandas.read_csv(api_result['url'])
        traffic['dates'] = traffic['date'].apply(
            lambda x:  datetime.strptime(str(x), '%Y%m%d'))
        traffic['imsi'] = traffic['imsi'].apply(lambda x: str(x))
        traffic.index = traffic['dates']
        traffic.index.name = None
        return traffic

    def getLogs(self, days):
        path = '/logs'
        now = int(time.time())
        params = {
            "from": now - 86400*days,
            "to": now,
            "limit": 10000
        }

        logs = self._do_get(path, params)
        for log in logs:
            log['time'] = datetime.fromtimestamp(log['time']/1000)
            log['message'] = log['body']['message']

        logs = DataFrame(data=logs)
        logs.index = logs['time']
        return logs
