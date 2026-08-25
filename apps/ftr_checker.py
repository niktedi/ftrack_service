import ftrack_api
import dotenv
import os
dotenv.load_dotenv()
session = ftrack_api.Session(
    server_url=os.getenv('FTRACK_SERVER_URL'),
    api_key=os.getenv('FTRACK_API_KEY'),
    api_user=os.getenv('FTRACK_API_USER')
)
locations = session.query('Location').all()
for location in locations:
    print(location['name'],location['id'])