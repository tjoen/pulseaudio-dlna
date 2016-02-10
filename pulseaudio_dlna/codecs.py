#!/usr/bin/python

# This file is part of pulseaudio-dlna.

# pulseaudio-dlna is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pulseaudio-dlna is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pulseaudio-dlna.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import functools
import logging
import re
import inspect
import sys

import pulseaudio_dlna.encoders
import pulseaudio_dlna.rules

logger = logging.getLogger('pulseaudio_dlna.codecs')

CODECS = {}


@functools.total_ordering
class BaseCodec(object):

    ENABLED = True
    IDENTIFIER = None

    def __init__(self):
        self.mime_type = None
        self.suffix = None
        self.priority = None
        self.rules = pulseaudio_dlna.rules.Rules()

    @property
    def enabled(self):
        return type(self).ENABLED

    @enabled.setter
    def enabled(self, value):
        type(self).ENABLED = value

    @property
    def specific_mime_type(self):
        return self.mime_type

    @property
    def encoder(self):
        for encoder_type in self.ENCODERS:
            if encoder_type.AVAILABLE:
                return encoder_type()
        return None

    @classmethod
    def accepts(cls, mime_type):
        for accepted_mime_type in cls.SUPPORTED_MIME_TYPES:
            if mime_type.lower().startswith(accepted_mime_type.lower()):
                return True
        return False

    def get_recorder(self, monitor):
        return pulseaudio_dlna.recorders.PulseaudioRecorder(monitor)

    def __eq__(self, other):
        return type(self) is type(other)

    def __gt__(self, other):
        return type(self) is type(other)

    def __str__(self, detailed=False):
        return '<{} enabled="{}" priority="{}" mime_type="{}">{}{}'.format(
            self.__class__.__name__,
            self.enabled,
            self.priority,
            self.specific_mime_type,
            ('\n' if len(self.rules) > 0 else '') + '\n'.join(
                ['    - ' + str(rule) for rule in self.rules]
            ) if detailed else '',
            '\n    ' + str(self.encoder) if detailed else '',
        )

    def to_json(self):
        attributes = ['priority', 'suffix', 'mime_type']
        d = {
            k: v for k, v in self.__dict__.iteritems()
            if k not in attributes
        }
        d['mime_type'] = self.specific_mime_type
        d['identifier'] = self.IDENTIFIER
        return d


class BitRateMixin(object):

    def __init__(self):
        self.bit_rate = None

    @property
    def encoder(self):
        for encoder_type in self.ENCODERS:
            if encoder_type.AVAILABLE:
                return encoder_type(self.bit_rate)
        return None

    def __eq__(self, other):
        return type(self) is type(other) and self.bit_rate == other.bit_rate

    def __gt__(self, other):
        return type(self) is type(other) and self.bit_rate > other.bit_rate


class Mp3Codec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/mpeg', 'audio/mp3']
    IDENTIFIER = 'mp3'
    ENCODERS = [
        pulseaudio_dlna.encoders.FFMpegMp3Encoder,
        pulseaudio_dlna.encoders.AVConvMp3Encoder,
    ]

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.priority = 18
        self.suffix = 'mp3'
        self.mime_type = mime_string or 'audio/mp3'


class WavCodec(BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/wav', 'audio/x-wav']
    IDENTIFIER = 'wav'
    ENCODERS = [
        pulseaudio_dlna.encoders.FFMpegWavEncoder,
        pulseaudio_dlna.encoders.AVConvWavEncoder,
    ]

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        self.priority = 15
        self.suffix = 'wav'
        self.mime_type = mime_string or 'audio/wav'


class L16Codec(BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/l16']
    IDENTIFIER = 'l16'
    ENCODERS = [
        pulseaudio_dlna.encoders.FFMpegL16Encoder,
        pulseaudio_dlna.encoders.AVConvL16Encoder,
    ]

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        self.priority = 0
        self.suffix = 'pcm16'
        self.mime_type = 'audio/L16'

        self.sample_rate = None
        self.channels = None

        if mime_string:
            match = re.match(
                '(.*?)(?P<mime_type>.*?);'
                '(.*?)rate=(?P<sample_rate>.*?);'
                '(.*?)channels=(?P<channels>\d)', mime_string)
            if match:
                self.mime_type = match.group('mime_type')
                self.sample_rate = int(match.group('sample_rate'))
                self.channels = int(match.group('channels'))

    @property
    def specific_mime_type(self):
        if self.sample_rate and self.channels:
            return '{};rate={};channels={}'.format(
                self.mime_type, self.sample_rate, self.channels)
        else:
            return self.mime_type

    @property
    def encoder(self):
        for encoder_type in self.ENCODERS:
            if encoder_type.AVAILABLE:
                return encoder_type(self.sample_rate, self.channels)
        return None

    def __eq__(self, other):
        return type(self) is type(other) and (
            self.sample_rate == other.sample_rate and
            self.channels == other.channels)

    def __gt__(self, other):
        return type(self) is type(other) and (
            self.sample_rate > other.sample_rate and
            self.channels > other.channels)


class AacCodec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/aac', 'audio/x-aac']
    IDENTIFIER = 'aac'
    ENCODERS = [
        pulseaudio_dlna.encoders.FFMpegAacEncoder,
        pulseaudio_dlna.encoders.AVConvAacEncoder,
    ]

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.priority = 12
        self.suffix = 'aac'
        self.mime_type = mime_string or 'audio/aac'


class OggCodec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/ogg', 'audio/x-ogg', 'application/ogg']
    IDENTIFIER = 'ogg'
    ENCODERS = [
        pulseaudio_dlna.encoders.FFMpegOggEncoder,
        pulseaudio_dlna.encoders.AVConvOggEncoder,
    ]

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.priority = 6
        self.suffix = 'ogg'
        self.mime_type = mime_string or 'audio/ogg'


class FlacCodec(BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/flac', 'audio/x-flac']
    IDENTIFIER = 'flac'
    ENCODERS = [
        pulseaudio_dlna.encoders.FFMpegFlacEncoder,
        pulseaudio_dlna.encoders.AVConvFlacEncoder,
    ]

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        self.priority = 9
        self.suffix = 'flac'
        self.mime_type = mime_string or 'audio/flac'


class OpusCodec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/opus', 'audio/x-opus']
    IDENTIFIER = 'opus'
    ENCODERS = [
        pulseaudio_dlna.encoders.FFMpegOpusEncoder,
        pulseaudio_dlna.encoders.AVConvOpusEncoder,
    ]

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.priority = 3
        self.suffix = 'opus'
        self.mime_type = mime_string or 'audio/opus'


def load_codecs():
    if len(CODECS) == 0:
        logger.debug('Loaded codecs:')
        for name, _type in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(_type) and issubclass(_type, BaseCodec):
                if _type is not BaseCodec:
                    logger.debug('  {} = {}'.format(_type.IDENTIFIER, _type))
                    CODECS[_type.IDENTIFIER] = _type
    return None

load_codecs()
