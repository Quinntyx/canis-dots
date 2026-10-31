"""route_scheduler.py — CP-SAT weekly scheduler.

Consolidated 2026-10-06 from the scheduler.ipynb debug session (cells 7, 14, 17,
59, 110). The ipynb stays as provenance; this file is the product. Run:

    python3 route_scheduler.py [--json out.json]
"""
import argparse, json, math, os, re, subprocess, sys, datetime, random, tomllib
from datetime import time
os.environ['TZ'] = 'America/Chicago'
from ortools.sat.python import cp_model

# User-editable preferences (weights, budgets, hard floors) — see prefs.toml / PREFS.md
_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, 'prefs.toml'), 'rb') as _pf:
    PREFS = tomllib.load(_pf)


# ---- data loading (omn + taskwarrior exports) ----
NOW = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5)))
HOME = "At home"
print("now:", NOW.isoformat())
omn = json.loads(subprocess.check_output(['omn', 'export']))
tasks = json.loads(subprocess.check_output(['task', 'rc.json.array=on', 'export']))
os.makedirs('/tmp/route-week', exist_ok=True)
json.dump(omn, open('/tmp/route-week/omn.json', 'w'))
json.dump(tasks, open('/tmp/route-week/tasks.json', 'w'))
print("omn records:", len(omn), "| tasks:", len(tasks))
rr = [r for r in omn if r.get('meta', {}).get('rrule')]


# %% Cell 3 — WEEK DATA: fixed events, work items, support policies. All semantics live here (data, not code).
# Plan horizon: Mon 2026-10-12 .. Sun 2026-10-18 (user 2026-10-12: MATH 3351 exam Tue in the normal
# lecture slot; >=6h exam study Monday; lab presence EVERY weekday this week — trial, one-week only).
WD0 = 12   # Oct 12 2026 is Monday the 12th
T = lambda d, hm: datetime.datetime.combine(datetime.date(2026,10,WD0+d), datetime.time(*hm), NOW.tzinfo)
EOD = lambda d: T(d+1,(0,0)) - datetime.timedelta(minutes=1)   # 23:59 that day

def _tt(x):
    if isinstance(x, datetime.time): return x
    if isinstance(x, str):
        s2 = x.replace('Z', '+00:00')
        try:
            dt = datetime.datetime.fromisoformat(s2)
            dt = dt.astimezone(NOW.tzinfo) if dt.tzinfo else dt
            return datetime.time(dt.hour, dt.minute)
        except ValueError:
            h, mi = x.split(':')[:2]; return datetime.time(int(h), int(mi))
    return x

def expand_rrule(rec):
    """Expand this week's occurrences of a weekly rrule record -> (start, end, location)."""
    m = rec['meta']
    import re
    days = {'MO':0,'TU':1,'WE':2,'TH':3,'FR':4,'SA':5,'SU':6}
    bydays = re.search(r'BYDAY=([A-Z,]+)', m['rrule']).group(1).split(',')
    cancelled = set(m.get('cancelled') or [])
    out = []
    for wd in bydays:
        d = WD0 + days[wd]          # day-of-month for this week (base Mon the 12th)
        if datetime.date(2026,10,d).isoformat() in cancelled:
            continue  # this occurrence was explicitly cancelled
        s = T(d - WD0, (_tt(m['start']).hour, _tt(m['start']).minute))   # T() takes a week OFFSET
        e = T(d - WD0, (_tt(m['end']).hour, _tt(m['end']).minute)) if 'end' in m else s + datetime.timedelta(hours=1)
        out.append((s, e, m.get('location', HOME)))
    return out

FIXED, WORK, SUPPORT = [], [], []

# --- fixed events (classes, meetings, exam, package pickup) ---
for rec in rr:
    ttl, tags = rec['title'], rec.get('tags',[])
    if ttl == 'Swimming' or 'errand' in tags:
        continue  # swimming: dated node below; errands: flexible items
    if ttl == 'Prof. Jee lab hours':
        continue  # lab requirement = WORK pieces (this week's daily trial), not a fixed node
    if rec.get('meta', {}).get('active') is False:
        continue  # inactive rrule records are not live events (e.g. cs-2336-701 lab stub)
    if ttl.startswith('CS 3345 Quiz'):
        continue  # Quiz 4 sits at the start of Thursday's lecture block (merged node below)
    if rec.get('type') == 'event' or (any(t in tags for t in ('class','lab','recurring')) and not ttl.startswith('ECS 2390 chapter')):
        for s,e,loc in expand_rrule(rec):
            t = ttl.replace('.010','').replace('.HON lecture','').replace('.501 lecture','').replace(' lecture','')
            if 'class' in tags or ttl.endswith('lecture') or ttl == 'Piano lesson':
                t = 'Attend ' + t
            if ttl.startswith('CS 3345') and s.weekday() == 3:
                t = 'Attend CS 3345 (Quiz 4 at start) + lecture'
            FIXED.append(dict(title=t, start=s, end=e, loc=loc))
# MATH 3351 midterm in the normal Tue lecture slot (Tue lecture occurrence cancelled in omn)
FIXED.append(dict(title="Attend MATH 3351 midterm exam", start=T(1,(17,30)), end=T(1,(18,50)), loc="FN 2.214"))
# Package pickup (policy 2026-10-12): inside the 7-day/3-day window, anchored to
# a walk home from class. CCH North Luxer One lockers are 24/7, so it is a
# flexible Tue-Thu piece at HOME (not a fixed node — a fixed 19:05 stop would
# leave Tuesday's arcs infeasible after the 18:50 exam, which cascades to the
# whole week). Dinner Tue sits 19:20-20:05 within its window.
# Swimming: normal standing slot this week (Wed 16:00-19:00, no current-week override)
FIXED.append(dict(title="Attend Swimming", start=T(2,(16,0)), end=T(2,(19,0)), loc="UTD Activity Center on campus"))

# --- work items (omn assignments; est from store; deadline = due date EOD) ---
def omn_task(rec, est_h, loc=HOME):
    due = parse_due(rec.get('meta', {}).get('due'))
    if due is None:
        raise ValueError(f"record without usable due: {rec['title']}")
    return dict(id=rec['id'][:80], title=rec['title'].split(' [')[0], est=est_h*60,
                loc=loc, deadline=due)

def parse_due(d):
    """Canvas dues arrive as dates ('2026-10-11') or ISO datetimes; date-only means EOD local."""
    if d is None:
        return None
    s2 = str(d).replace('Z', '+00:00')
    if len(s2) <= 10:
        s2 = s2 + 'T23:59:00'
    try:
        dt = datetime.datetime.fromisoformat(s2)
    except ValueError:
        return None
    return dt.astimezone(NOW.tzinfo) if dt.tzinfo else dt.replace(tzinfo=NOW.tzinfo)

def find_by_title(*needles):
    """Latest-due future record matching any needle (first match ties -> latest due)."""
    cands = []
    for r in omn:
        t = r.get('title', '')
        if any(n.lower() in t.lower() for n in needles):
            dd = parse_due(r.get('meta', {}).get('due'))
            if dd and dd > NOW:
                cands.append((dd, r))
    return max(cands)[1] if cands else None

def synthetic(id_, title, est_h, deadline_day, loc=HOME):
    return dict(id=id_, title=title, est=int(est_h*60), loc=loc, deadline=EOD(deadline_day))

# Assignment-budget clamp applies ONLY to Canvas assignments (TA#4, Ignite):
# everything else keeps its store estimate (exam study 6h, projects, errands).
_ASSIGN_PREFIX = ('Theory Assignment #4', 'Ignite Talk')

_OMN_WORK = [  # (title needles, est hours, synthetic fallback)
    (('Theory Assignment #4',), 2.0, None),          # CS 3345, due Fri
    (('Ignite Talk!',), 2.0, None),                  # ECS 2390 slides, due Oct 16
    (('Study for MATH 3351',), 6.0, None),           # exam prep, >=6h Monday (user)
    (('Review ECS2390',), 1.0, lambda: synthetic(    # record's old due keyed 10/11; replan this week
        'manual:task:review-ecs2390-cover-letter-rough-feedback',
        'Review ECS2390 rough-draft feedback', 1.0, 6)),
    (('Quiz #1 feedback',), 2.0, lambda: synthetic(
        'manual:utd:2026-fall:task:review-cs3345-quiz-1-feedback',
        'Review Quiz #1 feedback (CS 3345)', 2.0, 6)),
    (('ECS Chapter 8',), 1.0, lambda: synthetic(
        'manual:utd:2026-fall:task:ecs-2390-chapter-8',
        'ECS Chapter 8 reading + quiz', 1.0, 3)),    # before Friday class (late = 0)
    (('chapter quizzes',), 2.0, lambda: synthetic(
        'manual:utd:2026-fall:task:ecs-2390-chapter-quiz-makeup-1-4',
        'Make up ECS 2390 chapter quizzes 1-4', 2.0, 6)),
    (('Research MIT Lincoln',), 2.0, lambda: synthetic(
        'manual:task:research-mit-lincoln-lab',
        'Research MIT Lincoln Lab programs', 2.0, 6)),
    (('Apply to DTCC',), 2.0, lambda: synthetic(
        'manual:task:apply-dtcc-2027-programs',
        'Research + apply: DTCC 2027 internship/EDGE', 2.0, 6)),
    (('Follow up with Micron',), 0.5, None),
    (('Follow up with Tinker',), 0.5, None),
    (('Follow up with TetraPak',), 0.5, lambda: synthetic(
        'manual:contact:tetrapak',
        'Follow up with TetraPak', 0.5, 6)),
    (('orthodontist',), 1.0, None),                  # due 2027-01-01 — target this week
    (('Set up HomePod',), 4.0, lambda: synthetic(
        'manual:task:setup-smart-home',
        'Set up HomePod Mini and IKEA smart home', 4.0, 6)),
    (('Cancel mail forwarding',), 1.0, lambda: synthetic(
        'manual:task:cancel-mail-forwarding',
        'Cancel mail forwarding (post office, car)', 1.0, 4)),
]
WORK = []
for needles, est_h, synth in _OMN_WORK:
    r = find_by_title(*needles)
    if r is not None:
        t = omn_task(r, est_h)
    elif synth is not None:
        t = synth()
    else:
        print("!! no omn record for", needles); continue
    if t['deadline'] <= NOW:
        print("  (past-deadline, skipped:", t['title'], t['deadline'].isoformat(), ")")
        continue
    if t['deadline'] > EOD(6):
        print("  (next-week due, deferred to the Oct 19 week:", t['title'], t['deadline'].isoformat(), ")")
        continue   # plan work in its own week; pull-forward needs an explicit choice
    if 'Cancel mail forwarding' in t['title']:
        t['loc'] = 'Richardson post office (car)'; t['errand'] = True   # venue-hours rule: weekday run
    if t['title'].startswith(_ASSIGN_PREFIX):
        t['assignment'] = True   # exact-2h assignment budget (prefs.toml)
    WORK.append(t)

# exam study is Monday-only (user: at least 6h worth ON Monday; exam Tue 17:30)
for t in WORK:
    if t['title'].startswith('Study for MATH 3351'):
        t['days'] = [0]
        t['chunk_min'] = 60; t['chunk_max'] = 120
# Apply-to/DTCC/etc flexible detail tweaks are handled by CONTRACT/RANK below

# daily lab presence (TRIAL week 2026-10-12): 5 x 1h flexible pieces Mon-Fri;
# the Wed PyLingual meeting (11-12) counts toward the 6h requirement as usual.
for _d, _nm in enumerate(['Mon','Tue','Wed','Thu','Fri']):
    WORK.append(dict(id=f"manual:lab-hours-d{_d}", title=f"Lab time (Prof. Jee, {_nm})",
                     est=60, loc="ECSS 3.226 (Prof. Jee's lab)", deadline=EOD(4),
                     work_win=(time(10,0), time(17,0)), days=[_d],
                     chunk_min=60, chunk_max=90, no_frag=True))

# weekend errands: omn records tagged 'errand' + rrule BYDAY — flexible placement,
# constrained to Sat/Sun via days (hard contract: they must happen every weekend).
# Race for the Cure closures 10/15-17: grocery must stay clear of the 8:00-12:00
# road lockdown on Saturday; work_win 13:00+ keeps the route sane.
_GROCERY_WINDOW = (time(13,0), time(20,0))
for rec in rr:
    if 'errand' not in rec.get('tags', []):
        continue
    m = rec['meta']
    w = dict(id=rec['id'], title=rec['title'], est=int(m.get('est_minutes', 60)),
             loc=m.get('location', HOME), deadline=EOD(11), days=[5, 6], errand=True)
    if 'grocer' in w['title'].lower():
        WORK.append(dict(w, title=w['title'], work_win=_GROCERY_WINDOW))  # race window
        continue
    WORK.append(w)

# piano practice (R1-Q3a: HARD >= 4 sessions/week of 30-60m each). Sessions are
# afternoon / after-break by preference (agent-side PREF), never right after the lesson.
WORK.append(dict(id='manual:piano-practice', title='Practice piano', est=240, loc=HOME,
                 deadline=EOD(11), days=[0, 1, 2, 3, 4, 5, 6],
                 chunk_min=30, chunk_max=60, day_cap=60, no_frag=True))

# Package pickup piece: Tue-Thu only (delivered Oct 10; window Oct 10->24; policy:
# grab it on the way home from a class). 30 min at the HOME lobby lockers.
WORK.append(dict(id='manual:task:package-pickup-cch-north',
                 title='Pick up package (CCH North lobby)', est=30, loc=HOME,
                 deadline=EOD(3), days=[1, 2, 3, 4], errand=True,
                 chunk_min=30, chunk_max=30, no_frag=True))

# indivisible items (R3-Q3a): omn meta.chunks=1 -> one exact-length block.
for _w in WORK:
    if _w['title'].startswith('Quinncia'):
        _w['chunks'] = 1
# sub-hour items (0.5h contacts/errands) must be single <=30m pieces, not
# spec'd against the standing 1h minimum piece — otherwise sum(30m) vs
# pieces>=60m is unsatisfiable on sight.
for _w in WORK:
    if _w['est'] < 60:
        _w['chunk_min'] = _w['est']; _w['chunk_max'] = _w['est']; _w['no_frag'] = True

# --- PERMANENT RULES (user 2026-10-09; initially trialled 2026-10-07) ---
# Every assignment gets 120 minutes TOTAL, not per block. Normal chunking
# and independent indivisibility constraints remain. Day bounds below enforce
# the hard 22:00 daily stop; earlier academic deadlines still bind.
for _w in WORK:
    if _w.get('assignment'):
        _w['est'] = PREFS['hard']['assignment_minutes']

# CONTRACT / RANK derive from the items actually loaded
CONTRACT = {w['title']: (int(w['est']), int(w['est'])) for w in WORK}
RANK = {w['title']: 50 for w in WORK}
for t, r in (('Study for MATH 3351 midterm exam', 100), ('Theory Assignment #4', 90),
             ('Ignite Talk', 80), ('ECS Chapter 8 reading + quiz', 70),
             ('Make up ECS 2390 chapter quizzes 1-4', 40), ('Research MIT Lincoln Lab programs', 25),
             ('Research + apply: DTCC 2027 internship/EDGE', 24), ('Lab time (Prof. Jee, Mon)', 20),
             ('Lab time (Prof. Jee, Wed)', 20), ('Lab time (Prof. Jee, Tue)', 19),
             ('Lab time (Prof. Jee, Thu)', 19), ('Lab time (Prof. Jee, Fri)', 19)):
    if t in RANK: RANK[t] = r
for t in list(CONTRACT):
    if t.startswith('Review '):                       # reviews soft range
        CONTRACT[t] = (0, CONTRACT[t][1])
    if t.startswith(('Follow up with', 'Set up HomePod')):
        CONTRACT[t] = (0, CONTRACT[t][1])             # deadline-free personal items
if 'Lab time (Prof. Jee, Mon)' in CONTRACT: CONTRACT['Study for MATH 3351 midterm exam'] = (360, 420)
if 'Practice piano' in CONTRACT: CONTRACT['Practice piano'] = (210, 240)   # rest 30m cover 4h target
# --- support nodes: geometry from prefs.toml. R1/R2/R3: meals are a full
# inviolable hour (60m) and the afternoon break shrinks to a 30m floor but
# never disappears (R1-Q5a). CRUSH mode (module global, set by solve loop when
# 60m meals are proven infeasible) compresses lunch/dinner to the crush floor.
_H = PREFS['hard']
CRUSH = False

def build_supports():
    meal_lo = _H['meal_crush_minutes'] if (CRUSH and _H.get('crush_allowed', True)) else _H['meal_minutes']
    bf_lo, bf_hi = _H['breakfast_minutes']
    br_lo, br_hi = _H['break_minutes']
    return [
        dict(key='cook_breakfast', title='Cook + breakfast', loc=HOME, lo=bf_lo, hi=bf_hi, win=(T(6,(6,0)), T(7,(9,0)))),
        dict(key='lunch',          title='Lunch',            loc=HOME, lo=meal_lo, hi=_H['meal_minutes'], win=(T(6,(11,30)), T(7,(14,30)))),
        dict(key='break',          title='Afternoon break',  loc=HOME, lo=br_lo, hi=br_hi, win=(time(13,0), time(17,30))),
        dict(key='dinner',         title='Dinner',           loc=HOME, lo=meal_lo, hi=_H['meal_minutes'], win=(T(6,(17,0)), T(7,(20,15)))),
    ]

SUPPORT = build_supports()

# --- day bounds ---
_day_end = time.fromisoformat(_H['day_end'])
DAY_START, DAY_END = 6*60, _day_end.hour*60 + _day_end.minute
print(f"fixed={len(FIXED)} work_items={len(WORK)} (total {sum(w['est'] for w in WORK)//60}h)")
for f in FIXED: print(f"  {f['start']:%a %H:%M}-{f['end']:%H:%M} {f['title'][:44]:44} @{f['loc']}")
for w in WORK:  print(f"  {w['est']/60:>4}h due {w['deadline']:%a} {w['title'][:40]}")


# ---- week window + chunks ----
START = NOW.replace(hour=0, minute=0, second=0, microsecond=0)  # Tuesday 00:00
END   = START + datetime.timedelta(days=7)
ndays = 6  # 0=Tue .. 5=Sun; Monday Oct 12 is next week

CHUNK_MAX, CHUNK_MIN = 120, 60
minutes = lambda dt: int((dt - START).total_seconds() // 60)
HOME = "At home"


# %% Cell 5 — CIRCUIT LINKING + travel arcs + no-overlap per day + travel-by-arc semantics.
# For each day: collect candidate nodes (fixed always present; support/work optional).
# Circuit: depot(0) -> nodes present -> depot. Arc cost = transit_minutes(loc_a, loc_b) * NODE.
# Optional nodes: self-loop arc (literal = presence inverted) skips them.
def transit_minutes(a, b):
    a, b = (a or '').strip().lower(), (b or '').strip().lower()
    if not a or not b: return 30
    if a == b: return 0
    pair = {a, b}
    if any('ecss' in x for x in pair) and any('activity center' in x for x in pair): return 5
    if any('ecss' in x for x in pair) and any('ecsn' in x for x in pair): return 10
    def campus(x): return any(k in x for k in ('ecss','ecs','fo ','jo ','gr ','mc ','su ','ssb','activity center','utd','on campus','library'))
    def bld(x): return x.split()[0]
    if campus(a) and campus(b): return 10 if bld(a) == bld(b) else 20
    if campus(a) and campus(b): pass
    if any('grocery' in x or 'walmart' in x for x in pair): return 15  # grocery↔home is a quick car hop
    return 30  # campus <-> home



def build_week():
    model = cp_model.CpModel()
    def mn(dt): return int((dt - START).total_seconds() // 60)
    # R1-Q1b morning boundary (HARD): no work before the first morning class
    # ENDS on class days; ~10:00 on free days. Cooking+breakfast always exempt
    # (supports carry their own windows). Errands exempt (early grocery habit).
    def day_work_floor(d):
        if globals().get('FLOOR_OFF'):
            return 6 * 60
        ds = START + datetime.timedelta(days=d)
        morning = [f for f in FIXED if f['start'].date() == ds.date()
                   and f['start'].hour < 12]
        if not morning:
            return 10 * 60
        return int(max(6 * 60, min((f['end'] - ds).total_seconds() // 60 for f in morning)))
    nodelist = []
    for f in FIXED:
        s0, e0 = mn(f['start']), mn(f['end'])
        d0 = (f['start']-START).days
        if d0 >= ndays or d0 < 0: continue
        nodelist.append(dict(title=f['title'], loc=f['loc'], kind='fixed', item=None,
                             start=model.NewConstant(s0), size=model.NewConstant(e0-s0),
                             presence=None, day=d0, fixed=(s0,e0)))
    for sup in SUPPORT:
        for d in range(ndays):
            ds = START + datetime.timedelta(days=d); wnd = sup['win']
            lo, hi = (mn(ds)+wnd[0].hour*60+wnd[0].minute, mn(ds)+wnd[1].hour*60+wnd[1].minute) if wnd else (mn(ds)+DAY_START, mn(ds)+DAY_END)
            if d == 0:
                lo = max(lo, mn(NOW) - mn(START))   # never plan today's meals in the past
            if lo + sup['lo'] > hi:
                continue  # today's window for this support block has already passed
            lo_dur, hi_dur = sup['lo'], sup['hi']
            # Required unless marked optional (break is required by R1-Q5a;
            # the probe harness toggles this to bisect infeasibility).
            pv = model.NewBoolVar(f"{sup['key']}_p_d{d}")
            if sup.get('optional'):
                zv = model.NewIntVar(0, hi_dur, f"{sup['key']}_z_d{d}")
                model.Add(zv == 0).OnlyEnforceIf(pv.Not())
                model.Add(zv >= lo_dur).OnlyEnforceIf(pv)
            else:
                model.Add(pv == 1)                            # meals AND break always scheduled
                zv = model.NewIntVar(lo_dur, hi_dur, f"{sup['key']}_z_d{d}")
            sv = model.NewIntVar(lo, hi, f"{sup['key']}_s_d{d}")
            model.Add(sv >= lo).OnlyEnforceIf(pv); model.Add(sv+zv <= hi).OnlyEnforceIf(pv)
            nodelist.append(dict(title=sup['title'], loc=sup['loc'], kind='support', item=sup['key'],
                                 start=sv, size=zv, presence=pv, day=d, win=(lo,hi)))
    for w in WORK:
        min_req, target = CONTRACT[w['title']]
        # per-item chunk geometry: default 60-120m; lab 120-150m (R2-Q3);
        # chunks=1 -> one exact block (indivisible, R3-Q3a)
        cmin = w.get('chunk_min', CHUNK_MIN)
        cmax = w.get('chunk_max', CHUNK_MAX)
        if w.get('chunks') == 1:
            nchunks, cmin, cmax = 1, target, target
        else:
            # day-capped items (piano 60m/day): a 120m chunk can never exceed
            # the day cap, so the chunk count must divide by the EFFECTIVE cap
            # or the item is silently unachievable (4h piano in 2x60m chunks).
            cap_eff = min(cmax, w['day_cap']) if w.get('day_cap') is not None else cmax
            nchunks = max(1, math.ceil(target/cap_eff))
        dmax = (w['deadline']-START).days
        allowed_days = w.get('days')
        # allowed_days are stored as Python weekday ints (Mon=0, so [5,6] =
        # Sat/Sun) and translated to day INDICES against START's weekday —
        # hardcoding indices silently breaks when NOW crosses midnight and
        # START advances (Sat/Sun became next-week Mon/Tue, past the deadline).
        if allowed_days is not None:
            allowed_days = sorted((wd - START.weekday()) % 7 for wd in allowed_days)
        wwin = w.get('work_win')                # e.g. lab hours: 10:00-17:00
        errand = w.get('errand', False)
        for c in range(nchunks):
            for d in range(min(ndays, dmax+1)):
                if allowed_days is not None and d not in allowed_days:
                    continue
                ds = START + datetime.timedelta(days=d)
                # Day-0 floor is NOW (not DAY_START + NOW — the offset already
                # is minutes since midnight); summing both put the floor at
                # 19:25 and collided with early-afternoon work windows.
                floor = DAY_START if errand else max(DAY_START, day_work_floor(d))
                lo = mn(ds) + max(floor, (mn(NOW)-mn(START) if d==0 else 0))
                hi = min(mn(w['deadline']), mn(ds)+DAY_END)
                if wwin:
                    lo = max(lo, mn(ds)+wwin[0].hour*60+wwin[0].minute)
                    hi = min(hi, mn(ds)+wwin[1].hour*60+wwin[1].minute)
                if lo > hi:
                    continue  # this day's work window has passed (e.g. lab 10-17 after 17:00)
                sv = model.NewIntVar(lo, hi, f"c{w['id'][:18]}_s_d{d}_c{c}")
                zv = model.NewIntVar(0, cmax, f"c{w['id'][:18]}_z_d{d}_c{c}")
                pv = model.NewBoolVar(f"p{w['id'][:18]}_d{d}_c{c}")
                model.Add(zv >= cmin).OnlyEnforceIf(pv)
                model.Add(zv == 0).OnlyEnforceIf(pv.Not())
                model.Add(sv+zv <= hi).OnlyEnforceIf(pv)
                nodelist.append(dict(title=w['title'], loc=w['loc'], kind='work', item=w['id'],
                                     start=sv, size=zv, presence=pv, day=d, chunk=c, rank=RANK[w['title']],
                                     deadline=mn(w['deadline'])))
    for w in WORK:
        min_req, target = CONTRACT[w['title']]
        ch = [n for n in nodelist if n['item']==w['id'] and n['kind']=='work']
        model.Add(sum(n['size'] for n in ch) >= min_req)
        model.Add(sum(n['size'] for n in ch) <= target)
        if w.get('day_cap') is not None:      # piano: max 60m of practice per day
            for d in range(ndays):
                chd = [n for n in ch if n['day']==d]
                if chd: model.Add(sum(n['size'] for n in chd) <= w['day_cap'])
        # Chunk order only WITHIN a day: ch is c-major over the (chunk, day)
        # grid, so a flat zip chain would make any later chunk force chunk-0
        # present on EVERY day (presence ⇒ size ≥ CHUNK_MIN), overflowing the
        # item's target upper bound. Within a day the implication is harmless
        # and keeps same-day pieces sequenced; cross-day order is implicit in
        # absolute start minutes.
        for d in range(ndays):
            chd = sorted((n for n in ch if n['day']==d), key=lambda n: n['chunk'])
            for a, b in zip(chd, chd[1:]):
                model.AddImplication(b['presence'], a['presence'])
    # lab days <= 3 (R2-Q3): count distinct days with lab presence
    lab = next((w for w in WORK if w.get('lab')), None)
    if lab is not None and lab.get('day_cap_days'):
        lch = [n for n in nodelist if n['item']==lab['id'] and n['kind']=='work']
        lused = []
        for d in range(ndays):
            chd = [n for n in lch if n['day']==d]
            if not chd: continue
            u = model.NewBoolVar(f"labused_d{d}")
            model.AddBoolOr([u.Not()] + [n['presence'] for n in chd])  # u -> some presence
            for n in chd: model.AddImplication(n['presence'], u)
            lused.append(u)
        model.Add(sum(lused) <= lab['day_cap_days'])
    prod_cache = {}
    def BOTH(x,y):
        k=(x.Index(),y.Index())
        if k not in prod_cache:
            v=model.NewBoolVar(f"and_{x.Name()}_{y.Name()}")
            model.AddBoolAnd([x,y]).OnlyEnforceIf(v)      # v → x ∧ y
            model.AddBoolOr([v.Not(), x]).OnlyEnforceIf(x)  # x → v
            model.AddBoolOr([v.Not(), y]).OnlyEnforceIf(y)  # y → v
            prod_cache[k]=v
        return prod_cache[k]
    circuits, travel_terms, arcmap = {}, [], {}
    for d in range(ndays):
        dn = [n for n in nodelist if n['day']==d]
        arcs = [(0,0,False)]
        day_arcs = []
        lit_cache = {}
        def lit(i,j,p):
            if (i,j) not in lit_cache:
                v = model.NewBoolVar(f"x{d}_{i}_{j}")
                if p is not None: model.AddImplication(v, p)
                lit_cache[(i,j)] = v
            return lit_cache[(i,j)]
        for i,a in enumerate(dn,1):
            pa = a['presence']
            arcs.append((i,i,False) if pa is None else (i,i,pa.Not()))
            arcs.append((0,i,lit(0,i,pa)))
            arcs.append((i,0,lit(i,0,pa)))
            for j,b in enumerate(dn,1):
                if i==j: continue
                pb = b['presence']
                p = BOTH(pa,pb) if (pa is not None and pb is not None) else (pa if pb is None and pa is not None else pb)
                l = lit(i,j,p); arcs.append((i,j,l))
                cost = transit_minutes(a['loc'],b['loc'])
                if cost:
                    travel_terms.append((lit(i,j,p), cost))
                # Spacing on EVERY arc, even same-location (cost 0) ones:
                # without it the circuit can visit home nodes out of time
                # order for free, decoupling the charged route from the
                # rendered timeline.
                model.Add(b['start'] >= a['start'] + a['size'] + cost).OnlyEnforceIf(lit(i,j,p))
        model.AddCircuit(arcs)
        circuits[d]=dn
        day_arcs += [a[2] for a in arcs if a[2] is not False and a[0]!=a[1]]
        arcmap[d] = day_arcs
    travel_cost = model.NewIntVar(0, 10**6, 'travel_cost')
    model.Add(travel_cost == sum(l*c for l,c in travel_terms))
    return model, nodelist, circuits, travel_cost, arcmap

def solve_week2(wts):
    """One candidate schedule under a weight vector (fuzzed per candidate).
    Weights: travel, weekend_homework, earliness, fragmentation, late_evening,
    lab_wednesday. Budgets come from prefs.toml [solver].
    Crush retry: if 60m meals are infeasible, rebuild with crush meals (45m,
    still required) and flag it — never silently.
    NOTE: CRUSH is a module global reset by solve_candidates per candidate —
    do NOT reset it here; the crush retry recurses into this function and must
    keep the flag."""
    global CRUSH, SUPPORT
    SUPPORT = build_supports()   # re-evaluate meal floors for the CRUSH state
    mm, nds, cts, tc, arcmap = build_week()
    TRUEx = mm.NewBoolVar('T'); mm.Add(TRUEx == 1)
    late_terms, work_terms, eve_terms = [], [], []
    for d, dn in cts.items():
        ints = []
        day20 = d*1440 + 20*60  # 20:00 overflow-valve line (day windows are day*1440 + minutes)
        for n in dn:
            endv = mm.NewIntVar(0, minutes(END), f"e_{d}_{n['title'][:14]}")
            mm.Add(endv == n['start'] + n['size'])
            pres = n['presence'] if n['presence'] is not None else TRUEx
            n['interval'] = mm.NewOptionalIntervalVar(n['start'], n['size'], endv, pres, f"iv_{d}_{n['title'][:14]}")
            n['end'] = endv; ints.append(n['interval'])
            if n['kind']=='support' and n['item'] in ('dinner','lunch','breakfast'):
                late = mm.NewIntVar(0, minutes(END), f"late_{n['item']}_{d}")
                mm.Add(late >= n['start'] - n['win'][0]); late_terms.append(late)
            if n['kind']=='work':
                work_terms.append((n['size'], n['rank']))
                ev = mm.NewIntVar(0, minutes(END), f"eve_{d}_{n['title'][:14]}")
                mm.Add(ev >= n['start'] + n['size'] - day20)   # work minutes past 20:00
                eve_terms.append(ev)
        mm.AddNoOverlap(ints)
        by_item = {}
        for n in dn:
            if n['kind']=='work': by_item.setdefault(n['item'], []).append(n)
        for item, chs in by_item.items():
            chs.sort(key=lambda n: n['chunk'])
            for a, b in zip(chs, chs[1:]):
                mm.Add(a['start'] <= b['start']).OnlyEnforceIf([a['presence'], b['presence']])
    lateness = mm.NewIntVar(0, 10**6, 'lateness'); mm.Add(lateness == sum(late_terms))
    # Standing rule 11: assignment work lives on weekdays. Weekend minutes are
    # penalized (errands exempt — they must run Sat/Sun by contract).
    # Weekend day indices move with START (they were hardcoded >= 5, which
    # silently became "Monday only" when START crossed midnight to Wednesday).
    weekend_days = {(5 - START.weekday()) % 7, (6 - START.weekday()) % 7}
    weekend_cost = mm.NewIntVar(0, 10**6, 'weekend_cost')
    mm.Add(weekend_cost == sum(n['size'] for n in nds
                               if n['kind']=='work' and n['day'] in weekend_days
                               and not any(w['id']==n['item'] and w.get('errand') for w in WORK)))
    # Fragmentation (R2-Q5a): penalize each extra day an item spans — prefer
    # one day with adjacent ~2h chunks over scattering. Piano is exempt (4
    # separate days by design).
    frag_terms = []
    for w in WORK:
        if w.get('no_frag'): continue
        ch = [n for n in nds if n['item']==w['id'] and n['kind']=='work']
        used = []
        for d in range(ndays):
            chd = [n for n in ch if n['day']==d]
            if not chd: continue
            u = mm.NewBoolVar(f"used_{w['id'][:14]}_{d}")
            model_add_or(mm, u, [n['presence'] for n in chd])
            used.append(u)
        if len(used) >= 2:
            extra = mm.NewIntVar(0, len(used)-1, f"frag_{w['id'][:14]}")
            mm.Add(extra >= sum(used) - 1)
            frag_terms.append(extra)
    # lab-on-Wednesday reward (R2-Q3): Wednesday's day index moves with START
    lab = next((w for w in WORK if w.get('lab')), None)
    lab_wed_day = (2 - START.weekday()) % 7   # 2 = Wednesday (Mon=0)
    lab_wed = mm.NewIntVar(0, 10**6, 'lab_wed')
    if lab is not None:
        mm.Add(lab_wed == sum(n['size'] for n in nds
                              if n['kind']=='work' and n['item']==lab['id'] and n['day']==lab_wed_day))
    priority_value = mm.NewIntVar(0, 10**7, 'priority_value')
    mm.Add(priority_value == sum(sz * rk for sz, rk in work_terms))
    s = cp_model.CpSolver(); s.parameters.num_workers = 24
    s.parameters.max_time_in_seconds = PREFS['solver']['phase1_seconds']
    mm.ClearObjective(); mm.Maximize(priority_value)
    st = s.Solve(mm)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if not CRUSH and _H.get('crush_allowed', True):
            print("phase1 infeasible with 1h meals — CRUSH retry (meals 45m, still required)")
            CRUSH = True
            return solve_week2(wts)   # rebuild everything with crushed meal floors
        print("phase1:", s.StatusName(st)); return None
    # phase 2 reuses this solver; bump the wall clock for the harder minimization
    s.parameters.max_time_in_seconds = PREFS['solver']['phase2_seconds']
    pv1 = s.Value(priority_value)
    mm.Add(priority_value >= pv1)  # lock rank value; then minimize travel/lateness/earliness
    # Warm-start phase 2 from the phase-1 assignment: without hints the solver
    # burns its whole budget re-deriving a feasible baseline and returns the
    # first FEASIBLE point (unbalanced weekends) instead of an improving one.
    mm.ClearHints()
    for n in nds:
        if n['presence'] is None:
            continue  # fixed nodes: constants (NewConstant) cannot take hints
        mm.AddHint(n['start'], s.Value(n['start']))
        mm.AddHint(n['size'], s.Value(n['size']))
        mm.AddHint(n['presence'], s.Value(n['presence']))
    for d, lits in arcmap.items():
        for l in lits:
            mm.AddHint(l, s.Value(l))
    earliness = mm.NewIntVar(0, 10**7, 'earliness')
    mm.Add(earliness == sum(n['start'] for n in nds if n['kind']=='work'))
    ear_h = mm.NewIntVar(0, 10**6, 'ear_h'); mm.AddDivisionEquality(ear_h, earliness, 60)
    eve_h = mm.NewIntVar(0, 10**6, 'eve_h'); mm.AddDivisionEquality(eve_h, sum(eve_terms), 60)
    frag = mm.NewIntVar(0, 10**5, 'frag'); mm.Add(frag == sum(frag_terms) if frag_terms else frag == 0)
    labw_h = mm.NewIntVar(0, 10**4, 'labw_h'); mm.AddDivisionEquality(labw_h, lab_wed, 60)
    mm.ClearObjective()
    mm.Minimize(tc*wts['travel'] + lateness*PREFS['weights']['meal_lateness']
                + ear_h*wts['earliness'] + weekend_cost*wts['weekend_homework']
                + frag*wts['fragmentation'] + eve_h*wts['late_evening']
                - labw_h*wts['lab_wednesday'])
    st = s.Solve(mm)
    stats = dict(travel=s.Value(tc), late=s.Value(lateness), ear_h=s.Value(ear_h),
                 weekend=s.Value(weekend_cost), frag=s.Value(frag),
                 eve_h=s.Value(eve_h), lab_wed_h=s.Value(labw_h), crush=CRUSH)
    print("phase2:", s.StatusName(st), "|", stats)
    return (s, nds, cts, stats) if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None

def model_add_or(mm, u, presences):
    """u <-> OR(presences) for bool vars."""
    mm.AddBoolOr([u.Not()] + list(presences))       # u -> some presence
    for p in presences:
        mm.AddImplication(p, u)                     # presence -> u

def solve_candidates():
    """Generate prefs['solver']['candidates'] schedules with fuzzed weights.
    Returns [(idx, weights, result-or-None)]. Candidates land in
    /tmp/route-week/candidates/cand_<i>.json for the agent to pick from."""
    n = PREFS['solver']['candidates']
    rng = random.Random(PREFS['solver']['seed'])
    fuzz, base = PREFS['fuzz'], PREFS['weights']
    global CRUSH
    out = []
    os.makedirs('/tmp/route-week/candidates', exist_ok=True)
    for i in range(n):
        wts = {k: float(rng.choice(fuzz[k])) for k in fuzz}
        print(f"=== candidate {i+1}/{n} weights={wts}")
        CRUSH = False   # fresh meals-1h attempt per candidate; crush retry sets it
        res = solve_week2(wts)
        out.append((i, wts, res))
        if res:
            s, nds, cts, stats = res
            dump = []
            for nod in sorted(nds, key=lambda x: (x['day'], s.Value(x['start']))):
                z = s.Value(nod['size']); v0 = s.Value(nod['start'])
                if nod['kind'] in ('work', 'support') and z == 0:
                    continue
                t0 = START + datetime.timedelta(minutes=v0)
                dump.append(dict(day=nod['day'], start=t0.isoformat(), size=z,
                                 kind=nod['kind'], item=nod['item'], title=nod['title'],
                                 loc=str(nod['loc'])))
            json.dump(dict(candidate=i, weights=wts, stats=stats, crush=stats['crush'],
                           schedule=dump),
                      open(f'/tmp/route-week/candidates/cand_{i}.json', 'w'), indent=1)
    return out


def render(nodes, circuits, solver):
    rows = []
    for n in sorted(nodes, key=lambda n: (n['day'], solver.Value(n['start']))):
        v0 = solver.Value(n['start']); z = solver.Value(n['size'])
        if n['kind']=='work' and z == 0: continue
        if n['kind']=='support' and z == 0: continue
        if n['kind']=='fixed' and n['day'] < 0: continue
        # n['start'] is absolute minutes since START (each day's window is
        # mn(ds)+…), so the wall clock is START + the value — NOT the day's
        # midnight plus the value, which double-counts the day offset.
        t0 = START + datetime.timedelta(minutes=v0)
        t1 = t0 + datetime.timedelta(minutes=z)
        loc = n['loc'] if isinstance(n['loc'], str) else n['loc'].get('type','?')
        rows.append((n['day'], v0, f"{t0:%a %H:%M}-{t1:%H:%M} {n['title'][:38]:38s} {loc}"))
    return rows



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', help='also dump the chosen candidate\'s schedule to this file')
    ap.add_argument('--pick', type=int, default=None,
                    help='candidate index to treat as chosen (default: lowest travel+frag)')
    a = ap.parse_args()
    cands = solve_candidates()
    ok = [(i, w, r) for i, w, r in cands if r]
    if not ok:
        print("no feasible candidate"); sys.exit(1)
    print(f"\n{len(ok)}/{len(cands)} feasible candidates in /tmp/route-week/candidates/")
    for i, w, (s, nds, cts, stats) in ok:
        print(f"  cand_{i}: travel={stats['travel']:>4} frag={stats['frag']:>2} "
              f"eve_h={stats['eve_h']:>4} weekend={stats['weekend']:>4} lab_wed_h={stats['lab_wed_h']}")
    # default pick: agent may override with --pick; scoring here is only a fallback
    if a.pick is not None:
        chosen = next((c for c in ok if c[0] == a.pick), ok[0])
    else:
        chosen = min(ok, key=lambda c: c[2][3]['travel'] + 50*c[2][3]['frag'] + 30*c[2][3]['eve_h'])
    i, w, (s, nodes, circuits, stats) = chosen
    print(f"\n--- candidate {i} (fallback pick; agent selects from the pool) ---")
    rows = render(nodes, circuits, s)
    cur = None
    for d, v0, line in rows:
        if d != cur:
            print(f"--- day {d} ---")
            cur = d
        print(line)
    if a.json:
        dump = []
        for n in sorted(nodes, key=lambda n: (n['day'], s.Value(n['start']))):
            z = s.Value(n['size']); v0 = s.Value(n['start'])
            if n['kind'] in ('work', 'support') and z == 0:
                continue
            day = START + datetime.timedelta(days=n['day'])
            t0 = START + datetime.timedelta(minutes=v0)
            dump.append(dict(day=n['day'], start=t0.isoformat(), size=z, kind=n['kind'],
                             item=n['item'], title=n['title'], loc=str(n['loc'])))
        json.dump(dump, open(a.json, 'w'), indent=1)
        print("wrote", a.json)

if __name__ == '__main__':
    main()
