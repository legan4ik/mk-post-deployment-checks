import os
import yaml
import requests
import re


class salt_remote:
    def cmd(self, tgt, fun, param=None,expr_form=None):
        config = get_configuration(__file__)
        for salt_cred in ['SALT_USERNAME', 'SALT_PASSWORD', 'SALT_URL']:
            if os.environ.get(salt_cred):
                config[salt_cred] = os.environ[salt_cred]
        headers = {'Accept':'application/json'}
        login_payload = {'username':config['SALT_USERNAME'],'password':config['SALT_PASSWORD'],'eauth':'pam'}
        accept_key_payload = {'fun': fun,'tgt':tgt,'client':'local','expr_form':expr_form}
        if param:
            accept_key_payload['arg']=param

        login_request = requests.post(os.path.join(config['SALT_URL'],'login'),headers=headers,data=login_payload)
        request = requests.post(config['SALT_URL'],headers=headers,data=accept_key_payload,cookies=login_request.cookies)
        return request.json()['return'][0]


def init_salt_client():
    local = salt_remote()
    return local


def get_active_nodes(config):
    local_salt_client = init_salt_client()

    skipped_nodes = config.get('skipped_nodes') or []
    # TODO add skipped nodes to cmd command instead of filtering
    nodes = local_salt_client.cmd('*', 'test.ping')
    active_nodes = [
        node_name for node_name in nodes
        if nodes[node_name] and node_name not in skipped_nodes
    ]
    return active_nodes


def get_groups(config):
    # assume that node name is like <name>.domain
    # last 1-3 digits of name are index, e.g. 001 in cpu001
    # name doesn't contain dots
    active_nodes = get_active_nodes(config)
    skipped_group = config.get('skipped_group') or []
    groups = []

    for node in active_nodes:
        index = re.search('[0-9]{1,3}$', node.split('.')[0])
        if index:
            group_name = node.split('.')[0][:-len(index.group(0))]
        else:
            group_name = node
        if group_name not in skipped_group and group_name not in groups:
            groups.append(group_name)
    test_groups = []
    groups_from_config = config.get('groups')
    # check if config.yaml contains `groups` key
    if groups_from_config is not None:
        invalid_groups = []
        for group in groups_from_config:
            # check if group name from config
            # is substring of one of the groups
            grp = [x for x in groups if group in x]
            if grp:
                test_groups.append(grp[0])
            else:
                invalid_groups.append(group)
        if invalid_groups:
            raise ValueError('Config file contains'
                             ' invalid groups name: {}'.format(invalid_groups))

    groups = test_groups if test_groups else groups

    # For splitting Ceph nodes
    local_salt_client = init_salt_client()

    if "ceph*" in groups:
        groups.remove("ceph*")

        ceph_status = local_salt_client.cmd(
            'ceph*', "cmd.run", ["ps aux | grep ceph-mon | grep -v grep"])

        mon = []
        ceph = []
        for node in ceph_status:
            if ceph_status[node] != '':
                mon.append(node.split('.')[0])
            else:
                ceph.append(node.split('.')[0])

        mon_regex = "({0}.*)".format(".*|".join(mon))
        groups.append(mon_regex)

        ceph_regex = "({0}.*)".format(".*|".join(ceph))
        groups.append(ceph_regex)

    return groups


def get_configuration(path_to_test):
    """function returns configuration for environment

    and for test if it's specified"""
    global_config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../global_config.yaml")
    with open(global_config_file, 'r') as file:
        global_config = yaml.load(file)

    config_file = os.path.join(
        os.path.dirname(os.path.abspath(path_to_test)), "config.yaml")

    if os.path.exists(config_file):
        with open(config_file, 'r') as file:
            global_config.update(yaml.load(file))

    return global_config
