
import inspect
try:
    import cPickle as pickle 
except Exception as e:
    import pickle

import redis
from turbo.log import getLogger

logger = getLogger('smartcache')


class Cache(object):

    def __getattr__(self, name):
        new_name = name.replace('_Cache', '', 1)
        redis_client = self.get_connection(name=name)
        if new_name.startswith('__'):
            attr = getattr(redis_client, new_name[2:], None)
            if attr is not None:
                return attr

        return getattr(Cache, name)

    def get_connection(self, host='localhost', port=6379, db=0, name=None):
        return redis.StrictRedis(host=host, port=port, db=db)

    def inject_connection(self, connection):
        self.get_connection = connection

    def valid(self, key):
        if key is None or key is '':
            return False
        return True

    def pack(self, *args):
        return '_'.join(map(str, args))

    def unpack(self, key):
        return tuple(key.split('_'))

    def set(self, name, value, expire=86400):
        if not self.valid(value):
            return

        if not self.valid(name):
            return
        name = str(name)
        self.__set(name, pickle.dumps(value))
        self.__expire(name, expire)

    def get(self, name):
        data = self.__get(str(name))
        try:
            return pickle.loads(data) if data else data
        except:
            return data

    def exists(self, name):
        return bool(self.__exists(str(name)))

    def delete(self, name):
        return self.__delete(str(name))

    def expire(self, name, expire):
        return self.__expire(str(name), expire)

    def expireat(self, name, timestamp):
        return self.__expireat(str(name), timestamp)

    def persist(self, name):
        return self.__persist(str(name))

    def move(self, name, db):
        return self.__move(str(name), db)

    def object(self, name, infotype='idletime'):
        return self.__object(infotype, str(name))

    def rename(self, name, newname):
        return self.__rename(str(name), str(newname))

    def renamenx(self, name, newname):
        return self.__renamenx(str(name), str(newname))

    def ttl(self, name):
        return self.__ttl(str(name))

    def type(self, name):
        return self.__type(str(name))

    def size(self, key):
        ctype = self.__type(key)
        if ctype == 'set':
            return self.__scard(key)

        if ctype == 'zset':
            return self.__zcard(key)

        if ctype == 'hash':
            return self.__hlen(key)

        if ctype == 'string':
            raise ValueError('%s is string type' % key)

        return self.__llen(key)

    def append(self, name, value):
        return self.__append(str(name), value)

    def scan_db(self):
        start = 0
        result_length = 10
        while result_length:
            start, result = self.scan(start)
            result_length = len(result_length)
            yield result

    def update_dict(self, name, key, value, expire=86400):
        if not self.valid(name):
            return

        if not self.valid(key):
            return

        if not self.valid(value):
            return

        name, key = str(name), str(key)
        self.__hset(name, key, pickle.dumps(value))
        self.__expire(name, expire)

    def dict_value(self, name, key):
        data = self.__hget(str(name), key)
        return pickle.loads(data) if data else data

    def lupdate_list(self, name, data, expire=86400):
        self._update_list(name, data, self.__lpush)

    def rupdate_list(self, name, data, expire=86400):
        self._update_list(name, data, self.__rpush)

    def list_value(self, name, skip=0, limit=1):
        return [pickle.loads(i) for i in self.__lrange(str(name), skip, skip+limit-1)]

    def rpop_value(self, name):
        return self._pop_list_value(name, self.__rpop)

    def lpop_value(self, name):
        return self._pop_list_value(name, self.__lpop)

    def _pop_list_value(self, name, func):
        data = func(str(name))
        if not data:
            return

        return pickle.loads(data)

    def _update_list(self, name, data, func, expire=86400):
        if not self.valid(name):
            return

        result = None
        if self._is_iterable(data):
            result = [pickle.dumps(i) for i in data]
        else:
            result = [pickle.dumps(data)]

        if not result:
            return
        name = str(name)
        func(name, *result)
        self.__expire(name, expire)

    @staticmethod
    def _is_iterable(data):
        return isinstance(data, list) or isinstance(data, tuple) or inspect.isgenerator(data)

    def set_value(self, name, count=1):
        try:
            result = self.srandmember(self.message_wait, count)
        except:
            result = self.srandmember(self.message_wait)

        if result is None:
            return None

        if isinstance(result, list):
            return [pickle.loads(i) for i in result]

        return pickle.loads(result)

    def update_set(self, name, value):
        if not self.valid(name):
            return

        self.__sadd(str(name), pickle.dumps(value))

    def in_set(self, name, value):
        return self.sismember(str(name), pickle.dumps(value))

    def move_set_value(self, src, dst, value):
        return self.smove(str(src), str(dst), pickle.dumps(value))

    def pop_set_value(self, name, value):
        return self.srem(str(name), pickle.dumps(value))

    def sortedlist_value(self, name, skip, limit):
        return [pickle.loads(i) for i in self.__zrangebyscore(str(name), float('-inf'), float('inf'), start=skip, num=limit)]

    def update_sorted_set(self, name, value_list, expire=86400):
        if not self.valid(name):
            return

        if not self._is_iterable(value_list):
            return

        result = []
        if isinstance(value_list, tuple):
            result.append(value_list[1])
            result.append(pickle.dumps(value_list[0]))
        else:
            for value, score in value_list:
                result.append(score)
                result.append(pickle.dumps(value))

        if not result:
            return

        name = str(name)
        try:
            self.__zadd(name, *result)
        except Exception as e:
            logger.exception(e)
        self.__expire(name, expire)

if __name__ == '__main__':
    pass