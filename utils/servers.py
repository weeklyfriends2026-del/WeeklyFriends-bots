import os

def get_servers():
    servers = []
    for i in range(1, 4):
        servers.append({
            "name": os.getenv(f"SERVER{i}_NAME"),
            "rcon_host": os.getenv(f"SERVER{i}_HOST"),
            "rcon_port": int(os.getenv(f"SERVER{i}_PORT", 25575)),
            "rcon_password": os.getenv(f"SERVER{i}_RCON_PASSWORD"),
            "ftp_host": os.getenv(f"SERVER{i}_FTP_HOST"),
            "ftp_user": os.getenv(f"SERVER{i}_FTP_USER"),
            "ftp_password": os.getenv(f"SERVER{i}_FTP_PASSWORD"),
            "curseforge_id": os.getenv(f"SERVER{i}_CURSEFORGE_ID"),
        })
    return servers
