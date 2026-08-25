import datetime
import sqlite3
from pydantic import BaseModel
import ftrack_api as ftr
import clique
import subprocess
import tempfile
import sqlite3
import os
import dotenv
dotenv.load_dotenv()


class Data(BaseModel):
    seqPath: str = None
    compId: str = None
    fps: int = 30
    user: str = 'unknownuser' 
    
def process(vdata: Data):
    print('vdata',vdata.compId)
    print('process called')
    session = ftr.Session(
        server_url=os.getenv('FTRACK_SERVER_URL'),
        api_key=os.getenv('FTRACK_API_KEY'),
        api_user=os.getenv('FTRACK_API_USER')
    )
    component = session.get('Component',vdata.compId)
    componentName = component['name']
    print('componentName',componentName)
    version = session.get('AssetVersion',component['version_id'])
    xlocation = session.get('Location', 'a8bb4dbc-bf9c-4a7b-8bdc-d669938671b6')
    asset = session.get('Asset',version['asset_id'])
    resource_identifier = xlocation.get_resource_identifier(component)
    proj = session.get('Project',component['project_id'])
    try:
        fps = int(proj['custom_attributes'].get('fps', 25))
    except:
        fps = 25
    xpath = '/nas/data/proj/'+xlocation.get_resource_identifier(component)
    print('xpath',xpath)
    #version = session.get('AssetVersion',vdata.verId)
    files = os.listdir(os.path.dirname(xpath))
    collected,reminder = clique.assemble(files)
    seqstring = xpath +' ['+ collected[0].format('{ranges}')+']'
    seq = clique.parse(seqstring)
    print('seq',seq)
    print('version',version)
    firstFrame = int(list(seq.indexes)[0])
    firstFrameTimecode = '{}:{}:{}:{}'.format(str(firstFrame//(fps*3600)).zfill(2),
                                              str(firstFrame//(fps*60)).zfill(2),
                                              str(firstFrame//fps).zfill(2),
                                              str(firstFrame%fps).zfill(2))
    
    padding = '%'+str(str(seq.padding)).zfill(2)+'d'
    pathString = resource_identifier
    inFileName = '.'.join(pathString.split('.')[0:-2]) + '.' + padding + '.' + pathString.split('.')[-1]

    tstamp = datetime.datetime.now()
    tstampString='{}_{}:{}'.format(tstamp.date(),
                     tstamp.time().hour,
                     tstamp.time().minute
                     )
    oiiologFile = 'logs/o_{}_{}_{}.log'.format(vdata.user,asset['name'],tstampString)
    ffmpglogFile = 'logs/f_{}_{}_{}.log'.format(vdata.user,asset['name'],tstampString)

    with tempfile.TemporaryDirectory(prefix='/tmp/encoderTmp') as tempDir:

        srcSeq = '/nas/data/proj/' + inFileName
        outSeq = tempDir + '/' + componentName +'.'+ padding + '.png'

        outVideo = os.path.dirname(xpath)+'/'+proj['name']+'_'+componentName+'_v'+str(version['version']).zfill(3)+'.mp4'
        print(outVideo)
        if seq.tail == '.exr':
            oiioCmd = ['oiiotool','-i',
                '{0}'.format(srcSeq),
                '--colorconfig','ocio/config.ocio', '--tocolorspace', 'Output - sRGB', '-o',
                '{0}'.format(outSeq)
                ]
            with open(oiiologFile,'w') as f:
                #subprocess.run(oiioCmd,stderr=f)
                subprocess.run(oiioCmd)
        else:
            outSeq = srcSeq
        if seq.tail in ['.png','.tga','.jpg','.jpeg','.exr']:
            ffmpegCmd = ['ffmpeg', '-framerate', str(fps),'-y', '-start_number', str(firstFrame), '-i', '{0}'.format(outSeq), 
                         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-vprofile', 'high', '-bf', '0', 
                        '-strict', 'experimental','-timecode', firstFrameTimecode,
                        '-vf', 'scale=ceil(iw/2)*2:ceil(ih/2)*2,drawtext=text={}:start_number={}:boxcolor=black:boxborderw=10:fontsize=30:fontcolor=white:x=25:y=25'.format(r'%{frame_num}',str(firstFrame).zfill(4)),
                        '-f', 'mp4', '-g', str(int(vdata.fps/4)), outVideo
                        ]
            with open(ffmpglogFile,'w') as f:
                #subprocess.run(ffmpegCmd,stderr=f)
                subprocess.run(ffmpegCmd)

            movie = version.encode_media(outVideo)
            session.commit()
    return
def processDumb(vdata:Data):
    pass
#----
while True:
    print('started')
    #for i in range(1):
    print('in a loop')
    qItem = Data()
    db = sqlite3.connect("db/queue.db",timeout=10.0)
    cur = db.cursor()
    try:
        cur.execute('SELECT min(id),component_id FROM queue')
        id,qItem.compId = cur.fetchone()
        print('id',id)
        print('qItem.compId',qItem.compId)
    finally:
        cur.close()
        db.close()
    if id == None:
        break
    process(qItem)

    db = sqlite3.connect("db/queue.db")
    cur = db.cursor()
    cur.execute('DELETE FROM queue WHERE id=?',(id,))
    db.commit()
    db.close()

