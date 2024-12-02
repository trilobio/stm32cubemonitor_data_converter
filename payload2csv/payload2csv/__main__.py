"""Main CLI entry point for the payload2csv tool."""
import csv
import json
import logging
import pathlib
import re
from tkinter.filedialog import askopenfilename

import plac

logger = logging.getLogger("payload2csv")


def find_variablenames(payload: list[str]) -> list[str]:
    """Get all variable names from a payload."""
    varnames: list[str] = []
    line_idx = 0
    while True:
        varname = re.findall(r'"variablename":"([a-zA-Z0-9_]+)"', payload[line_idx])
        line_idx += 1
        if line_idx > len(payload) or any(v in varnames for v in varname):
            break

        varnames.extend(varname)

    return varnames


def payload_to_csv(payload_in: pathlib.Path, csv_out: pathlib.Path) -> None:
    """Convert msg.payload blob to csv blob."""
    with payload_in.open("r") as f:
        lines = f.readlines()
    
    varnames = find_variablenames(lines)
    logger.info("Found variable names: %s", varnames)

    # Parse payload into data_out
    data_out: dict[float, dict[str, int]] = {}
    for line_no, line in enumerate(lines):
        try:
            line_data = json.loads(line)
            x, y = line_data["variabledata"][0]["x"], line_data["variabledata"][0]["y"]
            name = line_data["variablename"]
            if x not in data_out:
                data_out[x] = {}

            data_out[x][name] = y

        except Exception as e:
            logger.error("Failed to parse line %s with err %s: '%s'", line_no, repr(e), line)
            pass

    # Write data_out to csv_out
    with csv_out.open("w") as f:
        csv_writer = csv.DictWriter(f, fieldnames=["x", *varnames])
        csv_writer.writeheader()
        for x, row in data_out.items():
            row["x"] = x
            csv_writer.writerow(row)


@plac.annotations(
    input_file=("Input payload file", "positional", None, pathlib.Path),
    output_file=("Output CSV file", "positional", None, pathlib.Path),
    log_level=("Log level", "option", "l", int),
)
def main(input_file: pathlib.Path | None = None, output_file: pathlib.Path | None = None, log_level: int = logging.INFO) -> None:
    """Convert a payload file to a CSV file."""
    h = logging.StreamHandler()
    f = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    h.setFormatter(f)
    logger.addHandler(h)
    logger.setLevel(log_level)

    if input_file is None:
        while True:
            input_file = pathlib.Path(askopenfilename(
                title="Select a payload file",
                initialdir=pathlib.Path("~").expanduser(),
                filetypes=[("Payload files", "*.payload"), ("All files", "*.*")],
            ))
            if input_file.exists():
                break

    if output_file is None:
        output_file = input_file.with_suffix(".csv")
        logger.info("No output file specified, writing to %s", output_file)

    blob = payload_to_csv(input_file, output_file)


plac.call(main)
