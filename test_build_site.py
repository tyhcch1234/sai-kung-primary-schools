#!/usr/bin/env python3
"""Offline contracts only; synthetic fixtures are never written into the repository."""
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('school_builder', ROOT / 'build_site.py')
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.hrefs = []
        self.script_data = ''
        self.in_payload = False
        self.detail_count = 0
        self.source_keys = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.hrefs.append(attrs.get('href', ''))
        if tag == 'details' and 'school-card' in attrs.get('class', '').split():
            self.detail_count += 1
        if tag == 'script' and attrs.get('id') == 'site-data':
            self.in_payload = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_payload = False

    def handle_data(self, data):
        if self.in_payload:
            self.script_data += data


def fixture():
    """Clearly labelled, artificial contract objects; not facts about any school."""
    school = {
        'id': 7, 'name': '合約測試甲 <script>alert("not real")</script>',
        'english_name': '=contract test', 'category': '合成類別',
        'website': 'javascript:alert(1)', 'profile_url': 'https://example.invalid/profile',
        'address': {'note': '<img src=x onerror=alert(1)>'}, 'school_net': None,
        'status': '僅為程式測試', 'scope_note': ['非學校研究', {'學制': '原標籤'}],
        'checked_date': '2099-01-01',
        'enrolment': {
            'academic_year': '2098/99', 'total': {'students': 11, 'academic_year': '2097/98', 'source_ids': ['1']},
            'grades': [
                {'grade': 'P1', 'students': None, 'classes': 2, 'source_ids': [1], 'note': None},
                {'grade': 'P6', 'students': 0, 'classes': 0, 'source_ids': ['1', 'missing'], 'academic_year': '2096/97', 'note': '真實0契約，不推算'},
                {'grade': 'Year 7', 'students': 3, 'classes': 1, 'source_ids': [1], 'note': '不得換作P6'},
                None,
            ], 'p6': None, 'source_ids': [1], 'note': {'原始備註': '不可加總'},
        },
        'enrolment_history': [{'academic_year': '2095/96', 'total': 15}],
        'activities': [{'title': '活動全部呈現', 'description': ['合成活動', {'object': '</script><script>bad</script>'}], 'tags': ['棋藝', {'測試': '結構'}], 'year': '2098/99', 'source_ids': ['1']}],
        'destinations': {
            'academic_year': '2096/97', 'cohort_total': 0, 'coverage': {'範圍': '僅部分公開，非全屆'},
            'note': '不是第一志願',
            'schools': [{'name': f'合成接收中學{i}', 'count': i if i else None, 'percentage': None, 'source_ids': [1], 'note': {'保留': i}, **({'academic_year': '2094/95'} if i == 12 else {})} for i in range(13)],
            'source_ids': [1],
        },
        'preferences': {'observed': '觀察證據', 'inference': '策略推論', 'caveat': None, 'source_ids': [1]},
        'school_links': [{'school': '合成關係中學', 'relationship': '尚待確認', 'note': None, 'source_ids': [1]}],
        'social': [
            {'platform': 'Facebook', 'account': '合成官方帳戶', 'url': 'https://example.invalid/fb', 'status': 'verified official', 'verification': {'官網連結': 'https://example.invalid/proof'}, 'source_ids': ['1']},
            {'platform': 'Instagram', 'account': '合成校友帳戶', 'url': 'https://example.invalid/ig', 'status': '校友會／非官方', 'verification': '不可混統計', 'source_ids': [1]},
            {'platform': 'YouTube', 'account': '合成第三方', 'url': 'data:text/html,bad', 'status': '第三方', 'verification': None, 'source_ids': [999]},
        ],
        'contact': {'phone': '=CMD(1)', 'email': 'contract@example.invalid', 'source_ids': [1]},
        'marketing': {'segment': '合成分群', 'priority_rationale': {'缺口': None}, 'entry_offer': '合成提案', 'contact_role': '未聯絡', 'message': '中學P5/P6支援', 'channels': ['官網'], 'caveats': ['非排名']},
        'sources': [{'id': 1, 'title': '合成來源 & proof', 'url': 'https://example.invalid/source', 'academic_year': '2098/99', 'accessed_date': '2099-01-01'}],
        'gaps': ['合成測試，不可發布'], 'extra': {'new-field': '<object>'},
    }
    irregular = {
        'id': 'special/id', 'name': '合約測試乙', 'english_name': None, 'category': '另一合成類別',
        'enrolment': {'academic_year': None, 'total': None, 'grades': {'grade': 'Grade 6', 'students': '2', 'classes': None, 'source_ids': 's2', 'note': '保留學制'}, 'p6': None},
        'activities': {'title': '單項活动', 'description': {'text': '可讀'}, 'year': None, 'source_ids': {'id': 's2'}},
        'destinations': None, 'preferences': ['不規則但保留'], 'school_links': '尚待研究',
        'social': {'facebook': {'status': '未找到', 'url': None, 'verification': None}, 'instagram': 'https://example.invalid/unverified', 'xiaohongshu': None},
        'contact': None, 'marketing': None,
        'sources': {'s2': {'title': '來源物件鍵契約', 'url': 'https://example.invalid/s2', 'academic_year': None, 'accessed_date': None}}, 'gaps': None,
    }
    data = {'checked_date': '2099-01-01', 'scope_notes': ['僅合成測試'], 'schools': [school, irregular, None], 'failures': [{'id': None, 'reason': '合成失敗'}], 'summary': {'notice': '合約測試不是真實研究'}}
    strategy = {'context': {'暫定': '中學P5/P6招生'}, 'main_conclusion': '非學校排名',
                'segments': [{'name': '測試分群', 'rationale': None, 'school_ids': ['7', 'special/id', 'unknown'], 'offer': {'list': ['提案']}, 'message': None, 'channels': []}],
                'priority': [{'school_id': 7, 'reason': '合成考量', 'evidence_gap': '合成缺口'}],
                'timeline': [{'period': '測試階段', 'action': ['提案'], 'kpi': None}, None],
                'content_plan': [{'channel': '官網', 'audience': '合成對象', 'content': {'note': '安全<內容>'}, 'cta': '閱讀'}],
                'measurement': [{'kpi': '合成量度'}], 'limitations': ['不可對外發布'], 'extra_strategy': {'keep': True}}
    return data, strategy


class StaticBuildContracts(unittest.TestCase):
    def test_end_to_end_without_repo_index_change(self):
        original = (ROOT / 'index.html').read_bytes()
        data, strategy = fixture()
        with tempfile.TemporaryDirectory(prefix='sai-kung-contract-', dir='/tmp') as tmp:
            tmp = Path(tmp)
            data_path, strategy_path = tmp / 'input.json', tmp / 'strategy-input.json'
            data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            strategy_path.write_text(json.dumps(strategy, ensure_ascii=False) + '\n', encoding='utf-8')
            output = tmp / 'output'
            command = [sys.executable, str(ROOT / 'build_site.py'), '--data', str(data_path), '--strategy', str(strategy_path), '--output-dir', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = {'index.html', 'data.json', 'strategy.json', 'report.md', 'styles.css', 'app.js', 'manus-routes.json'}
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            self.assertEqual((output / 'data.json').read_bytes(), data_path.read_bytes())
            self.assertEqual((output / 'strategy.json').read_bytes(), strategy_path.read_bytes())
            content = (output / 'index.html').read_text(encoding='utf-8')
            parser = PageParser(); parser.feed(content)
            self.assertEqual(len(parser.ids), len(set(parser.ids)), 'Duplicate HTML IDs')
            self.assertEqual(parser.detail_count, len(data['schools']))
            payload = json.loads(parser.script_data)
            self.assertEqual(payload['data'], data)
            self.assertTrue(payload['index'][0]['p6_known'], 'Actual 0 is known')
            self.assertEqual(payload['index'][0]['p6_sort'], 0)
            self.assertFalse(payload['index'][1]['p6_known'], 'Grade 6 is not silently P6')
            self.assertEqual(payload['index'][0]['total_sort'], 11)
            self.assertIn('來源 missing：未能對應', content)
            self.assertNotIn('來源 1：未能對應', content)
            self.assertNotIn('來源 s2：未能對應', content)
            self.assertNotIn('<script>alert(', content)
            self.assertNotIn('<img src=x', content)
            self.assertIn('&lt;script&gt;alert', content)
            self.assertIn('合成接收中學12', content)
            self.assertIn('Year 7', content)
            self.assertIn('Grade 6', content)
            self.assertIn('2097/98', content)
            self.assertIn('2096/97', content)
            self.assertIn('2094/95', content)
            self.assertIn('verified official', content)
            self.assertIn('校友會／非官方', content)
            self.assertIn('身份核實證據', content)
            self.assertIn('小紅書', content)
            self.assertIn('活動全部呈現', content)
            self.assertIn('合成來源', content)
            self.assertIn('來源物件鍵契約', content)
            self.assertIn('每校宣傳切入建議', content)
            self.assertIn('合成測試，不可發布', content)
            self.assertIn('學年：2096/97', content)
            self.assertIn('<span class="value">0</span>', content)
            self.assertIn(BUILDER.UNKNOWN, content)
            self.assertIn('href="../"', content)
            self.assertIn('aria-live="polite"', content)
            self.assertIn(BUILDER.CANONICAL, content)
            self.assertTrue(any(tag == 'link' and attrs.get('rel') == 'icon' and attrs.get('href') == BUILDER.read_favicon() for tag, attrs in parser.tags))
            for href in parser.hrefs:
                self.assertTrue(href.startswith('#') or href in ('../', 'data.json', 'strategy.json', 'report.md') or BUILDER.safe_url(href), href)
                if href.startswith('#'):
                    self.assertIn(href[1:], parser.ids, f'Broken local hash {href}')
            scripts = [(tag, attrs) for tag, attrs in parser.tags if tag == 'script']
            self.assertEqual(len(scripts), 2)
            self.assertTrue(any(attrs.get('src') == 'app.js?v=readable20261109' for _, attrs in scripts))
            self.assertTrue(any(tag == 'link' and attrs.get('href') == 'styles.css?v=readable20261109' for tag, attrs in parser.tags))
            self.assertEqual(json.loads((output / 'manus-routes.json').read_text())['routes'][0]['path'], '/sai-kung-primary-schools/')
            report = (output / 'report.md').read_text(encoding='utf-8')
            self.assertIn('合成接收中學12', report)
            self.assertIn('extra', report)
            self.assertIn('未能對應', report)
            self.assertIn('<https://example.invalid/source>', report)
            before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir()}
            rerun = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir()}
            self.assertEqual(before, after, 'Rebuild must be deterministic')
            # Missing/invalid/empty input must not overwrite existing outputs.
            for bad in (None, [], {'schools': []}, {'schools': 'bad'}):
                data_path.write_text(json.dumps(bad), encoding='utf-8')
                failed = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual(after, {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir()})
            data_path.write_text('{broken', encoding='utf-8')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            data_path.unlink()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual((ROOT / 'index.html').read_bytes(), original)

    def test_url_allowlist_and_values(self):
        for url in ('javascript:alert(1)', 'data:text/plain,test', '//example.invalid', 'https://user:pass@example.invalid', 'https://example.invalid/\n', 'https://example.invalid\\evil', ' https://example.invalid', {'url': 'https://example.invalid'}, 'https://example.invalid:bad'):
            self.assertIsNone(BUILDER.safe_url(url), url)
        self.assertEqual(BUILDER.safe_url('https://example.invalid/a?x=1&y=2'), 'https://example.invalid/a?x=1&y=2')
        self.assertEqual(BUILDER.safe_url('http://example.invalid'), 'http://example.invalid')
        self.assertEqual(BUILDER.scalar_id(7), BUILDER.scalar_id('7'))
        self.assertIsNone(BUILDER.scalar_id({}))
        self.assertEqual(BUILDER.number(0), 0)
        self.assertIsNone(BUILDER.number(None))
        self.assertIsNone(BUILDER.number(True))
        self.assertIsNone(BUILDER.number('unknown'))
        self.assertEqual(BUILDER.metric_parts({'students': 0, 'academic_year': None}, {'academic_year': 'parent'})['academic_year'], None)
        self.assertIsNone(BUILDER.grade_code('Year 6'))
        self.assertEqual(BUILDER.grade_code('小六'), 'P6')
        self.assertNotIn('<script>', BUILDER.rich({'x': ['<script>']}))

    def test_duplicate_and_irregular_records(self):
        data, strategy = fixture()
        data['schools'].append(dict(data['schools'][0]))
        data['schools'][0]['enrolment']['p6'] = {'students': 8, 'academic_year': '2099/00'}
        # shared nested fixture object has two facts in both duplicated records
        renderer = BUILDER.Renderer(data, strategy)
        page = renderer.build(BUILDER.read_favicon())
        parsed = PageParser(); parsed.feed(page)
        self.assertEqual(len(parsed.ids), len(set(parsed.ids)))
        self.assertIsNone(renderer.index[0]['p6_sort'])
        self.assertTrue(renderer.index[0]['p6_known'])
        self.assertTrue(any('重複學校ID' in warning for warning in renderer.warnings))
        self.assertTrue(any('多條' in warning for warning in renderer.warnings))
        self.assertIn('2099/00', page)
        self.assertIn('不相加', page)

    def test_javascript_filter_sort_csv(self):
        script = r'''
const assert = require('node:assert/strict');
const { csvCell, makeCSV, filtered } = require(process.argv[1]);
for (const value of ['=1+1','+SUM(A1)','-2','@CMD','  =CMD','\t=CMD','\r=CMD','\n=CMD']) assert.ok(csvCell(value).startsWith('"\''), value);
assert.equal(csvCell('a"b,c'), '"a""b,c"');
assert.equal(csvCell(0), '"0"');
assert.equal(csvCell(null), '"未公開／未核實"');
const index = [
 {key:0,name:'A',category:'X',search:'A Chess ReceiverOne',p6_known:true,p6_sort:0,total_sort:11},
 {key:1,name:'B',category:'Y',search:'B Music ReceiverTwo',p6_known:false,p6_sort:null,total_sort:null},
 {key:2,name:'C',category:'X',search:'C Chess ReceiverTwo',p6_known:true,p6_sort:4,total_sort:20}
];
const state = {query:'',category:'',knownP6:false,sort:'p6-asc'};
assert.deepEqual(filtered(index,state).map(x=>x.key),[0,2,1]);
assert.deepEqual(filtered(index,{...state,sort:'p6-desc'}).map(x=>x.key),[2,0,1]);
assert.deepEqual(filtered(index,{...state,sort:'total-asc'}).map(x=>x.key),[0,2,1]);
assert.deepEqual(filtered(index,{...state,query:'receiverTwo',category:'X',knownP6:true}).map(x=>x.key),[2]);
assert.deepEqual(filtered(index,{...state,query:'chess',category:'Y'}),[]);
assert.equal(index[0].key,0,'Original index should not be sorted/mutated');
const schools = [{id:0,name:'=BAD()',category:'X',enrolment:{academic_year:'2098/99',total:0,grades:[{grade:'P6',students:null,classes:2,source_ids:[1],note:'a"b,c'},{grade:'Year 7',students:3,academic_year:'2097/98'}],p6:{students:0,academic_year:'2096/97'}}}];
const csv=makeCSV(schools);
assert.ok(csv.startsWith('\ufeff'));
assert.ok(csv.includes('"\'=BAD()"'));
assert.ok(csv.includes('"a""b,c"'));
assert.ok(csv.includes('"2097/98"'));
assert.ok(csv.includes('"2096/97"'));
assert.ok(csv.includes('"未公開／未核實"'));
assert.ok(csv.includes('"0"'));
assert.ok(csv.includes('獨立小六紀錄'));
assert.equal(csv.split('\r\n').length,6);
const nullCSV=makeCSV([{id:1,name:'Null',enrolment:{academic_year:'parent-year',total:{students:null,count:99,academic_year:null},grades:[{grade:'P6',students:0,academic_year:null}],p6:{students:null,count:88,academic_year:null}}}]);
assert.ok(!nullCSV.includes('parent-year'),'Explicit null year must not inherit parent year');
assert.ok(!nullCSV.includes('"99"'),'Explicit null students must not fall through to count');
assert.ok(!nullCSV.includes('"88"'),'Explicit null p6 students must not fall through');
console.log('PASS Node: combined filters, zero/null sort, years, quoting, formula injection');
'''
        result = subprocess.run(['node', '-e', script, str(ROOT / 'app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_destination_history_static_search_and_single_school_wrapper(self):
        data, strategy = fixture()
        school = data['schools'][0]
        school['destinations_history'] = [
            {'academic_year': '2093/94', 'cohort_total': 7, 'coverage': '合成歷年部分名單', 'schools': [{'name': '只在歷史的接收校甲', 'count': 0}]},
            {'academic_year': '2092/93', 'cohort_total': 9, 'coverage': '合成歷年第二屆', 'schools': [{'name': '只在歷史的接收校乙', 'count': None}]},
        ]
        school['destinations'].update({'listed_count_sum': 117, 'reported_cohort_total': 117, 'cohort_total_verification': 'unverified_full_cohort_denominator'})
        data['schools'][1]['destinations'] = {'academic_year': None, 'coverage': '合成政策，不是結果', 'record_type': 'policy_or_permission_not_observed_distribution', 'schools': [{'name': '僅政策對象', 'percentage': 100}]}
        renderer = BUILDER.Renderer(data, strategy)
        self.assertIn('只在歷史的接收校甲', renderer.index[0]['destination_names'])
        self.assertIn('只在歷史的接收校乙', renderer.index[0]['search'])
        self.assertNotIn('僅政策對象', renderer.index[1]['destination_names'])
        self.assertFalse(renderer.index[1]['any_destinations'])
        block = renderer.destination(0, True)
        self.assertEqual(block.count('<article '), 1)
        self.assertEqual(block.count('<table>'), 3)
        self.assertEqual(block.count('data-destination='), 15)
        detail = renderer.destination(0)
        for value in ('2093/94', '2092/93', '合成歷年部分名單', '合成歷年第二屆', '公開列項人數小計（非全屆分母）', '原研究隊列值（未獨立核實，不採為全屆）', '全屆分母核實狀態'):
            self.assertIn(value, detail)
        self.assertEqual(detail.count('該屆總人數：'), 3)
        self.assertEqual(detail.count('公布覆蓋範圍：'), 3)
        self.assertIn('data-destination="僅政策對象" data-observed="false"', renderer.destination(1))

    def test_p6_fact_dedup_normalized_year_and_preferred_object(self):
        data, strategy = fixture()
        e = data['schools'][0]['enrolment']
        e['p6'] = {'students': 0, 'classes': 0, 'academic_year': '2096/2097（原文）', 'note': 'p6首選備註', 'source_ids': ['1'], 'verification': 'official_exact', 'applicability': 'standard_primary_final_year'}
        renderer = BUILDER.Renderer(data, strategy)
        parts = renderer.p6_entries(e)
        self.assertEqual(len(parts), 1, 'Different notes/sources do not duplicate the same numeric fact')
        self.assertEqual(parts[0]['note'], 'p6首選備註')
        self.assertEqual(renderer.index[0]['p6_sort'], 0)
        e['grades'].append({'grade': 'P6', 'students': 1, 'classes': 0, 'academic_year': '2096/97'})
        self.assertEqual(len(renderer.p6_entries(e)), 2, 'Different numeric fact remains separate')
        e['grades'].append({'grade': 'P6', 'students': 0, 'classes': 0, 'academic_year': '2095/96'})
        e['grades'].append({'grade': 'P6', 'students': 0, 'classes': 1, 'academic_year': '2096/97'})
        self.assertEqual(len(renderer.p6_entries(e)), 4, 'Different year or classes remains separate')
        self.assertIsNone(BUILDER.Renderer(data, strategy).index[0]['p6_sort'])

    def test_platform_normalized_and_original_alumni_status(self):
        data, strategy = fixture()
        school = data['schools'][0]
        school['social'].extend([
            {'platform': '小紅書／REDnote', 'platform_normalized': '小紅書', 'account': '合成已核實小紅書', 'status': '校方連出，內容未讀', 'verification': '合成校網連出'},
            {'platform': 'REDnote', 'platform_normalized': '小紅書', 'account': '合成校友', 'status': '已核實校友會／非官方', 'verification': '校友帳戶證據'},
            {'platform': 'Instagram', 'platform_normalized': 'Facebook', 'account': '標準化優先', 'status': '未核實'},
        ])
        renderer = BUILDER.Renderer(data, strategy)
        groups = renderer.social_groups(school)
        self.assertEqual(len(groups['小紅書']), 2)
        self.assertTrue(any(r.get('account') == '標準化優先' for r in groups['Facebook']))
        output = renderer.social_cell(0, groups['小紅書'])
        self.assertIn('校方連出，內容未讀', output)
        self.assertIn('已核實校友會／非官方', output)
        self.assertNotIn('verified official', output)

    def test_applicability_conflicted_total_and_separate_class_year(self):
        data, strategy = fixture()
        e = data['schools'][0]['enrolment']
        e.update({'total': 450, 'reported_total': 450, 'total_verification': 'official_table_with_unresolved_internal_conflict', 'total_scope': 'primary_school'})
        e['p6'] = {'students': None, 'classes': None, 'academic_year': '2098/99', 'source_ids': ['1'], 'verification': 'not_applicable', 'applicability': 'not_a_standard_primary_P6', 'note': '合成學制'}
        e['grades'] = [{'grade': 'Year 1', 'students': None, 'academic_year': None, 'classes': None, 'reported_classes': 4, 'classes_scope': 'average_not_grade_actual', 'classes_academic_year': None, 'source_ids': [1]}]
        data['schools'][0]['enrolment_history'] = [dict(e)]
        renderer = BUILDER.Renderer(data, strategy)
        self.assertIsNone(renderer.index[0]['total_sort'])
        parts = BUILDER.metric_parts(e['p6'], e)
        self.assertEqual(parts['applicability'], 'not_a_standard_primary_P6')
        metric = renderer.metric(0, parts)
        for value in ('不適用（非標準小六學制）', '2098/99', 'not_applicable', '來源 1', '合成學制'):
            self.assertIn(value, metric)
        output = renderer.enrolment_detail(0)
        self.assertEqual(output.count('原表列450（總數有矛盾）'), 2, 'Main and historical totals are qualified')
        self.assertNotIn('<span class="value">450</span>', output)
        self.assertIn('來源列平均4班，非本級實際班數；班數年份未明', output)
        grade_parts = BUILDER.metric_parts(e['grades'][0], e)
        grade_parts['classes_academic_year'] = '2092/93'
        self.assertIn('班數學年：2092/93', renderer.class_metric(0, grade_parts))
        self.assertNotIn('2098/99', renderer.class_metric(0, grade_parts))
        e['total_verification'] = 'official_exact'
        self.assertEqual(BUILDER.Renderer(data, strategy).index[0]['total_sort'], 450)
        self.assertIn('<span class="value">450</span>', BUILDER.Renderer(data, strategy).enrolment_detail(0))

    def test_summary_contract_and_explicit_main_record_fallback(self):
        data, strategy = fixture()
        expected = [15, 11, 10, 20, 3]
        fields = ['verified_total_count', 'verified_grade_count', 'verified_p6_count', 'verified_destinations_count', 'verified_destination_school_counts_count']
        data['summary'] = {**dict(zip(fields, expected)), 'definitions': {field: '合成定義：' + field for field in fields}}
        renderer = BUILDER.Renderer(data, strategy)
        kpis = renderer.coverage_kpis()
        self.assertEqual([value for value, _, _ in kpis[1:]], expected, 'Use supplied audited summary, not main-record calculations')
        for _, _, note in kpis[1:]:
            self.assertIn('合成定義', note)
        self.assertFalse(any('僅主記錄' in label for _, label, _ in kpis))
        data['summary']['verified_p6_count'] = 0
        self.assertEqual(BUILDER.Renderer(data, strategy).coverage_kpis()[3][0], 0)
        data.pop('summary')
        fallback = BUILDER.Renderer(data, strategy).coverage_kpis()
        self.assertTrue(all('僅主記錄' in label for _, label, _ in fallback[1:]))
        self.assertEqual(fallback[2][0], 1, 'Historical totals do not enter legacy fallback')

    def test_report_copy_and_lazy_raw_payload(self):
        data, strategy = fixture()
        data['integration'] = {'local_path': '/sandbox/internal'}
        data['schools'][0]['raw_data'] = {'sensitive_shadow': '只在原資料審核', 'percentage': 77}
        data['schools'][0]['integration'] = {'local_path': '/sandbox/internal-school'}
        renderer = BUILDER.Renderer(data, strategy)
        page = renderer.build(BUILDER.read_favicon())
        static = page.split('<script id="site-data"')[0]
        self.assertNotIn('sensitive_shadow', static)
        self.assertNotIn('/sandbox/internal', static)
        self.assertEqual(static.count('<pre></pre>'), 3)
        self.assertIn('data-school-key="0"><summary>檢視此校完整原始JSON', static)
        self.assertIn('href="data.json" download', static)
        parser = PageParser(); parser.feed(page)
        self.assertEqual(json.loads(parser.script_data)['data'], data)
        fallback = renderer.report()
        self.assertNotIn('sensitive_shadow', fallback)
        self.assertNotIn('integration', fallback)
        self.assertNotIn('{"', fallback)
        self.assertIn('合成接收中學12', fallback)
        with tempfile.TemporaryDirectory(prefix='sai-kung-report-contract-', dir='/tmp') as tmp:
            tmp = Path(tmp)
            inp, strat, report = tmp / 'input.json', tmp / 'strategy.json', tmp / 'readable-report.md'
            inp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            strat.write_text(json.dumps(strategy, ensure_ascii=False), encoding='utf-8')
            original = '# 合成可讀報告\r\n原報告不可重寫。\r\n'.encode('utf-8')
            report.write_bytes(original)
            command = [sys.executable, str(ROOT / 'build_site.py'), '--data', str(inp), '--strategy', str(strat), '--report', str(report), '--output-dir', str(tmp / 'out')]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((tmp / 'out' / 'report.md').read_bytes(), original)
            self.assertEqual(report.read_bytes(), original)
            report.unlink()
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual((tmp / 'out' / 'report.md').read_bytes(), original)

    def test_csv_history_qualifications_and_safe_lazy_raw(self):
        script = r'''
const assert = require('node:assert/strict');
const { makeCSV, populateRawRecord } = require(process.argv[1]);
const schools = [{id: 0, name: '合成CSV', category: '測試', sources: [{id:1,note:'來源備註原文'}],
  enrolment: {academic_year:'2098/99',total:450,reported_total:450,total_verification:'official_table_with_unresolved_internal_conflict',total_scope:'primary_scope',source_ids:[1],note:'總數矛盾原文',
    grades:[{grade:'Year 1',students:null,academic_year:null,classes:null,reported_classes:4,classes_scope:'average_not_grade_actual',classes_academic_year:null,classes_source_ids:[1],source_ids:[1]}],
    p6:{students:null,academic_year:'2098/99',source_ids:[1],verification:'not_applicable',applicability:'not_a_standard_primary_P6'}},
  enrolment_history:[{academic_year:'2096/97',total:0,reported_total:0,total_verification:'official_exact',total_scope:'historical_primary_scope',source_ids:[1],note:'歷年原文',grades:[{grade:'P6',students:0,classes:0,academic_year:'2095/96',classes_academic_year:'2094/95',source_ids:[1],note:'年级原文'}]}]}];
const csv = makeCSV(schools);
const lines = csv.slice(1).trimEnd().split('\r\n');
const parse = line => Array.from(line.matchAll(/"((?:[^"]|"")*)"(?:,|$)/g), x=>x[1].replace(/""/g,'"'));
const headers = parse(lines[0]);
const rows = lines.slice(1).map(parse);
const value = (row, column) => row[headers.indexOf(column)];
assert.equal(rows.length, 5, 'main and history each remain separate, no summation');
assert.ok(rows.every(row=>row.length===headers.length));
assert.equal(value(rows[0],'實際人數'),'未公開／未核實');
assert.equal(value(rows[0],'原報告值'),'450');
assert.equal(value(rows[0],'核實狀態'),'official_table_with_unresolved_internal_conflict');
assert.equal(value(rows[0],'總數範圍'),'primary_scope');
assert.equal(value(rows[1],'原報告班數'),'4');
assert.equal(value(rows[1],'班數口徑'),'average_not_grade_actual');
assert.equal(value(rows[1],'班數來源學年'),'未公開／未核實');
assert.equal(value(rows[2],'小六適用性'),'not_a_standard_primary_P6');
assert.equal(value(rows[2],'核實狀態'),'not_applicable');
assert.equal(value(rows[3],'實際人數'),'0');
assert.equal(value(rows[3],'原報告值'),'0');
assert.equal(value(rows[3],'學年'),'2096/97');
assert.ok(value(rows[3],'紀錄類別').includes('歷年記錄1'));
assert.equal(value(rows[4],'班數來源學年'),'2094/95');
assert.equal(value(rows[4],'學年'),'2095/96');
assert.ok(csv.includes('來源備註原文'));
assert.ok(csv.includes('年级原文'));
const pre = {dataset:{},textContent:''};
const detail = {open:false,dataset:{schoolKey:'0'},querySelector:()=>pre};
const raw = [{name:'<img src=x onerror=alert(1)>',extra:{keep:0}}];
populateRawRecord(detail,raw); assert.equal(pre.textContent,'');
detail.open=true; populateRawRecord(detail,raw);
assert.equal(pre.textContent,JSON.stringify(raw[0],null,2));
assert.equal(pre.dataset.loaded,'true');
assert.equal(pre.innerHTML,undefined,'Only textContent may be assigned');
raw[0].name='changed'; populateRawRecord(detail,raw);
assert.ok(pre.textContent.includes('<img'),'First toggle populates exactly once');
console.log('PASS Node: history/verification/scope/applicability/class years/source notes/zero + textContent-only lazy raw');
'''
        result = subprocess.run(['node', '-e', script, str(ROOT / 'app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


    def test_readable_static_structure_and_fold_defaults(self):
        data, strategy = fixture()
        renderer = BUILDER.Renderer(data, strategy)
        page = renderer.build(BUILDER.read_favicon())
        parsed = PageParser(); parsed.feed(page)
        self.assertLess(page.index('<section id="profiles"'), page.index('<section id="roster"'))
        self.assertIn('<h1>西貢小學研究指南</h1>', page)
        self.assertIn('<a href="#profiles">搜尋及查看學校</a>', page)
        self.assertIn('排序依主紀錄', page)
        for classname in ('source-index', 'history-record', 'evidence-panel', 'fold-panel'):
            details = [attrs for tag, attrs in parsed.tags if tag == 'details' and classname in attrs.get('class', '').split()]
            self.assertTrue(details, classname)
            self.assertTrue(all('open' not in attrs for attrs in details), classname)
        sections = [attrs for tag, attrs in parsed.tags if tag == 'details' and 'profile-section' in attrs.get('class', '').split()]
        self.assertEqual(len(sections), 6 * len(data['schools']))
        self.assertEqual(sum('open' in attrs for attrs in sections), len(data['schools']))
        for key in range(len(data['schools'])):
            card = renderer.school_card(key)
            summary = card.split('<summary>', 1)[1].split('</summary>', 1)[0]
            self.assertNotIn('<a ', summary, 'Summary must not mix links with toggle interaction')
            for classname in ('school-name', 'summary-stats', 'stat-year', 'social-chip', 'summary-expand'):
                self.assertIn(classname, summary)
            for heading in ('學生人數', '重點活動', '升中去向與制度', '社交平台', '宣傳切入與聯絡', '來源與資料限制'):
                self.assertIn('<summary>' + heading + '</summary>', card)
        self.assertIn('逐級比較表（展開查看）', page)
        compact = renderer.roster_row(0)
        self.assertNotIn('不可加總', compact, 'Long whole-school note belongs in profile evidence')
        self.assertNotIn('真實0契約', compact)
        self.assertIn('來源 1', compact)

    def test_readable_summary_latest_official_history_and_p6_applicability(self):
        data, strategy = fixture()
        school = data['schools'][0]
        school['enrolment'] = {'academic_year': '2100/01', 'total': None, 'total_verification': 'not_verified', 'grades': [], 'p6': {'students': None, 'verification': 'not_verified', 'applicability': 'standard_primary_final_year'}}
        def historical(year, total, status='official_exact', p6=0):
            return {'academic_year': year, 'total': total, 'total_verification': status,
                    'p6': {'students': p6, 'verification': status, 'applicability': 'standard_primary_final_year'}}
        school['enrolment_history'] = [historical('2095/96', 25, p6=5), historical('2097/98', 0), historical('2098/99', 450, 'official_table_with_unresolved_internal_conflict'), historical('2099/00', 99, 'media_report_not_official_exact'), historical('2100/01', 120, 'out_of_primary_scope')]
        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
        renderer = BUILDER.Renderer(data, strategy)
        total, history = renderer.summary_metric(school, 'total')
        self.assertTrue(history)
        self.assertEqual(total['value'], 0)
        self.assertEqual(total['academic_year'], '2097/98')
        p6, history = renderer.summary_metric(school, 'p6')
        self.assertTrue(history)
        self.assertEqual(p6['value'], 0)
        self.assertIsNone(renderer.index[0]['total_sort'], 'Historical summary must not change sorting contract')
        self.assertFalse(renderer.index[0]['p6_known'])
        card = renderer.school_card(0)
        self.assertIn('歷史資料 · 2097/98', card.split('</summary>', 1)[0])
        renderer.build(BUILDER.read_favicon())
        self.assertEqual(before, json.dumps(data, ensure_ascii=False, sort_keys=True))
        school['enrolment']['p6']['applicability'] = 'not_a_standard_primary_P6'
        part, history = renderer.summary_metric(school, 'p6')
        self.assertFalse(history)
        self.assertEqual(part['applicability'], 'not_a_standard_primary_P6')
        self.assertIn('不適用（非標準小六學制）', renderer.school_card(0).split('</summary>', 1)[0])

    def test_readable_social_uses_normalized_identity_not_status_keywords(self):
        data, strategy = fixture()
        renderer = BUILDER.Renderer(data, strategy)
        self.assertEqual(renderer.social_status({'status': '已核實官方校友 fake official'}), ('unverified', '核實狀態未標準化'))
        self.assertEqual(renderer.social_status({'verification_status_normalized': 'other_scope_not_counted', 'status': '官方帳戶'}), ('other', '其他範圍帳戶'))
        self.assertEqual(renderer.social_status({'verification_status_normalized': 'verified_identity', 'account_scope': 'other_organisation_or_subaccount'}), ('other', '其他範圍帳戶'))
        record = {'platform': 'Facebook', 'url': 'https://example.invalid/fb', 'account': '合成帳戶', 'verification_status_normalized': 'verified_identity', 'status': '原始狀態完整保留', 'verification': '完整長身份證據不可截斷', 'extra': {'safe': '保留'}}
        output = renderer.social_entry(0, record)
        self.assertIn('social-chip verified', output)
        self.assertIn('完整長身份證據不可截斷', output)
        self.assertIn('原始狀態完整保留', output)
        self.assertIn('evidence-panel', output)
        self.assertNotIn(' open', output)

    def test_readable_destination_limit_visible_before_evidence(self):
        data, strategy = fixture()
        renderer = BUILDER.Renderer(data, strategy)
        d = {'academic_year': '2099/00', 'coverage': '部分公開名單；其餘去向未列。',
             'completeness_verified': False, 'schools': [{'name': '合成中學', 'count': 3}],
             'source_ids': [1]}
        self.assertIn('部分名單；不可視作全屆分佈', renderer.destination_summary(d))
        output = renderer.destination_record(0, d)
        visible_prefix = output.split('<details class="evidence-panel">', 1)[0]
        self.assertIn('部分名單；不可視作全屆分佈', visible_prefix)
        d['coverage'] = '公開列項，未獨立證明全屆分母。'
        self.assertIn('名單完整性未核實', renderer.destination_summary(d))
        self.assertIn('名單完整性未核實', renderer.destination_record(0, d).split('<details class="evidence-panel">', 1)[0])

    def test_javascript_matching_destination_opens_all_ancestors(self):
        script = r'''
const assert = require('node:assert/strict');
const { openAncestors } = require(process.argv[1]);
const outer = { open:false, closest:()=>outer, parentElement:null };
const inner = { open:false, closest:()=>inner, parentElement:{closest:()=>outer} };
const row = {closest:()=>inner};
openAncestors(row); assert.equal(inner.open,true); assert.equal(outer.open,true);
openAncestors({closest:()=>null});
// Clearing a filter must not close an already opened user's fold.
openAncestors(row); assert.equal(inner.open,true);
console.log('PASS Node: matched receiver opens cohort and school folds without closing user choices');
'''
        result = subprocess.run(['node', '-e', script, str(ROOT / 'app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        javascript = (ROOT / 'app.js').read_text(encoding='utf-8')
        self.assertIn('if (hasFilter) openAncestors(row)', javascript)
        self.assertIn("['roster', 'classes', 'social'].includes(id)", javascript)
        self.assertIn('tr[data-destination]:not([data-observed="false"])', javascript)


if __name__ == '__main__':
    unittest.main(verbosity=2)
