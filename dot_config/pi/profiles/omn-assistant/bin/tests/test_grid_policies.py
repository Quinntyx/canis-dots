"""Standing policy compilation and objective probes use only fake input stores."""
import json
from datetime import date, datetime, timedelta

from grid_scheduler.adapter import load_live
from grid_scheduler.checks import policy_errors
from grid_scheduler.decode import decode
from grid_scheduler.engine import solve
from grid_scheduler.metrics import group_counts
from grid_scheduler.schema import Color, Group, Item, Problem, Reservation
from grid_scheduler.verify import verify
from scheduler.common import TZ

WEEK = date(2026, 9, 28)


def live(records=(), tasks=(), **kwargs):
    return load_live(str(WEEK), now=kwargs.pop('now', datetime(2026, 9, 28, tzinfo=TZ)),
                     omn_records=list(records), task_records=list(tasks), **kwargs)


def test_supports_do_not_silently_drop_a_partly_elapsed_required_break():
    p = live(now=datetime(2026, 10, 1, 17, 45, tzinfo=TZ))
    color = next(c for c in p.colors if c.key == 'support:break')
    assert color.daily[3] == (4, 8)
    result = solve(p)
    assert result['status'] == 'INFEASIBLE'
    assert any(e.get('day') == 3 and e.get('color') == color.key for e in result['capacity_errors'])


def test_break_is_one_run_and_prefers_two_hours_when_it_fits():
    p = Problem(WEEK, [Color('break', 'support', 4, 8, ((40, 48),), 4, 8,
        daily={0: (4, 8)}, daily_max_runs=1, prefer_maximum=True)])
    c = solve(p, timeout_ms=2000)
    assert c['status'] == 'ok' and c['grid'].count('break') == 8
    assert c['amount_optimization_exact'] and not verify(p, c)
    p.colors = [Color('break', 'support', 8, 8, ((40, 44), (46, 50)), 4, 8,
                       daily={0: (8, 8)}, daily_max_runs=1)]
    assert solve(p)['status'] == 'INFEASIBLE'


def test_dinner_has_a_shared_start_and_checker_catches_a_drift():
    p = Problem(WEEK, [Color('dinner', 'support', 6, 6, ((40, 48), (136, 144)), 3, 3,
        daily={0: (3, 3), 1: (3, 3)}, same_start_daily=True, daily_max_runs=1)])
    c = solve(p, timeout_ms=2000)
    assert c['status'] == 'ok' and not verify(p, c)
    assert c['runs'][0]['start'] % 96 == c['runs'][1]['start'] % 96
    bad = [{'color': 'dinner', 'start': 40, 'end': 43, 'cells': 3},
           {'color': 'dinner', 'start': 137, 'end': 140, 'cells': 3}]
    assert any('same daily start' in e for e in policy_errors(p, c['grid'], bad))


def test_car_clustering_is_a_preference_not_a_false_weekday_ban():
    p = Problem(WEEK, [Color('car', 'work', 4, 4, ((40, 42), (136, 138)))],
        [Item('a', 'First errand', 'car', 2, 2, ((40, 42),)),
         Item('b', 'Second errand', 'car', 2, 2, ((136, 138),))],
        groups=[Group('outing', ('car',), 96, 2, prefer_fewer_runs=True)])
    c = solve(p, timeout_ms=2000)
    assert c['status'] == 'ok' and not verify(p, c)
    assert group_counts(p, c['grid'])['outing'][:2] == [1, 1]


def test_explicit_completed_cooking_is_not_restored_even_when_early():
    tasks = [{'uuid': str(day), 'status': 'completed', 'description': 'Cook breakfast',
              'scheduled': str(WEEK + timedelta(days=day))} for day in range(7)]
    p = live(tasks=tasks)
    assert all(c.key != 'support:cook' for c in p.colors)
    assert next(c for c in p.colors if c.key == 'support:breakfast').follows is None
    assert Problem.from_dict(json.loads(json.dumps(p.to_dict()))).to_dict() == p.to_dict()


def test_deleted_support_and_fixed_occurrence_are_not_recreated():
    records = [{'id': 'meeting', 'type': 'event', 'title': 'Seminar', 'meta': {
        'start': '2026-09-28T12:00:00-05:00', 'end': '2026-09-28T13:00:00-05:00', 'location': 'At home'}}]
    previous = {'problem': {'week_start': str(WEEK), 'colors': [], 'metadata': {
        'source_task_snapshot': [
            {'uuid': 'break', 'description': 'Take afternoon break', 'scheduled': str(WEEK),
             'tags': ['managed', 'schedule']},
            {'uuid': 'fixed', 'description': 'Attend Seminar', 'scheduled': str(WEEK),
             'tags': ['managed', 'fixed'], 'todo': '- Seminar [omn:meeting]'}]}},
        'candidate': {'status': 'ok', 'grid': ['free'] * 672}}
    p = live(records, previous=previous)
    assert 0 not in next(c for c in p.colors if c.key == 'support:break').daily
    assert all(r.id != 'meeting@2026-09-28' for r in p.reservations)
    assert p.metadata['cancelled_occurrences'] == ['meeting@2026-09-28']


def test_partial_away_window_absorbs_a_whole_meal_not_the_whole_daily_range():
    records = [{'id': 'away', 'type': 'event', 'title': 'Away', 'meta': {
        'start': '2026-10-03T11:30:00-05:00', 'end': '2026-10-04T17:00:00-05:00', 'location': 'San Antonio'}}]
    p = live(records)
    assert 5 not in next(c for c in p.colors if c.key == 'support:lunch').daily
    assert 6 not in next(c for c in p.colors if c.key == 'support:break').daily
    assert 6 in next(c for c in p.colors if c.key == 'support:dinner').daily


def test_daily_occurrences_keep_one_semantic_color_and_real_source_references():
    records = [{'id': name, 'type': 'task', 'title': 'Practice ' + name, 'meta': {
        'daily_est': {'0': '1h', '1': '1h'}, 'hours': '14:00-18:00',
        'target_week': str(WEEK), 'color': 'music'}} for name in ('piano', 'violin')]
    p = live(records)
    assert len(p.items) == 4 and len({i.color for i in p.items}) == 1
    assert {i.reference for i in p.items} == {'piano', 'violin'}
    # Isolate the work compiler to keep this a small exact objective test.
    work = Problem(WEEK, [c for c in p.colors if c.kind == 'work'], p.items)
    c = solve(work, timeout_ms=3000)
    assert c['status'] == 'ok' and not verify(work, c)
    rows = decode(work, c)
    assert all('@2026-' not in r['todo'] for r in rows)
    assert sum(int(r['est'][:-1]) for r in rows) == 240


def test_verified_venue_hours_are_hard_and_missing_required_hours_block():
    record = {'id': 'bank', 'type': 'task', 'title': 'Visit bank', 'meta': {
        'est': '1h', 'target_week': str(WEEK), 'requires_open': True}}
    assert solve(live([record]))['status'] == 'BLOCKED'
    record['meta']['open_hours'] = {'0': [['10:00', '11:00']]}
    p = live([record])
    assert p.items[0].windows == ((40, 44),)


def test_unknown_canvas_quantity_is_not_silently_a_legacy_two_hour_default():
    record = {'id': 'quiz', 'type': 'task', 'title': 'Oddly named real quiz',
              'tags': ['canvas'], 'meta': {'due': '2026-09-29', 'ical': {'description': ''}}}
    c = solve(live([record]))
    assert c['status'] == 'BLOCKED' and any('no recorded estimate' in e for e in c['source_errors'])


def test_predecessor_exception_is_day_local_and_survives_json_roundtrip():
    p = Problem(WEEK, [Color('cook', 'support', 1, 1, ((135, 136),)),
        Color('breakfast', 'support', 2, 2, ((40, 41), (136, 137)),
              daily={0: (1, 1), 1: (1, 1)}, follows='cook', follows_exceptions=(0,))])
    assert Problem.from_dict(json.loads(json.dumps(p.to_dict()))).to_dict() == p.to_dict()
    c = solve(p)
    assert c['status'] == 'ok' and not verify(p, c)
    p.reservations = [Reservation('busy', 'no-cook', 135 * 15, 136 * 15)]
    p.colors += [Color('no-cook', 'fixed')]
    assert solve(p)['status'] == 'INFEASIBLE'


def test_fixed_attendance_publication_is_exact_and_refuses_protected_overlap():
    from test_grid_scheduler import FakeTasks

    from grid_scheduler.apply import apply
    p = Problem(WEEK, [Color('fixed', 'fixed', location='At home')],
        reservations=[Reservation('meeting', 'fixed', 727, 740, 'Seminar', 'At home')],
        source='live', metadata={'fixed_attendance': [{'reservation': 'meeting', 'source': 'event'}]})
    c = solve(p)
    rows = decode(p, c)
    assert len(rows) == 1 and rows[0]['starttime'] == '12:07'
    fake = FakeTasks()
    now = datetime(2026, 9, 28, tzinfo=TZ)
    assert apply(p, c, rows, taskwarrior=fake, now=now, post_publish=False)['dry_run']
    assert not fake.calls
    result = apply(p, c, rows, taskwarrior=fake, now=now, confirmed=True, post_publish=False)
    assert result['applied'] and 'fixed' in fake.tasks[0]['tags']
    protected = FakeTasks([{'uuid': 'unrelated', 'status': 'pending', 'tags': ['fixed'],
        'scheduled': str(WEEK), 'starttime': '12:10', 'endtime': '12:15'}])
    assert apply(p, c, rows, taskwarrior=protected, now=now, confirmed=True,
                 post_publish=False)['refused']
    assert not protected.calls


def test_co_scheduling_subtracts_exact_and_approximate_person_busy_time():
    from grid_scheduler.people import participant_windows
    from grid_scheduler.policies import intersect_windows
    people = [{'id': 'person:leo', 'type': 'person', 'title': 'Leo', 'meta': {
        'times_approximate': True, 'busy': [{'days': ['mon'], 'start': '10:07', 'end': '11:07'}]}}]
    assert intersect_windows([(32, 48)], participant_windows({'with': ['Leo']}, people)) == [(32, 39), (46, 48)]
    import pytest
    with pytest.raises(ValueError, match='unresolved co-scheduling'):
        participant_windows({'people': ['unknown']}, people)


def test_direct_production_apply_cannot_publish_a_spec(monkeypatch):
    from grid_scheduler import apply as module
    p = Problem(WEEK, [])
    c = solve(p)
    def forbidden_transport():
        raise AssertionError('production transport must not be constructed')
    monkeypatch.setattr(module, 'Taskwarrior', forbidden_transport)
    report = module.apply(p, c, [], confirmed=True)
    assert report['refused'] and 'spec plans are dry-run only' in report['refused'][0]


def test_direct_production_apply_checks_source_fingerprint_before_transport(monkeypatch):
    from grid_scheduler import apply as module
    from scheduler import sources
    p = Problem(WEEK, [], source='live', metadata={'source_digest': 'obsolete'})
    c = solve(p)
    monkeypatch.setattr(sources, 'read_omn_export', list)
    monkeypatch.setattr(sources, 'read_task_export', list)
    def forbidden_transport():
        raise AssertionError('production transport must not be constructed')
    monkeypatch.setattr(module, 'Taskwarrior', forbidden_transport)
    report = module.apply(p, c, [], confirmed=True, now=datetime(2026, 9, 28, tzinfo=TZ))
    assert report['refused'] and 'source state changed' in report['refused'][0]
