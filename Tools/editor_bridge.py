"""Process local editor tasks on the editor thread, allowing ticks between tasks."""
import json
import sys
import time
import traceback
from pathlib import Path
import unreal

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0,str(TOOLS))
QUEUE = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'EditorTask.py'
RESULT = QUEUE.parent / 'EditorTaskResult.json'
last_seen = QUEUE.stat().st_mtime_ns if QUEUE.exists() else 0
last_poll = 0


def tick(delta):
    global last_seen,last_poll
    now=time.monotonic()
    if now-last_poll < .4:
        return
    last_poll=now
    if not QUEUE.exists() or QUEUE.stat().st_mtime_ns==last_seen:
        return
    last_seen=QUEUE.stat().st_mtime_ns
    try:
        scope={'__name__':'__editor_task__','__file__':str(QUEUE)}
        exec(compile(QUEUE.read_text(encoding='utf-8-sig'),str(QUEUE),'exec'),scope)
        status={'ok':True,'task':last_seen,'result':scope.get('RESULT',None)}
    except Exception:
        status={'ok':False,'task':last_seen,'error':traceback.format_exc()}
        unreal.log_error(status['error'])
    RESULT.write_text(json.dumps(status,ensure_ascii=False,indent=2,default=str),encoding='utf-8')


handle=unreal.register_slate_post_tick_callback(tick)
unreal.log('EDITOR_TASKS_READY')
