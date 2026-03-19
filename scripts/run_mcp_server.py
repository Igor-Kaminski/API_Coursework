from pathlib import Path

from dotenv import load_dotenv

from app.mcp.server import main


load_dotenv(dotenv_path=Path(".env"))


if __name__ == "__main__":
    main()
