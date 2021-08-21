import sys
import traceback

from init import init_bot
import logging
import os
import subprocess
from queue import Queue, Empty
from threading import Thread
import locale


encode = 'UTF-8'
if locale.getdefaultlocale()[1] == 'cp936':
    encode = 'GBK'


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

init_bot()

logging.basicConfig(format="%(msg)s", level=logging.INFO)
botdir = './core/bots/'
lst = os.listdir(botdir)
runlst = []
for x in lst:
    bot = f'{botdir}{x}/bot.py'
    if os.path.exists(bot):
        p = subprocess.Popen(f'python {bot}', shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.abspath('.'))
        runlst.append(p)
q = Queue()
threads = []
for p in runlst:
    threads.append(Thread(target=enqueue_output, args=(p.stdout, q)))

for t in threads:
    t.daemon = True
    t.start()

while True:
    try:
        line = q.get_nowait()
    except Empty:
        pass
    except KeyboardInterrupt:
        for x in runlst:
            x.kill()
    else:
        try:
            logging.info(line[:-1].decode(encode))
        except Exception:
            print(line)
            traceback.print_exc()

    # break when all processes are done.
    if all(p.poll() is not None for p in runlst):
        break
