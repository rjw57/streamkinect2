from logging import getLogger
import time

log = getLogger(__name__)

class TestListener(object):
    def __init__(self):
        self.servers = set()

    def add_server(self, info):
        log.info('Listener told to add server: {0}'.format(info))
        self.servers.add(info)

    def remove_server(self, info):
        log.info('Listener told to remove server: {0}'.format(info))
        self.servers.remove(info)

def wait_for_server_add(listener, name, timeout=2):
    delay = 0.1 # seconds
    for tries in range(int(timeout / delay)):
        for s in listener.servers:
            if s.name == name:
                log.info('Server "{0}" found'.format(name))
                return True
        time.sleep(delay)

    log.info('Server "{0}" not found'.format(name))
    return False

def wait_for_server_remove(listener, name, timeout=2):
    delay = 0.1 # seconds
    for tries in range(int(timeout / delay)):
        found = False
        for s in listener.servers:
            if s.name == name:
                found = True
        if not found:
            log.info('Server "{0}" not found'.format(name))
            return True
        time.sleep(delay)

    log.info('Server "{0}" remained in list'.format(name))
    return False

