from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import secrets, asyncio
from app.db.session import get_db
from app.models.models import *
from app.security.auth import *
from app.services.audit import audit
from app.websocket.manager import manager
api=APIRouter(prefix="/api/v1")
class LoginIn(BaseModel): email:str; password:str
class CommandIn(BaseModel): command:str; parameters:dict={}
class TaskIn(BaseModel): title:str; description:str=""; task_type:str="delivery"; priority:str="normal"; source_zone:str="Storage Zone A"; destination_zone:str="Packing Area"; destination_x:float=700; destination_y:float=300; assigned_robot_id:str|None=None
class AlertUpdate(BaseModel): notes:str|None=None
class MaintenanceIn(BaseModel): robot_id:str; title:str; issue_description:str=""; type:str="inspection"; priority:str="normal"; technician:str|None=None
class AssistantIn(BaseModel): message:str; confirmed:bool=False
def row(o):
    d={c.name:getattr(o,c.name) for c in o.__table__.columns}
    for k,v in d.items():
        if hasattr(v,"value"): d[k]=v.value
        elif isinstance(v, datetime): d[k]=v.isoformat()
    return d
@api.get("/health")
def health(): return {"status":"ok","service":"Robot Fleet Control Center"}
@api.post("/auth/login")
def login(data:LoginIn, db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==data.email).first()
    if not u or not verify_password(data.password,u.hashed_password): audit(db,None,"failed_login","user",None,f"Failed login for {data.email}"); raise HTTPException(401,"Invalid credentials")
    u.last_login=datetime.utcnow(); access=create_token(u.id,30); refresh=create_token(u.id,60*24*7,"refresh"); db.add(RefreshToken(user_id=u.id,token=refresh,expires_at=datetime.utcnow()+timedelta(days=7))); db.commit(); audit(db,u,"login","user",u.id,"User logged in")
    out=row(u); out.pop("hashed_password",None); return {"access_token":access,"refresh_token":refresh,"token_type":"bearer","user":out}
@api.get("/auth/me")
def me(u:User=Depends(current_user)): d=row(u); d.pop("hashed_password",None); return d
@api.get("/robots")
def robots(q:str="", status:str|None=None, db:Session=Depends(get_db), u:User=Depends(require_perm("robots:read"))):
    qry=db.query(Robot)
    if q: qry=qry.filter(Robot.name.contains(q) | Robot.code.contains(q))
    if status: qry=qry.filter(Robot.status==status)
    return [row(r) for r in qry.order_by(Robot.code).all()]
@api.get("/robots/{rid}")
def robot(rid:str, db:Session=Depends(get_db), u:User=Depends(require_perm("robots:read"))):
    r=db.get(Robot,rid)
    if not r: raise HTTPException(404,"Robot not found")
    return row(r)
@api.post("/robots/{rid}/commands")
async def command(rid:str, data:CommandIn, db:Session=Depends(get_db), u:User=Depends(require_perm("commands:send"))):
    r=db.get(Robot,rid)
    if not r: raise HTTPException(404,"Robot not found")
    c=RobotCommand(robot_id=rid,command=data.command,parameters=data.parameters,status="completed",requested_by=u.id,executed_at=datetime.utcnow(),response={"ok":True})
    if data.command=="emergency_stop": r.status=RobotStatus.emergency_stopped
    elif data.command=="clear_emergency_stop": r.status=RobotStatus.idle
    elif data.command=="go_to_charger": r.status=RobotStatus.charging
    elif data.command=="stop": r.status=RobotStatus.idle; r.current_speed=0
    elif data.command=="pause": r.status=RobotStatus.paused
    elif data.command=="start": r.status=RobotStatus.active
    elif data.command=="set_speed": r.maximum_speed=float(data.parameters.get("speed",r.maximum_speed))
    elif data.command=="move_to": r.x=float(data.parameters.get("x",r.x)); r.y=float(data.parameters.get("y",r.y)); r.status=RobotStatus.active
    db.add(c); db.commit(); audit(db,u,"robot_command","robot",rid,f"Command {data.command} sent to {r.name}",data.parameters); await manager.broadcast({"event":"robot.command_updated","timestamp":datetime.utcnow().isoformat(),"robot_id":rid,"data":row(c)}); return row(c)
@api.get("/telemetry/{rid}")
def telemetry(rid:str, limit:int=80, db:Session=Depends(get_db), u:User=Depends(require_perm("robots:read"))): return [row(t) for t in db.query(Telemetry).filter(Telemetry.robot_id==rid).order_by(Telemetry.timestamp.desc()).limit(limit).all()][::-1]
@api.get("/tasks")
def tasks(db:Session=Depends(get_db), u:User=Depends(require_perm("robots:read"))): return [row(t) for t in db.query(FleetTask).order_by(FleetTask.created_at.desc()).all()]
@api.post("/tasks")
def create_task(data:TaskIn, db:Session=Depends(get_db), u:User=Depends(require_perm("tasks:write"))):
    rid=data.assigned_robot_id
    if not rid:
        rs=db.query(Robot).filter(Robot.status.in_([RobotStatus.idle,RobotStatus.active]),Robot.battery_percentage>25).all()
        if rs: rid=sorted(rs,key=lambda r:((r.x-data.destination_x)**2+(r.y-data.destination_y)**2)**.5)[0].id
    t=FleetTask(code=f"TSK-{secrets.randbelow(99999):05}",created_by=u.id,assigned_robot_id=rid,status=TaskStatus.assigned if rid else TaskStatus.pending,assigned_at=datetime.utcnow() if rid else None,**data.model_dump(exclude={"assigned_robot_id"}))
    db.add(t); db.commit(); audit(db,u,"task_creation","task",t.id,f"Created task {t.title}"); return row(t)
@api.get("/alerts")
def alerts(db:Session=Depends(get_db), u:User=Depends(require_perm("alerts:read"))): return [row(a) for a in db.query(Alert).order_by(Alert.created_at.desc()).all()]
@api.post("/alerts/{aid}/acknowledge")
def ack(aid:str, data:AlertUpdate, db:Session=Depends(get_db), u:User=Depends(require_perm("alerts:write"))):
    a=db.get(Alert,aid); a.status=AlertStatus.acknowledged; a.acknowledged_by=u.id; a.acknowledged_at=datetime.utcnow(); db.commit(); audit(db,u,"alert_acknowledgement","alert",aid,"Acknowledged alert"); return row(a)
@api.post("/alerts/{aid}/resolve")
def resolve(aid:str, data:AlertUpdate, db:Session=Depends(get_db), u:User=Depends(require_perm("alerts:write"))):
    a=db.get(Alert,aid); a.status=AlertStatus.resolved; a.resolved_by=u.id; a.resolved_at=datetime.utcnow(); a.resolution_notes=data.notes; db.commit(); audit(db,u,"alert_resolution","alert",aid,"Resolved alert"); return row(a)
@api.get("/maintenance")
def maint(db:Session=Depends(get_db), u:User=Depends(require_perm("maintenance:read"))): return [row(m) for m in db.query(MaintenanceRecord).order_by(MaintenanceRecord.created_at.desc()).all()]
@api.post("/maintenance")
def create_maint(data:MaintenanceIn, db:Session=Depends(get_db), u:User=Depends(require_perm("maintenance:write"))):
    m=MaintenanceRecord(**data.model_dump()); db.add(m); db.commit(); audit(db,u,"maintenance_update","maintenance",m.id,f"Created maintenance ticket {m.title}"); return row(m)
@api.get("/analytics")
def analytics(db:Session=Depends(get_db), u:User=Depends(require_perm("analytics:read"))):
    robots=db.query(Robot).all(); tasks=db.query(FleetTask).all(); alerts=db.query(Alert).all()
    return {"fleet_uptime":97.4,"robot_utilization":64,"tasks_completed":len([t for t in tasks if t.status==TaskStatus.completed]),"failed_tasks":len([t for t in tasks if t.status==TaskStatus.failed]),"average_task_duration":18,"distance_travelled":round(sum(r.current_speed for r in robots)*42,1),"battery_consumption":round(sum(100-r.battery_percentage for r in robots),1),"alerts_per_robot":len(alerts),"maintenance_cost":db.query(func.sum(MaintenanceRecord.cost)).scalar() or 0,"top_robot":robots[0].name if robots else None}
@api.get("/dashboard/summary")
def summary(db:Session=Depends(get_db), u:User=Depends(require_perm("robots:read"))):
    robots=db.query(Robot).all(); tasks=db.query(FleetTask).all()
    return {"total":len(robots),"active":len([r for r in robots if r.status==RobotStatus.active]),"idle":len([r for r in robots if r.status==RobotStatus.idle]),"offline":len([r for r in robots if r.status==RobotStatus.offline]),"charging":len([r for r in robots if r.status==RobotStatus.charging]),"maintenance":len([r for r in robots if r.status==RobotStatus.maintenance]),"low_battery":len([r for r in robots if r.battery_percentage<20]),"critical_errors":db.query(Alert).filter(Alert.severity==AlertSeverity.critical,Alert.status!=AlertStatus.resolved).count(),"pending_tasks":len([t for t in tasks if t.status==TaskStatus.pending]),"completed_today":len([t for t in tasks if t.status==TaskStatus.completed])}
@api.get("/audit-logs")
def logs(db:Session=Depends(get_db), u:User=Depends(require_perm("*"))): return [row(a) for a in db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200).all()]
@api.post("/assistant/chat")
def assistant(data:AssistantIn, db:Session=Depends(get_db), u:User=Depends(current_user)):
    msg=data.message.lower(); robots=db.query(Robot).all(); alerts=db.query(Alert).filter(Alert.status!=AlertStatus.resolved).all()
    if "low battery" in msg: answer="Robots with low battery: "+(", ".join(r.name for r in robots if r.battery_percentage<25) or "none")
    elif "critical" in msg or "alerts" in msg: answer="Active critical alerts: "+(", ".join(a.title for a in alerts if a.severity==AlertSeverity.critical) or "none")
    elif "attention" in msg or "maintenance" in msg: answer="Robots needing attention: "+(", ".join(r.name for r in robots if r.status in [RobotStatus.error,RobotStatus.maintenance,RobotStatus.offline] or r.battery_percentage<20) or "none")
    else: answer=f"Fleet summary: {len(robots)} robots, {len(alerts)} active alerts, {db.query(FleetTask).filter(FleetTask.status==TaskStatus.completed).count()} completed tasks. Mock AI mode is active."
    audit(db,u,"ai_assistant","assistant",None,"Assistant answered fleet question",{"message":data.message}); return {"answer":answer,"mock":True}
@api.get("/camera/{rid}/stream")
def camera(rid:str):
    async def gen():
        while True:
            svg=f"<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360'><rect width='100%' height='100%' fill='#111827'/><text x='28' y='48' fill='white' font-size='26'>Robot Camera {rid[:8]}</text><text x='28' y='92' fill='#22c55e' font-size='18'>{datetime.utcnow().isoformat()}Z</text><circle cx='{100+(datetime.utcnow().second*7)%500}' cy='210' r='34' fill='#38bdf8'/></svg>"
            yield b"--frame\r\nContent-Type: image/svg+xml\r\n\r\n"+svg.encode()+b"\r\n"; await asyncio.sleep(1)
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")
