import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple

from db_con import connectcls_postgres  

from db_setup import run as main_setup_db


from update_subtables import run as update_subtables_run


def main():
    main_setup_db()
    update_subtables_run()



if __name__ == "__main__":
    main()

