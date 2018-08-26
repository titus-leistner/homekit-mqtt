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

from homekit_mqtt import cfg_loader, mqtt_bridge, tasmota


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
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_BOOL, 'true') is True
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_FLOAT, '3.14') == 3.14
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_INT, '42') == 42
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_STRING, 'foo') == 'foo'
    assert mqtt_bridge.mqtt2hap(pyhap_char.HAP_FORMAT_DATA, 'bar') == 'bar'

    assert mqtt_bridge.mqtt2hap(
        pyhap_char.HAP_FORMAT_ARRAY, '[1, 1, 2, 3]') == [1, 1, 2, 3]

    assert mqtt_bridge.mqtt2hap(
        pyhap_char.HAP_FORMAT_ARRAY, '{"x" : 1, "y" : 2}') == {'x': 1, 'y': 2}

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


def test_tasmota():
    # test POWER adapter
    assert tasmota.POWER.input('', 'ON') is True
    assert tasmota.POWER.input('', 'OFF') is False
    assert tasmota.POWER.input('', '{"POWER":"ON"}') is True

    assert tasmota.POWER.output('', True) == 'ON'
    assert tasmota.POWER.output('', False) == 'OFF'

    # test HOLD adapter
    assert tasmota.HOLD.input('', 'HOLD') is 1
    assert tasmota.HOLD.input('', 'ON') is None

    # test HSB adapters
    assert tasmota.Hue.input(
        'stat/test/RESULT', '{"HSBColor":"21,42,63"}') == 21
    assert tasmota.Saturation.input(
        'stat/test/RESULT', '{"HSBColor":"21,42,63"}') == 42
    assert tasmota.Brightness.input(
        'stat/test/RESULT', '{"HSBColor":"21,42,63"}') == 63

    assert tasmota.Hue.output('cmnd/test/HSBColor', 30) == '30,42,63'
    assert tasmota.Saturation.output('cmnd/test/HSBColor', 60) == '30,60,63'
    assert tasmota.Brightness.output('cmnd/test/HSBColor', 90) == '30,60,90'

    assert tasmota.Dimmer.input(
        'stat/test/RESULT', '{"Dimmer": 42}') == 42

    # test ColorTemperature adapter
    assert tasmota.ColorTemperature.input('', '{"CT": 250}') == 250
    assert tasmota.ColorTemperature.output('', 140) == 153
    assert tasmota.ColorTemperature.output('', 600) == 500
    assert tasmota.ColorTemperature.output('', 250) == 250
