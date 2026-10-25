"""Asynchronous checks in real Play, including four boundary recoveries and a blocked route.

Load L_BoundedPatrol. Call static_checks() outside Play, start actual Play,
then call run() on a later editor tick. The report is written when the last
scenario finishes. Each run uses a freshly imported/reloaded module.
"""
import json, math, time
from pathlib import Path
import unreal
import lab_graph as g
from build_bounded_patrol import PATH, MAP

REPORT=Path(unreal.Paths.project_dir())/'Docs/PatrolValidation107.json'
checks=[]
samples=[]
handle=None
stage=-1
started=0
last=0
agent=None
world=None
baseline=0
route=[]

def check(name,passed,detail=None):
    checks.append({'check':name,'passed':bool(passed),'detail':detail})
def prop(a,n,v):a.set_editor_property(n,v,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
def inside(v,margin=0):return -900+margin<=v.x<=900-margin and -800+margin<=v.y<=800-margin
def finish():
    global handle
    if handle:unreal.unregister_slate_post_tick_callback(handle);handle=None
    check('No capsule penetrated any of the three Static Mesh obstacles',all(s['clearance']>=33.0 for s in samples),{'minimum_cm':min([s['clearance'] for s in samples],default=None)})
    check('Movement stayed on the floor',all(58<s['z']<70 for s in samples))
    check('Movement speed did not exceed configured Speed',all(s['velocity']<=s['speed']+2 for s in samples))
    REPORT.write_text(json.dumps({'map':MAP,'checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'sample_count':len(samples),'samples':samples},ensure_ascii=False,indent=2),encoding='utf8')
    unreal.log('PATROL_107_TESTS_FINISHED '+str(REPORT))
def clearance(p):
    rectangles=[(0,0,125,300),(-480,380,150,100),(480,-380,150,100)]
    return min(math.hypot(max(abs(p.x-x)-hx,0),max(abs(p.y-y)-hy,0)) for x,y,hx,hy in rectangles)
def setup_at(x,y,speed):
    agent.get_controller().stop_movement()
    agent.character_movement.stop_movement_immediately()
    agent.set_actor_location(unreal.Vector(x,y,62.15),False,True)
    prop(agent,'Speed',speed);agent.call_method('RestartPatrol')

def static_checks():
    bp=unreal.load_asset(PATH);g.compile_bp(bp)
    check('Character parent with CharacterMovement',isinstance(unreal.get_default_object(bp.generated_class()),unreal.Character))
    errors=[];warnings=[];moves=[];forbidden=[]
    for graph in g.B.list_graphs(bp):
        e=unreal.BlueprintGraphEditor.get_graph_editor(graph)
        errors.extend(str(n.get_node_title()) for n in e.list_nodes_with_errors())
        warnings.extend(str(n.get_node_title()) for n in e.list_nodes_with_warnings())
        nodes=e.list_all_nodes()
        if str(graph.get_name())!='UserConstructionScript':check('Short commented graph '+str(graph.get_name()),len(nodes)<=30 and bool(e.list_comment_nodes()))
        for n in nodes:
            if n.get_class().get_name()=='K2Node_AIMoveTo':moves.append(n)
            if any(x in str(n.get_node_title()).replace(' ','').lower() for x in ['setactorlocation','addactorworldoffset','addmovementinput','setworldlocation','setactortransform']):forbidden.append(str(n.get_node_title()))
    check('Blueprint compiles without errors or warnings',not errors and not warnings,{'errors':errors,'warnings':warnings})
    check('Exactly one standard AIMoveTo node',len(moves)==1)
    check('No manual translation nodes',not forbidden,forbidden)
    names=[str(n) for n in g.B.list_member_variable_names(bp,False)]
    for name in ['Speed','MinX','MaxX','MinY','MaxY']:
        check('Configuration variable and category '+name,name in names and str(g.B.get_blueprint_variable_category(bp,name))=='Patrol|Configuration')
    check('Public-repository ignore file exists',(Path(unreal.Paths.project_dir())/'.gitignore').exists())

def tick(delta):
    global stage,started,last,baseline,route
    try:
        now=unreal.GameplayStatics.get_time_seconds(world)
        if now-last<.05:return
        last=now
        p=agent.get_actor_location();v=agent.get_velocity();speed=max(0,agent.get_editor_property('Speed'))
        samples.append({'t':round(now,3),'stage':stage,'x':round(p.x,3),'y':round(p.y,3),'z':round(p.z,3),'velocity':round(v.length(),3),'speed':speed,'clearance':round(clearance(p),3)})
        elapsed=now-started
        if stage==-1:
            stage=0;started=now;baseline=agent.get_editor_property('CompletedMoves');return
        if stage==0 and elapsed>12:
            check('Repeated random destinations completed',agent.get_editor_property('CompletedMoves')>baseline)
            check('Random targets remain inside the configured area',inside(agent.get_editor_property('TargetLocation'),60))
            stage=1;started=now;setup_at(-650,0,240)
            agent.call_method('RequestDestination',args=(unreal.Vector(650,0,10),));baseline=agent.get_editor_property('CompletedMoves');route=[];return
        if stage==1:
            route.append((p.x,p.y))
            if agent.get_editor_property('CompletedMoves')>baseline or elapsed>15:
                check('Blocked route reached the opposite side',agent.get_editor_property('CompletedMoves')>baseline and p.x>600)
                check('Actual path went around the central mesh',max([abs(y) for x,y in route if abs(x)<200],default=0)>330)
                check('Actor turned along the route',len(route)>5 and max(y for x,y in route)-min(y for x,y in route)>300)
                stage=2;started=now;baseline=agent.get_editor_property('BoundaryTurns');setup_at(-1050,-500,300);return
        if 2<=stage<=5:
            if inside(p,10) or elapsed>16:
                edge=['MinX','MaxX','MinY','MaxY'][stage-2]
                check('Returned after crossing '+edge,inside(p,10),{'x':p.x,'y':p.y,'elapsed_s':round(elapsed,2)})
                check('Boundary turn and valid random destination '+edge,agent.get_editor_property('BoundaryTurns')>baseline and inside(agent.get_editor_property('TargetLocation'),60))
                stage+=1;started=now
                if stage<=5:
                    positions={3:(1050,500),4:(-600,-950),5:(600,950)}
                    baseline=agent.get_editor_property('BoundaryTurns');setup_at(*positions[stage],300)
                else:setup_at(-650,-450,100)
                return
        if stage in [6,7] and elapsed>4:
            subset=[s for s in samples if s['stage']==stage and s['t']>started+1]
            expected=100 if stage==6 else 360
            check('Runtime Speed '+str(expected)+' applied',abs(agent.character_movement.max_walk_speed-expected)<.1)
            check('Actor moved at configured Speed '+str(expected),any(s['velocity']>expected*.9 for s in subset))
            stage+=1;started=now
            if stage==7:setup_at(-650,-450,360)
            else:prop(agent,'Speed',0)
            return
        if stage==8 and elapsed>2:
            check('Zero Speed stops movement',agent.get_velocity().length()<1)
            prop(agent,'Speed',-25);stage=9;started=now;return
        if stage==9 and elapsed>1:
            check('Negative Speed safely clamps to zero',agent.character_movement.max_walk_speed==0 and agent.get_velocity().length()<1)
            prop(agent,'Speed',220);finish()
    except Exception as exc:
        check('Test execution completed',False,str(exc));finish()

def run():
    global agent,world,handle
    world=unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
    actors=[a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Character) if a.get_class().get_name()=='BP_BoundedPatrol_C']
    check('Two placed autonomous agents',len(actors)==2)
    actors.sort(key=lambda a:a.get_editor_property('Speed'));agent=actors[0]
    for a in actors:check('Navigation controller possessed '+a.get_name(),isinstance(a.get_controller(),unreal.AIController))
    # Park the second agent outside the test area to isolate each measured scenario.
    actors[1].get_controller().stop_movement();prop(actors[1],'Speed',0)
    actors[1].set_actor_location(unreal.Vector(1200,-1100,62.15),False,True)
    handle=unreal.register_slate_post_tick_callback(tick)
    return 'Runtime checks started'
