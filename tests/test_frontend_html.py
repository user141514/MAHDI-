from __future__ import annotations

import unittest
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_FILE = next(ROOT.glob("MAHDI*.html"))


def run_browser_script(body: str) -> None:
    """Run the real page script with an in-memory DOM and API boundary."""
    harness = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const html = fs.readFileSync(process.argv[1], 'utf8');
const bank = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const elements = new Map(), memory = new Map();
function element(id) {
  if (!elements.has(id)) {
    const classes = new Set(id === 's-welcome' ? ['on'] : []);
    elements.set(id, {id, innerHTML:'', textContent:'', value:'', style:{}, disabled:false,
      classList:{add(...x){x.forEach(v=>classes.add(v));},remove(...x){x.forEach(v=>classes.delete(v));},contains(x){return classes.has(x);},toggle(x,on){if(on)classes.add(x);else classes.delete(x);}},
      appendChild(){},click(){},remove(){},setAttribute(){}});
  }
  return elements.get(id);
}
const screens=['s-welcome','s-version','s-auth','s-instructor','s-question','s-calc','s-result'];
screens.forEach(element);
const context = vm.createContext({assert, bank, elements, memory, requests:[], console,
  document:{getElementById:element,querySelectorAll(selector){return selector==='.screen'?screens.map(element):[];},createElement(){return element('created-'+Math.random());},body:{appendChild(){}}},
  localStorage:{getItem(k){return memory.get(k)||null;},setItem(k,v){memory.set(k,v);},removeItem(k){memory.delete(k);}},
  location:{protocol:'http:'},alert(){},confirm(){return true;},
  btoa(s){return Buffer.from(s,'binary').toString('base64');},
  setTimeout,clearTimeout,AbortController,Blob,
  URL:{createObjectURL(){return 'blob:test';},revokeObjectURL(){}},
  fetch:async()=>{throw Error('Unexpected network request');}
});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
vm.runInContext(`currentUser=()=>({id:'student-1',email:'student@test',role:'student'}); currentToken=()=> 'test-token';`,context);
vm.runInContext(`function response(data,status=200){return {ok:status>=200&&status<300,status,json:async()=>data};}
function configData(){return {types:bank.types,questions:bank.questions.map(({sc,correct,...q})=>q),lite_question_count:12,full_question_count:44,algorithm_version:'standard_v2',question_bank_version:bank.bank_version};}
function savedResult(extra={}){return Object.assign({id:'saved-1',userId:'student-1',version:'lite',agent_type:'mahid',algorithm_version:'standard_v2',generated_at:'2026-10-26T12:00:00Z',createdAt:'2026-10-26T12:00:00Z',mainType:null,secondType:null,leadingType:'M',mainTypeName:'复合型 / 待观察',is_mixed:true,conclusion:'复合型 / 待观察',conclusion_reason:'两类接近',tendency_strength:'倾向不明显',final:{M:60,A:59,H:40,D:30,I:25},pcts:{M:60,A:59,H:40,D:30,I:25},sorted:[['M',60],['A',59],['H',40],['D',30],['I',25]],dimNorm:{E:{M:60},K:{M:60},I:{M:60},L:{M:60},P:{M:60}},level:2,levelName:'AI基础应用',kRate:50,stylePct:{social:25,practice:25,structure:25,research:25},topStyle:'social',topStyleName:'社交型',warns:[],lite_features:['特征一','特征二','特征三'],core_features:['一','二','三','四','五'],development_advice:'建议一',score_kind:'standardized_score',answers:{E1:2}},extra);}`,context);
(async()=>{await vm.runInContext('(async()=>{'+process.argv[3]+'})()',context);})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(
        ["node", "-e", harness, str(HTML_FILE), str(ROOT / "backend" / "assessment_bank.json"), body],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


class FrontendHtmlTests(unittest.TestCase):
    def test_defines_esc_html_before_instructor_dashboard_uses_it(self) -> None:
        source = HTML_FILE.read_text(encoding="utf-8")

        define_pos = source.find("function escHtml")
        render_pos = source.find("function renderInstructorDashboard")

        self.assertNotEqual(-1, define_pos)
        self.assertNotEqual(-1, render_pos)
        self.assertLess(define_pos, render_pos)

    def test_instructor_login_does_not_display_default_password(self) -> None:
        source = HTML_FILE.read_text(encoding="utf-8")

        self.assertNotIn("teacher / meitai123456", source)
        self.assertNotIn("默认密码：", source)

    def test_result_page_has_pdf_export_button_and_handler(self) -> None:
        source = HTML_FILE.read_text(encoding="utf-8")

        self.assertIn('id="pdfBtn"', source)
        self.assertIn("function exportLatestPdf", source)
        self.assertIn("/api/results/latest/pdf", source)

    def test_network_failure_preserves_answers_and_retry_does_not_fake_save(self) -> None:
        run_browser_script(r"""
fetch=async(url,options={})=>{
  requests.push({url,body:options.body?JSON.parse(options.body):null});
  if(url==='/api/assessment/config')return response(configData());
  if(url==='/api/assessment/selections')return response({selection:{id:'selection-1',version:'lite',question_ids:['E1','E2'],inherited_answers:{},config:{}},questions:bank.questions.slice(0,2),types:bank.types});
  throw Error('Connection lost');
};
await chooseVersion('lite'); answers={E1:2,E2:1};
await compute();
assert.equal(elements.get('s-result').classList.contains('on'),false);
assert.equal(readResults().length,0);
assert.equal(answers.E1,2);
fetch=async(url,options)=>{requests.push({url,body:JSON.parse(options.body)});return response({result:savedResult()});};
await compute(); await compute();
assert.equal(readResults().length,1);
assert.equal(readResults()[0].id,'saved-1');
assert.equal(elements.get('s-result').classList.contains('on'),true);
const sends=requests.filter(r=>r.url==='/api/assessment/evaluate');
assert.equal(sends[0].body.selection_id,'selection-1');
assert.equal(JSON.stringify(sends[0].body.answers),JSON.stringify(sends[1].body.answers));
""")

    def test_selection_retry_reuses_request_and_upgrade_skips_inherited_questions(self) -> None:
        run_browser_script(r"""
let fail=true;
fetch=async(url,options={})=>{
  if(url==='/api/assessment/config')return response(configData());
  const body=JSON.parse(options.body);requests.push(body);
  if(fail){fail=false;throw Error('Connection lost');}
  return response({selection:{id:'upgrade-1',version:'full',question_ids:['E1','E2'],inherited_answers:{E1:2},source_result_id:'lite-1',config:{}},questions:[bank.questions[1]],types:bank.types});
};
await chooseVersion('full','lite-1'); await retrySelection();
assert.equal(requests[0].client_request_id,requests[1].client_request_id);
assert.equal(requests[1].source_result_id,'lite-1');
assert.equal(activeQuestions.length,1);
assert.equal(activeQuestions[0].key,'E2');
assert.equal(answers.E1,2);
selectOpt(1);assert.equal(answers.E2,1);
""")

    def test_lite_has_four_sections_and_does_not_label_mixed_result_as_primary(self) -> None:
        run_browser_script(r"""
TYPE_INFO=bank.types;
showResult(savedResult());
const page=elements.get('s-result').innerHTML;
assert.equal((page.match(/data-report-block=/g)||[]).length,4);
assert.ok(page.includes('复合型 / 待观察'));
assert.ok(page.includes('继续深度测评'));
assert.ok(page.includes('60分'));
assert.ok(!page.includes('>60%</'));
assert.ok(!page.includes('你最适合的类型：M'));
assert.ok(!page.includes('当前AI知识水位'));
""")

    def test_recent_report_uses_server_result_without_resubmission(self) -> None:
        run_browser_script(r"""
fetch=async(url,options={})=>{requests.push({url,method:options.method||'GET'});return response(url==='/api/assessment/config'?configData():{result:savedResult({version:'full'})});};
await showLatestStoredResult();
assert.equal(requests.filter(r=>r.method!=='GET').length,0);
assert.ok(requests.some(r=>r.url==='/api/results/latest'));
assert.ok(elements.get('s-result').innerHTML.includes('当前AI知识水位'));
""")

    def test_full_radar_title_and_values_use_saved_main_type(self) -> None:
        run_browser_script(r"""
TYPE_INFO=bank.types;
const result=savedResult({version:'full',mainType:'A',mainTypeName:bank.types.A.name,leadingType:'M',is_mixed:false,
  dimNorm:{E:{A:11,M:91},K:{A:22,M:92},I:{A:33,M:93},L:{A:44,M:94},P:{A:55,M:95}}});
const original=JSON.stringify(result);
showResult(result);
const page=elements.get('s-result').innerHTML;
assert.ok(page.includes('AI赋能者五维倾向得分'));
for(const value of [11,22,33,44,55])assert.ok(page.includes('>'+value+'%</text>'));
assert.ok(!page.includes('>91%</text>'));
assert.equal(JSON.stringify(result),original);
""")

    def test_mixed_radar_keeps_reference_title_and_does_not_claim_a_main_type(self) -> None:
        run_browser_script(r"""
TYPE_INFO=bank.types;
showResult(savedResult({version:'full',mainType:'A',mainTypeName:bank.types.A.name,is_mixed:true,
  dimNorm:{E:{A:11,M:91},K:{A:22,M:92},I:{A:33,M:93},L:{A:44,M:94},P:{A:55,M:95}}}));
const page=elements.get('s-result').innerHTML;
assert.ok(page.includes('五维倾向参考得分（复合型 / 待观察）'));
assert.ok(!page.includes('AI赋能者五维倾向得分'));
assert.ok(page.includes('>91%</text>'));
""")

    def test_instructor_reads_server_statistics_and_handles_mixed_result(self) -> None:
        run_browser_script(r"""
currentUser=()=>({id:'teacher-1',role:'instructor'});
fetch=async(url)=>{
  if(url==='/api/assessment/config')return response(configData());
  if(url==='/api/instructor/version-stats')return response({total_selections:4,versions:{lite:{selections:3,completed:2,share:.75},full:{selections:1,completed:1,share:.25}}});
  return response({results:[savedResult()],users:[{id:'student-1'}]});
};
await renderInstructorDashboard();
const page=elements.get('instructorDashboard').innerHTML;
assert.ok(page.includes('75%'));
assert.ok(page.includes('复合型 / 待观察'));
assert.ok(page.includes('standard_v2'));
assert.equal(dashboardRecords[0].id,'saved-1');
""")

    def test_csv_exports_versions_real_generation_time_and_correct_score_unit(self) -> None:
        run_browser_script(r"""
const csv=buildInstructorCsv([savedResult({userName:'=1+1'}),savedResult({id:'old',version:undefined,algorithm_version:undefined,score_kind:undefined,pcts:{M:20},generated_at:undefined})]);
assert.ok(csv.includes('standard_v2'));
assert.ok(csv.includes('legacy_v1'));
assert.ok(csv.includes('精简版'));
assert.ok(csv.includes('完整版'));
assert.ok(csv.includes('60分'));
assert.ok(csv.includes('20%'));
assert.ok(csv.includes("'=1+1"));
assert.ok(csv.includes('2026-10-26'));
""")

    def test_late_evaluation_cannot_reopen_report_after_logout(self) -> None:
        run_browser_script(r"""
TYPE_INFO=bank.types;activeSelection={id:'selection-1',version:'lite'};answers={E1:2};
let finish;
fetch=()=>new Promise(resolve=>finish=resolve);
const evaluating=compute();
logout();finish(response({result:savedResult()}));await evaluating;
assert.equal(elements.get('s-welcome').classList.contains('on'),true);
assert.equal(elements.get('s-result').classList.contains('on'),false);
assert.equal(readResults().length,0);
""")

    def test_historical_report_preserves_legacy_units_and_labels_timestamp_source(self) -> None:
        run_browser_script(r"""
TYPE_INFO=bank.types;
const old=savedResult({mainType:'D',mainTypeName:bank.types.D.name,is_mixed:false,pcts:{M:19,A:21,H:17,D:23,I:20},answers:{0:1}});
for(const key of ['version','algorithm_version','score_kind','generated_at','core_features','conclusion','conclusion_reason'])delete old[key];
showResult(old);
const page=elements.get('s-result').innerHTML;
assert.ok(page.includes('完整版'));
assert.ok(page.includes('legacy_v1'));
assert.ok(page.includes('23%'));
assert.ok(page.includes('历史提交时间'));
assert.ok(page.includes('当前AI知识水位'));
assert.equal(readResults().length,0);
""")

    def test_pdf_request_names_the_result_currently_on_screen(self) -> None:
        run_browser_script(r"""
currentResult=savedResult({id:'saved-specific'});
fetch=async(url)=>{requests.push(url);return {ok:true,blob:async()=>new Blob(['pdf'])};};
await exportLatestPdf();
assert.equal(requests[0],'/api/results/latest/pdf?result_id=saved-specific');
""")

    def test_response_for_previous_account_is_not_rendered_after_cross_tab_login(self) -> None:
        run_browser_script(r"""
TYPE_INFO=bank.types;activeSelection={id:'selection-1',version:'lite'};answers={E1:2};
let finish;fetch=()=>new Promise(resolve=>finish=resolve);
const evaluating=compute();
currentUser=()=>({id:'student-2',role:'student'});
finish(response({result:savedResult()}));await evaluating;
assert.equal(elements.get('s-result').classList.contains('on'),false);
assert.equal(readResults().length,0);
""")

    def test_instructor_dashboard_drops_late_response_after_cross_tab_account_change(self) -> None:
        run_browser_script(r"""
TYPE_INFO=bank.types;assessmentConfig=configData();
currentUser=()=>({id:'teacher-1',role:'instructor'});
let finish;loadDashboardData=()=>new Promise(resolve=>finish=resolve);
const rendering=renderInstructorDashboard();
currentUser=()=>({id:'student-2',role:'student'});
finish({results:[savedResult({userName:'Private Student Record'})],users:[],stats:{total_selections:0,versions:{lite:{share:0},full:{share:0}}}});
await rendering;
assert.ok(!elements.get('instructorDashboard').innerHTML.includes('Private Student Record'));
assert.equal(dashboardRecords.length,0);
""")

    def test_pending_teacher_csv_does_not_download_after_logout(self) -> None:
        run_browser_script(r"""
currentUser=()=>({id:'teacher-1',role:'instructor'});
let finish,downloads=0;
loadDashboardData=()=>new Promise(resolve=>finish=resolve);
document.createElement=()=>({click(){downloads++;}});
const exporting=exportInstructorCsv();
logout();currentUser=()=>({id:'student-2',role:'student'});
finish({results:[savedResult({userName:'Private Student Record'})]});await exporting;
assert.equal(downloads,0);
""")

    def test_pending_teacher_clear_does_not_erase_another_accounts_local_projection(self) -> None:
        run_browser_script(r"""
currentUser=()=>({id:'teacher-1',role:'instructor'});
let finish;apiJson=()=>new Promise(resolve=>finish=resolve);
const clearing=clearAssessmentResults();
logout();currentUser=()=>({id:'student-2',role:'student'});
writeResults([savedResult({id:'new-account-result',userId:'student-2'})]);
finish({ok:true});await clearing;
assert.equal(readResults()[0].id,'new-account-result');
""")


if __name__ == "__main__":
    unittest.main()
