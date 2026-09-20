'use strict';
// Pin the browser Python host. User SHIN is data passed only to compile_source.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
let python;
async function initialize() {
  importScripts(PYODIDE + 'pyodide.js');
  python = await loadPyodide({indexURL: PYODIDE});
  const response = await fetch('./runtime.json');
  if (!response.ok) throw new Error('Could not load the SHIN runtime.');
  const bundle = await response.json();
  python.FS.mkdirTree('/home/pyodide/shin');
  for (const [name, content] of Object.entries(bundle.files)) {
    if (!['__init__.py', 'compiler.py', 'runtime.py', 'markup.py'].includes(name)) throw new Error('Unknown runtime file');
    python.FS.writeFile('/home/pyodide/shin/' + name, content);
  }
  python.runPython(bundle.bridge);
  self.postMessage({type: 'ready'});
}
self.onmessage = event => {
  const {source, allowDemo, id} = event.data;
  if (!python || typeof source !== 'string' || source.length > 65536) return;
  try {
    python.globals.set('_request_json', JSON.stringify({source, allowDemo: allowDemo === true}));
    const result = python.runPython("_request = json.loads(_request_json)\njson.dumps(run_playground(_request['source'], _request['allowDemo']))");
    self.postMessage({type: 'result', id, result: JSON.parse(result)});
  } catch (error) {
    self.postMessage({type: 'failure', message: 'The browser runtime failed. Reload the runtime and try again.'});
  }
};
initialize().catch(() => self.postMessage({type: 'failure', message: 'Runtime download failed. Check your connection or CDN access, then try again.'}));
