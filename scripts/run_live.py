"""Run real Groq investigations locally and optionally persist evidence to the deployed database.

Local subprocess execution is explicitly opted into here, never by production HTTP handlers.
"""
import argparse
import asyncio
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=['discount','retry','inventory'], required=True)
    parser.add_argument('--database-env', default='.env')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(args.database_env, override=True)
    os.environ['TRACEFORGE_ALLOW_LOCAL_EXECUTION'] = '1'
    from agent_engine import EngineConfig, execute
    from backend.config import settings
    from backend import storage
    from backend.security import redact
    storage.initialize()
    now = datetime.now(UTC).isoformat()
    run = {'id':str(uuid.uuid4()),'scenario_id':args.scenario,'status':'queued','created_at':now,'updated_at':now,
           'model':settings.reasoning_model,'events':[],'evidence':[],'hypotheses':[],'patch':None,
           'verification':None,'review':None,'report':None,'usage':{'requests':0,'tokens':0},'error':None,
           'controlled_scenario':True,'recorded_example':True,'recording_label':'Recorded from actual local execution'}
    storage.insert_run(run,'developer-local-evaluation',None)
    async def save(current):
        storage.save_run(redact(current))
        output=Path('.local')/f"live-{args.scenario}-{current['id']}.json"
        output.write_text(json.dumps(redact(current),indent=2))
    async def emit(agent,message,type='step',data=None):
        run['events'].append({'id':str(uuid.uuid4()),'agent':agent,'message':redact(message),'type':type,
                              'data':redact(data or {}),'created_at':datetime.now(UTC).isoformat()})
        await save(run)
        if type in ['step','error','complete','rate_limit']:
            print(agent,redact(message),flush=True)
    cfg=EngineConfig(groq_api_key=settings.groq_api_key.get_secret_value(),reasoning_model=settings.reasoning_model,
        efficient_model=settings.efficient_model,verification_mode='local',max_duration_seconds=600,max_tokens=18000)
    asyncio.run(execute(run,emit,save,cfg))
    asyncio.run(save(run))
    print(json.dumps({'id':run['id'],'scenario':args.scenario,'status':run['status'],'usage':run['usage'],'error':run.get('error')}))


if __name__=='__main__':
    main()
