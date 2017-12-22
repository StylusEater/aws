#!/usr/bin/python3

# Author: Adam M Dutko <adam@runbymany.com>
# License: Zero License
# Version: 0.0.1


import argparse
import datetime
import json
from os.path import isfile

import boto3


'''
    Create DNS records for a public hosted zone in Route 53. Required
    parameters are the domain name (zone) and a file containing the
    records you wish to create.
'''
class Zone:
    def __init__(self, _zone, _file, _region='us-east-2', _vpc_id=None,
                 _private=False):
        self._zone = _zone
        self._file = _file
        self._client = \
            Zone.setup_client(
                "route53",
                "ACCESS KEY",
                "SECRET KEY"
            )
        self._data = self.load()
        self._zone_id = None
        '''
           Try to create the zone if we get a zone doesn't exist error. 
        '''

        _zones = self._client.list_hosted_zones_by_name(
            DNSName=self._zone
        )['HostedZones']

        for _zone in _zones:
            if _zone['Name'] == self._zone:
                self._zone_id = _zone['Id']

        if self._zone_id is None:
            print "Zone " + self._zone + " does not exist. " \
                                             "Attempting to create..."
            if _vpc_id:
                try:
                    self._client.create_hosted_zone(
                        Name=self._zone,
                        VPC={
                            'VPCRegion': _region,
                            'VPCId': _vpc_id
                        },
                        CallerReference=
                            datetime.datetime.now().strftime('%s'),
                        HostedZoneConfig={
                            'Comment': self._zone + ' default zone.',
                            'PrivateZone': _private
                        }
                    )

                    print self._zone + " created."
                except Exception as cannot_create_private_zone:
                    print cannot_create_private_zone
                    exit(-1)
            else:
                try:
                    self._client.create_hosted_zone(
                        Name=self._zone,
                        CallerReference=
                            datetime.datetime.now().strftime('%s'),
                        HostedZoneConfig={
                            'Comment': self._zone + ' default zone.',
                            'PrivateZone': _private
                        }
                    )
                    print self._zone + " created."
                except Exception as cannot_create_public_zone:
                    print cannot_create_public_zone
                    exit(-1)

            # Try again after creating the zone
            _zones = self._client.list_hosted_zones_by_name(
                DNSName=self._zone
            )['HostedZones']

            for _zone in _zones:
                if _zone['Name'] == self._zone:
                    self._zone_id = _zone['Id']

            if self._zone_id is None:
                print "ERROR: Could not create zone."
                exit(-1)

    @staticmethod
    def setup_client(_service, _access_key, _secret_key):
        return boto3.client(
            _service,
            aws_access_key_id=_access_key,
            aws_secret_access_key=_secret_key
        )

    def add_record(self, _record_type, _source, _destination, weight):
        try:
            if _record_type in ['SOA', 'A', 'TXT', 'NS', 'CNAME', 'NAPTR',
                                'PTR', 'SRV', 'SPF', 'AAAA', 'CAA']:
                self._client.change_resource_record_sets(
                    HostedZoneId=self._zone_id,
                    ChangeBatch={
                        'Comment': 'Add %s -> %s' % (_source, _destination),
                        'Changes': [{
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': _source,
                                'Type': _record_type,
                                'TTL': weight,
                                'ResourceRecords': [{'Value': _destination}]
                            }
                        }]
                    })
                print "Created " + _record_type + " record for " + self._zone
            elif _record_type in ['MX']:
                print _destination
                self._client.change_resource_record_sets(
                    HostedZoneId=self._zone_id,
                    ChangeBatch={
                        'Comment': 'Default mail records',
                        'Changes': [{
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': _source,
                                'Type': _record_type,
                                'ResourceRecords':  _destination,
                                'TTL': weight
                            }
                        }]
                    })
                print "Created " + _record_type + " record for " + self._zone
        except Exception as add_record_ex:
            ''' Various Errors:
            
            An error occurred (AccessDenied) when calling the 
            ChangeResourceRecordSets operation: 
            User: arn:aws:iam::671921086032:user/r53 is not authorized to
            perform: route53:ChangeResourceRecordSets on resource: 
            arn:aws:route53:::hostedzone/...
            
            CREATING: A : 0.0.0.0 --> www.flytlog.com
            An error occurred (InvalidChangeBatch) when calling the 
            ChangeResourceRecordSets operation: Invalid Resource Record: FATAL
            problem: ARRDATAIllegalIPv4Address (Value is not a valid IPv4 
            address) encountered with 'www.flytlog.com'

            CREATING: CNAME : www.flytlog.com --> flytlog.com
            {u'ChangeInfo': {u'Status': 'PENDING', u'Comment': 'add 
            www.flytlog.com -> flytlog.com', u'SubmittedAt': 
            datetime.datetime(2017, 12, 11, 16, 18, 16, 156000, 
            tzinfo=tzutc()), u'Id': '/change/...'}, 
            'ResponseMetadata': {'RetryAttempts': 0, 'HTTPStatusCode': 200, 
            'RequestId': '...', 
            'HTTPHeaders': {'x-amzn-requestid': 
            '...', 'date': 'Mon, 11 Dec 2017 
            16:18:16 GMT', 'content-length': '332', 'content-type': 
            'text/xml'}}}

            CREATING: MX : smtp --> smtp
            An error occurred (InvalidChangeBatch) when calling the 
            ChangeResourceRecordSets operation: Invalid Resource Record: FATAL 
            problem: MXRRDATANotTwoFields (MX record doesn't have 2 fields) 
            encountered with 'smtp'

            
            '''
            print add_record_ex

    def load(self):
        if isfile(self._file):
            try:
                return json.load(open(self._file))
            except Exception, ex:
                print ex
                exit(-1)
        else:
            print "ERROR: " + args.file + " is not a valid file."
            exit(-1)

    def create(self):
        # Create the zone based on the information in our zone data file
        for record in self._data['records']:
            record_type = record['type']
            if 'source' in record.keys():
                source = record['source']
            else:
                source = None

            if 'destination' in record.keys():
                destination = record['destination']
            else:
                destination = None
            if 'weight' in record.keys():
                weight = record['weight']
            else:
                weight = 300

            self.add_record(record_type, source, destination, weight)


if __name__ == "__main__":
    '''
        Create DNS records for a public hosted zone in Route 53. Required
        parameters are the domain name (zone) and a file containing the
        records you wish to create.
        
        python Zone.py --zone flytlog.com --file zones/flytlog.com.zone
    '''
    parser = \
        argparse.ArgumentParser(
            description="Create a public hosted zone from JSON records file."
        )
    parser.add_argument('--zone', required=True, default='flytlog.com',
                        help="The domain for which we're creating records.")
    parser.add_argument('--file', required=True, default='zone.data',
                        help="The JSON file containing the records.")
    parser.add_argument('--access_key', required=False, default='AAAAAAAAAA',
                        help="AWS Access Key ID")
    parser.add_argument('--secret-key', required=False, default='AAAAAAAAAA',
                        help="AWS Secret Access Key")

    args = parser.parse_args()

    new_zone = Zone(args.zone, args.file)
    new_zone.create()


