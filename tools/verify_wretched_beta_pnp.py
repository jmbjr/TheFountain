#!/usr/bin/env python3
"""Verify a generated Wretched Beta PnP PDF against its resolved target manifest."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


def fail(message: str) -> None:
    raise SystemExit(f"PnP verification failed: {message}")


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def included(entry: dict) -> bool:
    return entry.get("inclusion") != "excluded-override" and entry.get("resolved_quantity", 0) > 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    manifest_path = Path(args.manifest)
    if not pdf_path.is_file():
        fail(f"missing PDF: {pdf_path}")
    if not manifest_path.is_file():
        fail(f"missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text())
    if manifest.get("target") != "pnp":
        fail(f"expected pnp target, got {manifest.get('target')!r}")
    if manifest.get("dodge_identity", {}).get("dodge_version") != "0.2.1":
        fail("manifest is not DODGE 0.2.1")

    contents = manifest.get("contents") or []
    by_id = {entry["content_id"]: entry for entry in contents}
    if len(by_id) != len(contents):
        fail("manifest contains duplicate content_id values")

    reader = PdfReader(str(pdf_path))
    if len(reader.pages) < 2:
        fail("generated PDF is unexpectedly short")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    flat = compact(text)

    required_text = [
        args.git_sha[:12],
        "CONTENTS",
        "DODGE DIAGNOSTIC",
        "NONCANONICAL PLAYTEST",
    ]
    for marker in required_text:
        if compact(marker) not in flat:
            fail(f"PDF text is missing required marker {marker!r}")

    scene_prefix = "scene/scenario-01-the-cave/instance/"
    required_collections = [
        "crew-reference-cards-1",
        "captain-starter-deck-1",
        "security-starter-deck-1",
        "engineer-starter-deck-1",
        "medic-starter-deck-1",
        "scout-starter-deck-1",
        "scenario-room-cards-1",
        "scenario-encounter-cards-1",
        "scenario-salvage-cards-1",
        "enemy-reference-cards-1",
    ]
    for instance_id in required_collections:
        parent_id = scene_prefix + instance_id
        parent = by_id.get(parent_id)
        if not parent or not included(parent):
            fail(f"required semantic collection missing from manifest: {instance_id}")
        children = [
            entry
            for entry in contents
            if entry.get("parent_content_id") == parent_id and included(entry)
        ]
        if not children:
            fail(f"semantic collection has no included members: {instance_id}")
        if compact(instance_id) not in flat:
            fail(f"PDF diagnostic contents omit semantic collection {instance_id}")

    required_leaf_ids = [
        scene_prefix + "scenario-token-supply-1/member/0",
        scene_prefix + "scenario-token-supply-1/member/1",
        *[
            scene_prefix + f"enemy-token-supply-1/member/{i}"
            for i in range(5)
        ],
        "representation/health-unit-tokens/component/0",
        "representation/health-numbered-track/component/0",
        "representation/health-numbered-track/component/1",
        "representation/health-crew-card-marker/component/0",
        "representation/health-crew-card-marker/component/1",
    ]
    for content_id in required_leaf_ids:
        entry = by_id.get(content_id)
        if not entry or not included(entry):
            fail(f"required printable leaf missing from manifest: {content_id}")

    noncanonical = [
        entry
        for entry in contents
        if included(entry)
        and any(
            d.get("classification") == "noncanonical-playtest"
            for d in entry.get("diagnostics", [])
        )
    ]
    if not noncanonical:
        fail("manifest does not expose any noncanonical playtest quantities")

    # The exporter renders these supply labels directly from the manifest-backed
    # quantities. Text counts are intentionally lower-bound checks because the
    # same label may also appear in rules/reference prose.
    supply_labels = {
        scene_prefix + "enemy-token-supply-1/member/0": "Small Spider",
        scene_prefix + "enemy-token-supply-1/member/1": "Large Spider",
        scene_prefix + "enemy-token-supply-1/member/2": "Alpha Spider",
        scene_prefix + "enemy-token-supply-1/member/3": "Brood Mother",
        scene_prefix + "enemy-token-supply-1/member/4": "Men of Leng Servant",
        scene_prefix + "scenario-token-supply-1/member/0": "Spider Corpse",
        scene_prefix + "scenario-token-supply-1/member/1": "Chrysalis",
    }
    for content_id, label in supply_labels.items():
        expected = by_id[content_id]["resolved_quantity"]
        observed = text.count(label)
        if observed < expected:
            fail(
                f"PDF contains fewer {label!r} labels than manifest quantity "
                f"({observed} < {expected})"
            )

    print(
        f"PnP verification passed: {pdf_path.name} matches manifest "
        f"{manifest.get('manifest_id')} with {len(reader.pages)} pages."
    )


if __name__ == "__main__":
    main()
