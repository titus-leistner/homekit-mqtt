# -*- coding: utf-8 -*-

"""HomeKit MQTT Bridge Deamon"""
import sys
import click


@click.command()
@click.option('--reset/--load', default=False,
              help='Reset the bridge before readding it to the Home App again.')
@click.option('--cfg', default='etc/homekit-mqtt', 
              help='The directory containing the accessory configuration.')
def main(reset, args):
    # init logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    if reset:
        # remove accessory.state
        os.remove('accessory.state')

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
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
