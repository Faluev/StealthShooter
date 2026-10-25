"""Exercise actual Enhanced Input against the local Fab geometry in Play."""
import json,math,re,time,traceback
from pathlib import Path
import unreal

handle=None
checks=[];trials=[];cases=[];index=stage=0
world=pawn=inputs=None
started=0;origin=None;prepared={}


def check(name,ok,detail=None):
    checks.append({'check':name,'passed':bool(ok),'detail':detail})
    if not ok:raise AssertionError(name+': '+str(detail))


def vec(v):return [round(v.x,4),round(v.y,4),round(v.z,4)]


def trace(a,b):
    hit=unreal.SystemLibrary.capsule_trace_single_by_profile(world,a,b,pawn.capsule_component.get_scaled_capsule_radius(),pawn.capsule_component.get_scaled_capsule_half_height(),'Pawn',False,[pawn],unreal.DrawDebugTrace.NONE)
    if not hit:return None
    text=hit.export_text()
    values=re.search(r'(?:^|,)Location=\(X=([^,]+),Y=([^,]+),Z=([^\)]+)\)',text)
    return {'location':unreal.Vector(*(float(x) for x in values.groups())),'penetrating':'bStartPenetrating=True' in text,'text':text}


def inject(v):
    inputs.inject_input_vector_for_action(unreal.load_asset('/Game/ThirdPerson/Input/Actions/IA_Dash'),unreal.Vector(v,0,0),[],[])


def finish(error=None):
    global handle
    if handle:unreal.unregister_slate_post_tick_callback(handle);handle=None
    if pawn and inputs and origin:
        inject(0);pawn.character_movement.stop_movement_immediately();pawn.set_actor_location(origin,False,True);pawn.character_movement.set_movement_mode(unreal.MovementMode.MOVE_WALKING)
    folder=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))/'Docs'
    data={'map':world.get_path_name() if world else None,'checks':checks,'trials':trials,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'error':error}
    (folder/'DashRuinsValidation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    unreal.log('HW09_RUINS_VALIDATION_FINISHED')


def setup():
    global prepared,stage
    name,target,outward=cases[index]
    pawn.character_movement.stop_movement_immediately();pawn.character_movement.set_movement_mode(unreal.MovementMode.MOVE_FLYING)
    if target:
        center,extent=target.get_actor_bounds(False)
        center.z=96
        margin=abs(outward.x)*extent.x+abs(outward.y)*extent.y+80
        hit=trace(center+outward*margin,center)
        check(name+': visible obstacle has blocking collision',hit is not None)
        start=hit['location']+outward*120
        direction=outward*-1
    else:
        start=unreal.Vector(2100,1738,96);direction=unreal.Vector(1,0,0)
    end=start+direction*300
    expected=trace(start,end)
    check(name+': fixture starts outside blocking geometry',not expected or not expected['penetrating'])
    pawn.set_actor_location(start,False,True)
    pawn.set_actor_rotation(unreal.Rotator(yaw=math.degrees(math.atan2(direction.y,direction.x))),False)
    prepared={'name':name,'start':start,'direction':direction,'expected':expected,'cue_before':pawn.get_editor_property('DashCueCount')}
    inject(1);stage=2


def tick(dt):
    global world,pawn,inputs,origin,stage,cases,index,started
    try:
        if time.monotonic()-started>100:raise TimeoutError('Fab collision checks timed out')
        if stage==0:
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:return
            world=worlds[0];pawn=unreal.GameplayStatics.get_player_pawn(world,0)
            if not pawn:return
            assert 'L_DashRuins' in world.get_path_name()
            inputs=next(s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem) if not s.get_name().startswith('Default__') and s.get_outer().get_world()==world)
            origin=pawn.get_actor_location()
            actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor)
            rocks=[a for a in actors if a.get_actor_label().startswith('Ruins_DashRock_')]
            check('Four Fab rocks are present',len(rocks)==4,len(rocks))
            for rock in sorted(rocks,key=lambda a:a.get_actor_label()):
                for direction,outward in [('west',unreal.Vector(-1,0,0)),('east',unreal.Vector(1,0,0)),('south',unreal.Vector(0,-1,0)),('north',unreal.Vector(0,1,0))]:
                    cases.append((rock.get_actor_label()+'_'+direction,rock,outward))
            cases.append(('Gateway_opening',None,None))
            stage=1
        elif stage==1:setup()
        elif stage==2:
            position=pawn.get_actor_location();expected=prepared['expected'];delta=position-prepared['start']
            name=prepared['name'];direction=prepared['direction']
            if expected:
                check(name+': dash is shortened by collision',1<delta.length()<299,vec(delta))
                check(name+': pawn stops at the swept capsule contact',(position-expected['location']).length()<3,{'actual':vec(position),'expected':vec(expected['location'])})
                near=trace(position,position+direction*.01)
                check(name+': final capsule does not penetrate the surface',not near or not near['penetrating'])
                # Repeated requests into the same obstacle may not tunnel through it.
                prepared['contact']=position;inject(0);stage=3
            else:
                check(name+': clear arch opening permits the full dash',abs(delta.length()-300)<.1,vec(delta));inject(0);stage=5
            check(name+': one Gameplay Cue per press',pawn.get_editor_property('DashCueCount')==prepared['cue_before']+1)
            trials.append({'case':name,'start':vec(prepared['start']),'finish':vec(position),'displacement':round(delta.length(),4),'blocked':bool(expected)})
        elif stage==3:
            inject(1);stage=4
        elif stage==4:
            check(prepared['name']+': repeated press cannot enter obstacle',(pawn.get_actor_location()-prepared['contact']).length()<3)
            inject(0);stage=5
        elif stage==5:
            index+=1
            if index<len(cases):stage=1
            else:finish()
    except Exception:finish(traceback.format_exc())


def run():
    global handle,started,checks,trials,cases,index,stage,world,pawn,inputs,origin
    assert handle is None
    checks=[];trials=[];cases=[];index=stage=0;world=pawn=inputs=origin=None;started=time.monotonic()
    handle=unreal.register_slate_post_tick_callback(tick)
    return 'Fab rocks and arch collision validation started'
