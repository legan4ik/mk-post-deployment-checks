import pytest
import os
from mk_verificator import utils


@pytest.mark.parametrize(
    "node",
    utils.get_active_nodes(utils.get_configuration(__file__))
)
def test_ntp_sync(local_salt_client, node):
    config = utils.get_configuration(__file__)
    fail = {}

    saltmaster_time = int(local_salt_client.cmd(
        os.uname()[1] + '*', 'cmd.run', ['date +%s']).values()[0])

    nodes_time = local_salt_client.cmd(
        node, 'cmd.run', ['date +%s'], expr_form='pcre')

    for node, time in nodes_time.iteritems():
        if (int(time) - saltmaster_time) > config["time_deviation"] or \
                (int(time) - saltmaster_time) < -config["time_deviation"]:
            fail[node] = time

    assert not fail, 'SaltMaster time: {}\n' \
                     'Nodes with time mismatch:\n {}'.format(saltmaster_time,
                                                             fail)
