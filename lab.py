from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

PHASES = ["Taxi", "Take-off Run", "Departure", "Climb", "En Route", "Descent", "Approach", "Landing Roll"]
GROUND_PHASES = ["Taxi", "Take-off Run", "Landing Roll"]
SIZES = ["Small", "Medium", "Large"]
STRIKE_GROUPS = ["Single", "Multiple"]
LEVELS = ["Unspecified", "Minor", "Substantial", "Destroyed"]
_RULES = [
    ("Bats", r"\bbats?\b|microbats|pipistrelle|myotis|serotine|noctule|vespertilionid"),
    ("Vultures", r"vulture"),
    ("Reptiles", r"turtle|snake|tortoise|iguana|alligator|terrapin|lizard|pond slider"),
    # Use word boundaries: 'Killdeer' is a bird, not a deer.
    ("Land mammals", r"\bdeer\b|coyote|fox|rabbit|cottontail|skunk|opossum|raccoon|woodchuck|prairie dog|squirrel|armadillo|porcupine|muskrat|\bcat\b|\bdog\b|mongoose|\bmammal\b|\belk\b|bobcat|beaver|swine|\bpigs?\b|marmot|\brats?\b|weasel|peccary|\bhares?\b|canid"),
    ("Doves & pigeons", r"dove|pigeon"),
    ("Swifts & swallows", r"swallow|swift|martin|nighthawk|nightjar|poorwill|pauraque|chuck-will|hummingbird"),
    ("Gulls & shorebirds", r"gull|\btern|plover|sandpiper|killdeer|snipe|curlew|dunlin|sanderling|phalarope|yellowlegs|stilt|avocet|willet|turnstone|dowitcher|woodcock|whimbrel|shorebird|skimmer|noddy|lapwing"),
    ("Waterfowl", r"duck|goose|geese|swan|mallard|teal|pintail|wigeon|gadwall|scaup|merganser|bufflehead|canvasback|redhead|goldeneye|brant|shoveler|\bcoot\b|grebe|\bloon\b|cormorant|pelican"),
    ("Waders", r"heron|egret|ibis|crane|bittern|stork|\brail\b|\bsora\b|anhinga"),
    ("Raptors & owls", r"hawk|eagle|falcon|kestrel|harrier|osprey|kite|merlin|caracara|\bowl\b|raptor"),
    ("Songbirds", r"sparrow|warbler|thrush|finch|lark|starling|robin|blackbird|grackle|wren|vireo|flycatcher|kingbird|phoebe|pewee|kinglet|bunting|pipit|junco|towhee|munia|waxbill|oriole|tanager|\bjay\b|crow|raven|cowbird|bobolink|waxwing|catbird|thrasher|mockingbird|bluebird|nuthatch|longspur|siskin|redpoll|grosbeak|shrike|magpie|myna|drongo|dickcissel|redstart|yellowthroat|ovenbird|veery|creeper|perching|woodpecker|sapsucker|flicker|cuckoo|bulbul|silverbill"),
]


def group_of(species: str) -> str:
    s = str(species).lower()
    if "unknown" in s or s == "not recorded":
        return "Unidentified"
    for name, pattern in _RULES:
        if re.search(pattern, s):
            return name
    return "Other"


def add_group(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["GROUP"] = result["SPECIES"].map(group_of)
    return result


def lab_payload(df: pd.DataFrame) -> dict:
    """Exact, observed data. Heatmap rates: phase×size×strike count (all species).

    Selected scenario rate: exact species×phase×size×strike count.
    Impact location and animation are illustrative, not recorded in the cleaned CSV.
    """
    data = df.copy()
    known = data.loc[~data["SPECIES"].astype(str).str.contains("Unknown", case=False, na=False)
                     & data["SPECIES"].ne("Not recorded")].copy()
    known = known[known["PHASE_OF_FLIGHT"].isin(PHASES)
                  & known["SIZE"].isin(SIZES)
                  & known["STRIKE_GROUP"].isin(STRIKE_GROUPS)]
    species_names = sorted(known["SPECIES"].dropna().unique().tolist(), key=str.casefold)
    species_groups = {name: group_of(name) for name in species_names}

    # Exact records for the four-dimensional scenario. No made-up probabilities.
    cross = (known.groupby(["SPECIES", "PHASE_OF_FLIGHT", "SIZE", "STRIKE_GROUP"])["INDICATED_DAMAGE"]
             .agg(["count", "sum"]).reset_index())
    cells: dict[str, list[int]] = {}
    for r in cross.itertuples(index=False):
        cells[f"{r.SPECIES}|{r.PHASE_OF_FLIGHT}|{r.SIZE}|{r.STRIKE_GROUP}"] = [int(r.count), int(r.sum)]

    # A short, context-dependent list replaces the hundreds of species shown before.
    # Rank by actual number of records in the selected phase × size × strike group.
    # Keep both well-sampled and less common combinations usable if records exist.
    options_by_cell = {}
    preferred_by_cell = {}
    for (phase, size, group), part in cross.groupby(["PHASE_OF_FLIGHT", "SIZE", "STRIKE_GROUP"]):
        part = part.sort_values(["count", "SPECIES"], ascending=[False, True])
        if phase not in GROUND_PHASES:
            part = part.loc[~part["SPECIES"].map(lambda sp: group_of(sp) in {"Land mammals", "Reptiles"})]
        if part.empty:
            continue
        sample = part.loc[part["count"] >= 10].head(12)
        # If no species meets the display threshold, still allow exploring an
        # observed small-sample cell, rather than showing a mysterious disabled button.
        if sample.empty:
            sample = part.head(8)
        names = sample["SPECIES"].tolist()
        key = f"{phase}|{size}|{group}"
        options_by_cell[key] = names
        preferred_by_cell[key] = names[0]

    # Heatmap uses ALL matching FAA reports (including unidentified wildlife).
    # This preserves the original Size × Phase aggregation from the EDA while
    # Single/Multiple remains an explicit active selection.
    heat_data = data[
        data["PHASE_OF_FLIGHT"].isin(PHASES)
        & data["SIZE"].isin(SIZES)
        & data["STRIKE_GROUP"].isin(STRIKE_GROUPS)
    ]
    heat_rows = (heat_data.groupby(["PHASE_OF_FLIGHT", "SIZE", "STRIKE_GROUP"])["INDICATED_DAMAGE"]
                 .agg(["count", "sum"]).reset_index())
    heat = {}
    for r in heat_rows.itertuples(index=False):
        key = f"{r.PHASE_OF_FLIGHT}|{r.SIZE}|{r.STRIKE_GROUP}"
        heat[key] = [int(r.count), int(r.sum)]

    # Damage-level distribution is based on the SPECIES' damaging reports (not substituted
    # from unrelated species). Missing damage severity is explicitly Unspecified.
    lv = {"M?": 0, "M": 1, "S": 2, "D": 3}
    damaged = known.loc[known["INDICATED_DAMAGE"].eq(1)].copy()
    damaged["_level"] = damaged["DAMAGE_LEVEL"].map(lv).fillna(0).astype(int)
    distributions = {}
    for species, part in damaged.groupby("SPECIES"):
        count = part["_level"].value_counts().reindex(range(4), fill_value=0).to_list()
        distributions[species] = count
    # Default example: a frequently reported, visually recognizable species.
    preferred = "Mourning dove" if "Mourning dove" in species_names else (species_names[0] if species_names else "")
    return {
        "species": species_names,
        "speciesGroup": species_groups,
        "phases": PHASES,
        "groundPhases": GROUND_PHASES,
        "sizes": SIZES,
        "groups": STRIKE_GROUPS,
        "cells": cells,
        "heat": heat,
        "best": preferred_by_cell,
        "optionsByCell": options_by_cell,
        "severity": distributions,
        "levels": LEVELS,
        "defaultSpecies": preferred,
    }


def build_lab_html(payload: dict) -> str:
    template = (Path(__file__).parent / "simulator.html").read_text(encoding="utf-8")
    return template.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
