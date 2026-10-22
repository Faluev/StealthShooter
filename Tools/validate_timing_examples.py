"""Observe latent actions across real editor frames in a play world."""
import json
from pathlib import Path
import unreal

def start():
    world=unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
    actor=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_actor_label()=='TimingExamples')
    state={'step':0,'checks':[],'finished':False}
    now=lambda:unreal.GameplayStatics.get_time_seconds(world)
    state['started']=now()
    state['initial_timer_count']=actor.get_editor_property('TimerCount')
    actor.call_method('StartNormalDelay');actor.call_method('StartRetriggerDelay')
    def check(name,value):
        assert value,name
        state['checks'].append({'name':name,'passed':True})
    def tick(delta):
        try:
            elapsed=now()-state['started']
            if state['step']==0 and elapsed>=.5:
                check('Sequence immediate branch',actor.get_editor_property('Immediate'))
                actor.call_method('StartNormalDelay');actor.call_method('StartRetriggerDelay');state['step']=1
            elif state['step']==1 and elapsed>=1.2:
                check('Delay ignores repeat while pending',actor.get_editor_property('NormalCount')==1)
                check('Retriggerable Delay restarts countdown',actor.get_editor_property('RetriggerCount')==0)
                state['step']=2
            elif state['step']==2 and elapsed>=1.8:
                check('Retriggerable Delay eventually completes',actor.get_editor_property('RetriggerCount')==1)
                normal=actor.get_editor_property('NormalTime')-state['started']
                restart=actor.get_editor_property('RetriggerTime')-state['started']
                check('Normal Delay timing',.9<=normal<=1.2)
                check('Retriggerable Delay timing',1.4<=restart<=1.75)
                state['step']=3
            elif state['step']==3 and elapsed>=4.3:
                check('Three second Delay completed',actor.get_editor_property('Delayed'))
                check('Looping two second timer fired',2<=actor.get_editor_property('TimerCount')-state['initial_timer_count']<=3)
                state['finished']=True
        except Exception as error:
            state['error']=str(error);state['finished']=True
        if state['finished']:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            output={k:v for k,v in state.items() if k!='handle'}
            output['passed']=len(state['checks'])
            path=Path(__file__).resolve().parents[1]/'Docs/TimingValidation.json'
            path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    state['handle']=unreal.register_slate_post_tick_callback(tick)
    return {'started':True}
