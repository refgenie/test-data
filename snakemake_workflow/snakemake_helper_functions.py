import os
from refgenie.asset_build_packages import *
from typing import Dict


INPUT_TEMPLATE = os.path.join(
    os.environ.get("REFGENIE_RAW"), "{genome}-{asset}-{input_id}"
)

# some asset dependacies in the reciepes have different names than the
# actual recipe names, we need to add them to the alias list
ASSET_ALIASES = {"esa": "suffixerator_index", "gtf": "gencode_gtf"}


def get_req_by_asset(req_type):
    return {
        asset: [req[KEY] for req in asset_recipe[req_type]]
        for asset, asset_recipe in asset_build_packages.items()
    }


def get_req_assets_by_asset():
    return get_req_by_asset(req_type=REQ_ASSETS)


def get_req_files_by_asset():
    return get_req_by_asset(req_type=REQ_FILES)


def get_input_templates(wildcards, asset=None):
    a = asset or wildcards.asset
    if isinstance(a, str):
        a = [a]
    nested_list = [
        [
            INPUT_TEMPLATE.format(genome=wildcards.genome, asset=a, input_id=file_id)
            for file_id in get_req_files_by_asset()[a]
        ]
        for a in a
    ]
    return [item for sublist in nested_list for item in sublist]


def get_asset_file_spec(wildcards, asset=None):
    return [
        "{}={}".format(
            file_id,
            INPUT_TEMPLATE.format(
                genome=wildcards.genome,
                asset=asset or wildcards.asset,
                input_id=file_id,
            ),
        )
        for file_id in get_req_files_by_asset()[asset or wildcards.asset]
    ]


def get_pep_intersect_for_genome(genome, recipe_list, project, exclusion_list=[]):
    genome_samples = [sample for sample in project.samples if sample.genome == genome]
    # this assumes that there is a 1:1 mapping between asset and recipe names
    # this is the case for now, but in the future we may want to use asset classes somehow
    return [
        sample.asset
        for sample in genome_samples
        if sample.asset in recipe_list and sample.asset not in exclusion_list
    ]


def resolve_dependancies(reqs_dict, asset_aliases=ASSET_ALIASES):
    """
    Resolve asset build dependancies

    :param Dict[str, Iterable[str]] reqs_dict: a dependency dictionary in which the values
        are the dependencies of their respective keys.
    :return List[Set[str]]: a list of sets that represet the build order
    """

    def _resolve_alias(asset_names):
        """
        Attempt to resolve an asset name to a known alias

        :param Iterable[str] | str asset_names: the asset names to resolve
        :return Iterable[str] | str: the resolved asset names
        """
        if isinstance(asset_names, str):
            return (
                asset_aliases[asset_names]
                if asset_names in asset_aliases
                else asset_names
            )
        if not isinstance(asset_names, list):
            asset_names = [asset_names]
        return [
            asset_aliases[asset_name] if asset_name in asset_aliases else asset_name
            for asset_name in asset_names
        ]

    # convert the lists to sets, to make sure that we don't have any duplicates, and resolve aliases
    reqs_dict_set = {
        _resolve_alias(k): set(_resolve_alias(v)) for k, v in reqs_dict.items()
    }
    build_groups = []
    while reqs_dict_set:
        # values not in keys, assets without depenencies
        build_group = set(i for v in reqs_dict_set.values() for i in v) - set(
            reqs_dict_set.keys()
        )
        # and keys without value, assets without depenencies
        build_group.update(k for k, v in reqs_dict_set.items() if not v)
        build_groups.append(build_group)
        # remove the completed items
        reqs_dict_set = {k: v - build_group for k, v in reqs_dict_set.items() if v}
    return build_groups


def get_build_resources(asset: str, genome: str) -> Dict[str, str]:
    """
    COPIED FROM 'pipeline_interfaces/build_compute_params.py'

    Get the build parameters for the given asset and genome.

    :param str asset: The asset to get the build parameters for.
    :param str genome: The genome to get the build parameters for.
    :return Dict[str, str]: A dictionary of build parameters.
    """

    compute = {
        "bulker_crate": "databio/refgenie:0.7.7",
        "mem": "24000",
        "cores": "1",
        "partition": "largemem",
        "time": "04:00:00",
    }

    # These are ones that go quick
    fast_assets = [
        "fasta",
        "gencode_gtf",
        "ensembl_gtf",
        "ensembl_rb",
        "feat_annotation",
        "refgene_anno",
        "fasta_txome",
    ]

    slow_assets = ["bismark_bt2_index", "bismark_bt1_index", "salmon_partial_sa_index"]

    if asset in fast_assets:
        compute["time"] = "01:00:00"
        compute["partition"] = "standard"
        compute["mem"] = "6000"
        if genome == "Picea_abies__ConGenIE_v1_0":
            compute["time"] = "08:00:00"
            compute["mem"] = "24000"

    if asset in slow_assets:
        compute["time"] = "8:00:00"

    if asset == "suffixerator_index":
        compute["mem"] = "32000"

    if asset == "bowtie2_index":
        compute["mem"] = "64000"

    if asset == "bismark_bt2_index":
        compute["mem"] = "64000"

    if asset == "bismark_bt1_index":
        compute["mem"] = "64000"

    if asset == "salmon_partial_sa_index":
        compute["mem"] = "112000"
        compute["time"] = "6:00:00"
        compute["cores"] = "8"

    if asset == "dbnsfp":
        compute["time"] = "12:00:00"

    if asset == "salmon_sa_index":
        compute["mem"] = "72000"

    if asset == "star_index":
        compute["mem"] = "64000"

    return compute



def get_build_resources_wrapper(
    wildcards, attempt=None, threads=None, force_asset=None
):
    """
    Wrapper for get_build_resources to allow for dynamic resource selection
    """
    return get_build_resources(
        asset=force_asset or wildcards.asset, genome=wildcards.genome
    )
