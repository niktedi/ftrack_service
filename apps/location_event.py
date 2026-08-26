import ftrack_api as ftr
import dotenv
import os
import requests

dotenv.load_dotenv()
def on_update(event):

    comp = session.get("Component", event['data']['component_id'])

    location = session.get("Location", event['data']['location_id'])

    if comp is not None and location is not None:
        if 'sequence' in comp['system_type'] and 'x.local' in location['name']:
            print("sequence id = {}".format(event['data']['component_id'])) 
            r = requests.post(
                "http://10.79.1.88:8000/encode",
                json={
                    "compId": event['data']['component_id']
                }
            )
session = ftr.Session(
    server_url=os.getenv("FTRACK_SERVER_URL"),
    api_key=os.getenv("FTRACK_API_KEY"),
    api_user=os.getenv("FTRACK_API_USER"),
    auto_connect_event_hub=True
)

session.event_hub.subscribe(
    "topic=ftrack.location.component-added",
    on_update
)
session.event_hub.wait()