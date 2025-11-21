from datetime import datetime

with open("/srv/demofile.txt", "w") as f:
    f.write(str(datetime.now()))