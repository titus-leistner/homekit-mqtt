import configparser
import logging
import os

from pyhap.const import *
from pyhap.accessory import Accessory, Bridge
import pyhap.loader as loader

logger = logging.getLogger(__name__)

categories = {
    'Other': CATEGORY_OTHER,
    'Bridge': CATEGORY_BRIDGE,
    'Fan': CATEGORY_FAN,
    'GarageDoorOpener': CATEGORY_GARAGE_DOOR_OPENER,
    'Lightbulb': CATEGORY_LIGHTBULB,
    'DoorLock': CATEGORY_DOOR_LOCK,
    'Outlet': CATEGORY_OUTLET,
    'Switch': CATEGORY_SWITCH,
    'Thermostat': CATEGORY_THERMOSTAT,
    'Sensor': CATEGORY_SENSOR,
    'AlarmSystem': CATEGORY_ALARM_SYSTEM,
    'Door': CATEGORY_DOOR,
    'Window': CATEGORY_WINDOW,
    'WindowCovering': CATEGORY_WINDOW_COVERING,
    'ProgrammableSwitch': CATEGORY_PROGRAMMABLE_SWITCH,
    'RangeExtender': CATEGORY_RANGE_EXTENDER,
    'Camera': CATEGORY_CAMERA
}


class CfgLoader:
    """
    Loader class that loads accessories from a directory with config files.

    A config file should contain an [Accessory] section with its 'Category' and 
    optional info about the accessory. (DisplayName, FirmwareRevision,
    Manufacturer, Model, SerialNumber, AID).

    In addition to that, the config file should contain one section for each
    service the accessory provides, containing one field for each corresponding
    characteristic:

    [ServiceName]
    AccessoryName1 = mqtt/input/topic mqtt/output/topic AdapterClass
    AccessoryName2 = mqtt/input/topic mqtt/output/topic AdapterClass

    If there is no topic or adapter class, replace it with a '_'.

    Adapter classes are defined in the module 'adapters'.
    """

    def __init__(self, driver, cfg_path='config'):
        """
        Initialize the loader

        :param driver: the AccessoryDriver
        :type driver: pyhap.accessory_driver.AccessoryDriver

        :param cfg_path: path to config-directory
        :type cfg_path: str
        """
        self.driver = driver
        self.cfg_path = cfg_path

        self.cfgs = []
        self.accs = None

    def load_accessories(self, override_ids=False):
        """
        Return a list of initialized accessories specified by the config files.

        The characteristics of those accessories should contain three additional
        values: topic_in, topic_out and adapter used by the MqttBridge class.

        :param override_ids: override accessory ids for a new bridge config
        :type override_ids: bool
        """
        # find all cfg files, but skip the bridge.cfg
        fnames = []
        for r, _, fs in os.walk(self.cfg_path):
            fnames += [os.path.join(r, f) for f in fs if f != 'bridge.cfg'
                       and f != 'accessory.state']

        for fname in fnames:
            cfg = configparser.ConfigParser()
            cfg.optionxform = str
            cfg.fname = fname

            try:
                cfg.read(fname)
                self.cfgs.append(cfg)
            except Exception as e:
                logger.warn(
                    'Skipping "{}" because of Exception: {}'.format(fname,
                                                                    str(e)))

        # sort by aid
        max_aid = 2**63 - 1
        self.cfgs = sorted(self.cfgs, key=lambda cfg: int(
            cfg['Accessory'].get('AID', max_aid)))

        self.accs = []
        for cfg in self.cfgs:
            try:
                # init accessory
                acc_def = cfg['Accessory']
                if acc_def['Category'] not in categories:
                    logger.warn('Unknown category: "{}"'.format(
                        acc_def['category']))
                    continue
                if 'DisplayName' not in acc_def.keys():
                    # use filename as display name
                    acc_def['DisplayName'] = os.path.basename(fname).split('.')[
                        0]

                aid = None
                if not override_ids:
                    aid = acc_def.get('AID', None)
                if aid is not None:
                    aid = int(aid)

                acc = Accessory(self.driver, acc_def['DisplayName'], aid=aid)
                acc.category = categories[acc_def.get('Category', 'Other')]

                acc.set_info_service(acc_def.get('FirmwareRevision', None),
                                     acc_def.get('Manufacturer', None),
                                     acc_def.get('Model', None),
                                     acc_def.get('SerialNumber', None))

                # init services
                serv_types = cfg.sections()
                serv_types.remove('Accessory')
                for serv_type in serv_types:
                    serv_def = cfg[serv_type]
                    serv = loader.get_loader().get_service(serv_type)
                    char_types = serv_def.keys()

                    for char_type in char_types:
                        char_def = serv_def[char_type]
                        char_def = char_def.split()

                        # init characteristic
                        try:
                            char = loader.get_loader().get_char(char_type)

                            if len(char_def) != 3:
                                logger.warn(
                                    'Skipping caracteristic "{}" because of invalid format'.format(char_type))
                                continue

                            # add topics and adapter
                            char.properties['topic_in'] = None
                            char.properties['topic_out'] = None
                            char.properties['adapter'] = None

                            if char_def[0] != '_':
                                char.properties['topic_in'] = char_def[0]
                            if char_def[1] != '_':
                                char.properties['topic_out'] = char_def[1]
                            if char_def[2] != '_':
                                char.properties['adapter'] = char_def[2]

                            # add characteristic
                            added = False
                            for i, old_char in enumerate(serv.characteristics):
                                if old_char.type_id == char.type_id:
                                    serv.characteristics[i] = char
                                    added = True
                                    break

                            if not added:
                                serv.add_characteristic(char)

                        except KeyError as e:
                            continue

                    acc.add_service(serv)

                self.accs.append(acc)
                logger.info('Added accessory "{}"'.format(acc.display_name))

            except Exception as e:
                logger.warn('Skipping "{}" because of Exception: {}: {}'.format(
                    type(e), cfg.fname, str(e)))

        return self.accs

    def save_accessories(self):
        """
        Save the accessories (with new aid's)
        """
        # add new aid's
        for i in range(len(self.accs)):
            self.cfgs[i]['Accessory']['AID'] = str(self.accs[i].aid)
            with open(self.cfgs[i].fname, 'w') as f:
                self.cfgs[i].write(f)
