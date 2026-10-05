"""Independent Windows lock contender: explicit post-construction readiness."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import time
from contextlib import contextmanager

OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
tempfile.tempdir=str(OUT)
os.environ['TMP']=os.environ['TEMP']=str(OUT)
def deny(event,args):
    if event.startswith('socket.'):raise RuntimeError('AUDIT_NETWORK_DENIED:'+event)
    if event=='open':
        mode,flags=args[1],args[2]
        if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            if isinstance(args[0],(str,bytes,os.PathLike)) and not Path(os.fsdecode(args[0])).absolute().is_relative_to(OUT):raise RuntimeError('WRITE_OUTSIDE_AUDIT')
    if event=='os.mkdir' and not Path(args[0]).absolute().is_relative_to(OUT):raise RuntimeError('MKDIR_OUTSIDE_AUDIT')
sys.addaudithook(deny)
parser=argparse.ArgumentParser()
for name in ('repo','directory','run-id','bad','sync'):parser.add_argument('--'+name,required=True)
a=parser.parse_args();sys.path.insert(0,str(Path(a.repo)/'tools'))
import g_cal1_lab as lab
from g_cal1_contract import Package
from g_extract1_contract import IntegrityError
from g_extract1_journal import write_once
p=Package();r=lab.Run(p,a.directory,a.run_id,resume=True)
sync=Path(a.sync)
write_once(sync/'loaded.json',{'pid':os.getpid(),'Package_loaded':True,'Run_loaded':True})
end=time.monotonic()+40
while not (sync/'go.json').exists():
    if time.monotonic()>end:raise RuntimeError('parent go timeout')
    time.sleep(.01)
original=lab.run_lock
@contextmanager
def lock(directory):
    write_once(sync/'attempting.json',{'pid':os.getpid(),'Package_loaded':True,'Run_loaded':True,'next':'OS lock acquisition'})
    with original(directory):
        write_once(sync/'acquired.json',{'pid':os.getpid()})
        yield
lab.run_lock=lock
try:r.verify_resume(a.bad)
except IntegrityError as exc:
    write_once(sync/'result.json',{'event':exc.event,'incidents':r.incidents.read()})
    sys.exit(0)
raise SystemExit(3)
