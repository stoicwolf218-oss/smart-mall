import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(BASE_DIR, "latest_backup")


def remove_dir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
        print("removed:", path)
    else:
        print("not found:", path)


if __name__ == "__main__":
    remove_dir(DATA_DIR)
    remove_dir(BACKUP_DIR)
    print("data reset done")
