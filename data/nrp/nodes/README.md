# NRP nodes

Nodes information can be collected via `kubectl` utility.
A list of nodes snapshot is stored in the `.txt` files, and node GPS information is stored in the `.json` files.

The JSON data is retrieved from [this dashboard portal](https://elastic-igrok.nrp-nautilus.io/app/discover#/) by following these steps:
1. Change index pattern from `metrics-*` to `nodes-*`
1. Change dates range to "Last 1 day"
1. Click on "Inspect", "Response" and then copy to clipboard.
