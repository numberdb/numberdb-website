"""What a run cost, in money rather than in tokens.

    python3 agents/ledger.py LOG STARTED STAGE ENGINE PROMPT SESSION RESUMED MODEL

Prints one tab-separated row for `agents/runs/COSTS.tsv`.

Tokens are not comparable across engines and barely across models: a cached
input token on Fable 5.1 costs a fortieth of a fresh one, the two harnesses
cache differently, and one of them counts a whole `exec` as a turn where the
other counts a message. Money is the only figure that means the same thing on
both sides, so every row carries it, at list API prices, whoever ran it.

Where the harness reports its own cost that is what is used: Claude Code
reports `costUSD` per model at `costBasis: "list"`, which is the same quantity
this would compute -- verified, to the cent, on the T160 build. Codex reports
tokens and no price, so its rows are priced from `agents/model-rates.tsv`.
A model with no row there leaves the cost empty and says so rather than being
priced at a guess.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RATES = os.path.join(HERE, 'model-rates.tsv')

COLUMNS = ('started', 'stage', 'engine', 'turns', 'cost_usd', 'result', 'log',
           'model', 'prompt', 'session', 'resumed', 'tokens_in',
           'tokens_cached', 'tokens_out', 'cost_by_model')


def load_rates(path=RATES):
	"""model name -> {input, cache_read, cache_write_5m, cache_write_1h, output}."""
	rates = {}
	try:
		with open(path, encoding='utf8') as handle:
			for line in handle:
				if line.startswith('#') or not line.strip():
					continue
				fields = line.rstrip('\n').split('\t')
				if len(fields) < 6 or fields[0] == 'model':
					continue
				try:
					rates[fields[0]] = {
						'input': float(fields[1]),
						'cache_read': float(fields[2]),
						'cache_write_5m': float(fields[3]),
						'cache_write_1h': float(fields[4]),
						'output': float(fields[5]),
					}
				except ValueError:
					continue
	except OSError:
		pass
	return rates


def rate_for(model, rates=None):
	"""The longest row whose name begins `model`, or None.

	Longest first, so `claude-haiku-4-5-20251001` finds `claude-haiku-4-5` and
	`gpt-5.5-pro` is not answered by `gpt-5`.
	"""
	rates = load_rates() if rates is None else rates
	best = None
	for name in rates:
		if model.startswith(name) and (best is None or len(name) > len(best)):
			best = name
	return rates[best] if best else None


def price(model, input_tokens=0, cache_read=0, cache_write_5m=0,
          cache_write_1h=0, output_tokens=0, rates=None):
	"""USD at list price, or None when the model has no rate.

	`input_tokens` is the uncached input: the cached part is priced by
	`cache_read`, and passing the total would charge for it twice.
	"""
	rate = rate_for(model, rates)
	if rate is None:
		return None
	return (input_tokens * rate['input']
	        + cache_read * rate['cache_read']
	        + cache_write_5m * rate['cache_write_5m']
	        + cache_write_1h * rate['cache_write_1h']
	        + output_tokens * rate['output']) / 1e6


def _last_result(path):
	last = None
	try:
		for line in open(path, errors='replace'):
			line = line.strip()
			if not line.startswith('{'):
				continue
			try:
				record = json.loads(line)
			except Exception:
				continue
			if record.get('type') == 'result':
				last = record
	except OSError:
		pass
	return last


def claude_run(path):
	"""(turns, cost, outcome, model, tokens, per-model costs) for a claude log."""
	last = _last_result(path)
	if last is None:
		return None
	usage = last.get('usage') or {}
	by_model = {}
	for name, spent in (last.get('modelUsage') or {}).items():
		#Its own figure, at list basis, which is the quantity wanted. The rate
		#table reproduces it and exists for the engine that reports none.
		cost = spent.get('costUSD')
		if cost is None:
			cost = price(name,
			             input_tokens=spent.get('inputTokens', 0),
			             cache_read=spent.get('cacheReadInputTokens', 0),
			             cache_write_1h=spent.get('cacheCreationInputTokens', 0),
			             output_tokens=spent.get('outputTokens', 0))
		by_model[name] = cost or 0.0
	total = sum(by_model.values()) if by_model else last.get('total_cost_usd')
	outcome = last.get('subtype', '')
	if last.get('is_error'):
		#`subtype` says "success" even when the run ended on an API error: the
		#401 that stopped the campaign on 2026-09-03 was recorded as a success
		#by every field except this one.
		outcome = 'error %s' % (last.get('api_error_status')
		                        or last.get('subtype') or '',)
	main = max(by_model, key=by_model.get) if by_model else ''
	return {
		'turns': last.get('num_turns', ''),
		'cost': total,
		'outcome': outcome.strip(),
		'model': main,
		'tokens_in': usage.get('input_tokens', 0),
		'tokens_cached': usage.get('cache_read_input_tokens', 0),
		'tokens_out': usage.get('output_tokens', 0),
		'by_model': by_model,
	}


def codex_run(path, model):
	"""The same, from codex's event stream, priced from the rate table.

	`input_tokens` there includes the cached part, as it does in the OpenAI
	API, so the uncached input is the difference. `reasoning_output_tokens`
	is likewise a part of `output_tokens` and is not added again.
	"""
	turns = thread = 0, ''
	turns, thread, failed = 0, '', False
	totals = {'input': 0, 'cached': 0, 'output': 0}
	seen = False
	try:
		for line in open(path, errors='replace'):
			line = line.strip()
			if not line.startswith('{'):
				continue
			try:
				record = json.loads(line)
			except Exception:
				continue
			seen = True
			kind = record.get('type', '')
			if kind == 'thread.started' and not thread:
				thread = record.get('thread_id', '') or ''
			elif kind == 'turn.completed':
				turns += 1
				usage = record.get('usage') or {}
				totals['input'] += usage.get('input_tokens', 0)
				totals['cached'] += usage.get('cached_input_tokens', 0)
				totals['output'] += usage.get('output_tokens', 0)
			elif kind in ('turn.failed', 'error'):
				failed = True
	except OSError:
		return None
	if not seen:
		return None
	uncached = max(totals['input'] - totals['cached'], 0)
	cost = price(model, input_tokens=uncached, cache_read=totals['cached'],
	             output_tokens=totals['output'])
	return {
		'turns': turns,
		'cost': cost,
		'outcome': ('error' if failed else
		            ('success' if turns else 'no turn recorded')),
		'model': model,
		'tokens_in': totals['input'],
		'tokens_cached': totals['cached'],
		'tokens_out': totals['output'],
		'by_model': {model: cost} if cost is not None else {},
		'thread': thread,
	}


def row(log, started, stage, engine, prompt, session, resumed, model):
	found = codex_run(log, model) if engine == 'codex' else claude_run(log)
	if found is None:
		return '\t'.join([started, stage, engine, '', '', 'no result record',
		                  os.path.basename(log), '', prompt, session, resumed,
		                  '', '', '', ''])
	cost = found['cost']
	outcome = found['outcome']
	if cost is None:
		#Said out loud rather than left blank: a missing rate is a thing to
		#fix in agents/model-rates.tsv, not a run that cost nothing.
		outcome = '%s (no rate for %s)' % (outcome, found['model'])
	breakdown = ';'.join('%s=%.4f' % (name, value)
	                     for name, value in sorted(found['by_model'].items(),
	                                               key=lambda pair: -pair[1]))
	return '\t'.join([
		started, stage, engine, str(found['turns']),
		'' if cost is None else '%.4f' % cost,
		outcome, os.path.basename(log), found['model'], prompt,
		session or found.get('thread', ''), resumed,
		str(found['tokens_in']), str(found['tokens_cached']),
		str(found['tokens_out']), breakdown,
	])


if __name__ == '__main__':
	if sys.argv[1:2] == ['--header']:
		print('\t'.join(COLUMNS))
	else:
		print(row(*sys.argv[1:9]))
