# NRP nodes

## Node name, region and zone info

Nodes information can be collected via `kubectl` utility and saved as a JSON file:

    kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone -o json > allnodes.kubectl.json

Then we can extract name, region and zone into a CSV file:

    cat allnodes.kubectl.json | \
    jq -r '.items[] | .metadata.name, .metadata.labels["topology.kubernetes.io/region"], .metadata.labels["topology.kubernetes.io/zone"]' | \
    paste -d'\t' - - - > allnodes.kubectl.tsv

## Node gps info
The JSON data is retrieved from [this dashboard portal](https://elastic-igrok.nrp-nautilus.io/app/discover#/) by following these steps:
1. Change index pattern from `metrics-*` to `nodes-*`
1. Change dates range to "Last 1 day"
1. Click on "Inspect", "Response" and then save as a JSON file, i.e. `allnodes.gps.json`.

We can then extracte name, latitude and longitude into a CSV file:

    cat allnodes.gps.json | \
    jq --raw-output '.rawResponse.hits.hits[] | .fields["name"][0], .fields["location"][0]["coordinates"][1], .fields["location"][0]["coordinates"][0]' | \
    paste -d'\t' - - - > allnodes.gps.tsv

## Combined info

Finally, we can join these two files:

    LANG=en_EN && \ # Needed for sort order to be consistent across join and sort
    join -t $'\t' -o auto <(sort allnodes.kubectl.tsv) <(sort allnodes.gps.tsv) > \
    allnodes.region.gps.tsv

We can then transform this into a yaml file and feed it to the API:

    preamble='---
    public_clouds:
    - provider: NRP
      regions:'
    awk -F '\t' -v preamble="$preamble" '
    BEGIN {
        print preamble
    }
    {
      printf "  - code: %s:%s\n", $2, $3
      printf "    name: %s\n", $1
      printf "    gps:\n"
      printf "    - %f\n", $4
      printf "    - %f\n", $5
    }' allnodes.region.gps.tsv > cloud_locations.nrp.yaml

TODO: Need to de-duplicate this data as this is based on node name
