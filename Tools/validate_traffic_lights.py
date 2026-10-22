"""Check real material changes and timer spacing over complete color cycles."""
import json,re,time
from pathlib import Path
import unreal

def start():
    world=unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
    manager=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_class().get_name()=='BP_TrafficLightsManager_C')
    get=manager.get_editor_property
    order=list(get('ColorOrder'));lights=list(get('Lights'))
    initial_count=get('CycleCount');initial_index=order.index(get('CurrentColor'))
    settings=get('ColorSettings')
    key=next(k for k in re.findall(r'([A-Za-z][A-Za-z0-9_]+)=',settings.export_text()) if k.startswith('ColorMap_'))
    colors=dict(settings.get_editor_property(key))
    state={'checks':[],'transitions':[],'mode':'equal','observed':0,'previous_count':get('CycleCount'),'previous_time':None,'previous_delay':None,'deadline':time.monotonic()+90,'finished':False}
    def check(name,condition):
        assert condition,name
        state['checks'].append({'name':name,'passed':True})
    check('Data Table row loaded',get('LoadedSettings'))
    check('Four supplied traffic light actors',len(lights)==4)
    check('Configured Green Yellow Red key sequence',[x.value for x in order]==[2,1,0])
    check('Every light has its dynamic material',all(a.get_editor_property('Material') is not None for a in lights))
    def tick(delta):
        try:
            assert time.monotonic()<state['deadline'],'Timed out waiting for color cycles'
            count=get('CycleCount')
            if count!=state['previous_count']:
                now=unreal.GameplayStatics.get_time_seconds(world)
                color=get('CurrentColor');expected=colors[color]
                check(state['mode']+' cycle follows configured order '+str(count),color==order[(initial_index+count-initial_count)%len(order)])
                for index,a in enumerate(lights):
                    actual=a.get_editor_property('Material').get_vector_parameter_value('Color')
                    check(state['mode']+' light '+str(index+1)+' matches Map '+str(count),max(abs(actual.r-expected.r),abs(actual.g-expected.g),abs(actual.b-expected.b))<.0001)
                if state['previous_time'] is not None:
                    spacing=now-state['previous_time']
                    check(state['mode']+' timer spacing '+str(count),abs(spacing-state['previous_delay'])<.2)
                state['transitions'].append({'mode':state['mode'],'cycle':count,'color':str(color),'value':color.value,'time':now,'next_delay':get('NextDelay')})
                state['previous_count']=count;state['previous_time']=now;state['previous_delay']=get('NextDelay');state['observed']+=1
                if state['mode']=='equal' and state['observed']>=7:
                    manager.set_editor_property('VariableIntervals',True,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
                    state.update(mode='variable',observed=0,previous_time=None)
                elif state['mode']=='variable' and state['observed']>=7:
                    check('Variable intervals select Green 3 Yellow 1 Red 5',all(abs(row['next_delay']-{2:3,1:1,0:5}[row['value']])<.001 for row in state['transitions'] if row['mode']=='variable'))
                    state['finished']=True
        except Exception as error:
            state['error']=str(error);state['finished']=True
        if state['finished']:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            manager.set_editor_property('VariableIntervals',False,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            manager.call_method('InitializeTraffic')
            output={k:v for k,v in state.items() if k not in ['handle','deadline']}
            output['passed']=len(state['checks'])
            (Path(__file__).resolve().parents[1]/'Docs/TrafficLightsValidation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    state['handle']=unreal.register_slate_post_tick_callback(tick)
    return {'started':True,'expected_seconds':40}
