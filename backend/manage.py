import os 
import sys 
from dotenv import load_dotenv
 
def main(): 
    load_dotenv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.local') 
    try: 
        from django.core.management import execute_from_command_line 
    except ImportError as exc: 
        raise ImportError("Couldn't import Django.") from exc 
    execute_from_command_line(sys.argv) 
 
if __name__ == '__main__': 
    main() 
