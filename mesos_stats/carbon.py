import socket
import struct
import time
import os
from mesos_stats.util import log

class Carbon:
    def __init__(self, host, prefix, pickle=False):
        self.host = host
        self.prefix = prefix
        self.port = None
        self.sock = None
        self.pickle = pickle
        self.timeout = 30

    def connect(self, port):
        if self.sock != None:
            raise Exception("Attempt to connect an already connected socket.")
        self.port = port
        self.sock = socket.socket()
        self.sock.settimeout(1.0)
        self.sock.connect((self.host, self.port))

    def ensure_connected(self, port):
        if self.sock == None:
            self.connect(port)
        elif self.port != port:
            self.close()
            self.sock.connect(port)
        timeval = struct.pack('ll', self.timeout, 0)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, timeval)

    def close(self):
        self.sock.close()
        self.sock = None

    def send_metrics(self, metrics, timeout, timestamp):
        self.timeout = timeout
        ts = int(timestamp)
        # Confusing control-flow...
        # If the send_metrics_pickle fails on socket.error, we
        # simply pass through to the send_metrics_plaintext.
        # If the send_metrics_pickle succeeds, we return early.
        # Well, I hope that's how it works.
        if self.pickle:
            try:
                self.send_metrics_pickle(metrics, ts)
                return
            except socket.error:
                pass
        
        self.send_metrics_plaintext(metrics, ts)

    def send_metrics_plaintext(self, metrics, ts):
        try:
            self.ensure_connected(2003)
            self.all_stats = ""
            def append(k, v):
                line = "%s %f %d\n" % (k, v, ts)
                self.all_stats += line
            self.forEachPrefixedMetric(metrics, append)
            totalsent = 0
            l = len(self.all_stats)
            iterations = 0
            while totalsent < l:
                iterations += 1
                sent = self.sock.send(self.all_stats[totalsent:])
                if sent == 0:
                    raise RuntimeError("socket connection broken")
                totalsent += sent
            if iterations != 1:
                log("INFO: Send took %s iterations" % iterations)
            log("%s out of %s (%s%s) characters sent successfully in %s iteration(s)." % (totalsent, l, (l/totalsent)*100, "%", iterations))
        finally:
            self.close()

    def send_metrics_pickle(self, metrics, ts):
        try:
            self.ensure_connected(2004)
            tuples = []
            ts = int(time.time())
            def addToTuple(k, v):
                tuples.append((k, (ts, v)))
            self.forEachPrefixedMetric(metrics, addToTuple)
            payload = pickle.dumps(tuples, protocol=2)
            header = struct.pack("!L", len(payload))
            message = header + payload
            self.sock.send(message)
        finally:
            self.close()

    def forEachPrefixedMetric(self, metrics, f):
        for m in metrics:
            for r in m.Results():
                k, v = r
                f(self.prefix + "." + k, v)
