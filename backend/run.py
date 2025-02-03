import uvicorn
import sys
from pathlib import Path

# Add both backend and backend/src to Python path
backend_path = Path(__file__).parent
src_path = backend_path / "src"
sys.path.extend([str(backend_path), str(src_path)])

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, reload_dirs=[str(src_path)]) 