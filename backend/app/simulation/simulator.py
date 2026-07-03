import asyncio, math, random
from datetime import datetime
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import RobotStatus, Robot, Telemetry, Alert, AlertSeverity, FleetTask, TaskStatus
from app.websocket.manager import manager
class SimulatedRobotAdapter:
    async def connect(self): return True
    async def disconnect(self): return True
    async def get_status(self, robot_id): return {}
    async def get_telemetry(self, robot_id): return {}
    async def assign_task(self, robot_id, task_id): return {"accepted": True}
    async def get_camera_source(self, robot_id): return f"/api/v1/camera/{robot_id}/stream"
    async def health_check(self): return {"ok": True}
    async def send_command(self, robot_id, command, parameters): return {"accepted": True}
async def simulation_loop():
    tick=0
    while True:
        await asyncio.sleep(settings.simulation_update_interval); db=SessionLocal()
        try:
            for r in db.query(Robot).all():
                if r.status in [RobotStatus.emergency_stopped, RobotStatus.maintenance]: continue
                r.cpu_usage=max(2,min(98,r.cpu_usage+random.uniform(-5,5))); r.memory_usage=max(5,min(95,r.memory_usage+random.uniform(-3,3)))
                r.temperature=max(25,min(85,r.temperature+random.uniform(-1,1)+(0.05 if r.current_speed>0 else -0.03)))
                if r.status == RobotStatus.charging:
                    r.battery_percentage=min(100,r.battery_percentage+1.6); r.current_speed=0
                    if r.battery_percentage>92: r.status=RobotStatus.idle
                elif r.status != RobotStatus.offline:
                    r.status = RobotStatus.active if random.random()>.35 else RobotStatus.idle; r.current_speed = 0 if r.status==RobotStatus.idle else round(random.uniform(.2,r.maximum_speed),2)
                    r.heading=(r.heading+random.uniform(-25,25))%360; r.x=max(35,min(860,r.x+math.cos(math.radians(r.heading))*r.current_speed*18)); r.y=max(35,min(520,r.y+math.sin(math.radians(r.heading))*r.current_speed*18)); r.battery_percentage=max(0,r.battery_percentage-r.current_speed*.25)
                    if r.battery_percentage<12: r.status=RobotStatus.charging
                if random.random()<0.01: r.connection_status="offline"; r.status=RobotStatus.offline
                elif r.status==RobotStatus.offline and random.random()<0.25: r.connection_status="online"; r.status=RobotStatus.idle
                r.last_seen=datetime.utcnow(); r.updated_at=datetime.utcnow()
                if tick % max(1,int(settings.telemetry_storage_interval/settings.simulation_update_interval)) == 0: db.add(Telemetry(robot_id=r.id,battery_percentage=r.battery_percentage,battery_voltage=20+r.battery_percentage*.06,temperature=r.temperature,speed=r.current_speed,x=r.x,y=r.y,heading=r.heading,cpu_usage=r.cpu_usage,memory_usage=r.memory_usage,current_draw=r.current_speed*4,distance_travelled=r.current_speed*settings.simulation_update_interval))
                if r.battery_percentage<20 and not db.query(Alert).filter(Alert.robot_id==r.id,Alert.code=="BATTERY_LOW",Alert.status=="open").first(): db.add(Alert(robot_id=r.id,code="BATTERY_LOW",title="Low battery",message=f"{r.name} battery is {r.battery_percentage:.0f}%",severity=AlertSeverity.warning))
                if r.temperature>80 and not db.query(Alert).filter(Alert.robot_id==r.id,Alert.code=="TEMP_CRITICAL",Alert.status=="open").first(): db.add(Alert(robot_id=r.id,code="TEMP_CRITICAL",title="Critical temperature",message=f"{r.name} is above 80C",severity=AlertSeverity.critical))
                await manager.broadcast({"event":"robot.telemetry","timestamp":datetime.utcnow().isoformat(),"robot_id":r.id,"data":{"battery":r.battery_percentage,"temperature":r.temperature,"speed":r.current_speed,"x":r.x,"y":r.y,"heading":r.heading,"cpu_usage":r.cpu_usage,"memory_usage":r.memory_usage,"status":r.status.value}})
            for t in db.query(FleetTask).filter(FleetTask.status.in_([TaskStatus.assigned,TaskStatus.in_progress])).all():
                t.status=TaskStatus.in_progress; t.progress_percentage=min(100,t.progress_percentage+random.randint(3,12))
                if t.progress_percentage>=100: t.status=TaskStatus.completed; t.completed_at=datetime.utcnow()
            db.commit(); await manager.broadcast({"event":"fleet.summary_updated","timestamp":datetime.utcnow().isoformat()}); tick+=1
        finally: db.close()
