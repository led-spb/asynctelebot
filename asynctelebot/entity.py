import collections


class Entity(object):
    def __init__(self, **kwargs):
        for attr in self.__slots__:
            if attr in kwargs:
                setattr(self, attr, kwargs[attr])

    def to_dict(self):
        result = {}
        for attr in self.__slots__:
            if hasattr(self, attr):
                result[attr] = getattr(self, attr)
        return result


File = collections.namedtuple('File', ['name', 'data', 'mime'])


class Photo(Entity):
    __slots__ = ['photo', 'caption']


class Audio(Entity):
    __slots__ = ['audio', 'caption', 'duration', 'performer', 'title']


class Document(Entity):
    __slots__ = ['document', 'caption']
    __files__ = ['document']


class Sticker(Entity):
    __slots__ = ['sticker']


class Video(Entity):
    __slots__ = ['video', 'duration', 'width', 'height', 'caption']
    __files__ = ['video']


class Voice(Entity):
    __slots__ = ['voice', 'caption', 'duration']


class Location(Entity):
    __slots__ = ['latitude', 'longitude']


class Venue(Entity):
    __slots__ = ['latitude', 'longitude', 'title', 'address', 'foursquare_id']


class Contact(Entity):
    __slots__ = ['phone_number', 'first_name', 'last_name']
