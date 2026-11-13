"""Provision only a free Render service using private environment settings.

Does not print, copy to source, or pass credentials as process arguments.
"""
from pathlib import Path
import json

import httpx
import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'tea-dbrmau0m7kps73cmho30'


def main():
    settings = {k: v for k, v in dotenv_values(ROOT / '.env.production').items() if v is not None}
    required = ['GROQ_API_KEY', 'DATABASE_URL', 'MIGRATION_DATABASE_URL', 'SESSION_SECRET', 'ADMIN_TOKEN']
    if any(not settings.get(k) for k in required):
        raise SystemExit('Required backend environment settings are missing; values hidden.')
    auth = yaml.safe_load((Path.home() / '.render/cli.yaml').read_text())
    token = auth['api']['key']
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json'}
    with httpx.Client(base_url='https://api.render.com/v1/', headers=headers, timeout=90) as client:
        response = client.get('services', params={'ownerId': OWNER, 'name': 'traceforge-ai', 'limit': 100})
        if response.status_code != 200:
            raise SystemExit('Render service lookup failed HTTP ' + str(response.status_code))
        matches = [r['service'] for r in response.json() if r['service']['name'] == 'traceforge-ai']
        if matches:
            service = matches[0]
            if service.get('serviceDetails', {}).get('plan') != 'free':
                raise SystemExit('Refusing to modify a service that is not explicitly on the free plan.')
            response = client.put(f"services/{service['id']}/env-vars", json=[{'key': k, 'value': v} for k,v in settings.items()])
            if response.status_code != 200:
                raise SystemExit('Secure environment update failed HTTP ' + str(response.status_code))
            print('Updated secure backend environment variable names:', ', '.join(sorted(settings)))
        else:
            response = client.post('services', json={
                'type': 'web_service', 'name': 'traceforge-ai', 'ownerId': OWNER,
                'repo': 'https://github.com/Premdoshi1208/traceforge-ai', 'branch': 'main',
                'autoDeployTrigger': 'checksPass',
                'envVars': [{'key':k,'value':v} for k,v in settings.items()],
                'serviceDetails': {'runtime':'docker','plan':'free','region':'oregon','numInstances':1,
                    'healthCheckPath':'/readyz','envSpecificDetails':{'dockerfilePath':'./Dockerfile','dockerContext':'.'}}})
            if response.status_code not in (200,201):
                message = response.json().get('message','No provider message') if 'json' in response.headers.get('content-type','') else 'No provider message'
                for value in [token,*settings.values()]:
                    if len(value)>5:
                        message=message.replace(value,'[REDACTED]')
                raise SystemExit('Free service creation failed HTTP '+str(response.status_code)+': '+message[:400])
            payload = response.json()
            service = payload.get('service',payload)
        result = {'service_id':service['id'],'url':service.get('serviceDetails',{}).get('url'),
                  'plan':service.get('serviceDetails',{}).get('plan'),'name':service['name']}
        (ROOT/'.local/render-deployment.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))


if __name__ == '__main__':
    main()
