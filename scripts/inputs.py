"""Load the versioned, repression-only well map and reject incomplete inputs."""
import json
import re
from config import PACKAGE, AUDIT


def load_inputs():
    """Return source records and maps keyed by the stable historical acquisition ID."""
    manifest=json.loads((PACKAGE/'inputs/source_manifest.json').read_text(encoding='utf-8'))
    mapping=json.loads(AUDIT.read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=1 or mapping.get('schema_version')!=1:
        raise ValueError('Unsupported input schema; use the manifest and map from the same package.')
    sources=manifest['files']
    maps={p['audit_index']:p for p in mapping['plates']}
    assert len(maps)==len(mapping['plates'])==len(sources)==6
    assert set(maps)=={p['audit_index'] for p in sources}
    for src in sources:
        assert src['path'].startswith('data/') and '..' not in src['path'].split('/')
        plate=maps[src['audit_index']]
        names=set();assigned={}
        for group in plate['groups']:
            assert group['name'] not in names
            names.add(group['name'])
            assert set(group['wells'])=={'N','P'}
            for condition,wells in group['wells'].items():
                assert len(wells)==3
                for well in wells:
                    assert re.fullmatch(r'[A-H](?:[1-9]|1[0-2])',well)
                    assert well not in assigned, f'Duplicate assignment: {src["path"]}, {well}'
                    assigned[well]=(group['name'],condition)
        reference={r['well']:r for r in plate['reference_wells']}
        assert len(reference)==len(plate['reference_wells'])==len(assigned)
        assert set(reference)==set(assigned)
        for well,(group,condition) in assigned.items():
            assert (reference[well]['group'],reference[well]['condition'])==(group,condition)
    # The corrected July NT assignment is essential to the N-GS15 comparison.
    nt=next(g for g in maps[9]['groups'] if g['name']=='132 / 168 (NT)')
    assert nt['wells']=={'N':['G1','G2','G3'],'P':['G4','G5','G6']}
    return sources,maps
