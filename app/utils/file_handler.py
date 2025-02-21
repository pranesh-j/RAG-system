import os
import uuid
from pathlib import Path
from fastapi import UploadFile
import shutil

class FileHandler:
    def __init__(self):
        self.temp_dir = Path("temp_uploads")
        self.temp_dir.mkdir(exist_ok=True)

    async def save_upload_file(self, upload_file: UploadFile) -> tuple[str, str]:
        """
        Save uploaded file to temporary directory
        Returns tuple of (file_path, file_extension)
        """
        try:
            # Create unique filename
            file_extension = Path(upload_file.filename).suffix.lower()[1:]
            temp_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = self.temp_dir / temp_filename
            
            # Save file
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            
            return str(file_path), file_extension
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            raise

    async def cleanup_file(self, file_path: str):
        """Remove temporary file after processing"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning up file: {str(e)}")
            # Don't raise here as this is cleanup

# Create singleton instance
file_handler = FileHandler()