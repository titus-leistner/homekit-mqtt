import json


class POWER:
    def input(topic, payload):
        if payload[0] != '{':
            return payload == 'ON'
        result = json.loads(payload)
        power = result.get('POWER', None)
        if power is None:
            return None

        return power == 'ON'

    def output(topic, payload):
        if bool(payload):
            return 'ON'
        return 'OFF'


class HOLD:
    def input(topic, payload):
        if payload == 'HOLD':
            return 1
        return None

    def output(topic, payload):
        return None


class HSBColor:
    cache = {}

    def gen_key(topic):
        return '/'.join(topic.split('/')[1:-1])

    def input(topic, payload, chan=0):
        if payload is None:
            return None

        result = json.loads(payload)
        hsb = result.get('HSBColor', None)
        if hsb is None:
            return None

        hsb = hsb.split(',')
        HSBColor.cache[HSBColor.gen_key(topic)] = hsb

        return int(hsb[chan])

    def output(topic, payload, chan=0):
        hsb = HSBColor.cache.get(HSBColor.gen_key(topic), [0, 0, 100])
        hsb[chan] = payload
        HSBColor.cache[HSBColor.gen_key(topic)] = hsb

        hsb = list(map(str, map(int, hsb)))
        hsb = ','.join(hsb)
        return hsb


class Hue:
    def input(topic, payload):
        return HSBColor.input(topic, payload, 0)

    def output(topic, payload):
        return HSBColor.output(topic, payload, 0)


class Saturation:
    def input(topic, payload):
        return HSBColor.input(topic, payload, 1)

    def output(topic, payload):
        return HSBColor.output(topic, payload, 1)


class Brightness:
    def input(topic, payload):
        return HSBColor.input(topic, payload, 2)

    def output(topic, payload):
        return HSBColor.output(topic, payload, 2)


class Dimmer:
    def input(topic, payload):
        result = json.loads(payload)
        dimmer = result.get('Dimmer', None)
        return dimmer

    def output(topic, payload):
        return float(payload)


class ColorTemperature:
    def input(topic, payload):
        result = json.loads(payload)
        ct = result.get('CT', None)
        return ct

    def output(topic, payload):
        ct = int(payload)
        ct = max(153, min(500, ct))

        return ct
