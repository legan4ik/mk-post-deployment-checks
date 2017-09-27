import pytest
import json
from cvp_checks import utils


@pytest.mark.parametrize(
    "group",
    utils.get_groups(utils.get_configuration(__file__))
)
def test_mtu(local_salt_client, group):
    config = utils.get_configuration(__file__)
    skipped_ifaces = config["skipped_ifaces"]
    total = {}
    network_info = local_salt_client.cmd(
        group, 'cmd.run', ['ls /sys/class/net/ | grep -v "veth" | grep -v "tap" | grep -v "cali"'], expr_form='pcre')

    kvm_nodes = local_salt_client.cmd(
        'salt:control', 'test.ping', expr_form='pillar').keys()

    if len(network_info.keys()) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    for node, ifaces_info in network_info.iteritems():
        if node in kvm_nodes:
            kvm_info = local_salt_client.cmd(node, 'cmd.run',
                                             ["virsh list | "
                                              "awk '{print $2}' | "
                                              "xargs -n1 virsh domiflist | "
                                              "grep -v br-pxe | grep br- | "
                                              "awk '{print $1}'"])
            ifaces_info = kvm_info.get(node)
        node_ifaces = ifaces_info.split('\n')
        ifaces = {}
        for iface in node_ifaces:
            if iface in skipped_ifaces:
                continue
            iface_mtu = local_salt_client.cmd(node, 'cmd.run',
                                                  ['cat /sys/class/'
                                                   'net/{}/mtu'.format(iface)])
            ifaces[iface] = iface_mtu.get(node)
        total[node] = ifaces

    nodes = []
    mtu_data = []
    my_set = set()

    for node in total:
        nodes.append(node)
        my_set.update(total[node].keys())
    for interf in my_set:
        diff = []
        row = []
        for node in nodes:
            if interf in total[node].keys():
                diff.append(total[node][interf])
                row.append("{}: {}".format(node, total[node][interf]))
            else:
                row.append("{}: No interface".format(node))
        if diff.count(diff[0]) < len(nodes):
            row.sort()
            row.insert(0, interf)
            mtu_data.append(row)
    assert len(mtu_data) == 0, \
        "Several problems found for {0} group: {1}".format(
        group, json.dumps(mtu_data, indent=4))

