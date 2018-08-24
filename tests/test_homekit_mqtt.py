#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `homekit_mqtt` package."""

import pytest

import os
import shutil
import configparser

from click.testing import CliRunner

from homekit_mqtt import cli

from pyhap.accessory_driver import AccessoryDriver

from homekit_mqtt import cfg_loader


@pytest.fixture(scope='module')
def config_dir():
    os.makedirs('test_config')

    bridge_conf = """
    [Accessory]
    DisplayName= MQTT Bridge

    [MQTT]
    HostName = localhost
    Port = 1883
    """

    bulb_conf = """
    [Accessory]
    Category = Lightbulb
    DisplayName = Lamp

    [Lightbulb]
    On = stat/Lamp/POWER cmnd/Lamp/POWER tasmota.POWER
    """

    thermo_conf = """
    [Accessory]
    Category = Sensor
    DisplayName = Thermometer

    [TemperatureSensor]
    CurrentTemperature = stat/Thermometer/DHT11Temperature _ _
    """

    with open(os.path.join('test_config', 'bridge.cfg'), 'w') as f:
        f.write(bridge_conf)

    with open(os.path.join('test_config', 'lamp.cfg'), 'w') as f:
        f.write(bulb_conf)

    with open(os.path.join('test_config', 'thermo.cfg'), 'w') as f:
        f.write(thermo_conf)

    yield 'test_config'

    shutil.rmtree('test_config')


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    # result = runner.invoke(cli.main)
    # assert result.exit_code == 0
    # assert 'homekit_mqtt.cli.main' in result.output
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    # assert '--help  Show this message and exit.' in help_result.output


def test_cfg_loader(config_dir):
    # start the accessory driver on port 51826
    driver = AccessoryDriver(port=51826)

    # load accs
    loader = cfg_loader.CfgLoader(driver, config_dir)
    accs = loader.load_accessories(False)

    assert len(accs) == 2
    assert 'topic_in' in \
        accs[0].services[1].characteristics[0].properties.keys()
    assert 'topic_in' in \
        accs[1].services[1].characteristics[0].properties.keys()

    # save accs
    loader.save_accessories()

    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    fname = os.path.join('test_config', 'lamp.cfg')
    cfg.fname = fname
    cfg.read(fname)

    assert 'AID' in cfg['Accessory'].keys()
