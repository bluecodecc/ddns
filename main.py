import json

from tencentcloud.common import credential
from tencentcloud.dnspod.v20210323 import dnspod_client, models

import config
import logging
import requests
import schedule
import time

client: dnspod_client.DnspodClient
recordId: dict = {}
lastPublicIp: dict = {}


def init():
    configs = config.configs['ddns']
    cred = credential.Credential(configs['secretId'], configs['secretKey'])
    global client
    client = dnspod_client.DnspodClient(cred, "ap-shanghai")
    global recordId
    if 'recordId' in configs:
        recordId = configs['recordId']
    else:
        get_record_id()
    logging.basicConfig(filename='logger.log', level=logging.INFO)


def get_record_id():
    req = models.DescribeRecordListRequest()
    req.Domain = config.configs['ddns']['domain']
    resp = client.DescribeRecordList(req)
    logging.info(resp.to_json_string())
    record_list = json.loads(resp.to_json_string())['RecordList']
    record_list_filter = list(filter(lambda x: x['Name'] == config.configs['ddns']['subDomain'], record_list))
    global recordId
    for record in record_list_filter:
        if record['Type'] in config.configs['ddns']['recordType']:
            recordId[record['Type']] = record['RecordId']


def update_record(public_ip):
    #  便利recordId,更新记录
    for key in recordId.keys():
        if key not in public_ip.keys():
            continue
        req = models.ModifyRecordRequest()
        req.RecordId = recordId[key]
        req.Domain = config.configs['ddns']['domain']
        req.SubDomain = config.configs['ddns']['subDomain']
        req.RecordLine = config.configs['ddns']['RecordLine']
        req.RecordType = key
        req.Value = public_ip[key]
        req.TTL = config.configs['ddns']['TTL']
        req.MX = 0
        resp = client.ModifyRecord(req)
        logging.info(resp.to_json_string())


def get_public_ip():
    res = {}
    ipv4 = requests.get('https://api.ipify.org').text.strip()
    logging.info('ipv4: ' + ipv4)
    res['A'] = ipv4
    ipv6 = requests.get('https://api64.ipify.org').text.strip()
    logging.info('ipv6: ' + ipv6)
    if ipv6 == ipv4:
        return res
    res['AAAA'] = ipv6
    return res


def job():
    public_ip = get_public_ip()
    global lastPublicIp
    if lastPublicIp is None or lastPublicIp.get('A') != public_ip.get('A') or lastPublicIp.get('AAAA') != public_ip.get(
            'AAAA'):
        update_record(public_ip)
        lastPublicIp = public_ip


if __name__ == '__main__':
    init()
    job()
    schedule.every(config.configs['schedule']['interval']).seconds.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
