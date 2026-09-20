# SHIN international launch kit — drafts, not posted

## English X post

What if an AI call had to declare its permissions—and its output had to be checked before use?

I'm building SHIN, an experimental open-source language for exploring that idea.

Try it in your browser. No install or API key:
https://ohayoo37.github.io/shin-lang/playground/

## Longer introduction

SHIN is a small experimental language with its own compiler and stack VM. It makes model permissions and validation of model output explicit. It also includes starters for websites, browser apps, JSON APIs and a small SQLite CMS.

The browser playground runs the actual Python reference implementation through Pyodide. Try a valid program, remove its host permission, or print an unchecked value to see where it stops. The demo model is an echo provider, not a real LLM.

SHIN is early: there is no native compiler or OS sandbox, and the current VM is slower than Python on the included loop benchmark. Source, limitations and reproducible tests are public under MIT.

We would like feedback from people building AI-enabled applications and people interested in language design. What is clear? What feels unnecessary? What would you try building?

Playground: https://ohayoo37.github.io/shin-lang/playground/
Source: https://github.com/ohayoo37/shin-lang
Discussion: https://github.com/ohayoo37/shin-lang/discussions

## 60-second screen recording script (not yet recorded)

- 0–8 s: Open Hello, change “world” to your name and run. “This is SHIN, a small experimental language you can try in your browser.”
- 8–23 s: Load Permission + validation. Run without the grant. Show rejection. Tick the explicit grant and run successfully. “The source declares access. The host has to allow it too.”
- 23–40 s: Load Unchecked output, grant the demo and run. Show rejection. Replace `print(draft)` with `print(check_text(draft, 100))` and rerun. “Model output must pass an explicit check before use. This demo uses an echo, not a real AI.”
- 40–50 s: Load the budget example and run. “Execution has a budget. This endless loop stops.”
- 50–60 s: Show GitHub and contribution guide. “It's MIT licensed and early. Try it, question it, or help improve it.”

## Initial feedback targets (goals, not measured results)

Aim for 10 independent users who complete a first run and 3 who build or modify a small example. Ask where they got stuck and what they tried to do. Track voluntary public feedback; do not add tracking of submitted source. Do not present stars or downloads as active usage.
