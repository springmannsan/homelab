import tarfile, os
import b2sdk.v3 as b2
from datetime import datetime
from dotenv import load_dotenv
from discord_webhook import DiscordWebhook, DiscordEmbed

def create_local_backup(backup_path, directories_to_backup: list):

    print("Creating local backup....")

    try:
        with tarfile.open(backup_path, mode="w:gz") as tar_file:

            print("Local archive created")
            for d in directories_to_backup:

                if not os.path.exists(d):
                    print(f"Skipping {d}, path does not exists")
                    continue

                print(f"Adding {d} to local backup...")
                tar_file.add(d)
                print(f"{d} added to local backup")
            tar_file_members = tar_file.getmembers()
        print(f"Files archived {backup_path}, {round(os.path.getsize(backup_path) / (1024 * 1024), 5)} MB written")
        
        return tar_file_members
    
    except FileNotFoundError as e:
        print(f"File not found error: {e}")
    except PermissionError as e:
        print(f"Permission denied: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print("Error occured during archiving")
    return None

def upload_backup(local_result, backup_path, backup_name):

    print("Uploading backup....")

    print("Checking local backup...")
    if not os.path.exists(backup_path):
        print("No local backup found")
        return None
    
    if not (local_result and len(local_result) > 0):
        print("Local backup empty")
        return None
    
    info = b2.InMemoryAccountInfo()
    b2_api = b2.B2Api(info)

    try:
        print("Authenticating to B2...")
        b2_api.authorize_account(application_key_id, application_key)
        print("OK")
        print("Getting buckets.....")
        bucket = b2_api.get_bucket_by_name(bucket_name)
        print("OK")
        print("Uploading to bucket")
        res = bucket.upload_local_file(
            local_file=backup_path,
            file_name = backup_name,
        )
        print(f"Uploaded {res.file_name}, {round(res.size / (1024 * 1024), 5)} MB")
        return res
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print("Error occured during upload")
    return None

def remove_local_backup(backup_path):

    print("Removing local backup....")

    if not os.path.exists(backup_path):
        print("Couldn't find local backup")

    try:
        os.remove(backup_path)
    except FileNotFoundError as e:
        print(f"File not found error: {e}")
    except PermissionError as e:
        print(f"Permission denied: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    if os.path.exists(backup_path):
        print("Couldn't remove local backup")
    else:
        print("Local backup removed")

def check_success(local_path, directories_to_backup, local_result, upload_response):

    print("Checking success...")

    report = {
        "overall_success": False,
        "local_ok": False,
        "local_size": 0,
        "remote_ok": False,
        "remote_name": "N/A",
        "remote_size": 0,
        "directories": [],
    }

    print("Checking directories....")
    
    #loops througt drectories_to_backup and checks if directory is in archive
    if local_result and len(local_result) > 0:
        for d in directories_to_backup:
            directory_size = 0
            for a in local_result:
                if a.path.startswith(d[1:]):
                    directory_size += a.size

            if os.path.exists(d) and (directory_size > 0):
                report["directories"].append({
                    "directory": d,
                    "ok": True,
                    "size": directory_size
                })
                print(f"{d} BACKED UP OK")
            else:
                report["directories"].append({
                    "directory": d,
                    "ok": False,
                    "size": directory_size
                })
                print(f"{d} FAILED")
    
    print("Directories checked")
    print("Checking local archive")
    
    #check is local backup was successful
    if os.path.exists(local_path) and len(local_result) > 0:
        report["local_ok"] = True
        report["local_size"] = os.path.getsize(local_path)
        print("Local archive OK")
    else:
        print("Local backup failed")

    if upload_response and (upload_response.file_name and upload_response.size):
        report["remote_name"] = upload_response.file_name
        report["remote_ok"] = True
        report["remote_size"] = upload_response.size
        print("Remote backup ok")
    else:
        print("Upload failed")

    if report["local_ok"] and report["remote_ok"] and all(i["ok"] for i in report["directories"]):
        report['overall_success'] = True

    print(report)

    return report

def send_discord_notification(report, discord_webhook, now):

    allowed_mentions = {"parse": ["everyone"]}
    content = f"{"Successful backup \u2705" if report["overall_success"] else "Failed backup \u274C"} @everyone"
    webhook = DiscordWebhook(url=discord_webhook, content=content, allowed_mentions=allowed_mentions)
    embed = DiscordEmbed(title="Backup Report", description=f"{now.strftime("%Y.%m.%d")}")

    for i in report["directories"]:
        if i["ok"]:
            embed.add_embed_field(
                 name=f"{i["directory"]} succesfully backed up \u2705",
                 value=f"{(i["size"]) / (1024 * 1024):.2f} MB archived",
                 inline=False
            )
        else:
            embed.add_embed_field(
                 name=f"{i["directory"]} failed to back up \u274C",
                 value="N/A",
                 inline=False
            )

    embed.add_embed_field(
        name=f"Local backup {"successful \u2705" if report["local_ok"] else "failed \u274C"}",
        value=f"{(report["local_size"]) / (1024 * 1024):.2f} MB written to disk"
    )

    embed.add_embed_field(
        name=f"Remote backup {"successful \u2705" if report["remote_ok"] else "failed \u274C"}",
        value=f"{(report["remote_size"]) / (1024 * 1024):.2f} MB uploaded to B2"    )

    webhook.add_embed(embed)
    response = webhook.execute()

print("Script started")
print("Loading variables")

now = datetime.now()

#COMMENT OUT FOR PRODUCTION
load_dotenv() 

try:
    directories_to_backup = open("/etc/backup/backup.directories.conf").read().splitlines()
except FileNotFoundError as e:
    print(f"File not found error: {e}")
except PermissionError as e:
    print(f"Permission denied: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

#loading environmental variables
application_key_id = os.getenv("STORAGE_KEY_ID")
application_key = os.getenv("STORAGE_KEY")
bucket_name = os.getenv("BUCKET_NAME")
local_backup_path = os.getenv("LOCAL_BACKUP_PATH")
discord_webhook = os.getenv("DISCORD_WEBHOOK")

print("Start backing up")

backup_name = "server-backup.tar.gz"
full_local_backup_path = f"{local_backup_path}/{backup_name}"

#creating local backup
local_result = create_local_backup(full_local_backup_path, directories_to_backup)
# uploading local backup
upload_response = upload_backup(local_result, full_local_backup_path, backup_name)
#checking success
report = check_success(full_local_backup_path, directories_to_backup, local_result, upload_response)
#delete backup
remove_local_backup(full_local_backup_path)
#send notification
send_discord_notification(report, discord_webhook, now)

print("Script finished")                           
