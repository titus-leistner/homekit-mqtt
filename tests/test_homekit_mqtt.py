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
import pyhap.characteristic as pyhap_char

from homekit_mqtt import cfg_loader, mqtt_bridge


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


def test_mqtt_bridge():
    # test conversion from MQTT to HAP
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_BOOL, b'true') is True
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_FLOAT, b'3.14') == 3.14
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_INT, b'42') == 42
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_STRING, b'foo') == 'foo'
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_DATA, b'bar') == 'bar'

    assert mqtt_bridge.mqtt2hap(
        pyhap_char.HAP_FORMAT_ARRAY, b'[1, 1, 2, 3]') == [1, 1, 2, 3]

    assert mqtt_bridge.mqtt2hap(
        pyhap_char.HAP_FORMAT_ARRAY, b'{"x" : 1, "y" : 2}') == {'x': 1, 'y': 2}

    # test conversion from HAP to python types
    assert mqtt_bridge.hap2var(pyhap_char.HAP_FORMAT_BOOL, True) is True
    assert mqtt_bridge.hap2var(pyhap_char.HAP_FORMAT_FLOAT, '3.14') == 3.14
    assert mqtt_bridge.hap2var(pyhap_char.HAP_FORMAT_INT, 42) == 42
    assert mqtt_bridge.hap2var(pyhap_char.HAP_FORMAT_STRING, 0.5) == '0.5'
    assert mqtt_bridge.hap2var(pyhap_char.HAP_FORMAT_DATA, 42) == '42'

    assert mqtt_bridge.hap2var(
        pyhap_char.HAP_FORMAT_ARRAY, [1, 1, 2, 3]) == '[1, 1, 2, 3]'

    assert mqtt_bridge.hap2var(
        pyhap_char.HAP_FORMAT_ARRAY, {'x': 1, 'y': 2}) == '{"x": 1, "y": 2}'
