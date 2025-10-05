# Chromobius: color code decoder

Chromobius is an implementation of a ["mobius decoder"](https://arxiv.org/abs/2108.11395), which approximates the color code decoding problem as a minimum weight matching problem.
Chromobius uses [PyMatching](https://github.com/oscarhiggott/PyMatching/) to solve the minimum weight matching problem.

See the paper ["New circuits and an open source decoder for the color code"](https://arxiv.org/abs/2312.08813) for more details on how Chromobius works.

## How to use Chromobius

See the [**getting started notebook**](doc/getting_started.ipynb).

Also see the [Python API reference](doc/chromobius_api_reference.md).

Programmers who want to edit and build Chromobius can check the [developer documentation](doc/developers.md).

## Example Snippets

### Decoding a shot with Chromobius

From Python:

```python
import stim
import chromobius
import numpy as np

def count_mistakes(circuit: stim.Circuit, shots: int) -> int:
    # Sample the circuit.
    dets, actual_obs_flips = circuit.compile_detector_sampler().sample(
        shots=shots,
        separate_observables=True,
        bit_packed=True,
    )

    # Decode with Chromobius.
    decoder = chromobius.compile_decoder_for_dem(circuit.detector_error_model())
    predicted_obs_flips = decoder.predict_obs_flips_from_dets_bit_packed(dets)

    # Count mistakes.
    return np.count_nonzero(np.any(predicted_obs_flips != actual_obs_flips, axis=1))
```

From the command line:

```bash
# Sample shots of detectors and observable flips.
stim detect \
    --shots 100000 \
    --in "example_circuit.stim" \
    --out "dets.b8" \
    --out_format "b8" \
    --obs_out "obs_actual.txt" \
    --obs_out_format "01"

# Extract a detector error model used to configure Chromobius.
stim analyze_errors \
    --in "example_circuit.stim" \
    --fold_loops \
    --out "dem.dem"

# Decode the shots.
chromobius predict \
    --dem "dem.dem" \
    --in "dets.b8" \
    --in_format "b8" \
    --out "obs_predicted.txt" \
    --out_format "01"

# Count the number of shots with a prediction mistake.
paste obs_actual.txt obs_predicted.txt \
    | grep -Pv "^([01]*)\\s*\\1$" \
    | wc -l
```

From Python using sinter:

```python
import sinter
import chromobius
import os

tasks: list[sinter.Task] = ...
stats: list[sinter.TaskStats] = sinter.collect(
    decoders=["chromobius"],
    custom_decoders=chromobius.sinter_decoders(),
    tasks=tasks,
    num_workers=os.cpu_count(),
    max_shots=100_000,
    max_errors=100,
)
```

From the command line using sinter:

```bash
sinter collect \
    --circuits "example_circuit.stim" \
    --decoders chromobius \
    --custom_decoders_module_function "chromobius:sinter_decoders" \
    --max_shots 100_000 \
    --max_errors 100
    --processes auto \
    --save_resume_filepath "stats.csv" \
```

## Disclaimer

This is not an officially supported Google product. This project is not
eligible for the [Google Open Source Software Vulnerability Rewards
Program](https://bughunters.google.com/open-source-security).

Copyright 2025 Google LLC.
