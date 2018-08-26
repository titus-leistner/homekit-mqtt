import os
import json
import logging
import configparser
import paho.mqtt.client as mqtt

from pyhap.accessory import Bridge
from pyhap.const import CATEGORY_BRIDGE
import pyhap.characteristic as pyhap_char

from homekit_mqtt import adapters

logger = logging.getLogger(__name__)


def mqtt2hap(hap_format, value):
    """
    Convert the MQTT payload value to a valid HAP value

    :param hap_format: The HAP_FORMAT constant from pyhap.pyhap_characteristic
    :type hap_format: str

    :param value: The value to convert
    :type value: bin
    """
    if hap_format == pyhap_char.HAP_FORMAT_BOOL:
        if value == b'true':
            return True
        return bool(value)
    elif hap_format == pyhap_char.HAP_FORMAT_FLOAT:
        return float(value)
    elif hap_format == pyhap_char.HAP_FORMAT_ARRAY:
        return json.loads(value)
    elif hap_format == pyhap_char.HAP_FORMAT_DICTIONARY:
        return json.loads(value)
    elif hap_format == pyhap_char.HAP_FORMAT_TLV8:
        return str(value)
    elif hap_format in pyhap_char.HAP_FORMAT_NUMERICS:
        return int(value)
    elif hap_format in [pyhap_char.HAP_FORMAT_STRING,
                        pyhap_char.HAP_FORMAT_DATA]:
        return str(value)

    return str(value)


def hap2var(hap_format, value):
    """
    Convert the HAP payload value to a python var

    :param hap_format: The HAP_FORMAT constant from pyhap.pyhap_characteristic
    :type hap_format: str

    :param value: The value to convert
    :type value: bin
    """
    if hap_format == pyhap_char.HAP_FORMAT_BOOL:
        return bool(value)
    elif hap_format == pyhap_char.HAP_FORMAT_FLOAT:
        return float(value)
    elif hap_format == pyhap_char.HAP_FORMAT_STRING:
        return str(value)
    elif hap_format == pyhap_char.HAP_FORMAT_ARRAY:
        return json.dumps(value)
    elif hap_format == pyhap_char.HAP_FORMAT_DICTIONARY:
        return json.dumps(value)
    elif hap_format == pyhap_char.HAP_FORMAT_DATA:
        return str(value)
    elif hap_format == pyhap_char.HAP_FORMAT_TLV8:
        return str(value)
    elif hap_format in pyhap_char.HAP_FORMAT_NUMERICS:
        return int(value)

    return str(value)


class MqttBridge(Bridge):
    """
    HomeKit-Bridge with a MQTT-Interface

    Publishes requests from iOS-devices to the corresponding
    accessory.properties['topic_out']

    Subscribes to each
    accessory.properties['topic_in']

    and sends the received values to iOS-devices.

    The optional adapter class accessory.properties['adapter']
    from the adapters module is used.
    """
    category = CATEGORY_BRIDGE

    def __init__(self, cfg, *args, **kwargs):
        """
        Init

        :param cfg: directory containing the configuration
        :type cfg: str
        """
        super().__init__(*args, **kwargs)

        self.client = None
        self.getter_callbacks = {}

        self._load_cfg(cfg)
        self._init_mqtt(self.broker_addr, self.creds)

    def _init_mqtt(self, broker_addr, creds=None):
        """
        Initialize the MQTT client

        :param broker_addr: The address:port of the MQTT Broker
        :type broker_addr: tuple(str, int)

        :param creds: login credentials for the Broker
        :type creds: tuple(username, password)
        """
        def on_connect(client, userdata, flags, rc):
            logger.info('Connected to MQTT Broker with result code ' + str(rc))

            for topic in self.getter_callbacks.keys():
                self.client.subscribe(topic)

        def on_disconnect(client, userdata, rc):
            logger.info('Disconnected from MQTT Broker with result code ' +
                        str(rc))

        def on_message(client, userdata, message):
            self.update_char(message.topic, message.payload)

        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message

        if creds is not None:
            self.client.username_pw_set(creds[0], creds[1])

        self.client.connect(broker_addr[0], broker_addr[1])

    def _load_cfg(self, cfg):
        """
        Loads the bridge configuration from cfg/bridge.cfg

        :param cfg: directory containing the configuration
        :type cfg: str
        """
        fname = os.path.join(cfg, 'bridge.cfg')
        cfg = configparser.ConfigParser()
        cfg.optionxform = str
        cfg.fname = fname
        cfg.read(fname)

        # Load Accessory Info
        acc_def = cfg['Accessory']

        if 'DisplayName' in acc_def.keys():
            self.display_name = acc_def['DisplayName']

        self.set_info_service(acc_def.get('FirmwareRevision', None),
                              acc_def.get('Manufacturer', None),
                              acc_def.get('Model', None),
                              acc_def.get('SerialNumber', None))

        mqtt_def = cfg['MQTT']
        self.broker_addr = (mqtt_def['HostName'], int(mqtt_def['Port']))

        self.creds = None
        username = mqtt_def.get('UserName', None)
        password = mqtt_def.get('Password', None)

        if username is not None and password is not None:
            self.creds = (username, password)

    def __getstate__(self):
        """
        Return the state of this instance
        """
        state = super().__getstate__()
        state['client'] = None
        state['broker_addr'] = self.broker_addr
        return state

    def __setstate__(self, state):
        """
        Load the state and set up the MQTT client
        with the address in the state.
        """
        self.__dict__.update(state)
        self._set_server(state['broker_addr'])

    def update_char(self, topic, payload):
        """
        Update a characteristic from a received MQTT message

        :param topic: topic of the MQTT message
        :type topic: str

        :param payload: payload of the MQTT message
        :type payload: bytes
        """
        # split topic into acc, char, serv
        callback = self.getter_callbacks.get(topic, None)
        if callback is None:
            self.warn('Received unknown topic "{}"'.format(topic))
            return

        callback(payload)

    def get_adapter(self, name):
        """
        Gets an adapter class by its name. The adapter has to be imported to
        adapters.py

        :param name: name of the adapter
        :type name: str
        """
        if name is None:
            return None

        name = name.split('.')
        adap = adapters

        try:
            for part in name:
                adap = getattr(adap, part)

        except AttributeError as e:
            self.warn('Unknown adapter "{}"'.format(name))
            return None

        return adap

    def add_accessory(self, acc):
        """
        Add a new accessory to this MqttBridge

        :param acc: the accessory
        :type acc: pyhap.accessory.Accessory
        """
        def build_setter_callback(old_callback, topic, adapter, hap_format):
            def setter_callback(value):
                # Call old callback
                if old_callback is not None:
                    old_callback(value)

                value = hap2var(hap_format, value)

                # all adapter
                if adapter is not None:
                    try:
                        value = adapter.output(topic, value)
                    except Exception as e:
                        self.warn('Exception in {}.output(): {}'.format(
                            adapter.__name__, e))

                if value is not None:
                    # publish value
                    self.client.publish(topic, value)

            return setter_callback

        def build_getter_callback(old_callback, topic, adapter, hap_format,
                                  char):
            def getter_callback(payload):
                # Call old callback
                if old_callback is not None:
                    old_callback(payload)

                # all adapter
                if adapter is not None:
                    try:
                        payload = adapter.input(topic, payload.decode('utf-8'))
                    except Exception as e:
                        self.warn('Exception in {}.input(): {}'.format(
                            adapter.__name__, e))

                if payload is not None:
                    payload = mqtt2hap(hap_format, payload)
                    char.set_value(payload)

            return getter_callback

        # Add callbacks to characteristics
        for serv in acc.services:
            for char in serv.characteristics:
                adapter = self.get_adapter(
                    char.properties.get('adapter', None))
                hap_format = char.properties[pyhap_char.PROP_FORMAT]

                # setter callback
                topic_out = char.properties.get('topic_out', None)
                if topic_out is not None:
                    char.setter_callback = build_setter_callback(
                        char.setter_callback, topic_out, adapter, hap_format)

                # getter callback
                topic_in = char.properties.get('topic_in', None)
                if topic_in is not None:
                    self.getter_callbacks[topic_in] = build_getter_callback(
                        self.getter_callbacks.get(topic_in, None),
                        topic_in, adapter, hap_format, char)

        super().add_accessory(acc)

    def run(self):
        """
        Start the MQTT Client Loop
        """
        super().run()
        logger.info("Starting MQTT Client Loop.")
        self.client.loop_start()

    def stop(self):
        """
        Stop the server and the MQTT Client Loop
        """
        super().stop()

        logger.info("Stopping MQTT Client Loop.")
        self.client.loop_stop()

    def warn(self, warning):
        """
        Helper class to log warnings to the logger and MQTT

        :param warning: the warning
        :type warning: str
        """
        logger.warn(warning)
        self.client.publish('stat/homekit/log', str(warning))
