import argparse
import json
import os
import sys
import time
from contextlib import nullcontext
import torch

# Disable torch.compile / dynamo warnings on Windows where Triton is not installed
torch._dynamo.config.disable = True
torch._dynamo.config.suppress_errors = True

import outlines
from transformers import AutoModelForCausalLM, AutoTokenizer

from cpe_resolver import CPEDictionaryResolver, TOEExtraction
from generate_synthetic_dataset import SYSTEM_PROMPT


BANNER = """
================================================================================
   Qwen 2.5 3B + CPE Dictionary Resolver — Interactive TOE-to-CPE Shell
================================================================================
Commands:
  <any text>     Extract structured clauses & generate CPE 2.3 strings
  :model         Cycle model mode: [Fine-Tuned LoRA] -> [Baseline Zero-Shot] -> [Compare Both]
  :compare <txt> Run BOTH Baseline and Fine-Tuned side-by-side on <txt> (or last input)
  :mode          Toggle firmware mode: Decoupled vs. Model-Bound (`_firmware`)
  :json          Toggle displaying raw Qwen 2.5 3B JSON extraction (default: ON)
  :lookup <str>  Query the 142k CPE Dictionary directly for a product/vendor slug
  :sample        Run a random entry from `names.json` or `reverse_benchmark_dict.json`
  :help          Show this command list
  :q / exit      Quit interactive shell
================================================================================
"""


def load_switchable_model(base_model_id: str, lora_dir: str = None):
    """
    Loads the base model and attaches the PeftModel adapter WITHOUT merging (`merge_and_unload`),
    so we can dynamically toggle the LoRA adapter ON or OFF (`hf_model.disable_adapter()`)
    in zero extra VRAM!
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if (device == "cuda" and torch.cuda.is_bf16_supported()) else torch.float16

    print(f"[Init] Loading base model `{base_model_id}` on {device} ({dtype})...")
    tokenizer = AutoTokenizer.from_pretrained(
        lora_dir if (lora_dir and os.path.exists(lora_dir)) else base_model_id
    )
    hf_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=dtype,
        device_map="auto" if device == "cuda" else None,
    )

    has_lora = False
    if lora_dir and os.path.exists(lora_dir):
        from peft import PeftModel
        print(f"[Init] Attaching switchable LoRA adapter from `{lora_dir}` (zero extra VRAM toggle enabled)...")
        hf_model = PeftModel.from_pretrained(hf_model, lora_dir)
        has_lora = True
    else:
        print(f"[Warn] LoRA directory `{lora_dir}` not found; running in Baseline-only mode.")

    hf_model.eval()
    outlines_model = outlines.from_transformers(hf_model, tokenizer)
    return hf_model, outlines_model, has_lora


def run_single_extraction(
    hf_model,
    outlines_model,
    resolver: CPEDictionaryResolver,
    raw_text: str,
    use_lora: bool,
    has_lora: bool,
    attach_fw: bool,
):
    prompt = (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f'<|im_start|>user\nExtract from: "{raw_text}"<|im_end|>\n'
        f"<|im_start|>assistant\n"
    )

    ctx = hf_model.disable_adapter() if (has_lora and not use_lora) else nullcontext()
    t0 = time.time()
    with ctx:
        raw_json = outlines_model(prompt, TOEExtraction, max_new_tokens=1024)
    elapsed = time.time() - t0

    parsed = (
        TOEExtraction.model_validate_json(raw_json)
        if isinstance(raw_json, str)
        else raw_json
    )
    cpes = resolver.build_cpes_from_extraction(
        parsed,
        attach_shared_firmware_to_models=attach_fw,
        raw_source_text=raw_text,
    )
    return parsed, cpes, elapsed


def print_result(
    title_tag: str,
    raw_text: str,
    parsed: TOEExtraction,
    cpes: list,
    elapsed: float,
    show_json: bool = True,
    attach_fw: bool = False,
):
    print(f"\n{'=' * 80}")
    print(f"MODEL  : {title_tag}")
    print(f"INPUT  : {raw_text}")
    print(f"TIME   : {elapsed:.2f}s | FW MODE: {'Model-Bound (`_firmware`)' if attach_fw else 'Decoupled'}")
    print(f"{'-' * 80}")

    if show_json:
        print("[Stage 1: Structured Clause Extraction]")
        for c_idx, clause in enumerate(parsed.clauses, 1):
            print(f"  Clause #{c_idx}:")
            for t in clause.targets:
                v_str = t.vendor if t.vendor else "null"
                print(f"    [Target]    part={t.part} | vendor={v_str:15s} | product={t.product:28s} | ver={t.version}")
            for comp in clause.companions:
                v_str = comp.vendor if comp.vendor else "null"
                vers = ", ".join(comp.versions)
                print(f"    [Companion] part={comp.part} | vendor={v_str:15s} | product={comp.product:28s} | vers=[{vers}]")

    print(f"\n[Stage 2: Resolved CPE 2.3 Strings ({len(cpes)} total)]")
    for idx, item in enumerate(cpes, 1):
        print(f"  {idx:2d}. {item['short']:50s}  [{item['resolution']}]")
        print(f"      {item['cpe']}")
    print(f"{'=' * 80}")


def handle_direct_lookup(resolver: CPEDictionaryResolver, query: str):
    from cpe_resolver import slugify_cpe
    q_slug = slugify_cpe(query)
    print(f"\n[CPE Dictionary Lookup] Query: '{query}' -> slug: '{q_slug}'")

    if q_slug in resolver.product_to_vendors:
        print(f"  Exact Product Matches for '{q_slug}':")
        for v, p, cnt in resolver.product_to_vendors[q_slug]:
            print(f"    -> cpe:2.3:{p}:{v}:{q_slug}:*   ({cnt} versions in NVD)")
    else:
        print(f"  No exact product match for '{q_slug}'.")

    matches = []
    for prod, vp_list in resolver.product_to_vendors.items():
        if q_slug in prod:
            v, p, cnt = vp_list[0]
            matches.append((cnt, p, v, prod))
    matches.sort(reverse=True)
    if matches:
        print(f"  Top Product Substring Matches ({min(10, len(matches))} of {len(matches)}):")
        for cnt, p, v, prod in matches[:10]:
            print(f"    -> {p}:{v}:{prod:38s} ({cnt} NVD entries)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Interactive TOE-to-CPE Extraction Shell")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--lora_dir", type=str, default="checkpoints/qwen25_3b_cpe_lora")
    parser.add_argument(
        "--start_model",
        type=str,
        choices=["lora", "base", "compare"],
        default="lora",
        help="Initial model mode: 'lora' (fine-tuned), 'base' (zero-shot baseline), or 'compare' (run both side-by-side)",
    )
    parser.add_argument("--attach_fw_to_models", action="store_true")
    args = parser.parse_args()

    resolver = CPEDictionaryResolver()
    hf_model, outlines_model, has_lora = load_switchable_model(args.base_model, args.lora_dir)

    sample_pool = []
    for fn in ("data/benchmarks/names.json", "data/benchmarks/reverse_benchmark_dict.json"):
        if os.path.exists(fn):
            with open(fn, "r", encoding="utf-8") as f:
                sample_pool.extend(json.load(f))

    show_json = True
    attach_fw = args.attach_fw_to_models
    model_mode = args.start_model if has_lora else "base"
    last_input = None

    print(BANNER)
    print(f"[Active Mode] Model: {model_mode.upper()} | Firmware: {'Model-Bound' if attach_fw else 'Decoupled'}\n")

    while True:
        try:
            user_in = input(f"TOE [{model_mode.upper()}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_in:
            continue

        if user_in.lower() in (":q", ":quit", "exit", "quit"):
            print("Exiting.")
            break

        if user_in.lower() == ":help":
            print(BANNER)
            continue

        if user_in.lower() == ":json":
            show_json = not show_json
            print(f"[Config] Show Stage 1 JSON extraction: {'ON' if show_json else 'OFF'}")
            continue

        if user_in.lower() == ":mode":
            attach_fw = not attach_fw
            mode_label = (
                "Model-Bound (`o:vendor:model_firmware:ver`)"
                if attach_fw
                else "Decoupled (`h:vendor:model:-` + `o:vendor:fw:ver`)"
            )
            print(f"[Config] Firmware attachment mode switched to: {mode_label}")
            continue

        if user_in.lower() in (":model", ":base", ":lora"):
            if not has_lora:
                print("[Warn] No LoRA adapter loaded; only BASE mode is available.")
                continue
            if user_in.lower() == ":base":
                model_mode = "base"
            elif user_in.lower() == ":lora":
                model_mode = "lora"
            else:
                cycle = {"lora": "base", "base": "compare", "compare": "lora"}
                model_mode = cycle[model_mode]
            print(f"[Config] Switched model mode to: {model_mode.upper()}")
            continue

        if user_in.lower().startswith(":lookup "):
            q = user_in[8:].strip()
            if q:
                handle_direct_lookup(resolver, q)
            continue

        run_comparison_once = False
        if user_in.lower() == ":compare" or user_in.lower().startswith(":compare "):
            comp_arg = user_in[8:].strip()
            if comp_arg:
                user_in = comp_arg
            elif last_input:
                user_in = last_input
                print(f"[Compare on Last Input] {user_in}")
            else:
                print("[Warn] Provide text after `:compare <text>` or run an input first.")
                continue
            run_comparison_once = True

        if user_in.lower() == ":sample":
            if not sample_pool:
                print("[Warn] No sample files found.")
                continue
            import random
            user_in = random.choice(sample_pool)
            print(f"[Sampled] {user_in}")

        last_input = user_in
        effective_mode = "compare" if run_comparison_once else model_mode

        try:
            if effective_mode == "compare" and has_lora:
                # 1. Run Baseline (LoRA disabled)
                b_parsed, b_cpes, b_time = run_single_extraction(
                    hf_model, outlines_model, resolver, user_in,
                    use_lora=False, has_lora=has_lora, attach_fw=attach_fw
                )
                print_result(
                    "BASELINE (Zero-Shot Qwen2.5-3B-Instruct)",
                    user_in, b_parsed, b_cpes, b_time, show_json=show_json, attach_fw=attach_fw
                )

                # 2. Run Fine-Tuned (LoRA enabled)
                ft_parsed, ft_cpes, ft_time = run_single_extraction(
                    hf_model, outlines_model, resolver, user_in,
                    use_lora=True, has_lora=has_lora, attach_fw=attach_fw
                )
                print_result(
                    f"FINE-TUNED (LoRA: {args.lora_dir})",
                    user_in, ft_parsed, ft_cpes, ft_time, show_json=show_json, attach_fw=attach_fw
                )

                # Print quick diff summary
                b_set = {c["short"] for c in b_cpes}
                ft_set = {c["short"] for c in ft_cpes}
                print(f"\n[Comparison Diff Summary]")
                print(f"  Baseline CPE count  : {len(b_cpes)}")
                print(f"  Fine-Tuned CPE count: {len(ft_cpes)}")
                if b_set == ft_set:
                    print("  Status              : IDENTICAL output")
                else:
                    only_b = b_set - ft_set
                    only_ft = ft_set - b_set
                    if only_b:
                        print("  Only in Baseline    : " + ", ".join(sorted(only_b)))
                    if only_ft:
                        print("  Added by Fine-Tuned : " + ", ".join(sorted(only_ft)))
                print()

            elif effective_mode == "base" or not has_lora:
                b_parsed, b_cpes, b_time = run_single_extraction(
                    hf_model, outlines_model, resolver, user_in,
                    use_lora=False, has_lora=has_lora, attach_fw=attach_fw
                )
                print_result(
                    "BASELINE (Zero-Shot Qwen2.5-3B-Instruct)",
                    user_in, b_parsed, b_cpes, b_time, show_json=show_json, attach_fw=attach_fw
                )
            else:
                ft_parsed, ft_cpes, ft_time = run_single_extraction(
                    hf_model, outlines_model, resolver, user_in,
                    use_lora=True, has_lora=has_lora, attach_fw=attach_fw
                )
                print_result(
                    f"FINE-TUNED (LoRA: {args.lora_dir})",
                    user_in, ft_parsed, ft_cpes, ft_time, show_json=show_json, attach_fw=attach_fw
                )

        except Exception as e:
            print(f"[Error] Failed to process input: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
