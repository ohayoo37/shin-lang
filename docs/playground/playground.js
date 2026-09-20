'use strict';
const $ = id => document.getElementById(id);
let language = new URLSearchParams(location.search).get('lang') === 'ja' ? 'ja' : 'en';
let examples = [], loaded = null, worker = null, ready = false, busy = false, pending = null, timer = null, runId = 0, replaceArmed = false;
const say = (en, ja) => language === 'ja' ? ja : en;
function status(en, ja) { $('status').textContent = say(en, ja); }
function setBusy(value) {
  busy = value;
  for (const id of ['run', 'example', 'load']) $(id).disabled = value || !examples.length;
  $('stop').disabled = !value;
  $('grant').disabled = value;
  $('editor').readOnly = value;
}
function hint() {
  if (!loaded) return;
  $('hint').textContent = language === 'ja' ? loaded.hint_ja : loaded.hint;
  if (loaded.grant) $('hint').textContent += say(' To run this sample, check “Allow the demo model” below.', ' この例では下の「デモモデルを許可する」にチェックを入れてください。');
}
function translate() {
  document.documentElement.lang = language;
  for (const element of document.querySelectorAll('[data-en]')) element.textContent = element.dataset[language];
  $('language').textContent = language === 'en' ? '日本語' : 'English';
  for (const option of $('example').options) {
    const sample = examples.find(x => x.id === option.value);
    option.textContent = language === 'ja' ? sample.ja : sample.name;
  }
  hint();
}
function loadExample(force = false) {
  if (loaded && $('editor').value !== loaded.source && !force && !replaceArmed) {
    replaceArmed = true;
    $('notice').textContent = say('Your code has edits. Download it to keep a copy, or press Load example again to replace it.', '編集中のコードがあります。必要なら保存してください。もう一度「サンプルを読み込む」を押すと置き換えます。');
    return;
  }
  replaceArmed = false;
  loaded = examples.find(x => x.id === $('example').value) || examples[0];
  $('editor').value = loaded.source;
  // Samples never grant a capability silently; only the user changes this checkbox.
  $('grant').checked = false;
  hint();
  $('output').textContent = $('error').textContent = $('metrics').textContent = $('notice').textContent = '';
  history.replaceState(null, '', '?lang=' + language + '#' + loaded.id);
  status('Ready. Press Run SHIN.', '準備完了。「SHINを実行」を押してください。');
}
function resetWorker() {
  clearTimeout(timer); timer = null;
  if (worker) worker.terminate();
  worker = null; ready = false; pending = null;
  setBusy(false);
}
function failed(en, ja) {
  resetWorker();
  status('Stopped.', '停止しました。');
  $('error').textContent = say(en, ja);
}
function execute() {
  status('Running…', '実行中…');
  timer = setTimeout(() => failed('Execution stopped after 5 seconds. You can run again.', '5秒で実行を停止しました。再実行できます。'), 5000);
  worker.postMessage(pending); pending = null;
}
function run() {
  if (busy || !examples.length) return;
  $('error').textContent = $('output').textContent = $('metrics').textContent = '';
  if (new TextEncoder().encode($('editor').value).length > 65536) {
    $('error').textContent = say('Source must be at most 64 KiB.', 'コードは64 KiB以下にしてください。'); return;
  }
  setBusy(true);
  pending = {id: ++runId, source: $('editor').value, allowDemo: $('grant').checked};
  if (ready) { execute(); return; }
  status('Loading browser runtime… First download may take a moment.', 'ブラウザ実行環境を読み込み中…初回は少し時間がかかります。');
  try {
    const instance = new Worker('./worker.js'); worker = instance;
    timer = setTimeout(() => failed('Runtime loading timed out. Check your connection and try again.', '読み込みがタイムアウトしました。接続を確認して再実行してください。'), 60000);
    instance.onmessage = event => {
      if (worker !== instance) return;
      const data = event.data;
      if (data.type === 'ready') { clearTimeout(timer); ready = true; execute(); }
      else if (data.type === 'result' && data.id === runId) {
        clearTimeout(timer);setBusy(false);
        $('output').textContent = data.result.output;
        $('error').textContent = data.result.error || '';
        $('metrics').textContent = say('VM instructions: ', '実行命令数：') + data.result.steps;
        if (data.result.ok) status('Finished.', '実行が完了しました。');
        else status('Rejected by SHIN. Read the diagnostic below.', 'SHINが拒否しました。下の診断を確認してください。');
      } else if (data.type === 'failure') failed(data.message, '実行環境を読み込めませんでした。ネットワーク接続やCDNへのアクセスを確認して、再実行してください。');
    };
    instance.onerror = () => failed('Browser runtime unavailable. Try again or use the local installation guide.', '実行環境が利用できません。再実行するか、ローカル環境でお試しください。');
  } catch { failed('This browser cannot start the worker. Try a recent browser or run SHIN locally.', '実行スレッドを開始できません。新しいブラウザかローカル環境をご利用ください。'); }
}
$('editor').addEventListener('input', () => {replaceArmed = false;});
$('example').addEventListener('change', () => {replaceArmed = false;});
$('run').addEventListener('click', run);
$('stop').addEventListener('click', () => {resetWorker();status('Stopped. Run again to restart the runtime.', '停止しました。再実行すると実行環境を読み込み直します。');});
$('load').addEventListener('click', () => loadExample());
$('editor').addEventListener('keydown', event => {if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {event.preventDefault();run();}});
$('language').addEventListener('click', () => {language = language === 'en' ? 'ja' : 'en';translate();history.replaceState(null, '', '?lang=' + language + location.hash);});
$('download').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([$('editor').value], {type: 'text/plain;charset=utf-8'}));
  const anchor = document.createElement('a'); anchor.href = url;anchor.download = 'playground.shin';anchor.click();setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$('share').addEventListener('click', async () => {
  if (!loaded) return;
  const url = new URL(location.href);url.search = '?lang=' + language;url.hash = loaded.id;
  try {await navigator.clipboard.writeText(url.href);$('notice').textContent = say('Example link copied. Your edited code is not included.', 'サンプルのリンクをコピーしました。編集したコードは含まれません。');}
  catch {$('notice').textContent = say('Copy this example link: ', 'このサンプルのリンクをコピーしてください：') + url.href;}
});
translate();
fetch('./examples.json').then(r => {if (!r.ok) throw new Error();return r.json();}).then(data => {
  examples = data;
  for (const sample of examples) {const option = document.createElement('option');option.value = sample.id;option.textContent = sample.name;$('example').append(option);}
  const id = location.hash.slice(1);
  if (examples.some(x => x.id === id)) $('example').value = id;
  translate();loadExample(true);setBusy(false);
}).catch(() => {status('Could not load examples. Reload the page or use the installation guide.', 'サンプルを読み込めません。ページを再読み込みするか導入ガイドをご利用ください。');});
