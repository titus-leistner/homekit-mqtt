# -*- coding: utf-8 -*-

"""HomeKit MQTT Bridge Deamon"""
import sys
import os
import shutil
import click
import logging
import signal

from pyhap.accessory_driver import AccessoryDriver
from homekit_mqtt.mqtt_bridge import MqttBridge

from homekit_mqtt import cfg_loader

logger = logging.getLogger(__name__)


def create_cfg(dname):
    """
    Create the configuration directory and copy initial bridge.cfg into it.

    :param dname: the config directory
    :type dmane: str
    """
    if not os.path.exists(dname):
        logger.info('Creating config directory at ' + dname)
        os.makedirs(dname)

    # copy initial bridge.cfg into place
    src = os.path.join(
        (os.path.abspath(os.path.dirname(__file__))), 'data', 'bridge.cfg')
    dst = os.path.join(dname, 'bridge.cfg')
    logger.info('Creating ' + dst)
    shutil.copyfile(src, dst)


def systmd():
    """
    Setup a systemd service for homekit-mqtt
    """
    src = os.path.join((os.path.abspath(os.path.dirname(__file__))),
                       'data', 'homekit-mqtt.service')
    dst = '/etc/systemd/system/homekit-mqtt.service'
    os.link(src, dst)

    # reload daemons
    os.system('systemctl daemon-reload')


@click.command()
@click.option('--cfg', default='/etc/homekit-mqtt',
              help='The directory containing the accessory configuration.')
@click.option('--reset/--load', is_flag=True,
              help='Reset the bridge before readding it \
                    to the Home App again.')
@click.option('--setup-systemd', is_flag=True,
              help='Create a systemd service.')
def main(cfg, reset, setup_systemd):
    # init logging
    logging.basicConfig(level=logging.INFO)

    if reset:
        # remove accessory.state
        os.remove('accessory.state')

    if setup_systemd:
        systmd()

    # create config if necessary
    if not os.path.exists(os.path.join(cfg, 'bridge.cfg')):
        create_cfg(cfg)

    # start the accessory driver on port 51826
    driver = AccessoryDriver(port=51826)

    # create bridge
    bridge = MqttBridge(cfg, driver, 'MQTT')

    # load accs
    loader = cfg_loader.CfgLoader(driver, cfg)
    accs = loader.load_accessories(reset)
    for acc in accs:
        bridge.add_accessory(acc)

    loader.save_accessories()

    # add the bridge
    driver.add_accessory(accessory=bridge)

    signal.signal(signal.SIGTERM, driver.signal_handler)

    # start HomeKit
    driver.start()
    print('Returned')
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
