# SKY130 timing data

This directory contains the SKY130 HD TT 25°C, 1.8 V Liberty used by the
examples, the common/cell Liberty JSON tables, and fixed-condition timing
extraction scripts. The library and tables are third-party SKY130 data;
they are not original project measurements.

Upstream library: https://github.com/google/skywater-pdk-libs-sky130_fd_sc_hd

The upstream Apache-2.0 license is preserved in `LICENSE.upstream`. It applies
to the upstream library data; this notice does not relicense the rest of this repository.
The archived input manifests and timing JSON files record hashes of the actual
library/table bytes used by this project. An upstream URL identifies the source
project, not a claim that these generated Liberty bytes equal its current HEAD.

From the repository root:

```bash
python3 sky130_pdk/extract_latch_timing.py --help
python3 -m unittest discover -s sky130_pdk -p 'test_extract_latch_timing.py'
```

`latch_timing.json` is a scalar characterization example at its recorded
slew/load. For the real three-latch circuit, use
`examples/tiny_sky130/latch_timing.json`, which contains per-instance values,
pulse checks, real IO budgets and STA operating conditions.
