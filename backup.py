import smtplib, ssl
import tarfile, os
import b2sdk.v3 as b2
from datetime import datetime
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from discord_webhook import DiscordWebhook

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

def send_email(port, smtp_server, email_sender, email_receiver, password, message: MIMEMultipart):
    
    context = ssl.create_default_context()
    print("Sending email....")
    
    try:
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            print("Authenticating to SMPT server")
            server.login(email_sender, password)
            print("OK")
            print("Sending email")
            server.sendmail(email_sender, email_receiver, message.as_string())
            print("Email sent successfully")
    
    except smtplib.SMTPAuthenticationError as e:
        print(f"Error: Authentication failed: {e}")
    except smtplib.SMTPRecipientsRefused:
        print(f"Error: Recipient address refused: {e}")
    except smtplib.SMTPServerDisconnected:
        print(f"Error: Server disconnected {e}")
    except Exception as e:
        print(f"Unexpected error sending email: {e}")

def build_message(full_path, directories_to_backup, local_result, upload_response, email_sender, email_receiver, now) -> MIMEMultipart:
    
    local_backup_successful = False
    local_backup_path = "N/A"
    local_backup_size = 0
    
    upload_successful = False
    uploaded_backup_path = "N/A"
    uploaded_backup_size = 0

    try:
        if os.path.exists(full_path) and (local_result and len(local_result) > 0):
            local_backup_path = full_path
            local_backup_size = os.path.getsize(full_path)
            local_backup_successful = local_backup_size > 0
    except OSError as e:
        print(f"OSError: {e}")
    except Exception as e:
        print(f"Unexcpected error: {e}")

    try: 
        if upload_response and (upload_response.file_name and upload_response.size):
            uploaded_backup_path = upload_response.file_name
            uploaded_backup_size = upload_response.size
            upload_successful = upload_response.size > 0
    except AttributeError as e:
            print(f"Attribute error: {e}")
    except Exception as e:
            print(f"Unexpected error: {e}")
    
    html_message = f"""\
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .success {{ background-color: #d4edda; }}
                .failed {{ background-color: #f8d7da; }}
            </style>
        </head>
        <body>
            <h1>Backup report</h1>
            <table style="margin: 25px;">
                <tr>
                    <th>Status</th>
                    <th>Directory</th>
                    <th>Size (MB) </th>
                </tr>
    """

    all_size = 0
    all_folders_successful = False
    if local_result and len(local_result) > 0:
        all_folders_successful = True
        for d in directories_to_backup:
            folder_successful = False
            size = 0
            for item in local_result:
                if item.path.startswith(d[1:]):
                    size += item.size
            folder_successful = size > 0
            if not folder_successful:
                all_folders_successful = False
            html_message += f'<tr class="{"success" if folder_successful else "failed"}">'
            html_message += f"<td>{"Success" if folder_successful else "Failed"}"
            html_message += f"<td>{d}</td>"
            html_message += f"<td>{size / (1024 * 1024):.2f}</td>"
            html_message += "</tr>"
            all_size += size

    html_message += f"""\
                <tr class="{"success" if all_folders_successful else "failed"}">
                    <td>{"Success" if all_folders_successful else "Failed"}</td>
                    <td>All</td>
                    <td>{all_size / (1024 * 1024):.2f}</td>
                </tr>
            </table>
            <table style="margin: 25px;">
                <tr>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Path / File</th>
                    <th>Size (MB)</th>
                </tr>
                <tr class="{"success" if local_backup_successful else "failed"}">
                    <td>Local</td>
                    <td>{"Success" if local_backup_successful else "Failed"}</td>
                    <td>{local_backup_path}</td>
                    <td>{local_backup_size / (1024 * 1024):.2f}</td>
                </tr>
                <tr class="{"success" if upload_successful else "failed"}">
                    <td>Remote</td>
                    <td>{"Success" if upload_successful else "Failed"}</td>
                    <td>{uploaded_backup_path}</td>
                    <td>{uploaded_backup_size / (1024 * 1024):.2f}</td>
                </tr>
            </table>
        </body>
    </html>
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = f"{"Successful" if (local_backup_successful and upload_successful and all_folders_successful) else "Failed"} backup {now.strftime("%Y.%m.%d")}"
    message["From"] = email_sender
    message["To"] = email_receiver

    message.attach(MIMEText("Backup Report", "plain"))
    message.attach(MIMEText(html_message, "html"))

    return message

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

def send_discord_notification(discord_webhook):
    webhook = DiscordWebhook(discord_webhook, content="Webhook message")
    response = webhook.execute()

print("Script started")
print("Loading variables")

now = datetime.now()

load_dotenv()

try:
    directories_to_backup = open("backup.directories.conf").read().splitlines()
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
port = os.getenv("SMTP_PORT")
smtp_server = os.getenv("SMTP_SERVER")
password = os.getenv("SMTP_PASSWORD")
email_sender = os.getenv("EMAIL_SENDER")
email_receiver = os.getenv("EMAIL_RECEIVER")
local_backup_path = os.getenv("LOCAL_BACKUP_PATH")
discord_webhook = os.getenv("DISCORD_WEBHOOK")

print("Start backing up")
#backup_name = f"{now.year}-{now.month}-{now.day}-backup.tar.gz"
backup_name = "server-backup.tar.gz"
full_local_backup_path = f"{local_backup_path}/{backup_name}"

#creating local backup
#local_result = create_local_backup(full_local_backup_path, directories_to_backup)
# uploading local backup
#upload_response = upload_backup(local_result, full_local_backup_path, backup_name)
#bulding email from returned data
#message = build_message(full_local_backup_path, directories_to_backup, local_result, upload_response, email_sender, email_receiver, now)
#sending email
#send_email(port, smtp_server, email_sender, email_receiver, password, message)
#delete backup
#remove_local_backup(full_local_backup_path)

send_discord_notification(discord_webhook)

print("Script finished")                           
