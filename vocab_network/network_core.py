"""YAMLにある全単語を保持し、確認できた語源関係だけを描画する。"""
from pathlib import Path
import yaml

CHAPTER_GROUPS = {
 '1': ['ad', 'a(p)', 'a(t)', 'a(c)', 'a(s)', 'a', 'ob', 'oc(ob)', 'of(ob)'],
 '2': ['con','com','co','cor'], '3':['de'], '4':['sub','sup','sus'],
 '5':['sur','super'], '6':['ex','e'], '7':['pro','pre','for','per','fore'],
 '8':['re'], '9':['in','im','en','indi','em'], '10':['ab','dis','se'],
 '11':['un','im','in','a'], '12':['mono','uni','bi','du','tri','multi']}
# 教材見出し・登録されたpartsから確認できる表記群。章内のStackだけに適用。
ROOT_VARIANTS = {
 '1-1':['minister','mini','min'], '1-2':['voc','vow'], '1-3':['mon','monit','monstr'],
 '1-4':['just','jur','jud'], '1-5':['point','punct','pung'], '1-7':['cur','cure','cour'],
 '1-8':['chief','cap','cape','cup'], '1-9':['cept','ceive'], '1-12':['cur','course'],
 '1-13':['fend','fest'], '2-3':['gress','grade','gree'], '2-5':['sent','scent'],
 '2-6':['crete','cre','crease','cruit'], '2-7':['pete','peat','petite','petent','petit'],
 '2-8':['quest','quire'], '2-9':['clude','close'], '2-10':['memor','member','mind'],
 '2-11':['pel','pulse'], '3-1':['cide','cise','sciss'], '3-2':['bat','beat'],
 '3-3':['part','port'], '3-5':['tour','turn','torn'], '4-1':['stitute','stition'],
 '4-2':['stance','state'], '4-3':['ordin','order'], '4-4':['mit','miss'],
 '4-5':['ply','plus','ple','fill','pli'], '4-6':['pend','pense','pens'],
 '5-1':['vey','vy','view'], '5-2':['vive','viv','vigor'],
 '5-3':['pass','passage','pas'], '5-4':['vise','vis'],
 '5-5':['flu','fluct（＝fluent）'], '6-1':['ceed','cede','cess'],
 '6-2':['ist','sist'], '6-3':['patri','pater','patron'],
 '6-4':['vac','vast','void'], '6-5':['man','mani','manu'],
 '7-1':['mote','mot','move'], '7-4':['long','length','ling'],
 '7-6':['duce','duc','duct'], '7-7':['gram','graph','graphy'],
 '7-8':['hibit','habit'], '7-11':['side','sess','set'],
 '7-12':['gna','nat','na'], '8-1':['treat','trait'],
 '8-2':['strict','strain'], '8-3':['sem','simil','simul'],
 '8-4':['sult','sault','sail','ult'], '8-5':['force','fort'],
 '8-6':['volve','volt'], '8-7':['mode','mod'],
 '8-8':['ly','lige','li','lly'], '8-9':['lieve','levi','lev'],
 '9-2':['cline','clim','cli'], '9-3':['gen','gene','geni'],
 '9-5':['ped','pedi'], '9-7':['cour','courage','cord'],
 '9-11':['vent','ven'], '10-1':['use','usu','uti','ute'],
 '10-2':['ort','orig','origin','ori'],
 '10-3':['par','pear','appear'],
 '10-4':['sting','stinct','ting','tinct'],
 '10-6':['charge','car','carry'], '10-7':['par','pare','pair'],
 '12-1':['ton','tun','toun'],'12-4':['ple','pli','ploy','ply'],
}
# 見出しを優先して表示。推測で一致させない。
ROOT_LABELS = {'10-3':'par / pear', '10-1':'use / usu / uti / ute',
               '10-2':'ort / orig / origin', '10-4':'sting / stinct / ting / tinct',
               '10-6':'charge / car / carry', '10-7':'par / pare / pair'}

def normalize(form):
    return str(form or '').strip().lower().rstrip('-')

def build_network(vocab_dir):
    nodes, edges, stacks = {}, [], []
    seen = set()
    def node(key, label, meaning='', **extra):
        if key not in nodes:
            nodes[key] = {'id':key,'label':label,'type':'part','meaning':meaning or '',**extra}
        return key
    def edge(a,b,w,d,role,verified=True,note=''):
        if not a or not b or a==b: return False
        k=(str(d.get('stack')),str(w.get('word','')).lower())
        if k in seen: return False
        seen.add(k)
        meanings=w.get('meanings') or {}
        edges.append({'source':a,'target':b,'label':w['word'],'word':w['word'],
            'role':role,'meaning':' / '.join(str(x) for vals in meanings.values() for x in (vals if isinstance(vals,list) else [vals])),
            'meanings':meanings,'parts':w.get('parts') or [],'derivatives':w.get('derivatives') or [],
            'chapter':d.get('chapter'),'stack':d.get('stack'),'verified':verified,'note':note})
        return True
    for path in sorted(Path(vocab_dir).glob('chapter_*/*.yaml')):
        d=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        if not isinstance(d,dict): continue
        words=[w for w in d.get('words',[]) if isinstance(w,dict) and w.get('word')]
        ch,st=str(d.get('chapter','')),str(d.get('stack',''))

        # YAMLに定義されたStack固有の語根情報
        root_data = d.get('root') or {}
        root_forms = root_data.get('forms') or []
        root_meanings = root_data.get('meanings') or []
        inv=[{'word':w['word'],'role':w.get('role','related'),'meanings':w.get('meanings') or {},
              'parts':w.get('parts') or [],'derivatives':w.get('derivatives') or [],
              'chapter':d.get('chapter'),'stack':d.get('stack')} for w in words]
        stacks.append({
            'chapter': ch,
            'stack': st,
            'main_word': d.get('main_word', ''),
            'root_forms': root_forms,
            'root_meanings': root_meanings,
            'words': inv
        })
        main=next((w for w in words if w.get('role')=='main'),None)
        if main is None: main=next((w for w in words if w['word']==d.get('main_word')),None)
        if not main: continue
        parts=main.get('parts') or []
        head=parts[0] if parts else {}
        root=parts[1] if len(parts)>1 else {}
        prefix_forms=CHAPTER_GROUPS.get(ch,[normalize(head.get('form'))])
        title=' / '.join(prefix_forms) if len(prefix_forms)<=5 else ' / '.join(prefix_forms[:4])+' …'
        chapter_id=node(f'chapter-head:{ch}',title,d.get('prefix_meaning',''),
                        main_chapters=[ch],variants=prefix_forms)
        root_form=normalize(root.get('form'))

        # YAMLのroot.formsを優先し、未登録なら従来の定義を使用
        variants=(
            [normalize(f) for f in root_forms]
            if root_forms
            else ROOT_VARIANTS.get(st,[root_form])
        )
        if root_form and root_form not in variants:
            variants=[root_form,*variants]
        root_title=ROOT_LABELS.get(st,root_form)
        # Stack専用IDにする。異なる章/Stackの同綴り語根を誤って合流させない。
        root_id=node(f'stack-root:{st}',root_title,root.get('meaning',''),
                     variants=variants,stack=st,chapter=ch)
        if len(parts)>=2: edge(chapter_id,root_id,main,d,'main')
        for w in words:
            if w is main: continue
            wp=w.get('parts') or []
            # 参照書のStackに属することと、語源的な共通語根が確かであることは別。
            hits=[i for i,p in enumerate(wp) if normalize(p.get('form')) in variants]
            if not hits:
                meanings_to_match = (
                    root_meanings
                    if root_meanings
                    else [root.get('meaning')]
                )
                hits = [
                    i for i,p in enumerate(wp)
                    if p.get('meaning') and p.get('meaning') in meanings_to_match
                ]
            # 他の構成要素を語源的に確認できるときのみ実線。
            if hits:
                idx=hits[-1]
                others=[p for i,p in enumerate(wp) if i!=idx and normalize(p.get('form'))]
                if others:
                    other=others[0]
                    # 他Stackとの誤結合を防ぐためノードIDをStack内に限定。
                    oid=node(f'stack-part:{st}:{normalize(other.get("form"))}',normalize(other.get('form')),other.get('meaning',''))
                    if edge(root_id,oid,w,d,'related'):continue
            # 接続未確認でもグラフから単語を消さない。破線は所属表示であり語源の主張ではない。
            wid=node(f'unverified-word:{st}:{w["word"].lower()}',w['word'],'語源接続は未確認',type='unverified_word')
            edge(root_id,wid,w,d,'related',verified=False,note='破線はStackへの所属のみを示し、語源の一致を意味しません')
    # 同じStack内で、既存単語を構成要素に持つ関連語を検出
    word_relations = []

    for s in stacks:
        registered = {
            w['word'].lower(): w
            for w in s['words']
        }

        for w in s['words']:
            if w['role'] == 'main':
                continue

            # 構成要素が2つ未満なら従来どおり
            if len(w['parts']) < 2:
                continue

            for part in w['parts']:
                base = normalize(part.get('form'))

                if base == w['word'].lower():
                    continue

                if base in registered:
                    # 元の単語が実線で接続済みの場合のみ対象
                    base_edge = next(
                        (
                            e for e in edges
                            if str(e['stack']) == s['stack']
                            and e['word'].lower() == base
                            and e['verified']
                        ),
                        None
                    )

                    if base_edge:
                        word_relations.append({
                            'stack': s['stack'],
                            'chapter': s['chapter'],
                            'base_word': base,
                            'derived_word': w['word']
                        })
                        break
    linked={(str(e['stack']),e['word'].lower()) for e in edges}
    for s in stacks:
        for w in s['words']:
            w['connected']=(s['stack'],w['word'].lower()) in linked
            matching=next((e for e in edges if str(e['stack'])==s['stack'] and e['word'].lower()==w['word'].lower()),None)
            w['verified']=bool(matching and matching['verified'])
    return {
        'nodes': list(nodes.values()),
        'edges': edges,
        'stacks': stacks,
        'word_relations': word_relations
    }