
import unittest
import binascii
import difflib
import signal
import struct
import array
import os

import Xlib.protocol.event
import Xlib.protocol.rq


class CmpArray(object):

    def __init__(self, *args, **kws):
        self.array = array.array(*args, **kws)

    def __len__(self):
        return len(self.array)

    def __getitem__(self, key):
        if isinstance(key, slice):
            x = key.start
            y = key.stop
            return list(self.array[x:y])
        else:
            return self.array[key]

    def __getattr__(self, attr):
        return getattr(self.array, attr)

    def __eq__(self, other):
        return self.array.tolist() == other

Xlib.protocol.rq.array = CmpArray


class DummyDisplay(object):

    def get_resource_class(self, x):
        return None

    event_classes = Xlib.protocol.event.event_class


class TestCase(unittest.TestCase):

    def assertBinaryEqual(self, bin1, bin2):
        if bin1 != bin2:
            self.fail('binary contents differ:\n' + bindiff(bin1, bin2))

    def assertBinaryEmpty(self, bin):
        if len(bin) != 0:
            self.fail('binary content not empty:\n' + ''.join(tohex(bin)))

class BigEndianTest(TestCase):

    @classmethod
    def setUpClass(cls):
        if struct.unpack('BB', struct.pack('H', 0x0100))[0] != 1:
            raise unittest.SkipTest('big-endian tests, skipping on this system')

class LittleEndianTest(TestCase):

    @classmethod
    def setUpClass(cls):
        if struct.unpack('BB', struct.pack('H', 0x0100))[0] != 0:
            raise unittest.SkipTest('little-endian tests, skipping on this system')


def tohex(bin):
    hex = []
    for i in range(0, len(bin), 16):
        hex.append(str(binascii.hexlify(bin[i:i+16])) + '\n')
    return hex

def bindiff(bin1, bin2):
    hex1 = tohex(bin1)
    hex2 = tohex(bin2)
    return ''.join(difflib.ndiff(hex1, hex2))


class XserverTest(TestCase):

    FAKE_DISPLAY = ':99'

    class SigException(Exception):
        pass

    def _setup_xserver(self, xserver):
        def sighandler(signum, frame):
            raise self.SigException()
        previous_sighandler = signal.signal(signal.SIGUSR1, sighandler)
        try:
            self.xserver_pid = os.fork()
            if 0 == self.xserver_pid:
                # This will make the xserver send us a SIGUSR1 when ready.
                signal.signal(signal.SIGUSR1, signal.SIG_IGN)
                # Note the use of `-noreset` so a SIGUSR1 is not
                # send when the last client connection is closed.
                os.execlp(xserver, xserver, '-noreset', self.FAKE_DISPLAY)
                sys.exit(1)
            self.teardown_display = self._teardown_xserver
            # Wait for server to be ready.
            try:
                signal.pause()
            except self.SigException:
                pass
        finally:
            signal.signal(signal.SIGUSR1, previous_sighandler)
        display = os.environ.get('XLIB_TESTS_DISPLAY', self.FAKE_DISPLAY)
        os.environ['DISPLAY'] = display

    def _teardown_xserver(self):
        os.kill(self.xserver_pid, signal.SIGTERM)
        os.waitpid(self.xserver_pid, 0)

    def setUp(self):
        super(XserverTest, self).setUp()
        self.teardown_display = lambda: None
        self.previous_display = os.environ.get('DISPLAY')
        display_type = os.environ.get('XLIB_TESTS_XSERVER', 'xvfb').lower()
        if display_type == 'xvfb':
            self._setup_xserver('Xvfb')
        elif display_type == 'xephyr':
            self._setup_xserver('Xephyr')
        elif display_type == 'system':
            display = os.environ.get('XLIB_TESTS_DISPLAY')
            if display is not None:
                os.environ['DISPLAY'] = display
        else:
            raise ValueError('unsupported display type: %s' % display_type)

    def tearDown(self):
        self.teardown_display()
        if self.previous_display is None:
            del os.environ['DISPLAY']
        else:
            os.environ['DISPLAY'] = self.previous_display
        super(XserverTest, self).tearDown()
