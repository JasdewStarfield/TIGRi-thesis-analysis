"""Run the thesis numerical pipeline into a separate, explicitly chosen folder."""
from pathlib import Path
from hashlib import sha256
import argparse,json,os,subprocess,sys

def main():
    if not __debug__:
        raise RuntimeError('Run without -O: numerical and source integrity assertions are required.')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,required=True,help='Directory containing data/ with the original relative paths')
    parser.add_argument('--output',type=Path,required=True,help='Empty or new directory for generated results')
    parser.add_argument('--font-regular',type=Path,default=Path('C:/Windows/Fonts/arial.ttf'))
    parser.add_argument('--font-bold',type=Path,default=Path('C:/Windows/Fonts/arialbd.ttf'))
    args=parser.parse_args();package=Path(__file__).resolve().parent
    output=args.output.resolve();root=args.data_root.resolve()
    if output.exists() and any(output.iterdir()):parser.error('--output must be empty to protect existing results')
    for font in [args.font_regular,args.font_bold]:
        if not font.is_file():parser.error(f'Font not found: {font}. Supply a readable TTF path.')
    manifest=json.loads((package/'inputs/source_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=1:
        parser.error('Unsupported source manifest schema version')
    sources=manifest['files']
    for record in sources:
        file=root/record['path']
        if not file.is_file():parser.error(f'Required raw export missing: {file}')
        if sha256(file.read_bytes()).hexdigest()!=record['sha256']:parser.error(f'Raw export hash differs: {file}')
    env=os.environ.copy();env.update(TIGR_DATA_ROOT=str(root),TIGR_OUTPUT=str(output),
        TIGR_FONT_REGULAR=str(args.font_regular.resolve()),TIGR_FONT_BOLD=str(args.font_bold.resolve()),PYTHONIOENCODING='utf-8')
    scripts=['analyze_endpoints.py','analyze_timeseries.py','verify_timeseries.py','make_tables.py','plot_endpoints.py','plot_timeseries.py']
    for name in scripts:
        print(f'Running {name}',flush=True)
        subprocess.run([sys.executable,str(package/'scripts'/name)],env=env,check=True)
    print(f'Completed; results: {output}')

if __name__=='__main__':main()
