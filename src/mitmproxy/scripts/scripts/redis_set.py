import redis

_r = redis.Redis()


SECRET = 'secret'


class RedisSet(object):

    def __init__(self, set_name):
        self._prefix = set_name + ':'

    def add(self, v):
        _r.setex(self._prefix + str(v), SECRET, 3600)

    def contains(self, v):
        return _r.get(self._prefix + str(v)) == SECRET


def main():
    rset = RedisSet('test')

    for ix in range(10):
        rset.add(ix)

    for ix in range(3, 13):
        print ix, rset.contains(ix)
    

if __name__ == '__main__':
    main()
