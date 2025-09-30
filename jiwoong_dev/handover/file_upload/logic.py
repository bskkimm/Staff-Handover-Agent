from typing import List
from .database import file_db


def list_uploaded_files() -> List[str]:
    files = file_db.get_all_files()
    return [f.original_name for f in files]


