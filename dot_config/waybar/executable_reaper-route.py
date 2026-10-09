#!/usr/bin/python3
"""Switch only REAPER's first stereo JACK output between the mix and Audigy.

The mix destination is piano-out, which already feeds piano-mix and headphones.
State is read from PipeWire, not a saved flag. No daemon or JACK wrapper is needed.
"""

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

    def mode(self):
        if self.reaper() is None:
            return "stopped"
        active = {mode: self.existing_pairs(mode) for mode in ("mix", "audigy")}
        if len(active["mix"]) == 2 and not active["audigy"]:
            return "mix"
        if len(active["audigy"]) == 2 and not active["mix"]:
            return "audigy"
        return "other"


def status(graph):
    mode = graph.mode()
    labels = {
        "mix": ("♫ Mix", "REAPER → Piano + Mic Mix, via Piano Output.\n"
                "You hear it in G-Track headphones.\nClick to send REAPER to Audigy instead.\n"
                "Meet microphone must be Monitor of Piano + Mic Mix to share it."),
        "audigy": ("♫ Audigy", "REAPER → Audigy (not sent to the piano call mix).\n"
                   "Click to send REAPER to Piano + Mic Mix and G-Track headphones."),
        "stopped": ("♫ REAPER off", "Open REAPER, then click to choose its audio destination."),
        "other": ("♫ Route?", "REAPER has partial, mixed, or different routing.\n"
                  "Click to route its first stereo output to Piano + Mic Mix."),
    }
    text, tooltip = labels[mode]
    return {"text": text, "tooltip": tooltip, "class": mode}


def switch(graph, target):
    """Connect first; on failure undo new links and preserve the original route."""
    wanted = graph.pairs(target)
    opposite = "audigy" if target == "mix" else "mix"
    unwanted = graph.existing_pairs(opposite)
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


def toggle():
    # Runtime-only lock prevents overlapping clicks; nothing is saved in dotfiles.
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    with (runtime / "waybar-reaper-route.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        graph = Graph.current()
        target = "audigy" if graph.mode() == "mix" else "mix"
        switch(graph, target)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        if command == "toggle":
            toggle()
        elif command == "status":
            print(json.dumps(status(Graph.current()), ensure_ascii=False))
        else:
            raise RouteError("Usage: reaper-route.py [status|toggle]")
    except RouteError as exc:
        if command == "status":
            print(json.dumps({"text": "♫ Route!", "tooltip": str(exc), "class": "error"}))
        else:
            print(str(exc), file=sys.stderr)
            if shutil.which("notify-send"):
                try:
                    run("notify-send", "REAPER routing", str(exc))
                except RouteError:
                    pass
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
