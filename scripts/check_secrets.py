"""Check tracked/unignored source and built frontend for configured credential values."""
from pathlib import Path
import subprocess
from dotenv import dotenv_values


def main():
    values = [str(v) for name in ['.env','.env.production']
              for key,v in dotenv_values(name).items() if v and len(v)>15
              and (any(word in key for word in ['KEY','TOKEN','SECRET']) or ('DATABASE' in key and '@' in v))]
    names = subprocess.run(['git','ls-files','--cached','--others','--exclude-standard'],capture_output=True,text=True,check=True).stdout.splitlines()
    paths = [Path(name) for name in names] + list(Path('frontend/dist').rglob('*'))
    leaked = [str(p) for p in paths if p.is_file() and any(v.encode() in p.read_bytes() for v in values)]
    print('Credential scan: '+ ('PASS' if not leaked else 'FAIL in '+', '.join(leaked)))
    if leaked:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
