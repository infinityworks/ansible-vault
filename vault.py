import os
import urllib2
import json
import sys
from urlparse import urljoin

from ansible import utils

from ansible.errors import AnsibleError

isNotV2 = False

try:
    # ansible-2.0
    from ansible.plugins.lookup import LookupBase
    isNotV2 = False
except ImportError:
    # ansible-1.9.x
    isNotV2 = True
    from ansible.utils import template
    class LookupBase(object):
        def __init__(self, basedir=None, **kwargs):
            self.basedir = basedir

class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):

        if isNotV2:
            try:
                inject = variables['inject'] if 'inject' in variables else None
                key = template.template(self.basedir, terms[0], inject)
            except Exception, e:
                pass
        else:
            key = terms[0]
            
        try:
            field = terms[1]
        except:
            field = None

        url = os.getenv('VAULT_ADDR')
        if not url:
            raise AnsibleError('VAULT_ADDR environment variable is missing')

        token = os.getenv('VAULT_TOKEN')
        if not token:
            token = self.get_local_auth_token()
        if not token:
            raise AnsibleError('VAULT_TOKEN environment variable is missing')

        request_url = urljoin(url, "v1/%s" % (key))
        try:
            # remove the proxy route from urllib2 to allow it to connect to an SSL endpoint without routing via the proxy.
            # http://www.decalage.info/en/python/urllib2noproxy
            proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)
            
            headers = { 'X-Vault-Token' : token }
            req = urllib2.Request(request_url, None, headers)
            response = opener.open(req)
        except urllib2.HTTPError as e:
            raise AnsibleError('Unable to read %s from vault: %s' % (key, e))
        except:
            raise AnsibleError('Unable to read %s from vault' % key)

        result = json.loads(response.read())

        return [result['data'][field]] if field is not None else [result['data']]

    def get_local_auth_token(self):
        locpath = os.getenv('HOME') + '/.vault-token'
        retval = ''
        with file(locpath) as f:
            retval = f.read()
        return str(retval)
