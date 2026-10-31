#!/usr/bin/python3
"""Toggle G-Track headphones/call mode and Audigy speaker mode.

Normal playback follows the selected physical output. In headphone mode REAPER
uses piano-out, which already feeds the call mix and G-Track headphones; in speaker
mode it plays directly to Audigy. Waybar's status poll also restores this routing
when REAPER opens. No microphone selections or explicit virtual app routes change.
"""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


class RouteError(Exception):
    pass


def run(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RouteError(str(exc)) from exc
    if result.returncode:
        raise RouteError(result.stderr.strip() or f"{args[0]} failed")
    return result.stdout


class Graph:
    def __init__(self, objects):
        self.nodes = {}
        self.ports = {}
        self.links = set()
        for obj in objects:
            kind = obj.get("type", "").rsplit(":", 1)[-1]
            info = obj.get("info") or {}
            props = info.get("props") or {}
            if kind == "Node":
                self.nodes[obj["id"]] = props
            elif kind == "Port":
                self.ports[obj["id"]] = props
            elif kind == "Link":
                self.links.add((info["output-port-id"], info["input-port-id"]))

    @classmethod
    def current(cls):
        try:
            return cls(json.loads(run("pw-dump")))
        except (ValueError, KeyError, TypeError) as exc:
            raise RouteError("Cannot read the PipeWire audio graph") from exc

    def find_node(self, predicate, label):
        matches = [node for node, props in self.nodes.items() if predicate(props)]
        if len(matches) > 1:
            raise RouteError(f"More than one {label} device is available")
        return matches[0] if matches else None

    def reaper(self):
        return self.find_node(lambda p: p.get("node.name") == "REAPER", "REAPER")

    def destination(self, mode):
        if mode == "mix":
            return self.find_node(lambda p: p.get("node.name") == "piano-out", "Piano Output")
        return self.find_node(
            lambda p: p.get("media.class") == "Audio/Sink"
            and "audigy" in p.get("node.description", "").lower(),
            "Audigy output",
        )

    def port(self, node, name, direction):
        matches = [
            port for port, props in self.ports.items()
            if str(props.get("node.id")) == str(node)
            and props.get("port.name") == name
            and props.get("port.direction") == direction
        ]
        if len(matches) != 1:
            raise RouteError(f"Audio port {name} is not available")
        return matches[0]

    def pairs(self, mode):
        source = self.reaper()
        target = self.destination(mode)
        if source is None:
            raise RouteError("Open REAPER before switching its output")
        if target is None:
            raise RouteError(f"{'Piano Output' if mode == 'mix' else 'Audigy'} is not available")
        return {
            (self.port(source, "out1", "out"), self.port(target, "playback_FL", "in")),
            (self.port(source, "out2", "out"), self.port(target, "playback_FR", "in")),
        }

    def existing_pairs(self, mode):
        if self.destination(mode) is None:
            return set()
        return self.links & self.pairs(mode)

    def primary_links(self):
        source = self.reaper()
        outputs = {self.port(source, "out1", "out"), self.port(source, "out2", "out")}
        targets = {
            node for node, props in self.nodes.items()
            if props.get("media.class") == "Audio/Sink"
            and (props.get("node.name") == "piano-out"
                 or "audigy" in props.get("node.description", "").lower()
                 or "g-track" in props.get("node.description", "").lower())
        }
        inputs = {
            port for port, props in self.ports.items()
            if any(str(props.get("node.id")) == str(node) for node in targets)
            and props.get("port.direction") == "in"
        }
        return {(output, dest) for output, dest in self.links
                if output in outputs and dest in inputs}

    def mode(self):
        if self.reaper() is None:
            return "stopped"
        active = self.primary_links()
        for mode in ("mix", "audigy"):
            if self.destination(mode) is not None and active == self.pairs(mode):
                return mode
        return "other"


HEADPHONES = "\uf025"
SPEAKERS = "\uf028"


def sinks():
    return json.loads(run("pactl", "-f", "json", "list", "sinks"))


def physical_sink(devices, mode):
    keyword = "g-track" if mode == "headphones" else "audigy"
    matches = [sink for sink in devices if keyword in sink.get("description", "").lower()]
    if len(matches) != 1:
        raise RouteError(f"{'G-Track headphones' if mode == 'headphones' else 'Audigy speakers'} "
                         "are unavailable or ambiguous")
    return matches[0]


def output_mode(devices, default):
    for mode in ("headphones", "speakers"):
        try:
            if physical_sink(devices, mode)["name"] == default:
                return mode
        except RouteError:
            continue
    return "other"


def movable_streams(devices, target):
    primary = {sink["index"] for sink in devices
               if any(name in sink.get("description", "").lower()
                      for name in ("g-track", "audigy"))}
    streams = json.loads(run("pactl", "-f", "json", "list", "sink-inputs"))
    return [stream for stream in streams
            if stream["sink"] in primary and stream["sink"] != target["index"]
            and stream.get("properties", {}).get("application.name")
            and not stream.get("properties", {}).get("node.name", "").startswith("piano-")]


@contextmanager
def route_lock(block=True):
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    with (runtime / "waybar-reaper-route.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | (0 if block else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
        else:
            try:
                yield True
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def sync_reaper(mode):
    graph = Graph.current()
    if graph.reaper() is not None:
        route = "mix" if mode == "headphones" else "audigy"
        if graph.mode() != route:
            switch(graph, route)


def status():
    devices = sinks()
    mode = output_mode(devices, run("pactl", "get-default-sink").strip())
    problem = None
    if mode != "other":
        # A nonblocking lock keeps the icon responsive while a click is in progress.
        try:
            with route_lock(block=False) as acquired:
                if acquired:
                    mode = output_mode(devices, run("pactl", "get-default-sink").strip())
                    if mode != "other":
                        sync_reaper(mode)
        except RouteError as exc:
            problem = str(exc)
    labels = {
        "headphones": (HEADPHONES, "Headphones / calls\nNormal audio → G-Track headphones.\n"
                       "REAPER → headphones + Piano + Mic Mix.\nClick for speakers.\n"
                       "Meet captures the mix only when its microphone is set to that monitor."),
        "speakers": (SPEAKERS, "Speakers\nNormal audio and REAPER → Audigy.\n"
                     "REAPER is not sent to the call mix.\nClick for headphones / calls."),
        "other": (SPEAKERS, "Another output is selected.\nClick for G-Track headphones / calls."),
    }
    text, tooltip = labels[mode]
    if problem:
        tooltip += f"\nREAPER routing error: {problem}"
    return {"text": text, "tooltip": tooltip, "class": "error" if problem else mode}


def switch(graph, target):
    """Connect first; on failure undo new links and preserve the original route."""
    wanted = graph.pairs(target)
    # Also remove direct G-Track connections made by REAPER's JACK auto-connect.
    unwanted = graph.primary_links() - wanted
    added = set()
    try:
        for output, input_port in sorted(wanted - graph.links):
            run("pw-link", str(output), str(input_port))
            added.add((output, input_port))
        if not wanted <= Graph.current().links:
            raise RouteError("The new stereo connection did not become available")
    except RouteError:
        for output, input_port in added:
            try:
                run("pw-link", "-d", str(output), str(input_port))
            except RouteError:
                pass
        raise
    for output, input_port in sorted(unwanted):
        run("pw-link", "-d", str(output), str(input_port))
    if Graph.current().mode() != target:
        raise RouteError("Routing changed unexpectedly; check the button's current status")


def select_mode(mode, devices):
    target = physical_sink(devices, mode)
    previous_default = run("pactl", "get-default-sink").strip()
    streams = movable_streams(devices, target)
    graph = Graph.current()
    route = "mix" if mode == "headphones" else "audigy"
    previous_links = None
    # Validate before changing anything. REAPER may be closed.
    if graph.reaper() is not None:
        graph.pairs(route)
        previous_links = graph.primary_links()
    moved = []
    try:
        if previous_links is not None:
            switch(graph, route)
        run("pactl", "set-default-sink", target["name"])
        for stream in streams:
            try:
                run("pactl", "move-sink-input", str(stream["index"]), target["name"])
                moved.append(stream)
            except RouteError:
                # Apps may close a stream between listing and moving it.
                current = json.loads(run("pactl", "-f", "json", "list", "sink-inputs"))
                if any(item["index"] == stream["index"] for item in current):
                    raise
    except RouteError:
        for stream in moved:
            try:
                run("pactl", "move-sink-input", str(stream["index"]), str(stream["sink"]))
            except RouteError:
                pass
        try:
            run("pactl", "set-default-sink", previous_default)
            if previous_links is not None:
                current = Graph.current()
                active = current.primary_links()
                for output, input_port in sorted(previous_links - active):
                    run("pw-link", str(output), str(input_port))
                for output, input_port in sorted(active - previous_links):
                    run("pw-link", "-d", str(output), str(input_port))
        except RouteError:
            pass
        raise


def toggle():
    with route_lock():
        devices = sinks()
        current = output_mode(devices, run("pactl", "get-default-sink").strip())
        select_mode("speakers" if current == "headphones" else "headphones", devices)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        if command == "toggle":
            toggle()
        elif command == "status":
            print(json.dumps(status(), ensure_ascii=False))
        else:
            raise RouteError("Usage: reaper-route.py [status|toggle]")
    except RouteError as exc:
        if command == "status":
            print(json.dumps({"text": SPEAKERS, "tooltip": str(exc), "class": "error"}))
        else:
            print(str(exc), file=sys.stderr)
            if shutil.which("notify-send"):
                try:
                    run("notify-send", "Audio output mode", str(exc))
                except RouteError:
                    pass
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
