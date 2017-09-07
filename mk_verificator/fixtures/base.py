import pytest
import os
import requests
import mk_verificator.utils as utils
import glanceclient.client as gl_client
from keystoneauth1.identity import v3
from keystoneauth1 import session
# TODO merge vm and vm_kp in one fixture


class salt_remote:
    def cmd(self, tgt, fun, param=None,expr_form=None):
        config = utils.get_configuration(__file__)
        url = 'http://10.100.0.5:6969'
        headers = {'Accept':'application/json'}
        login_payload = {'username':'salt','password':config['salt_pwd'],'eauth':'pam'}
        accept_key_payload = {'fun': fun,'tgt':tgt,'client':'local','expr_form':expr_form}
        if param:
            accept_key_payload['arg']=param

        login_request = requests.post(os.path.join(url,'login'),headers=headers,data=login_payload)
        request = requests.post(url,headers=headers,data=accept_key_payload,cookies=login_request.cookies)
        return request.json()['return'][0]


@pytest.fixture
def local_salt_client():
    #local = client.LocalClient()
    local = salt_remote()
    return local

@pytest.fixture
def active_nodes(local_salt_client, skipped_nodes=None):
    skipped_nodes = skipped_nodes or []
    nodes = local_salt_client.cmd('*', 'test.ping')
    active_nodes = [
        node_name for node_name in nodes
        if nodes[node_name] and node_name not in skipped_nodes
    ]
    return active_nodes


@pytest.fixture
def groups(active_nodes, skipped_group=None):
    skipped_group = skipped_group or []
    groups = [
        node.split('-')[0] for node in active_nodes
        if node not in skipped_group
    ]
    return groups


@pytest.fixture
def glance_client():
    config = utils.get_configuration(__file__)

    auth = v3.Password(
        auth_url=config['url_v3'],
        username=config['admin_username'],
        password=config['admin_password'],
        project_id=config['admin_project_id'],
        user_domain_id='default',
        project_domain_id='default')
    sess = session.Session(auth=auth, verify=False)

    endpoint = auth.get_endpoint(
        session=sess, service_type='image', interface='internal')
    client = gl_client.Client(
        config['glance_version'], endpoint, session=sess)

    return client
