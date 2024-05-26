import json
from typing import Any, Optional, Protocol

import torch
from huggingface_hub import hf_hub_download
from safetensors import safe_open


# loaders take in a repo_id, folder_name, device, and whether to force download, and returns a tuple of config and state_dict
class PretrainedSaeLoader(Protocol):

    def __call__(
        self,
        repo_id: str,
        folder_name: str,
        device: str | torch.device | None = None,
        force_download: bool = False,
    ) -> tuple[dict[str, Any], dict[str, torch.Tensor]]: ...


def sae_lens_loader(
    repo_id: str,
    folder_name: str,
    device: Optional[str] = None,
    force_download: bool = False,
) -> tuple[dict[str, Any], dict[str, torch.Tensor]]:
    cfg_filename = f"{folder_name}/cfg.json"
    cfg_path = hf_hub_download(
        repo_id=repo_id, filename=cfg_filename, force_download=force_download
    )

    weights_filename = f"{folder_name}/sae_weights.safetensors"
    sae_path = hf_hub_download(
        repo_id=repo_id, filename=weights_filename, force_download=force_download
    )
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    return load_pretrained_sae_lens_sae_components(cfg_path, sae_path, device)


def connor_rob_hook_z_loader(
    repo_id: str,
    folder_name: str,
    device: Optional[str] = None,
    force_download: bool = False,
) -> tuple[dict[str, Any], dict[str, torch.Tensor]]:

    file_path = hf_hub_download(
        repo_id=repo_id, filename=folder_name, force_download=force_download
    )
    config_path = folder_name.split(".pt")[0] + "_cfg.json"
    config_path = hf_hub_download(repo_id, config_path)
    old_cfg_dict = json.load(open(config_path, "r"))

    weights = torch.load(file_path, map_location=device)
    # weights_filename = f"{folder_name}/sae_weights.safetensors"
    # sae_path = hf_hub_download(
    #     repo_id=repo_id, filename=weights_filename, force_download=force_download
    # )
    # if device is None:
    #     device = "cuda" if torch.cuda.is_available() else "cpu"

    # return load_pretrained_sae_lens_sae_components(cfg_path, sae_path, device)

    # old_cfg_dict = {
    #     "seed": 49,
    #     "batch_size": 4096,
    #     "buffer_mult": 384,
    #     "lr": 0.0012,
    #     "num_tokens": 2000000000,
    #     "l1_coeff": 1.8,
    #     "beta1": 0.9,
    #     "beta2": 0.99,
    #     "dict_mult": 32,
    #     "seq_len": 128,
    #     "enc_dtype": "fp32",
    #     "model_name": "gpt2-small",
    #     "site": "z",
    #     "layer": 0,
    #     "device": "cuda",
    #     "reinit": "reinit",
    #     "head": "cat",
    #     "concat_heads": True,
    #     "resample_scheme": "anthropic",
    #     "anthropic_neuron_resample_scale": 0.2,
    #     "dead_direction_cutoff": 1e-06,
    #     "re_init_every": 25000,
    #     "anthropic_resample_last": 12500,
    #     "resample_factor": 0.01,
    #     "num_resamples": 4,
    #     "wandb_project_name": "gpt2-L0-20240117",
    #     "wandb_entity": "ckkissane",
    #     "save_state_dict_every": 50000,
    #     "b_dec_init": "zeros",
    #     "sched_type": "cosine_warmup",
    #     "sched_epochs": 1000,
    #     "sched_lr_factor": 0.1,
    #     "sched_warmup_epochs": 1000,
    #     "sched_finish": True,
    #     "anthropic_resample_batches": 100,
    #     "eval_every": 1000,
    #     "model_batch_size": 512,
    #     "buffer_size": 1572864,
    #     "buffer_batches": 12288,
    #     "act_name": "blocks.0.attn.hook_z",
    #     "act_size": 768,
    #     "dict_size": 24576,
    #     "name": "gpt2-small_0_24576_z",
    # }

    cfg_dict = {
        "d_in": old_cfg_dict["act_size"],
        "d_sae": old_cfg_dict["dict_size"],
        "dtype": "float32",
        "device": device if device is not None else "cpu",
        "model_name": "gpt2-small",
        "hook_point": old_cfg_dict["act_name"],
        "hook_point_layer": old_cfg_dict["layer"],
        "hook_point_head_index": None,
        "activation_fn_str": "relu",
        "apply_b_dec_to_input": True,
        "uses_scaling_factor": False,
        "sae_lens_training_version": None,
        "prepend_bos": True,
        "dataset_path": "apollo-research/Skylion007-openwebtext-tokenizer-gpt2",
        "context_size": 128,
        "normalize_activations": False,
    }

    return cfg_dict, weights


def load_pretrained_sae_lens_sae_components(
    cfg_path: str,
    weight_path: str,
    device: str = "cpu",
    dtype: str = "float32",
) -> tuple[dict[str, Any], dict[str, torch.Tensor]]:
    with open(cfg_path, "r") as f:
        config = json.load(f)

    # filter config for varnames
    config["device"] = device
    config["dtype"] = dtype

    # # # Removing this since we should add it during instantiation of the SAE, not the SAE config.
    # # TODO: if we change our SAE implementation such that old versions need conversion to be
    # # loaded, we can inspect the original "sae_lens_version" and apply a conversion function here.
    # config["sae_lens_version"] = __version__

    # check that the config is valid
    for key in ["d_sae", "d_in", "dtype"]:
        assert key in config, f"config missing key {key}"

    tensors = {}
    with safe_open(weight_path, framework="pt", device=device) as f:  # type: ignore
        for k in f.keys():
            tensors[k] = f.get_tensor(k)

    return config, tensors


# TODO: add more loaders for other SAEs not trained by us

NAMED_PRETRAINED_SAE_LOADERS: dict[str, PretrainedSaeLoader] = {
    "sae_lens": sae_lens_loader,  # type: ignore
    "connor_rob_hook_z": connor_rob_hook_z_loader,  # type: ignore
}
