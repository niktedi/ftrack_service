import asyncio
import datetime
import threading
import typing
from typing import Any, Dict, List, Optional, Tuple
from fastapi import FastAPI, BackgroundTasks, Header, Request, HTTPException
from pydantic import BaseModel
import ftrack_api as ftr
import clique
import subprocess
import tempfile
import ftrack_api.structure.standard
import ftrack_api.accessor.disk
import sqlite3
import psutil
import os
import shutil
import time
import ast
import json
import requests
import logging


app = FastAPI(
    docs_url=None,         
    redoc_url=None,        
    openapi_url=None       
)

class Data(BaseModel):
    seqPath: str = None
    compId: str = None
    fps: int = 30
    user: str = 'unknownuser'
# ftrack data ##############
class Metadata(BaseModel):
    date: str
    resource_id: str
    server_url: str
class Entity(BaseModel):
    id: typing.List[str]
    entity_type: str
    operation: str
    new: dict
    old: dict
class EntityEvent(BaseModel):
    id: str
    metadata: Metadata
    entity: Entity 
############################

def getPath(asset,path):
    try:
        parent = asset['parent']
    except:
        parent = None    
    if parent:
        path.append(parent['name'])
        getPath(parent,path)
        return path
    else:
        return path

#@app.post("/encode")
#async def endpoint(vdata: Data, background_tasks: BackgroundTasks):
#    #background_tasks.add_task(process, vdata)
#    return {"message": "OK"}

@app.post("/addq")
async def endpoint(vdata: Data, background_tasks: BackgroundTasks):
    background_tasks.add_task(addq, vdata)
    #ODODbackground_tasks.add_task(addq, vdata)
    return {"message": "OK"}

@app.post("/encode")
async def endpoint(vdata: Data, background_tasks: BackgroundTasks):
    
    #background_tasks.add_task(addq, vdata)
    background_tasks.add_task(addq, vdata)
    return {"message": "OKey"}

@app.post("/ping")
async def endpoint():
    return {"message": "OK"}

# @app.post("/ftrwh")
# async def ftrwh(request: Request):
#     print('! statuschanged detected ')
#     session = None
#     data = await request.json()
#     if request.headers.get("secret") != 'korova':
#         raise HTTPException(status_code=403, detail="Invalid secret")
#     try:
#         status_id = data['entity']['new']['status_id']
#     except:
#         return {"status": "no status found"}

#     target_status_id = '3977c897-af3f-433f-9c67-aa71b268e3fa'
#     if status_id != target_status_id:
#         print('-----not my job')
#         return {"status": "not my job"}

#     loop = asyncio.get_event_loop()
#     result = await loop.run_in_executor(None, on_use_this, data)
#     print(result)
#     if result[0]:
#         print('------ status changed to Use this')
#         await loop.run_in_executor(None, copy_file, data, result[1])
#     else:
#         print('------------nothing to copy--------------')
#     await loop.run_in_executor(None, reset_status, data, result[1])
#     print('@@@@@@@@@@@@@@@@@@@@@@@@@@@ status changed proccessed !!')
#     return {"status": "ok"}

# def reset_status(data: dict, session: ftr.Session):
#     print('-------------set publish status bakc')
#     asset = session.get('Asset', data['entity']['new']['asset_id'])
#     assVer = session.get('AssetVersion', data['entity']['id'][0])
#     published_status = session.query('Status where name is "Published"').one()
#     for version in asset['versions']:
#         if version['id'] != assVer['id']:
#             version['status'] = published_status
#     session.commit()
#     print('-------------set publish status bakc finished')
#     return

# def copy_file(data: dict, session: ftr.Session):
#     assVer = session.get('AssetVersion', data['entity']['id'][0])
#     x_loc = session.get('Location', '3e1a3d81-dbc1-44c5-982c-8ad1ea361a9b')
#     server_loc = session.query('Location where name is "ftrack.server"').one()
#     out_file_path = '/mnt/data/proj/'+assVer['project']['name']+'/_collected/'
#     if not os.path.exists(out_file_path):
#         os.makedirs(out_file_path)
#     print('copy func >>>>>>>')
#     for comp in assVer['components']:
#         if  comp['name'] == 'ftrackreview-mp4':
#             print('ftrack previrev download ----->',end = ' ')
#             file_name = assVer['asset']['parent']['name']+'_'+assVer['asset']['name']+'_'+comp['name']+comp['file_type']

#             COMPONENT_ID = comp['id']
#             url = f"{FTRACK_URL}/component/get"
#             params = {"id": COMPONENT_ID, "username": FTRACK_API_USER, "apiKey": FTRACK_API_KEY}
#             with requests.get(url, params=params, stream=True) as r:
#                 r.raise_for_status()
#                 filename = out_file_path + file_name
#                 cd = r.headers.get("content-disposition", "")
#                 # if "filename=" in cd:
#                 #     filename = cd.split("filename=")[1].strip('"; ')
#                 with open(filename, "wb") as f:
#                     for chunk in r.iter_content(chunk_size=8192):
#                         f.write(chunk)
#             print(filename)
#             continue
#         if  comp['name'] == 'ftrackreview-mp4-1080':
#             continue
#         #####
#         if (comp['file_type'] in ['.mov','.mp4']) and ('ftrackreview' not in comp['name']):
#             print('file copy ----->',end = ' ')
#             file_name = assVer['asset']['parent']['name']+'_'+assVer['asset']['name']+comp['file_type']
#             print('copy file ----->',end = ' ')
#             try:
#                 res_id = x_loc.get_resource_identifier(comp)
#             except:
#                 print('no resource identifier found')
#                 continue
#             shutil.copy2('/mnt/data/proj/'+res_id, out_file_path + file_name)
#             print(out_file_path + file_name)
#             continue
#         print('no componets to copy')
#         return

def addq(vdata: Data):
    print('addq called`')
    db = sqlite3.connect("db/queue.db", timeout=10.0)
    db.execute("PRAGMA journal_mode = WAL;")
    with open('vdt.txt','w') as f:
            print(vdata.compId,file=f)
    cur = db.cursor()
    try:
        cur.execute('''
            INSERT INTO queue (component_id) VALUES (?)
            ''',(vdata.compId,))
        with open('bdexec.txt','w') as f:
            print('ok',file=f)
    except Exception as e:
        with open('exc.txt','w') as f:
            print(f"Exception type: {type(e).__name__}",file=f)
            print(f"Exception message: {str(e)}",file=f)
            print(f"Exception args: {e.args}",file=f)
    finally:
        db.commit()
        cur.close()
        db.close()

    encoderRun = False
    for proc in psutil.process_iter():
        try:
            if 'apps.encodeq' in proc.cmdline():
                encoderRun = True
                print('encoderRun',encoderRun)
                break
        except:
            pass

    if not encoderRun:
        try:
            pass

            subprocess.run([".venv/bin/python3", "-m","apps.encodeq"])
        except:
            pass

#MARK: ONuse func    
# def on_use_this(data: dict):
#     print('>>>>>>>>>>onusethis started')
#     # print(data)
#     session = ftr.Session(
#         server_url='',
#         api_key='',
#         api_user='',
#         auto_connect_event_hub=True
#     )

#     if data.get('entity', {}).get('entity_type') != 'AssetVersion':
#         return [False,session]


#     assVer = session.get('AssetVersion', data['entity']['id'][0])
#     print('assVer version = ',assVer['version'])
#     x_loc = session.get('Location', '3e1a3d81-dbc1-44c5-982c-8ad1ea361a9b')
#     server_loc = session.query('Location where name is "ftrack.server"').one()
#     version_component_dict = {}
#     for comp in assVer['components']:
#         print(comp['name'],end=' ')
#         try:
#             print(x_loc.get_resource_identifier(comp))
#         except:
#             pass
#         try:
#             print(server_loc.get_resource_identifier(comp))
#         except:
#             pass
            

#         file_type = comp.get('file_type', None) or ''
#         version_component_dict[comp['name'] + file_type] = comp['id']

#     asset = session.get('Asset', data['entity']['new']['asset_id'])
#     asset_metadata = asset.get('metadata', {}) or {}
#     if not isinstance(asset_metadata, dict):
#         asset_metadata = {}

#     use_this_list = asset_metadata.get('use_this_list', {}) or {}
#     if isinstance(use_this_list, str):
#         try:
#             use_this_list = json.loads(use_this_list)
#         except Exception:
#             use_this_list = {}
#     elif not isinstance(use_this_list, dict):
#         use_this_list = {}

#     for key, value in version_component_dict.items():
#         use_this_list[key] = value

#     asset_metadata['use_this_list'] = use_this_list
#     asset['metadata'] = asset_metadata

#     event_received = threading.Event()

#     def event_check(event):

#         event_received.set()

#     use_update_event = ftr.event.base.Event(
#         topic="mroya.uselist.update",
#         data={'asset_id': asset['id'],
#               'version_id': assVer['id'],
#               'time': datetime.datetime.now().isoformat()}
#     )
#     session.event_hub.subscribe(subscription="topic=mroya.uselist.update", callback=event_check)

#     session.event_hub.publish(use_update_event)
#     tout = 10
#     while not event_received.is_set() and tout > 0:
#         # print(event_received.is_set())
#         time.sleep(0.3)
#         tout -= 1
#         session.event_hub.wait(duration=0.5)
#     if tout <= 0:
#         print("Event not sent")
#     print('<<<<<<<<<<<<<<<<<onusethis finished')
#     return [True,session]




